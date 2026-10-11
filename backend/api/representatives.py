"""
Phase 6 — Public Representative, Constituency & Performance API Blueprint.

Provides RESTful endpoints for:
1. Representative search & filtering (by type, party, constituency, term).
2. Representative detailed profile.
3. Constituency lookup & profiles.
4. Legislative activity breakdown (questions, debates, attendance).
5. Constituency works tracking (MPLADS / MLACDS status, expenditure, attribution).
6. Development indicator trends & baseline trajectories.
7. Political promise cross-references & evidence stages.
8. Performance metrics & within-cohort comparative analysis.
9. Data completeness index & audit provenance.
10. Source documents and data quality review.
"""

import logging
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from backend.database.session import SessionLocal
from backend.api.responses import success_response, error_response
from backend.models.representative import (
    Representative,
    Constituency,
    Election,
    RepresentativeTerm,
    LegislativeActivity,
    ConstituencyWork,
    DevelopmentIndicator,
    ConstituencyGeographicMapping,
    PromisePerformanceLink,
    PerformanceMetric,
    PerformanceDimension,
    RepresentativeType,
    WorkProjectStatus,
    AttributionType,
    PromiseEvidenceStage
)
from backend.models.news import PoliticalParty
from backend.services.performance_metrics import (
    PerformanceMetricsEngine,
    IncompatibleCohortError
)
from backend.services.promise_cross_reference import PromiseCrossReferenceService

logger = logging.getLogger("civiclens.api.representatives")

representatives_bp = Blueprint("representatives", __name__, url_prefix="/representatives")


def _get_db():
    return SessionLocal()


