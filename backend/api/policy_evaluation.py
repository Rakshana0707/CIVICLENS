"""
Phase 10.8 — Policy Outcome & Impact Evaluation REST API Router.
================================================================

Integrates Phase 10 into the CIVICLENS TN backend and Phase 9 Evidence Graph:
1.  GET  /api/policy-evaluation/policies/search                  Search canonical policies & schemes
2.  GET  /api/policy-evaluation/policies/<policy_id>            Retrieve policy evaluation details & cross-phase links
3.  GET  /api/policy-evaluation/plans                           List evaluation questions & plans
4.  GET  /api/policy-evaluation/plans/<plan_id>                 Retrieve single evaluation plan
5.  GET  /api/policy-evaluation/indicators                      List canonical indicator definitions
6.  GET  /api/policy-evaluation/indicators/<indicator_id>       Retrieve single indicator definition
7.  GET  /api/policy-evaluation/indicators/<id>/observations    List baseline & follow-up empirical observations
8.  GET  /api/policy-evaluation/policies/<id>/budget-analysis   Budget estimate vs revised vs actual execution analysis
9.  GET  /api/policy-evaluation/policies/<id>/output-analysis   Planned vs completed physical implementation outputs
10. GET  /api/policy-evaluation/indicators/<id>/compare         Baseline vs follow-up outcome comparison (9 mandatory fields)
11. GET  /api/policy-evaluation/findings                        List synthesized evaluation findings
12. GET  /api/policy-evaluation/findings/<finding_id>           Retrieve finding details (all 12 mandatory attributes)
13. GET  /api/policy-evaluation/findings/<id>/evidence          Retrieve supporting & contradicting evidence links
14. GET  /api/policy-evaluation/studies/<study_id>              Retrieve evaluation study methodology & causal rigor
15. GET  /api/policy-evaluation/policies/<id>/graph-connections Evidence graph explorer connecting budget, promises, claims,
                                                                civic issues, works, representatives & sources with
                                                                strict non-causal association guardrails.
16. POST /api/policy-evaluation/findings/<id>/review            Review/verify finding status (Requires authorization role)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from flask import Blueprint, request
from sqlalchemy.orm import Session

from backend.api.responses import error_response, success_response
from backend.database.session import SessionLocal
from backend.models.budget import (
    BudgetDepartment,
    BudgetScheme,
    BudgetRecord,
    BudgetStage,
    BudgetSourceDocument,
    HistoricalScheme,
)
from backend.models.promise import PoliticalPromise
from backend.models.claim import Claim
from backend.models.civic_issue import CivicIssue
from backend.models.representative import Representative, ConstituencyWork
from backend.models.policy_evaluation import (
    PolicyRegistryEntry,
    PolicyObjective,
    BeneficiaryGroup,
    ImplementationActivity,
    PolicyIndicator,
    IndicatorObservation,
    PolicyEvaluationPlan,
    EvaluationStudy,
    EvaluationFinding,
    FindingEvidenceLink,
    EvaluationLimitation,
    FindingType,
    FindingReviewStatus,
    ObservationStage,
    IndicatorDomain,
    IndicatorType,
)
from backend.models.graph import (
    CivicGraphNode,
    CivicEvidenceEdge,
    GraphEntityType,
    GraphRelationshipType,
)
from backend.services.policy_registry_service import PolicyRegistryService
from backend.services.policy_indicator_service import (
    PolicyIndicatorRegistryService,
    IncompatibleIndicatorComparisonError,
)
from backend.services.policy_budget_execution_service import (
    PolicyBudgetExecutionAnalyticsService,
    IncompatibleReportingPeriodError,
)
from backend.services.policy_outcome_analysis_service import (
    PolicyOutcomeAnalysisService,
    NON_CAUSAL_DESCRIPTIVE_LABEL,
)
from backend.services.policy_evidence_synthesis_service import (
    PolicyEvidenceSynthesisService,
    UnsupportedFindingConclusionError,
    NumericalInconsistencyError,
    UntraceableSourceError,
)

logger = logging.getLogger("civiclens.phase10.api")

policy_evaluation_bp = Blueprint("policy_evaluation", __name__, url_prefix="/policy-evaluation")

AUTHORIZED_POLICY_ROLES = {"ADMIN", "POLICY_ANALYST", "REVIEWER", "RESEARCHER"}

ASSOCIATION_GUARDRAIL_NOTE = (
    "EPISTEMIC GUARDRAIL: Do NOT infer that a representative, constituency, or department caused an outcome "
    "simply because they are associated with the relevant geography, sector, or policy. Cross-phase graph links "
    "reflect administrative jurisdiction and thematic relevance, not empirical causal attribution."
)


def _get_auth_role() -> Optional[str]:
    """Extracts reviewer role from request header or body."""
    role = request.headers.get("X-Reviewer-Role")
    if not role and request.is_json:
        body = request.get_json(silent=True) or {}
        role = body.get("reviewer_role")
    return role


def _verify_policy_role() -> Tuple[bool, Optional[str]]:
    role = _get_auth_role()
    if not role or role.upper() not in AUTHORIZED_POLICY_ROLES:
        return False, f"Unauthorized: requires one of {sorted(AUTHORIZED_POLICY_ROLES)}"
    return True, None


# ---------------------------------------------------------------------------
# 1. Policy Search
# ---------------------------------------------------------------------------
@policy_evaluation_bp.route("/policies/search", methods=["GET"])
@policy_evaluation_bp.route("/policies", methods=["GET"])
def search_policies_endpoint():
    """
    Operation 1: Searches canonical policies and evaluation registry entries.
    Query params: q, department, status, limit, offset.
    """
    q = request.args.get("q") or request.args.get("query")
    department = request.args.get("department")
    status = request.args.get("status")

    try:
        limit = min(max(int(request.args.get("limit", 20)), 1), 100)
        offset = max(int(request.args.get("offset", 0)), 0)
    except ValueError:
        return error_response(message="Invalid numeric limit or offset parameter.", status_code=400)

    db: Session = SessionLocal()
    try:
        query = db.query(PolicyRegistryEntry)
        if q:
            q_clean = f"%{q.strip().lower()}%"
            query = query.filter(
                (PolicyRegistryEntry.policy_name.ilike(q_clean))
                | (PolicyRegistryEntry.policy_id.ilike(q_clean))
                | (PolicyRegistryEntry.canonical_scheme_code.ilike(q_clean))
                | (PolicyRegistryEntry.objectives_summary.ilike(q_clean))
            )
        if department:
            query = query.filter(PolicyRegistryEntry.responsible_department.ilike(f"%{department.strip()}%"))
        if status:
            query = query.filter(PolicyRegistryEntry.evaluation_status == status.strip().upper())

        total_count = query.count()
        entries = query.offset(offset).limit(limit).all()

        return success_response(
            data={
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "policies": [e.to_dict() for e in entries],
            },
            message="Policies retrieved successfully.",
        )
    except Exception as e:
        logger.exception("Error searching policies")
        return error_response(message="Failed to search policies.", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 2. Policy Evaluation Details & Canonical Linkages
# ---------------------------------------------------------------------------
@policy_evaluation_bp.route("/policies/<policy_id>", methods=["GET"])
def get_policy_details_endpoint(policy_id: str):
    """
    Operation 2: Retrieves full canonical details for a policy, including linked
    objectives, beneficiary groups, evaluation plans, implementation activities,
    and cross-phase canonical model links.
    """
    db: Session = SessionLocal()
    try:
        policy = PolicyRegistryService.resolve_policy(db, policy_id)
        if not policy:
            return error_response(
                message=f"Policy '{policy_id}' not found in Policy Evaluation Registry.", status_code=404
            )

        data = policy.to_dict()

        # Linked Objectives
        objs = db.query(PolicyObjective).filter_by(policy_id=policy.policy_id).all()
        data["objectives"] = [o.to_dict() for o in objs]

        # Linked Beneficiary Groups
        obj_ids = [o.objective_id for o in objs]
        b_groups = (
            db.query(BeneficiaryGroup).filter(BeneficiaryGroup.objective_id.in_(obj_ids)).all()
            if obj_ids
            else []
        )
        data["beneficiary_groups"] = [bg.to_dict() for bg in b_groups]

        # Linked Evaluation Plans
        plans = db.query(PolicyEvaluationPlan).filter_by(policy_id=policy.policy_id).all()
        data["evaluation_plans"] = [p.to_dict() for p in plans]

        # Linked Implementation Activities
        acts = (
            db.query(ImplementationActivity)
            .filter(
                (ImplementationActivity.policy_id == policy.policy_id)
                | (ImplementationActivity.scheme_id == policy.canonical_scheme_code)
            )
            .all()
        )
        data["implementation_activities"] = [a.to_dict() for a in acts]

        # Cross-Phase Canonical Links Metadata
        cross_phase_links = {
            "budget_scheme_id": policy.budget_scheme_id,
            "historical_scheme_id": policy.historical_scheme_id,
            "promise_id": policy.promise_id,
            "canonical_scheme_code": policy.canonical_scheme_code,
        }
        if policy.budget_scheme_id:
            bs = db.query(BudgetScheme).filter_by(id=policy.budget_scheme_id).first()
            cross_phase_links["budget_scheme_name"] = bs.name if bs else None
        if policy.promise_id:
            p_rec = db.query(PoliticalPromise).filter_by(promise_id=policy.promise_id).first()
            cross_phase_links["promise_title"] = p_rec.title if p_rec else None

        data["cross_phase_links"] = cross_phase_links

        return success_response(data=data, message="Policy details retrieved successfully.")
    except Exception as e:
        logger.exception(f"Error retrieving policy {policy_id}")
        return error_response(message="Failed to retrieve policy details.", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 3. Evaluation Questions and Plans
# ---------------------------------------------------------------------------
@policy_evaluation_bp.route("/plans", methods=["GET"])
def list_plans_endpoint():
    """
    Operation 3A: Lists structured policy evaluation plans.
    Query params: policy_id, evaluation_type, limit, offset.
    """
    policy_id = request.args.get("policy_id")
    eval_type = request.args.get("evaluation_type")

    try:
        limit = min(max(int(request.args.get("limit", 20)), 1), 100)
        offset = max(int(request.args.get("offset", 0)), 0)
    except ValueError:
        return error_response(message="Invalid numeric limit or offset.", status_code=400)

    db: Session = SessionLocal()
    try:
        query = db.query(PolicyEvaluationPlan)
        if policy_id:
            query = query.filter_by(policy_id=policy_id.strip())
        if eval_type:
            query = query.filter_by(evaluation_type=eval_type.strip().upper())

        total = query.count()
        plans = query.offset(offset).limit(limit).all()

        return success_response(
            data={"total": total, "limit": limit, "offset": offset, "plans": [p.to_dict() for p in plans]},
            message="Evaluation plans retrieved successfully.",
        )
    except Exception as e:
        logger.exception("Error listing evaluation plans")
        return error_response(message="Failed to list evaluation plans.", error_details=str(e), status_code=500)
    finally:
        db.close()


@policy_evaluation_bp.route("/plans/<plan_id>", methods=["GET"])
def get_plan_details_endpoint(plan_id: str):
    """
    Operation 3B: Retrieves a specific evaluation plan by plan_id.
    """
    db: Session = SessionLocal()
    try:
        plan = db.query(PolicyEvaluationPlan).filter_by(plan_id=plan_id.strip()).first()
        if not plan:
            return error_response(message=f"Evaluation plan '{plan_id}' not found.", status_code=404)
        return success_response(data=plan.to_dict(), message="Evaluation plan details retrieved.")
    except Exception as e:
        logger.exception(f"Error retrieving plan {plan_id}")
        return error_response(message="Failed to retrieve plan.", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 4. Indicator Definitions
# ---------------------------------------------------------------------------
@policy_evaluation_bp.route("/indicators", methods=["GET"])
def list_indicators_endpoint():
    """
    Operation 4: Lists canonical indicator definitions with full Phase 10.4 attributes.
    Query params: domain, indicator_type, scheme_id, limit, offset.
    """
    domain = request.args.get("domain")
    ind_type = request.args.get("indicator_type")
    scheme_id = request.args.get("scheme_id")

    try:
        limit = min(max(int(request.args.get("limit", 20)), 1), 100)
        offset = max(int(request.args.get("offset", 0)), 0)
    except ValueError:
        return error_response(message="Invalid numeric limit or offset.", status_code=400)

    db: Session = SessionLocal()
    try:
        query = db.query(PolicyIndicator)
        if domain:
            query = query.filter_by(indicator_domain=domain.strip().upper())
        if ind_type:
            query = query.filter_by(indicator_type=ind_type.strip().upper())
        if scheme_id:
            query = query.filter_by(scheme_id=scheme_id.strip())

        total = query.count()
        indicators = query.offset(offset).limit(limit).all()

        return success_response(
            data={"total": total, "limit": limit, "offset": offset, "indicators": [i.to_dict() for i in indicators]},
            message="Policy indicators retrieved successfully.",
        )
    except Exception as e:
        logger.exception("Error listing indicators")
        return error_response(message="Failed to list indicators.", error_details=str(e), status_code=500)
    finally:
        db.close()


@policy_evaluation_bp.route("/indicators/<indicator_id>", methods=["GET"])
def get_indicator_endpoint(indicator_id: str):
    """
    Retrieves canonical definition for a single PolicyIndicator.
    """
    db: Session = SessionLocal()
    try:
        indicator = db.query(PolicyIndicator).filter_by(indicator_id=indicator_id.strip()).first()
        if not indicator:
            return error_response(message=f"Indicator '{indicator_id}' not found.", status_code=404)
        return success_response(data=indicator.to_dict(), message="Indicator definition retrieved.")
    except Exception as e:
        logger.exception(f"Error retrieving indicator {indicator_id}")
        return error_response(message="Failed to retrieve indicator.", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 5. Baseline and Follow-up Empirical Observations
# ---------------------------------------------------------------------------
@policy_evaluation_bp.route("/indicators/<indicator_id>/observations", methods=["GET"])
def list_indicator_observations_endpoint(indicator_id: str):
    """
    Operation 5: Lists baseline, follow-up, intermediate, and target empirical observations
    for an indicator, strictly preserving None for missing values.
    Query params: stage, reference_period, geographic_unit_id, limit, offset.
    """
    stage = request.args.get("stage")
    ref_period = request.args.get("reference_period")
    geo_unit = request.args.get("geographic_unit_id")

    try:
        limit = min(max(int(request.args.get("limit", 50)), 1), 200)
        offset = max(int(request.args.get("offset", 0)), 0)
    except ValueError:
        return error_response(message="Invalid numeric limit or offset.", status_code=400)

    db: Session = SessionLocal()
    try:
        ind = db.query(PolicyIndicator).filter_by(indicator_id=indicator_id.strip()).first()
        if not ind:
            return error_response(message=f"Indicator '{indicator_id}' not found.", status_code=404)

        query = db.query(IndicatorObservation).filter_by(indicator_id=ind.indicator_id)
        if stage:
            query = query.filter_by(stage=stage.strip().upper())
        if ref_period:
            query = query.filter_by(reference_period=ref_period.strip())
        if geo_unit:
            query = query.filter_by(geographic_unit_id=geo_unit.strip())

        total = query.count()
        observations = query.offset(offset).limit(limit).all()

        return success_response(
            data={
                "indicator_id": ind.indicator_id,
                "unit": ind.unit,
                "total_observations": total,
                "limit": limit,
                "offset": offset,
                "observations": [o.to_dict() for o in observations],
            },
            message="Indicator observations retrieved successfully.",
        )
    except Exception as e:
        logger.exception(f"Error listing observations for indicator {indicator_id}")
        return error_response(message="Failed to list indicator observations.", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 6. Budget & Implementation Analysis
# ---------------------------------------------------------------------------
@policy_evaluation_bp.route("/policies/<policy_id>/budget-analysis", methods=["GET"])
def get_policy_budget_analysis_endpoint(policy_id: str):
    """
    Operation 6A: Evaluates BE vs RE and Allocation vs Actual Expenditure for a policy
    using linked Phase 1 Budget records. Enforces epistemic guardrails.
    Query params: financial_year (mandatory).
    """
    fy = request.args.get("financial_year") or request.args.get("fy")
    if not fy:
        return error_response(message="Query parameter 'financial_year' (YYYY-YY) is required.", status_code=400)

    db: Session = SessionLocal()
    try:
        policy = PolicyRegistryService.resolve_policy(db, policy_id)
        if not policy:
            return error_response(message=f"Policy '{policy_id}' not found.", status_code=404)

        # Retrieve budget records linked via budget_scheme_id or canonical_scheme_code
        b_records = []
        if policy.budget_scheme_id:
            b_records = (
                db.query(BudgetRecord)
                .filter_by(scheme_id=policy.budget_scheme_id)
                .all()
            )

        if not b_records:
            return success_response(
                data={
                    "policy_id": policy.policy_id,
                    "financial_year": fy,
                    "status": "NO_LINKED_BUDGET_RECORDS",
                    "budget_records_found": 0,
                    "epistemic_note": "No Phase 1 BudgetRecord rows are canonically linked to this policy.",
                },
                message="No budget records linked to policy.",
            )

        analysis = PolicyBudgetExecutionAnalyticsService.analyze_allocation_vs_actual(
            b_records, financial_year=fy
        )
        analysis["policy_id"] = policy.policy_id
        analysis["canonical_scheme_code"] = policy.canonical_scheme_code
        return success_response(data=analysis, message="Policy budget analysis computed.")
    except IncompatibleReportingPeriodError as e:
        return error_response(message=str(e), status_code=400)
    except Exception as e:
        logger.exception(f"Error computing budget analysis for policy {policy_id}")
        return error_response(message="Failed to compute budget analysis.", error_details=str(e), status_code=500)
    finally:
        db.close()


@policy_evaluation_bp.route("/policies/<policy_id>/output-analysis", methods=["GET"])
def get_policy_output_analysis_endpoint(policy_id: str):
    """
    Operation 6B: Evaluates planned outputs vs completed outputs across ImplementationActivity records.
    """
    db: Session = SessionLocal()
    try:
        policy = PolicyRegistryService.resolve_policy(db, policy_id)
        if not policy:
            return error_response(message=f"Policy '{policy_id}' not found.", status_code=404)

        acts = (
            db.query(ImplementationActivity)
            .filter(
                (ImplementationActivity.policy_id == policy.policy_id)
                | (ImplementationActivity.scheme_id == policy.canonical_scheme_code)
            )
            .all()
        )

        output_analysis = PolicyBudgetExecutionAnalyticsService.analyze_planned_vs_completed_outputs(acts)
        output_analysis["policy_id"] = policy.policy_id
        output_analysis["canonical_scheme_code"] = policy.canonical_scheme_code
        return success_response(data=output_analysis, message="Policy output analysis computed.")
    except Exception as e:
        logger.exception(f"Error computing output analysis for policy {policy_id}")
        return error_response(message="Failed to compute output analysis.", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 7. Outcome Comparisons (9 Mandatory Fields & Non-Causality)
# ---------------------------------------------------------------------------
@policy_evaluation_bp.route("/indicators/<indicator_id>/compare", methods=["GET"])
def compare_indicator_outcome_endpoint(indicator_id: str):
    """
    Operation 7: Evaluates baseline vs follow-up outcome change for an indicator.
    Query params: baseline_period, followup_period, geographic_unit_id, allow_unit_conversion.
    Returns all 9 mandatory Phase 10.6 fields with explicit non-causal labeling.
    """
    base_period = request.args.get("baseline_period")
    follow_period = request.args.get("followup_period")
    geo_unit = request.args.get("geographic_unit_id")
    allow_conv = request.args.get("allow_unit_conversion", "false").lower() in ("true", "1")

    db: Session = SessionLocal()
    try:
        ind = db.query(PolicyIndicator).filter_by(indicator_id=indicator_id.strip()).first()
        if not ind:
            return error_response(message=f"Indicator '{indicator_id}' not found.", status_code=404)

        # Query baseline observation
        b_query = db.query(IndicatorObservation).filter(
            IndicatorObservation.indicator_id == ind.indicator_id,
            IndicatorObservation.stage == ObservationStage.BASELINE,
        )
        if base_period:
            b_query = b_query.filter(IndicatorObservation.reference_period == base_period.strip())
        if geo_unit:
            b_query = b_query.filter(IndicatorObservation.geographic_unit_id == geo_unit.strip())
        b_obs = b_query.first()

        # Query follow-up observation
        f_query = db.query(IndicatorObservation).filter(
            IndicatorObservation.indicator_id == ind.indicator_id,
            IndicatorObservation.stage == ObservationStage.FOLLOW_UP,
        )
        if follow_period:
            f_query = f_query.filter(IndicatorObservation.reference_period == follow_period.strip())
        if geo_unit:
            f_query = f_query.filter(IndicatorObservation.geographic_unit_id == geo_unit.strip())
        f_obs = f_query.first()

        comparison = PolicyOutcomeAnalysisService.analyze_baseline_vs_followup(
            ind, b_obs, f_obs, allow_linear_unit_conversion=allow_conv
        )
        return success_response(data=comparison, message="Outcome comparison computed.")
    except IncompatibleIndicatorComparisonError as e:
        return error_response(message=str(e), status_code=400)
    except Exception as e:
        logger.exception(f"Error comparing indicator {indicator_id}")
        return error_response(message="Failed to compute outcome comparison.", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 8. Evaluation Findings
# ---------------------------------------------------------------------------
@policy_evaluation_bp.route("/findings", methods=["GET"])
def list_findings_endpoint():
    """
    Operation 8A: Lists synthesized evaluation findings.
    Query params: policy_id, evaluation_id, finding_type, review_status, limit, offset.
    """
    policy_id = request.args.get("policy_id")
    eval_id = request.args.get("evaluation_id")
    ft = request.args.get("finding_type")
    status = request.args.get("review_status")

    try:
        limit = min(max(int(request.args.get("limit", 20)), 1), 100)
        offset = max(int(request.args.get("offset", 0)), 0)
    except ValueError:
        return error_response(message="Invalid numeric limit or offset.", status_code=400)

    db: Session = SessionLocal()
    try:
        query = db.query(EvaluationFinding)
        if policy_id:
            query = query.filter_by(policy_id=policy_id.strip())
        if eval_id:
            query = query.filter_by(study_id=eval_id.strip())
        if ft:
            query = query.filter_by(finding_type=ft.strip().upper())
        if status:
            query = query.filter_by(review_status=status.strip().upper())

        total = query.count()
        findings = query.offset(offset).limit(limit).all()

        return success_response(
            data={"total": total, "limit": limit, "offset": offset, "findings": [f.to_dict() for f in findings]},
            message="Evaluation findings retrieved successfully.",
        )
    except Exception as e:
        logger.exception("Error listing findings")
        return error_response(message="Failed to list findings.", error_details=str(e), status_code=500)
    finally:
        db.close()


@policy_evaluation_bp.route("/findings/<finding_id>", methods=["GET"])
def get_finding_details_endpoint(finding_id: str):
    """
    Operation 8B: Retrieves all 12 attributes for a specific evaluation finding.
    """
    db: Session = SessionLocal()
    try:
        finding = db.query(EvaluationFinding).filter_by(finding_id=finding_id.strip()).first()
        if not finding:
            return error_response(message=f"Evaluation finding '{finding_id}' not found.", status_code=404)
        return success_response(data=finding.to_dict(), message="Finding details retrieved.")
    except Exception as e:
        logger.exception(f"Error retrieving finding {finding_id}")
        return error_response(message="Failed to retrieve finding.", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 9. Supporting and Contradicting Evidence
# ---------------------------------------------------------------------------
@policy_evaluation_bp.route("/findings/<finding_id>/evidence", methods=["GET"])
def get_finding_evidence_endpoint(finding_id: str):
    """
    Operation 9: Retrieves granular supporting, contradicting, and contextual documentary
    evidence links for an evaluation finding.
    """
    db: Session = SessionLocal()
    try:
        finding = db.query(EvaluationFinding).filter_by(finding_id=finding_id.strip()).first()
        if not finding:
            return error_response(message=f"Evaluation finding '{finding_id}' not found.", status_code=404)

        links = db.query(FindingEvidenceLink).filter_by(finding_id=finding.finding_id).all()
        supporting = [l.to_dict() for l in links if l.stance == "SUPPORTS"]
        contradicting = [l.to_dict() for l in links if l.stance == "CONTRADICTS"]
        contextual = [l.to_dict() for l in links if l.stance in ("QUALIFIES", "NEUTRAL")]

        return success_response(
            data={
                "finding_id": finding.finding_id,
                "finding_statement": finding.finding_text,
                "has_contradicting_evidence": finding.has_contradicting_evidence,
                "total_evidence_links": len(links),
                "supporting_evidence": supporting,
                "contradicting_evidence": contradicting,
                "contextual_evidence": contextual,
            },
            message="Finding evidence links retrieved successfully.",
        )
    except Exception as e:
        logger.exception(f"Error retrieving evidence for finding {finding_id}")
        return error_response(message="Failed to retrieve finding evidence.", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 10. Source Documents and Evaluation Studies
# ---------------------------------------------------------------------------
@policy_evaluation_bp.route("/studies/<study_id>", methods=["GET"])
def get_study_methodology_endpoint(study_id: str):
    """
    Operation 10A: Retrieves methodology description, conducting agency, causal rigor grade,
    and identification strategy for an evaluation study.
    """
    db: Session = SessionLocal()
    try:
        study = db.query(EvaluationStudy).filter_by(study_id=study_id.strip()).first()
        if not study:
            return error_response(message=f"Evaluation study '{study_id}' not found.", status_code=404)

        data = study.to_dict()
        data["limitations"] = [lim.to_dict() for lim in study.limitations]
        return success_response(data=data, message="Study methodology details retrieved.")
    except Exception as e:
        logger.exception(f"Error retrieving study {study_id}")
        return error_response(message="Failed to retrieve study.", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 11. Cross-Phase Evidence Graph Explorer
# ---------------------------------------------------------------------------
@policy_evaluation_bp.route("/policies/<policy_id>/graph-connections", methods=["GET"])
def get_policy_graph_connections_endpoint(policy_id: str):
    """
    Operation 11: Explores Phase 9 Evidence Graph connections for a policy, linking:
    - Phase 1 budget schemes & records
    - Phase 3 promise records
    - Phase 7 claim verification records
    - Phase 8 civic issues & public works
    - Phase 6 representative & constituency records
    - Source documents
    Enforces strict non-causal association guardrail.
    """
    db: Session = SessionLocal()
    try:
        policy = PolicyRegistryService.resolve_policy(db, policy_id)
        if not policy:
            return error_response(message=f"Policy '{policy_id}' not found.", status_code=404)

        policy_node_id = f"NODE:POLICY:{policy.policy_id}"

        # 1. Connected Graph Edges
        edges = (
            db.query(CivicEvidenceEdge)
            .filter(
                (CivicEvidenceEdge.source_node_id == policy_node_id)
                | (CivicEvidenceEdge.target_node_id == policy_node_id)
            )
            .all()
        )

        connected_node_ids = set()
        for e in edges:
            connected_node_ids.add(e.source_node_id)
            connected_node_ids.add(e.target_node_id)
        connected_node_ids.discard(policy_node_id)

        connected_nodes = (
            db.query(CivicGraphNode).filter(CivicGraphNode.node_id.in_(connected_node_ids)).all()
            if connected_node_ids
            else []
        )

        # 2. Associated Phase 1–8 Entities
        linked_entities = {
            "budget_scheme_id": policy.budget_scheme_id,
            "canonical_scheme_code": policy.canonical_scheme_code,
            "promise_id": policy.promise_id,
            "department": policy.responsible_department,
            "claims": [],
            "civic_issues": [],
            "constituency_works": [],
            "representatives": [],
        }

        # Look up claims related to canonical scheme code
        claims = (
            db.query(Claim)
            .filter(Claim.original_text.ilike(f"%{policy.policy_name}%"))
            .limit(5)
            .all()
        )
        linked_entities["claims"] = [
            {"claim_id": c.claim_id, "claim_text": c.original_text} for c in claims
        ]

        # Look up representative / constituency works in policy geographic focus
        if policy.geographic_scope:
            works = db.query(ConstituencyWork).limit(5).all()
            linked_entities["constituency_works"] = [
                {
                    "work_id": w.work_id,
                    "title": w.project_description,
                    "constituency_id": w.constituency_id,
                }
                for w in works
            ]

        return success_response(
            data={
                "policy_id": policy.policy_id,
                "policy_name": policy.policy_name,
                "policy_node_id": policy_node_id,
                "evidence_graph": {
                    "total_edges": len(edges),
                    "edges": [e.to_dict() for e in edges],
                    "connected_nodes": [n.to_dict() for n in connected_nodes],
                },
                "associated_entities": linked_entities,
                "epistemic_guardrail": {
                    "causal_claim_from_association_permitted": False,
                    "association_guardrail_note": ASSOCIATION_GUARDRAIL_NOTE,
                },
            },
            message="Evidence graph connections retrieved successfully.",
        )
    except Exception as e:
        logger.exception(f"Error exploring graph connections for policy {policy_id}")
        return error_response(message="Failed to retrieve graph connections.", error_details=str(e), status_code=500)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 12. Review/Verify Finding (Requires Authorization)
# ---------------------------------------------------------------------------
@policy_evaluation_bp.route("/findings/<finding_id>/review", methods=["POST"])
def review_finding_endpoint(finding_id: str):
    """
    Operation 12: Updates review status of an evaluation finding.
    Requires authorization role in {'ADMIN', 'POLICY_ANALYST', 'REVIEWER', 'RESEARCHER'}.
    """
    authorized, err = _verify_policy_role()
    if not authorized:
        return error_response(message=err or "Unauthorized", status_code=403)

    body = request.get_json(silent=True) or {}
    new_status = body.get("review_status")
    review_notes = body.get("review_notes", "")

    if not new_status:
        return error_response(message="Missing required field 'review_status'.", status_code=400)

    try:
        parsed_status = FindingReviewStatus.from_string(new_status)
    except ValueError:
        return error_response(
            message=f"Invalid review_status. Allowed: {[s.value for s in FindingReviewStatus]}", status_code=400
        )

    db: Session = SessionLocal()
    try:
        finding = db.query(EvaluationFinding).filter_by(finding_id=finding_id.strip()).first()
        if not finding:
            return error_response(message=f"Finding '{finding_id}' not found.", status_code=404)

        finding.review_status = parsed_status
        if review_notes:
            lims = list(finding.limitations or [])
            lims.append(f"REVIEW_NOTE ({_get_auth_role()}): {review_notes}")
            finding.limitations = lims

        db.commit()
        db.refresh(finding)

        return success_response(
            data=finding.to_dict(),
            message=f"Finding '{finding_id}' review status updated to {parsed_status.value}.",
        )
    except Exception as e:
        db.rollback()
        logger.exception(f"Error reviewing finding {finding_id}")
        return error_response(message="Failed to review finding.", error_details=str(e), status_code=500)
    finally:
        db.close()
