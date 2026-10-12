"""
CIVICLENS TN — Phase 8.8 Civic Issue Intelligence REST API Router.
==================================================================

Endpoints:
- GET  /api/civic/issues                         List & search civic issues with multi-attribute filters
- GET  /api/civic/issues/<issue_id>              Full issue details, department, area, metrics, cross-phase links
- GET  /api/civic/categories                     List canonical categories with SLA standards and issue counts
- GET  /api/civic/areas                          List administrative areas with population context
- GET  /api/civic/departments                    List departments with docket counts and resolution stats
- GET  /api/civic/departments/<dept_id>/summary  Detailed department performance summary & SLA compliance
- GET  /api/civic/issues/<issue_id>/responses    Response history and action-taken reports
- GET  /api/civic/issues/<issue_id>/evidence     Resolution evidence artifacts (empirical proof)
- GET  /api/civic/clusters                       Recurring issue hotspots by area and category
- GET  /api/civic/analytics/trends               Trend analytics across 10 core metrics with guarded anomaly detection
- GET  /api/civic/source-documents               Statutory gazettes, council proceedings, portal data dumps
- GET  /api/civic/issues/<issue_id>/source-documents Source documents linked to an issue
- POST /api/civic/issues/<issue_id>/cross-phase-link Register documented link to Phase 1-7 entities
- GET  /api/civic/issues/<issue_id>/cross-phase  Resolved cross-phase relationships for an issue

Strict Principles:
- PII scrubbing on all grievance and complaint summaries (DPDPA 2023 compliance).
- No causal links assumed merely because records share a geographic area.
- All cross-phase linkages must provide documented matching methods and provenance summaries.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from flask import Blueprint, request
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from backend.api.responses import error_response, success_response
from backend.database.session import SessionLocal
from backend.models.civic_issue import (
    AdministrativeArea,
    CivicCrossPhaseLink,
    CivicDepartment,
    CivicIssue,
    CivicIssueSeverity,
    CivicIssueStatus,
    DataQualityIssue,
    GrievanceRecord,
    IssueCategory,
    IssueCategoryEnum,
    IssueEvent,
    IssueMetric,
    PublicWork,
    ResolutionEvidence,
    ResponseRecord,
    ServiceStandard,
    SourceDocument,
)
from backend.services.civic_analytics_service import CivicAnalyticsEngine

logger = logging.getLogger(__name__)

civic_bp = Blueprint("civic", __name__, url_prefix="/civic")


# ---------------------------------------------------------------------------
# Helper: Cross-Phase Entity Resolver
# ---------------------------------------------------------------------------
def resolve_civic_cross_phase_entities(db: Session, links: List[CivicCrossPhaseLink]) -> List[Dict[str, Any]]:
    """
    Resolves linked entities from Phases 1-7 via stable identifiers
    without copying datasets across databases.
    """
    resolved_links: List[Dict[str, Any]] = []

    for link in links:
        link_dict = link.to_dict()
        entity_payload: Optional[Dict[str, Any]] = None

        try:
            # Phase 1-2: Historical Scheme / Budget
            if link.target_phase == "PHASE_1_2_BUDGET_SCHEME" or link.entity_type in {"HISTORICAL_SCHEME", "BUDGET_SCHEME"}:
                if link.entity_type == "HISTORICAL_SCHEME":
                    from backend.models.budget import HistoricalScheme
                    scheme_id = int(link.entity_id) if str(link.entity_id).isdigit() else link.entity_id
                    hs = db.query(HistoricalScheme).filter(HistoricalScheme.id == scheme_id).first()
                    if hs:
                        entity_payload = {
                            "id": hs.id,
                            "scheme_name": hs.scheme_name,
                            "financial_year": hs.financial_year,
                            "department": hs.department.name if hs.department else None,
                            "objectives": hs.objectives,
                        }
                elif link.entity_type == "BUDGET_SCHEME":
                    from backend.models.budget import BudgetScheme
                    scheme_id = int(link.entity_id) if str(link.entity_id).isdigit() else link.entity_id
                    bs = db.query(BudgetScheme).filter(BudgetScheme.id == scheme_id).first()
                    if bs:
                        entity_payload = {
                            "id": bs.id,
                            "name": bs.name,
                            "department_id": bs.department_id,
                        }

            # Phase 3: Political Promise
            elif link.target_phase == "PHASE_3_PROMISE" or link.entity_type == "POLITICAL_PROMISE":
                from backend.models.promise import PoliticalPromise
                p = db.query(PoliticalPromise).filter(PoliticalPromise.promise_id == link.entity_id).first()
                if p:
                    entity_payload = {
                        "promise_id": p.promise_id,
                        "original_text": p.original_text,
                        "classification": p.classification,
                        "manifesto_id": p.manifesto_id,
                    }

            # Phase 4: News Article
            elif link.target_phase == "PHASE_4_NEWS" or link.entity_type in {"NEWS_ARTICLE", "ARTICLE"}:
                from backend.models.news import Article
                art = db.query(Article).filter(Article.article_id == link.entity_id).first()
                if art:
                    entity_payload = {
                        "article_id": art.article_id,
                        "title": art.title,
                        "url": art.url,
                        "source_name": art.source.source_name if art.source else None,
                        "publication_date": art.publication_date.isoformat() if art.publication_date else None,
                    }

            # Phase 5: Financial Document
            elif link.target_phase == "PHASE_5_FUNDING" or link.entity_type == "FINANCIAL_DOCUMENT":
                from backend.models.funding import FinancialDocument
                fd = db.query(FinancialDocument).filter(FinancialDocument.document_id == link.entity_id).first()
                if fd:
                    entity_payload = {
                        "document_id": fd.document_id,
                        "financial_year": fd.financial_year,
                        "filing_type": fd.filing_type,
                        "source_url": fd.source_url,
                    }

            # Phase 6: Representative & Constituency
            elif link.target_phase in {"PHASE_6_REPRESENTATIVE", "PHASE_6_CONSTITUENCY"} or link.entity_type in {"REPRESENTATIVE", "CONSTITUENCY"}:
                if link.entity_type == "REPRESENTATIVE":
                    from backend.models.representative import Representative
                    rep = db.query(Representative).filter(Representative.representative_id == link.entity_id).first()
                    if rep:
                        entity_payload = {
                            "representative_id": rep.representative_id,
                            "official_name": rep.official_name,
                            "representative_type": rep.representative_type,
                            "party_id": rep.party_id,
                            "constituency_id": rep.constituency_id,
                        }
                elif link.entity_type == "CONSTITUENCY":
                    from backend.models.representative import Constituency
                    con = db.query(Constituency).filter(Constituency.constituency_id == link.entity_id).first()
                    if con:
                        entity_payload = {
                            "constituency_id": con.constituency_id,
                            "official_name": getattr(con, "official_name", None) or getattr(con, "name", None),
                            "constituency_type": con.constituency_type.value if hasattr(con.constituency_type, "value") else str(con.constituency_type),
                            "district": getattr(con, "district", None),
                        }

            # Phase 7: Claim
            elif link.target_phase == "PHASE_7_CLAIM" or link.entity_type == "CLAIM":
                from backend.models.claim import Claim
                cl = db.query(Claim).filter(Claim.claim_id == link.entity_id).first()
                if cl:
                    claim_cat = getattr(cl, "claim_category", None) or getattr(cl, "category", None)
                    entity_payload = {
                        "claim_id": cl.claim_id,
                        "canonical_text": getattr(cl, "original_text", None) or getattr(cl, "canonical_text", ""),
                        "category": claim_cat.value if hasattr(claim_cat, "value") else str(claim_cat),
                        "status": cl.status.value if hasattr(cl.status, "value") else str(cl.status),
                    }
        except Exception as e:
            logger.warning(f"Could not resolve cross-phase link {link.entity_type}:{link.entity_id}: {e}")
            entity_payload = None

        link_dict["resolved_entity"] = entity_payload
        resolved_links.append(link_dict)

    return resolved_links


# ---------------------------------------------------------------------------
# 1. GET /api/civic/issues (Issue Search & Multi-Attribute Filtering)
# ---------------------------------------------------------------------------
@civic_bp.route("/issues", methods=["GET"])
def search_civic_issues():
    """
    Searches and filters civic issues across categories, areas, departments,
    statuses, and date intervals with pagination.
    """
    db: Session = SessionLocal()
    try:
        query = db.query(CivicIssue)

        # Keyword Search
        q_text = request.args.get("q")
        if q_text and q_text.strip():
            term = f"%{q_text.strip()}%"
            query = query.filter(
                or_(
                    CivicIssue.title.ilike(term),
                    CivicIssue.description.ilike(term),
                    CivicIssue.title_ta.ilike(term),
                    CivicIssue.issue_code.ilike(term),
                )
            )

        # Category Filter
        category_param = request.args.get("category")
        if category_param:
            cat_obj = db.query(IssueCategory).filter(
                or_(
                    IssueCategory.code == category_param.lower(),
                    IssueCategory.name_en.ilike(category_param),
                )
            ).first()
            if cat_obj:
                query = query.filter(CivicIssue.category_id == cat_obj.id)

        # Administrative Area Filter
        area_param = request.args.get("area_id")
        if area_param:
            area_obj = db.query(AdministrativeArea).filter(
                or_(
                    AdministrativeArea.area_code == area_param,
                    AdministrativeArea.name_en.ilike(area_param),
                    AdministrativeArea.id == int(area_param) if area_param.isdigit() else False,
                )
            ).first()
            if area_obj:
                query = query.filter(CivicIssue.administrative_area_id == area_obj.id)

        # Department Filter
        dept_param = request.args.get("department_id")
        if dept_param:
            dept_obj = db.query(CivicDepartment).filter(
                or_(
                    CivicDepartment.code == dept_param,
                    CivicDepartment.name_en.ilike(dept_param),
                    CivicDepartment.id == int(dept_param) if dept_param.isdigit() else False,
                )
            ).first()
            if dept_obj:
                query = query.filter(CivicIssue.department_id == dept_obj.id)

        # Status Filter
        status_param = request.args.get("status")
        if status_param:
            try:
                status_enum = CivicIssueStatus(status_param.upper())
                query = query.filter(CivicIssue.status == status_enum)
            except ValueError:
                pass

        # Severity Filter
        severity_param = request.args.get("severity")
        if severity_param:
            try:
                severity_enum = CivicIssueSeverity(severity_param.upper())
                query = query.filter(CivicIssue.severity == severity_enum)
            except ValueError:
                pass

        # Recurring Filter
        is_recurring = request.args.get("is_recurring")
        if is_recurring is not None:
            if is_recurring.lower() in {"true", "1"}:
                query = query.filter(CivicIssue.repeat_count > 1)
            elif is_recurring.lower() in {"false", "0"}:
                query = query.filter(CivicIssue.repeat_count <= 1)

        # Date Range Filter
        start_date = request.args.get("start_date")
        if start_date:
            try:
                s_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                query = query.filter(CivicIssue.reported_date >= s_dt)
            except Exception:
                pass

        end_date = request.args.get("end_date")
        if end_date:
            try:
                e_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                query = query.filter(CivicIssue.reported_date <= e_dt)
            except Exception:
                pass

        total_count = query.count()

        # Pagination
        page = max(1, request.args.get("page", 1, type=int))
        per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))
        offset = (page - 1) * per_page

        issues = query.order_by(desc(CivicIssue.reported_date)).offset(offset).limit(per_page).all()

        results = [issue.to_dict() for issue in issues]

        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

        return success_response(
            data={
                "issues": results,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total_count,
                    "total_pages": total_pages,
                },
            },
            message="Civic issues retrieved successfully.",
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 2. GET /api/civic/issues/<issue_id> (Issue Details)
# ---------------------------------------------------------------------------
@civic_bp.route("/issues/<issue_id>", methods=["GET"])
def get_civic_issue_details(issue_id: str):
    """
    Retrieves full details of a specific civic issue, including category,
    department, administrative area, SLA standards, public works, metrics,
    and cross-phase links.
    """
    db: Session = SessionLocal()
    try:
        # Match by integer id or string issue_code
        issue = None
        if issue_id.isdigit():
            issue = db.query(CivicIssue).filter(CivicIssue.id == int(issue_id)).first()
        if not issue:
            issue = db.query(CivicIssue).filter(CivicIssue.issue_code == issue_id).first()

        if not issue:
            return error_response(message=f"Civic issue '{issue_id}' not found.", status_code=404)

        data = issue.to_dict()

        # Category
        data["category"] = issue.category.to_dict() if issue.category else None

        # Department
        data["department"] = issue.department.to_dict() if issue.department else None

        # Administrative Area
        data["administrative_area"] = issue.administrative_area.to_dict() if issue.administrative_area else None

        # Service Standard (SLA)
        sla = None
        if issue.department_id and issue.category_id:
            std = (
                db.query(ServiceStandard)
                .filter(
                    ServiceStandard.department_id == issue.department_id,
                    ServiceStandard.category_id == issue.category_id,
                )
                .first()
            )
            if std:
                sla = std.to_dict()
        data["service_standard"] = sla

        # Counts
        data["responses_count"] = len(issue.responses) if issue.responses else 0
        data["grievance_records_count"] = len(issue.grievance_records) if issue.grievance_records else 0
        data["public_works_count"] = len(issue.public_works) if issue.public_works else 0

        # Public Works linked
        data["public_works"] = [pw.to_dict() for pw in issue.public_works] if issue.public_works else []

        # Data quality issues
        data["quality_issues"] = [qi.to_dict() for qi in issue.quality_issues] if issue.quality_issues else []

        # Cross-phase links with resolved entities
        cross_links = resolve_civic_cross_phase_entities(db, issue.cross_phase_links or [])
        data["cross_phase_links"] = cross_links

        return success_response(data=data, message="Civic issue details retrieved.")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 3. GET /api/civic/categories (Issue Categories & Service Standards)
# ---------------------------------------------------------------------------
@civic_bp.route("/categories", methods=["GET"])
def get_issue_categories():
    """
    Returns all canonical civic issue categories with descriptions,
    default department routing, priority weights, and active issue counts.
    """
    db: Session = SessionLocal()
    try:
        categories = db.query(IssueCategory).order_by(IssueCategory.name_en).all()
        results = []

        for cat in categories:
            cat_dict = cat.to_dict()
            issue_count = db.query(func.count(CivicIssue.id)).filter(CivicIssue.category_id == cat.id).scalar() or 0
            cat_dict["active_issues_count"] = issue_count

            # Service standards for this category
            standards = db.query(ServiceStandard).filter(ServiceStandard.category_id == cat.id).all()
            cat_dict["service_standards"] = [s.to_dict() for s in standards]
            results.append(cat_dict)

        return success_response(data={"categories": results}, message="Civic issue categories retrieved.")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 4. GET /api/civic/areas (Administrative Areas)
# ---------------------------------------------------------------------------
@civic_bp.route("/areas", methods=["GET"])
def get_administrative_areas():
    """
    Returns administrative jurisdictions in Tamil Nadu with population context,
    LGD codes, and active issue counts.
    """
    db: Session = SessionLocal()
    try:
        query = db.query(AdministrativeArea)

        level = request.args.get("level")
        if level:
            query = query.filter(AdministrativeArea.administrative_level == level.upper())

        parent_id = request.args.get("parent_id")
        if parent_id and parent_id.isdigit():
            query = query.filter(AdministrativeArea.parent_id == int(parent_id))

        q_name = request.args.get("q")
        if q_name and q_name.strip():
            term = f"%{q_name.strip()}%"
            query = query.filter(
                or_(
                    AdministrativeArea.name_en.ilike(term),
                    AdministrativeArea.name_ta.ilike(term),
                    AdministrativeArea.area_code.ilike(term),
                )
            )

        areas = query.order_by(AdministrativeArea.name_en).all()
        results = []

        for area in areas:
            area_dict = area.to_dict()
            issue_count = db.query(func.count(CivicIssue.id)).filter(CivicIssue.administrative_area_id == area.id).scalar() or 0
            area_dict["active_issues_count"] = issue_count
            results.append(area_dict)

        return success_response(data={"areas": results}, message="Administrative areas retrieved.")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 5. GET /api/civic/departments (Department Summaries)
# ---------------------------------------------------------------------------
@civic_bp.route("/departments", methods=["GET"])
def get_civic_departments():
    """
    Returns departments and local body directorates with assigned issue counts
    and contact details.
    """
    db: Session = SessionLocal()
    try:
        departments = db.query(CivicDepartment).order_by(CivicDepartment.name_en).all()
        results = []

        for dept in departments:
            dept_dict = dept.to_dict()
            issue_count = db.query(func.count(CivicIssue.id)).filter(CivicIssue.department_id == dept.id).scalar() or 0
            dept_dict["total_assigned_issues"] = issue_count
            results.append(dept_dict)

        return success_response(data={"departments": results}, message="Civic departments retrieved.")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 6. GET /api/civic/departments/<dept_id>/summary (Specific Department Summary)
# ---------------------------------------------------------------------------
@civic_bp.route("/departments/<dept_id>/summary", methods=["GET"])
def get_department_performance_summary(dept_id: str):
    """
    Returns a detailed performance summary for a specific department:
    total dockets, open, under review, marked resolved, verified resolved,
    SLA compliance rate, and statutory turnaround limits.
    """
    db: Session = SessionLocal()
    try:
        dept = None
        if dept_id.isdigit():
            dept = db.query(CivicDepartment).filter(CivicDepartment.id == int(dept_id)).first()
        if not dept:
            dept = db.query(CivicDepartment).filter(CivicDepartment.code == dept_id).first()

        if not dept:
            return error_response(message=f"Department '{dept_id}' not found.", status_code=404)

        issues = db.query(CivicIssue).filter(CivicIssue.department_id == dept.id).all()
        total_issues = len(issues)

        open_count = sum(1 for i in issues if i.status == CivicIssueStatus.OPEN)
        under_review_count = sum(1 for i in issues if i.status == CivicIssueStatus.IN_PROGRESS)
        marked_resolved_count = sum(1 for i in issues if i.status == CivicIssueStatus.RESOLVED)
        disputed_count = sum(1 for i in issues if i.status == CivicIssueStatus.DISPUTED)

        # Resolution times & SLA breaches
        resolved_issues = [i for i in issues if i.actual_resolution_date and i.reported_date]
        resolution_days = [(i.actual_resolution_date - i.reported_date).total_seconds() / 86400.0 for i in resolved_issues]
        avg_res_days = round(sum(resolution_days) / len(resolution_days), 2) if resolution_days else None

        # Check responses SLA breaches
        responses = db.query(ResponseRecord).filter(ResponseRecord.department_id == dept.id).all()
        total_resp = len(responses)
        breached_resp = sum(1 for r in responses if r.is_sla_breached)
        sla_compliance_rate = round(((total_resp - breached_resp) / total_resp) * 100, 2) if total_resp > 0 else 100.0

        summary = {
            "department": dept.to_dict(),
            "total_assigned_issues": total_issues,
            "status_breakdown": {
                "open": open_count,
                "under_review": under_review_count,
                "marked_resolved": marked_resolved_count,
                "disputed": disputed_count,
            },
            "average_resolution_days": avg_res_days,
            "sla_compliance_percentage": sla_compliance_rate,
            "total_responses_logged": total_resp,
            "sla_breaches_count": breached_resp,
            "service_standards": [s.to_dict() for s in dept.service_standards],
        }

        return success_response(data=summary, message=f"Department summary for '{dept.name_en}' retrieved.")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 7. GET /api/civic/issues/<issue_id>/responses (Response History)
# ---------------------------------------------------------------------------
@civic_bp.route("/issues/<issue_id>/responses", methods=["GET"])
def get_issue_response_history(issue_id: str):
    """
    Returns the complete chronological response history, action-taken reports,
    and state transitions for a specific issue.
    """
    db: Session = SessionLocal()
    try:
        issue = None
        if issue_id.isdigit():
            issue = db.query(CivicIssue).filter(CivicIssue.id == int(issue_id)).first()
        if not issue:
            issue = db.query(CivicIssue).filter(CivicIssue.issue_code == issue_id).first()

        if not issue:
            return error_response(message=f"Civic issue '{issue_id}' not found.", status_code=404)

        responses = (
            db.query(ResponseRecord)
            .filter(ResponseRecord.civic_issue_id == issue.id)
            .order_by(ResponseRecord.action_taken_date.asc())
            .all()
        )
        events = (
            db.query(IssueEvent)
            .filter(IssueEvent.civic_issue_id == issue.id)
            .order_by(IssueEvent.event_timestamp.asc())
            .all()
        )

        return success_response(
            data={
                "issue_id": issue.id,
                "issue_code": issue.issue_code,
                "responses": [r.to_dict() for r in responses],
                "events": [e.to_dict() for e in events],
            },
            message="Response history retrieved.",
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 8. GET /api/civic/issues/<issue_id>/evidence (Resolution Evidence)
# ---------------------------------------------------------------------------
@civic_bp.route("/issues/<issue_id>/evidence", methods=["GET"])
def get_issue_resolution_evidence(issue_id: str):
    """
    Returns empirical evidence artifacts supporting or refuting resolution claims
    (e.g., work orders, completion certificates, site verification).
    """
    db: Session = SessionLocal()
    try:
        issue = None
        if issue_id.isdigit():
            issue = db.query(CivicIssue).filter(CivicIssue.id == int(issue_id)).first()
        if not issue:
            issue = db.query(CivicIssue).filter(CivicIssue.issue_code == issue_id).first()

        if not issue:
            return error_response(message=f"Civic issue '{issue_id}' not found.", status_code=404)

        response_ids = [r.id for r in issue.responses] if issue.responses else []
        evidences = []
        if response_ids:
            evidences = db.query(ResolutionEvidence).filter(ResolutionEvidence.response_id.in_(response_ids)).all()

        return success_response(
            data={
                "issue_id": issue.id,
                "issue_code": issue.issue_code,
                "resolution_verification_status": issue.resolution_verification_status.value,
                "evidence_count": len(evidences),
                "evidences": [e.to_dict() for e in evidences],
            },
            message="Resolution evidence retrieved.",
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 9. GET /api/civic/clusters (Recurring Issue Clusters & Hotspots)
# ---------------------------------------------------------------------------
@civic_bp.route("/clusters", methods=["GET"])
def get_recurring_clusters():
    """
    Identifies and returns recurring issue hotspots aggregated by administrative
    area and category.
    """
    db: Session = SessionLocal()
    try:
        engine = CivicAnalyticsEngine(default_source="VALIDATED_CIVIC_RECORDS")
        issues = db.query(CivicIssue).all()

        clusters_metric = engine.calculate_recurring_clusters(issues, period="ALL_TIME")

        return success_response(
            data={
                "recurring_records_count": clusters_metric.distribution.get("recurring_records_count", 0),
                "recurrence_rate_pct": clusters_metric.distribution.get("recurrence_rate_pct", 0.0),
                "hotspot_clusters_count": clusters_metric.distribution.get("hotspot_clusters_count", 0),
                "top_hotspots": clusters_metric.distribution.get("top_hotspots", {}),
                "caveats": clusters_metric.caveats,
            },
            message="Recurring issue clusters retrieved.",
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 10. GET /api/civic/analytics/trends (Trend Analytics & Core 10 Metrics)
# ---------------------------------------------------------------------------
@civic_bp.route("/analytics/trends", methods=["GET"])
def get_civic_trend_analytics():
    """
    Executes the CivicAnalyticsEngine across validated records, providing
    time-series aggregations, category counts, turnaround times, and guarded
    statistical anomaly detection.
    """
    db: Session = SessionLocal()
    try:
        period = request.args.get("period", "ALL_TIME")
        data_source = request.args.get("data_source", "VALIDATED_CIVIC_RECORDS")

        # Load areas and population map
        areas = db.query(AdministrativeArea).all()
        pop_map = {a.area_code: a.population for a in areas if a.population}

        issues = db.query(CivicIssue).all()
        engine = CivicAnalyticsEngine(default_source=data_source)

        report = engine.generate_comprehensive_report(
            records=issues,
            period=period,
            data_source=data_source,
            population_map=pop_map,
        )

        metrics_dict = {k: v.__dict__ for k, v in report.metrics.items()}
        anomaly_dict = report.anomaly_detection.__dict__ if report.anomaly_detection else None

        return success_response(
            data={
                "reporting_period": report.reporting_period,
                "data_source": report.data_source,
                "total_records": report.total_records,
                "metrics": metrics_dict,
                "anomaly_detection": anomaly_dict,
                "general_disclaimer": report.general_disclaimer,
            },
            message="Civic trend analytics computed successfully.",
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 11. GET /api/civic/source-documents (Statutory Source Documents)
# ---------------------------------------------------------------------------
@civic_bp.route("/source-documents", methods=["GET"])
def get_source_documents():
    """
    Returns official gazettes, government orders, and portal report documents
    with SHA256 checksums and source tiers.
    """
    db: Session = SessionLocal()
    try:
        docs = db.query(SourceDocument).order_by(desc(SourceDocument.published_date)).all()
        return success_response(
            data={"source_documents": [d.to_dict() for d in docs]},
            message="Source documents retrieved.",
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 12. GET /api/civic/issues/<issue_id>/source-documents
# ---------------------------------------------------------------------------
@civic_bp.route("/issues/<issue_id>/source-documents", methods=["GET"])
def get_issue_source_documents(issue_id: str):
    """
    Returns source documents directly connected to a specific civic issue,
    its underlying petitions, or official responses.
    """
    db: Session = SessionLocal()
    try:
        issue = None
        if issue_id.isdigit():
            issue = db.query(CivicIssue).filter(CivicIssue.id == int(issue_id)).first()
        if not issue:
            issue = db.query(CivicIssue).filter(CivicIssue.issue_code == issue_id).first()

        if not issue:
            return error_response(message=f"Civic issue '{issue_id}' not found.", status_code=404)

        doc_ids = set()
        for g in issue.grievance_records:
            if g.source_document_id:
                doc_ids.add(g.source_document_id)
        for r in issue.responses:
            if getattr(r, "source_document_id", None):
                doc_ids.add(r.source_document_id)

        docs = []
        if doc_ids:
            docs = db.query(SourceDocument).filter(SourceDocument.id.in_(doc_ids)).all()

        return success_response(
            data={"source_documents": [d.to_dict() for d in docs]},
            message="Issue source documents retrieved.",
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 13. POST /api/civic/issues/<issue_id>/cross-phase-link
# ---------------------------------------------------------------------------
@civic_bp.route("/issues/<issue_id>/cross-phase-link", methods=["POST"])
def create_cross_phase_link(issue_id: str):
    """
    Explicitly registers a cross-phase relationship connecting a CivicIssue
    to an entity from Phases 1-7.

    STRICT ANTI-CAUSALITY GUARD:
    Rejects superficial links created solely because records share a geographic area.
    Every relationship requires a documented matching method and provenance summary.
    """
    db: Session = SessionLocal()
    try:
        issue = None
        if issue_id.isdigit():
            issue = db.query(CivicIssue).filter(CivicIssue.id == int(issue_id)).first()
        if not issue:
            issue = db.query(CivicIssue).filter(CivicIssue.issue_code == issue_id).first()

        if not issue:
            return error_response(message=f"Civic issue '{issue_id}' not found.", status_code=404)

        payload = request.get_json(silent=True) or {}

        target_phase = payload.get("target_phase")
        entity_type = payload.get("entity_type")
        entity_id = payload.get("entity_id")
        relationship_nature = payload.get("relationship_nature")
        matching_method = payload.get("matching_method")
        provenance_summary = payload.get("provenance_summary")
        confidence = float(payload.get("confidence", 1.0))
        extra_metadata = payload.get("extra_metadata", {})

        # Validation
        if not all([target_phase, entity_type, entity_id, relationship_nature, matching_method, provenance_summary]):
            return error_response(
                message="Missing required fields: target_phase, entity_type, entity_id, relationship_nature, matching_method, provenance_summary.",
                status_code=400,
            )

        # STRICT GUARD: Disallow causal links purely based on shared geographic area
        forbidden_methods = {"same_area", "same_district", "geographic_proximity_only", "co_located_only"}
        if matching_method.strip().lower() in forbidden_methods:
            return error_response(
                message=(
                    "Invalid cross-phase relationship: Cannot create cross-phase links merely because "
                    "records share a geographic area without explicit empirical connection (e.g. tender reference, "
                    "scheme sanction, constituency attribution, or news citation)."
                ),
                status_code=400,
            )

        link_id = f"CPL-{uuid.uuid4().hex[:12].upper()}"

        link = CivicCrossPhaseLink(
            link_id=link_id,
            civic_issue_id=issue.id,
            target_phase=target_phase,
            entity_type=entity_type,
            entity_id=str(entity_id),
            relationship_nature=relationship_nature,
            matching_method=matching_method,
            confidence=confidence,
            provenance_summary=provenance_summary,
            extra_metadata=extra_metadata,
            is_test_fixture=bool(payload.get("is_test_fixture", False)),
        )

        db.add(link)
        db.commit()
        db.refresh(link)

        return success_response(
            data=link.to_dict(),
            message="Cross-phase relationship established with explicit provenance.",
            status_code=201,
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 14. GET /api/civic/issues/<issue_id>/cross-phase
# ---------------------------------------------------------------------------
@civic_bp.route("/issues/<issue_id>/cross-phase", methods=["GET"])
def get_issue_cross_phase_links(issue_id: str):
    """
    Returns all documented cross-phase relationships for an issue,
    with resolved entity payloads from Phases 1-7.
    """
    db: Session = SessionLocal()
    try:
        issue = None
        if issue_id.isdigit():
            issue = db.query(CivicIssue).filter(CivicIssue.id == int(issue_id)).first()
        if not issue:
            issue = db.query(CivicIssue).filter(CivicIssue.issue_code == issue_id).first()

        if not issue:
            return error_response(message=f"Civic issue '{issue_id}' not found.", status_code=404)

        links = db.query(CivicCrossPhaseLink).filter(CivicCrossPhaseLink.civic_issue_id == issue.id).all()
        resolved_links = resolve_civic_cross_phase_entities(db, links)

        return success_response(
            data={
                "issue_id": issue.id,
                "issue_code": issue.issue_code,
                "cross_phase_links_count": len(resolved_links),
                "cross_phase_links": resolved_links,
            },
            message="Cross-phase relationships retrieved.",
        )
    finally:
        db.close()