# ---------------------------------------------------------------------------
# 1. REPRESENTATIVE EXPLORER & SEARCH
# ---------------------------------------------------------------------------
@representatives_bp.route("/", methods=["GET"])
@representatives_bp.route("/search", methods=["GET"])
def search_representatives():
    """
    Search and filter representatives by query string, type, party, constituency, and term.
    """
    db: Session = _get_db()
    try:
        q = request.args.get("q", "").strip()
        rep_type = request.args.get("type", "").strip()
        party_id = request.args.get("party_id", "").strip()
        constituency_id = request.args.get("constituency_id", "").strip()
        active_only = request.args.get("active_only", "false").lower() == "true"

        query = db.query(Representative)

        if q:
            query = query.filter(
                or_(
                    Representative.official_name.ilike(f"%{q}%"),
                    Representative.representative_id.ilike(f"%{q}%")
                )
            )

        if rep_type and rep_type != "All":
            query = query.filter(Representative.representative_type == rep_type)

        if party_id and party_id != "All":
            query = query.filter(Representative.party_id == party_id)

        if constituency_id and constituency_id != "All":
            query = query.filter(Representative.constituency_id == constituency_id)

        if active_only:
            query = query.filter(Representative.term_end.is_(None))

        representatives = query.all()

        results = []
        for rep in representatives:
            # Resolve party name
            party_name = rep.party.party_name if rep.party else rep.party_id
            # Resolve constituency name
            const_name = rep.constituency.official_name if rep.constituency else None

            results.append({
                "representative_id": rep.representative_id,
                "official_name": rep.official_name,
                "aliases": rep.aliases or [],
                "representative_type": rep.representative_type,
                "party_id": rep.party_id,
                "party_name": party_name,
                "constituency_id": rep.constituency_id,
                "constituency_name": const_name,
                "term_start": rep.term_start,
                "term_end": rep.term_end,
                "is_active": rep.term_end is None,
                "source_document_ids": rep.source_document_ids or []
            })

        return success_response(data={"representatives": results, "total_count": len(results)})
    except Exception as e:
        logger.error(f"Error in search_representatives: {e}")
        return error_response(f"Internal server error: {str(e)}", 500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 2. REPRESENTATIVE PROFILE
# ---------------------------------------------------------------------------
@representatives_bp.route("/<representative_id>", methods=["GET"])
def get_representative_profile(representative_id: str):
    """
    Get detailed representative profile including historical terms,
    basic completeness score, and metadata.
    """
    db: Session = _get_db()
    try:
        rep = db.query(Representative).filter(Representative.representative_id == representative_id).first()
        if not rep:
            return error_response(f"Representative '{representative_id}' not found.", status_code=404)

        # Retrieve historical terms
        terms = db.query(RepresentativeTerm).filter(
            RepresentativeTerm.representative_id == representative_id
        ).all()

        terms_data = [
            {
                "term_id": t.term_id,
                "election_id": t.election_id,
                "house_type": t.house_type,
                "party_id": t.party_id,
                "party_name": t.party.party_name if t.party else t.party_id,
                "term_start": t.term_start,
                "term_end": t.term_end,
                "term_number": t.term_number,
                "is_active_term": t.is_active_term
            }
            for t in terms
        ]

        engine = PerformanceMetricsEngine(db=db)
        completeness = engine.calculate_data_completeness_metric(
            representative_id=rep.representative_id,
            constituency_id=rep.constituency_id
        )

        party_name = rep.party.party_name if rep.party else rep.party_id
        const_name = rep.constituency.official_name if rep.constituency else None

        return success_response(data={
            "representative_id": rep.representative_id,
            "official_name": rep.official_name,
            "aliases": rep.aliases or [],
            "representative_type": rep.representative_type,
            "party_id": rep.party_id,
            "party_name": party_name,
            "constituency_id": rep.constituency_id,
            "constituency_name": const_name,
            "term_start": rep.term_start,
            "term_end": rep.term_end,
            "date_of_birth": rep.date_of_birth,
            "historical_terms": terms_data,
            "data_completeness": completeness,
            "source_document_ids": rep.source_document_ids or []
        })
    except Exception as e:
        logger.error(f"Error in get_representative_profile: {e}")
        return error_response(f"Internal server error: {str(e)}", 500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 3. CONSTITUENCY LOOKUP & PROFILE
# ---------------------------------------------------------------------------
@representatives_bp.route("/constituencies", methods=["GET"])
def list_constituencies():
    """
    List constituencies with filtering by district and type.
    """
    db: Session = _get_db()
    try:
        district = request.args.get("district", "").strip()
        c_type = request.args.get("type", "").strip()

        query = db.query(Constituency)
        if district and district != "All":
            query = query.filter(Constituency.district.ilike(f"%{district}%"))
        if c_type and c_type != "All":
            query = query.filter(Constituency.constituency_type == c_type)

        constituencies = query.order_by(Constituency.official_name).all()

        results = [
            {
                "constituency_id": c.constituency_id,
                "official_name": c.official_name,
                "constituency_type": c.constituency_type,
                "district": c.district,
                "state": c.state,
                "reservation_status": c.reservation_status,
                "delimitation_year": c.delimitation_year
            }
            for c in constituencies
        ]

        return success_response(data={"constituencies": results, "total_count": len(results)})
    except Exception as e:
        logger.error(f"Error in list_constituencies: {e}")
        return error_response(f"Internal server error: {str(e)}", 500)
    finally:
        db.close()


@representatives_bp.route("/constituencies/<constituency_id>", methods=["GET"])
def get_constituency_profile(constituency_id: str):
    """
    Get detailed constituency profile including current representative,
    taluks, and geographic mappings.
    """
    db: Session = _get_db()
    try:
        c = db.query(Constituency).filter(Constituency.constituency_id == constituency_id).first()
        if not c:
            return error_response(f"Constituency '{constituency_id}' not found.", status_code=404)

        # Current representative
        current_rep = db.query(Representative).filter(
            Representative.constituency_id == constituency_id,
            Representative.term_end.is_(None)
        ).first()

        rep_info = None
        if current_rep:
            rep_info = {
                "representative_id": current_rep.representative_id,
                "official_name": current_rep.official_name,
                "party_id": current_rep.party_id,
                "party_name": current_rep.party.party_name if current_rep.party else current_rep.party_id,
                "representative_type": current_rep.representative_type
            }

        # Geographic mappings
        mappings = db.query(ConstituencyGeographicMapping).filter(
            ConstituencyGeographicMapping.constituency_id == constituency_id
        ).all()

        mappings_data = [
            {
                "mapping_id": m.mapping_id,
                "district_name": m.district_name,
                "taluk_names": m.taluk_names or [],
                "population_share": m.population_share_in_district,
                "mapping_methodology": m.mapping_methodology
            }
            for m in mappings
        ]

        return success_response(data={
            "constituency_id": c.constituency_id,
            "official_name": c.official_name,
            "constituency_type": c.constituency_type,
            "district": c.district,
            "state": c.state,
            "reservation_status": c.reservation_status,
            "current_representative": rep_info,
            "geographic_mappings": mappings_data,
            "source_document_ids": c.source_document_ids or []
        })
    except Exception as e:
        logger.error(f"Error in get_constituency_profile: {e}")
        return error_response(f"Internal server error: {str(e)}", 500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 4. LEGISLATIVE ACTIVITY
# ---------------------------------------------------------------------------
@representatives_bp.route("/<representative_id>/legislative", methods=["GET"])
def get_representative_legislative_activity(representative_id: str):
    """
    Get granular legislative activity records and sitting-adjusted metrics.
    """
    db: Session = _get_db()
    try:
        reporting_period = request.args.get("period", "2021-2026")
        engine = PerformanceMetricsEngine(db=db)

        metrics = engine.calculate_legislative_metrics(
            representative_id=representative_id,
            reporting_period=reporting_period
        )

        activities = db.query(LegislativeActivity).filter(
            LegislativeActivity.representative_id == representative_id
        ).order_by(LegislativeActivity.session).all()

        activity_records = [
            {
                "activity_id": a.activity_id,
                "session": a.session,
                "activity_type": a.activity_type,
                "count": a.count,
                "value": a.value,
                "title_subject": a.title_subject,
                "source_reference": a.source_reference,
                "data_quality_status": a.data_quality_status
            }
            for a in activities
        ]

        return success_response(data={
            "summary_metrics": metrics,
            "activity_records": activity_records,
            "total_records": len(activity_records)
        })
    except ValueError as e:
        return error_response(str(e), status_code=404)
    except Exception as e:
        logger.error(f"Error in get_representative_legislative_activity: {e}")
        return error_response(f"Internal server error: {str(e)}", 500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 5. CONSTITUENCY WORKS TRACKER
# ---------------------------------------------------------------------------
@representatives_bp.route("/works", methods=["GET"])
def get_constituency_works():
    """
    Filter constituency works by constituency, representative, scheme, status, and attribution.
    """
    db: Session = _get_db()
    try:
        constituency_id = request.args.get("constituency_id", "").strip()
        representative_id = request.args.get("representative_id", "").strip()
        scheme_id = request.args.get("scheme_id", "").strip()
        status = request.args.get("status", "").strip()
        attribution = request.args.get("attribution", "").strip()

        query = db.query(ConstituencyWork)
        if constituency_id and constituency_id != "All":
            query = query.filter(ConstituencyWork.constituency_id == constituency_id)
        if representative_id and representative_id != "All":
            query = query.filter(ConstituencyWork.representative_id == representative_id)
        if scheme_id and scheme_id != "All":
            query = query.filter(ConstituencyWork.scheme_id == scheme_id)
        if status and status != "All":
            query = query.filter(ConstituencyWork.project_status == status)
        if attribution and attribution != "All":
            query = query.filter(ConstituencyWork.attribution_type == attribution)

        works = query.all()

        results = [
            {
                "work_id": w.work_id,
                "constituency_id": w.constituency_id,
                "representative_id": w.representative_id,
                "scheme_id": w.scheme_id,
                "project_description": w.project_description,
                "sanctioned_amount": w.sanctioned_amount,
                "released_amount": w.released_amount,
                "reported_expenditure": w.reported_expenditure,
                "project_status": w.project_status,
                "attribution_type": w.attribution_type,
                "approval_date": w.approval_date,
                "completion_date": w.completion_date,
                "source_document_id": w.source_document_id,
                "source_reference": w.source_reference,
                "verification_source": w.verification_source,
                "has_conflicting_status": w.has_conflicting_status,
                "is_independently_verified": w.project_status == WorkProjectStatus.INDEPENDENTLY_VERIFIED_COMPLETED
            }
            for w in works
        ]

        engine = PerformanceMetricsEngine(db=db)
        summary = {}
        if constituency_id and constituency_id != "All":
            summary = engine.calculate_financial_execution_metrics(
                constituency_id=constituency_id,
                reporting_period="All",
                representative_id=representative_id if representative_id and representative_id != "All" else None
            )

        return success_response(data={
            "works": results,
            "total_count": len(results),
            "financial_summary": summary
        })
    except Exception as e:
        logger.error(f"Error in get_constituency_works: {e}")
        return error_response(f"Internal server error: {str(e)}", 500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 6. DEVELOPMENT INDICATOR TRENDS
# ---------------------------------------------------------------------------
@representatives_bp.route("/indicators", methods=["GET"])
def get_development_indicators():
    """
    Get development indicators with baseline comparison across reference periods.
    """
    db: Session = _get_db()
    try:
        geographic_unit_id = request.args.get("unit_id", "").strip()
        indicator_name = request.args.get("indicator_name", "").strip()
        period_baseline = request.args.get("baseline", "2011")
        period_current = request.args.get("current", "2021")

        query = db.query(DevelopmentIndicator)
        if geographic_unit_id and geographic_unit_id != "All":
            query = query.filter(DevelopmentIndicator.geographic_unit_id == geographic_unit_id)
        if indicator_name and indicator_name != "All":
            query = query.filter(DevelopmentIndicator.indicator_name == indicator_name)

        indicators = query.all()

        results = [
            {
                "indicator_id": ind.indicator_id,
                "geographic_unit_id": ind.geographic_unit_id,
                "constituency_id": ind.constituency_id,
                "indicator_name": ind.indicator_name,
                "value": ind.value,
                "unit": ind.unit,
                "reference_period": ind.reference_period,
                "geographic_level": ind.geographic_level,
                "calculation_method": ind.calculation_method,
                "data_quality_status": ind.data_quality_status,
                "source_document_id": ind.source_document_id,
                "source_reference": ind.source_reference
            }
            for ind in indicators
        ]

        engine = PerformanceMetricsEngine(db=db)
        trend = None
        if geographic_unit_id and indicator_name and geographic_unit_id != "All" and indicator_name != "All":
            trend = engine.calculate_development_trend_metrics(
                constituency_id=geographic_unit_id,
                indicator_name=indicator_name,
                period_baseline=period_baseline,
                period_current=period_current
            )

        return success_response(data={
            "indicators": results,
            "total_count": len(results),
            "trend_analysis": trend
        })
    except Exception as e:
        logger.error(f"Error in get_development_indicators: {e}")
        return error_response(f"Internal server error: {str(e)}", 500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 7. PROMISE AND EVIDENCE TRACKER
# ---------------------------------------------------------------------------
@representatives_bp.route("/<representative_id>/promises", methods=["GET"])
def get_representative_promises(representative_id: str):
    """
    Get linked manifesto promises and evidence progression for a representative.
    """
    db: Session = _get_db()
    try:
        service = PromiseCrossReferenceService(db=db)
        scorecard = service.get_representative_promise_scorecard(representative_id=representative_id)

        links = db.query(PromisePerformanceLink).filter(
            PromisePerformanceLink.representative_id == representative_id
        ).all()

        linked_promises = [
            {
                "link_id": l.link_id,
                "promise_id": l.promise_id,
                "promise_text": l.promise.original_text if l.promise else None,
                "scheme_id": l.scheme_id,
                "evidence_id": l.evidence_id,
                "work_id": l.work_id,
                "indicator_id": l.indicator_id,
                "evidence_stage": l.evidence_stage,
                "matching_method": l.matching_method,
                "has_conflicting_dates": l.has_conflicting_dates,
                "evidence_summary": l.evidence_summary
            }
            for l in links
        ]

        return success_response(data={
            "scorecard": scorecard,
            "linked_promises": linked_promises,
            "total_count": len(linked_promises)
        })
    except ValueError as e:
        return error_response(str(e), status_code=404)
    except Exception as e:
        logger.error(f"Error in get_representative_promises: {e}")
        return error_response(f"Internal server error: {str(e)}", 500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 8. COMPARATIVE ANALYSIS & COMPOSITE SCORE
# ---------------------------------------------------------------------------
@representatives_bp.route("/compare", methods=["POST"])
def compare_representatives():
    """
    Within-cohort comparative analysis across representatives of the same legislative tier.
    """
    db: Session = _get_db()
    try:
        payload = request.get_json() or {}
        representatives = payload.get("representatives", [])
        reporting_period = payload.get("reporting_period", "2021-2024")
        cohort_type = payload.get("cohort_type", "TN_ASSEMBLY_MLA")

        if not representatives or len(representatives) < 2:
            return error_response("Please provide at least 2 representative IDs to compare.", status_code=400)

        engine = PerformanceMetricsEngine(db=db)
        cohort_comparison = engine.compare_within_cohort(
            cohort_representatives=representatives,
            reporting_period=reporting_period,
            cohort_type=cohort_type
        )

        return success_response(data={
            "cohort_type": cohort_type,
            "reporting_period": reporting_period,
            "comparisons": cohort_comparison
        })
    except IncompatibleCohortError as e:
        return error_response(str(e), status_code=400)
    except Exception as e:
        logger.error(f"Error in compare_representatives: {e}")
        return error_response(f"Internal server error: {str(e)}", status_code=500)
    finally:
        db.close()


@representatives_bp.route("/<representative_id>/composite", methods=["GET"])
def get_transparent_composite(representative_id: str):
    """
    Compute transparent composite index with full weight disclosure,
    missing-data treatment, and sensitivity analysis.
    """
    db: Session = _get_db()
    try:
        rep = db.query(Representative).filter(Representative.representative_id == representative_id).first()
        if not rep:
            return error_response(f"Representative '{representative_id}' not found.", status_code=404)

        constituency_id = rep.constituency_id or request.args.get("constituency_id", "")
        reporting_period = request.args.get("period", "2021-2024")

        engine = PerformanceMetricsEngine(db=db)
        res = engine.calculate_transparent_composite(
            representative_id=representative_id,
            constituency_id=constituency_id,
            reporting_period=reporting_period
        )

        return success_response(data=res)
    except Exception as e:
        logger.error(f"Error in get_transparent_composite: {e}")
        return error_response(f"Internal server error: {str(e)}", 500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 9. DATA COMPLETENESS & PROVENANCE
# ---------------------------------------------------------------------------
@representatives_bp.route("/<representative_id>/completeness", methods=["GET"])
def get_data_completeness(representative_id: str):
    """
    Get audit breakdown of public record availability.
    """
    db: Session = _get_db()
    try:
        rep = db.query(Representative).filter(Representative.representative_id == representative_id).first()
        if not rep:
            return error_response(f"Representative '{representative_id}' not found.", 404)

        engine = PerformanceMetricsEngine(db=db)
        completeness = engine.calculate_data_completeness_metric(
            representative_id=representative_id,
            constituency_id=rep.constituency_id
        )

        return success_response(data=completeness)
    except Exception as e:
        logger.error(f"Error in get_data_completeness: {e}")
        return error_response(f"Internal server error: {str(e)}", status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 10. EVIDENCE TRACEABILITY & AUDIT TRAIL ENDPOINTS (PHASE 6.11)
# ---------------------------------------------------------------------------
@representatives_bp.route("/sources", methods=["GET"])
def list_source_documents():
    """List canonical source documents with metadata and SHA-256 checksums."""
    db: Session = _get_db()
    try:
        from backend.services.traceability_service import TraceabilityService
        service = TraceabilityService(db=db)
        publisher = request.args.get("publisher", "").strip()
        docs = service.list_source_documents(publisher=publisher if publisher else None)

        results = [
            {
                "document_id": d.document_id,
                "source_name": d.source_name,
                "source_type": d.source_type,
                "document_title": d.document_title,
                "publisher": d.publisher,
                "official_source_url": d.official_source_url,
                "publication_date": d.publication_date,
                "retrieval_date": d.retrieval_date,
                "file_format": d.file_format,
                "sha256_checksum": d.sha256_checksum,
                "reporting_period": d.reporting_period,
                "geographic_coverage": d.geographic_coverage,
                "verification_status": d.verification_status,
                "notes": d.notes
            }
            for d in docs
        ]
        return success_response(data={"documents": results, "total_count": len(results)})
    except Exception as e:
        logger.error(f"Error in list_source_documents: {e}")
        return error_response(f"Internal server error: {str(e)}", status_code=500)
    finally:
        db.close()


@representatives_bp.route("/sources/<document_id>", methods=["GET"])
def get_source_document_detail(document_id: str):
    """Get detailed metadata for a single source document."""
    db: Session = _get_db()
    try:
        from backend.services.traceability_service import TraceabilityService
        service = TraceabilityService(db=db)
        d = service.get_source_document(document_id)
        if not d:
            return error_response(f"Source document '{document_id}' not found.", status_code=404)

        return success_response(data={
            "document_id": d.document_id,
            "source_name": d.source_name,
            "source_type": d.source_type,
            "document_title": d.document_title,
            "publisher": d.publisher,
            "official_source_url": d.official_source_url,
            "publication_date": d.publication_date,
            "retrieval_date": d.retrieval_date,
            "file_format": d.file_format,
            "sha256_checksum": d.sha256_checksum,
            "reporting_period": d.reporting_period,
            "geographic_coverage": d.geographic_coverage,
            "verification_status": d.verification_status,
            "notes": d.notes
        })
    except Exception as e:
        logger.error(f"Error in get_source_document_detail: {e}")
        return error_response(f"Internal server error: {str(e)}", status_code=500)
    finally:
        db.close()


@representatives_bp.route("/evidence", methods=["GET"])
def get_evidence_for_entity():
    """Retrieve supporting evidence, citations, and excerpts for a given fact/entity."""
    db: Session = _get_db()
    try:
        from backend.services.traceability_service import TraceabilityService
        service = TraceabilityService(db=db)
        entity_type = request.args.get("entity_type", "").strip()
        entity_id = request.args.get("entity_id", "").strip()

        if not entity_type or not entity_id:
            return error_response("Both 'entity_type' and 'entity_id' are required parameters.", status_code=400)

        evidences = service.get_evidence_for_entity(entity_type=entity_type, entity_id=entity_id)
        return success_response(data={
            "entity_type": entity_type,
            "entity_id": entity_id,
            "evidence_links": evidences,
            "total_links_count": len(evidences)
        })
    except Exception as e:
        logger.error(f"Error in get_evidence_for_entity: {e}")
        return error_response(f"Internal server error: {str(e)}", status_code=500)
    finally:
        db.close()


@representatives_bp.route("/metrics/<metric_id>/lineage", methods=["GET"])
def get_metric_lineage_drilldown(metric_id: str):
    """Retrieve exact mathematical formula, input record IDs, and voucher drill-down for a derived metric."""
    db: Session = _get_db()
    try:
        from backend.services.traceability_service import TraceabilityService
        service = TraceabilityService(db=db)
        drilldown = service.get_metric_drilldown(metric_id=metric_id)
        if not drilldown:
            return error_response(f"Lineage for metric '{metric_id}' not found.", status_code=404)

        return success_response(data=drilldown)
    except Exception as e:
        logger.error(f"Error in get_metric_lineage_drilldown: {e}")
        return error_response(f"Internal server error: {str(e)}", status_code=500)
    finally:
        db.close()


@representatives_bp.route("/conflicts", methods=["GET"])
def list_conflicting_evidence():
    """Retrieve preserved divergent or conflicting evidence records."""
    db: Session = _get_db()
    try:
        from backend.services.traceability_service import TraceabilityService
        service = TraceabilityService(db=db)
        entity_type = request.args.get("entity_type", "").strip()
        conflicts = service.list_conflicts(entity_type=entity_type if entity_type else None)
        return success_response(data={"conflicts": conflicts, "total_count": len(conflicts)})
    except Exception as e:
        logger.error(f"Error in list_conflicting_evidence: {e}")
        return error_response(f"Internal server error: {str(e)}", status_code=500)
    finally:
        db.close()


@representatives_bp.route("/audit-trail", methods=["GET"])
def list_audit_trail_events():
    """Retrieve immutable audit ledger events for verification and tracking."""
    db: Session = _get_db()
    try:
        from backend.services.traceability_service import TraceabilityService
        service = TraceabilityService(db=db)
        record_id = request.args.get("record_id", "").strip()
        limit = int(request.args.get("limit", 50))
        events = service.list_audit_trail(record_id=record_id if record_id else None, limit=limit)
        return success_response(data={"audit_events": events, "total_count": len(events)})
    except Exception as e:
        logger.error(f"Error in list_audit_trail_events: {e}")
        return error_response(f"Internal server error: {str(e)}", status_code=500)
    finally:
        db.close()

