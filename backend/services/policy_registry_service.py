"""
Phase 10.3 — Policy Registry and Evaluation Plan Builder Service.
=================================================================

Implements the business logic and epistemic guardrails for:
1. Creating and extending the Policy Evaluation Registry linked to Phase 1–3 models
   (BudgetScheme, HistoricalScheme, PoliticalPromise, BudgetDepartment).
2. Preserving exact original objective wording and flagging ambiguous objectives for review.
3. Enforcing strict target provenance:
   - Distinguishing OFFICIALLY_STATED targets from ANALYST_PROPOSED_BENCHMARK and NO_PUBLISHED_TARGET.
   - Prohibiting invented targets (OFFICIALLY_STATED targets require documentary source references;
     NO_PUBLISHED_TARGET must have target_value=None).
4. Building and validating structured PolicyEvaluationPlans with all 11 mandatory fields.
5. Synchronizing PolicyRegistryEntry and PolicyEvaluationPlan entities into the Phase 9
   Unified Civic Intelligence & Evidence Graph without duplication.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.models.budget import BudgetDepartment, BudgetScheme, HistoricalScheme
from backend.models.promise import PoliticalPromise
from backend.models.policy_evaluation import (
    PolicyRegistryEntry,
    PolicyObjective,
    PolicyIndicator,
    PolicyEvaluationPlan,
    PolicyEvaluationStatus,
    TargetProvenanceType,
    ObjectiveReviewStatus,
    EvaluationType,
    IndicatorType,
)
from backend.models.graph import (
    CivicGraphNode,
    CivicEvidenceEdge,
    GraphEntityType,
    GraphRelationshipType,
    MatchingMethod,
    GraphProvenanceStatus,
    GraphReviewStatus,
)


VAGUE_OBJECTIVE_PATTERNS = [
    r"\bworld[- ]class\b",
    r"\bholistic(?:ally)?\b",
    r"\ball[- ]round development\b",
    r"\btransform(?:ative|ation)\b",
    r"\boverall upliftment\b",
    r"\bcomprehensive welfare\b",
    r"\bparadigm shift\b",
    r"\bseamless empowerment\b",
]


class PolicyRegistryService:
    """
    Service for managing canonical PolicyRegistryEntry records, ambiguity detection,
    target provenance validation, and structured PolicyEvaluationPlan building.
    """

    # -----------------------------------------------------------------------
    # 1. Objective Ambiguity Detection & Wording Preservation
    # -----------------------------------------------------------------------
    @staticmethod
    def assess_objective_ambiguity(
        original_wording: str,
        stated_targets: Optional[List[Dict[str, Any]]] = None,
        explicit_is_ambiguous: Optional[bool] = None,
        explicit_notes: Optional[str] = None,
    ) -> Tuple[bool, ObjectiveReviewStatus, Optional[str]]:
        """
        Evaluates whether a policy objective is ambiguous or underspecified.
        Always preserves original_wording verbatim and flags ambiguous objectives for review.
        """
        if not original_wording or not original_wording.strip():
            raise ValueError("Policy objective original_wording cannot be empty.")

        if explicit_is_ambiguous is True:
            notes = explicit_notes or (
                "Objective explicitly flagged as ambiguous; original wording preserved verbatim for human review."
            )
            return True, ObjectiveReviewStatus.FLAGGED_AMBIGUOUS, notes

        matched_vague_terms: List[str] = []
        for pattern in VAGUE_OBJECTIVE_PATTERNS:
            match = re.search(pattern, original_wording, flags=re.IGNORECASE)
            if match:
                matched_vague_terms.append(match.group(0))

        # Check if there are any quantitative numbers or concrete deliverables in wording or targets
        has_numeric_signal = bool(re.search(r"\d+", original_wording)) or bool(stated_targets)

        if matched_vague_terms and not has_numeric_signal:
            notes = explicit_notes or (
                f"Ambiguous/aspirational wording detected ({', '.join(matched_vague_terms)}) "
                "without measurable quantitative criteria. Original wording preserved; flagged for human review."
            )
            return True, ObjectiveReviewStatus.FLAGGED_AMBIGUOUS, notes

        if explicit_is_ambiguous is False:
            return False, ObjectiveReviewStatus.VERIFIED_CLEAR, explicit_notes

        return False, ObjectiveReviewStatus.VERIFIED_CLEAR, explicit_notes

    # -----------------------------------------------------------------------
    # 2. Target Provenance Validation (Never Invent a Policy Target)
    # -----------------------------------------------------------------------
    @staticmethod
    def validate_target_provenance(
        target_value: Optional[float],
        target_provenance: TargetProvenanceType | str,
        target_source_reference: Optional[str],
    ) -> Tuple[Optional[float], TargetProvenanceType, Optional[str]]:
        """
        Enforces strict epistemic separation between:
        - OFFICIALLY_STATED targets (must have target_value AND documentary target_source_reference)
        - ANALYST_PROPOSED_BENCHMARK (must have target_value AND analytical rationale in target_source_reference)
        - NO_PUBLISHED_TARGET (target_value MUST be None — never invent a target)
        """
        prov = TargetProvenanceType.from_string(target_provenance)

        if prov == TargetProvenanceType.NO_PUBLISHED_TARGET:
            if target_value is not None:
                raise ValueError(
                    "Epistemic violation: target_value must be None when target_provenance is NO_PUBLISHED_TARGET. "
                    "Never invent a policy target."
                )
            return None, prov, target_source_reference

        if prov == TargetProvenanceType.OFFICIALLY_STATED:
            if target_value is None:
                raise ValueError(
                    "Validation error: OFFICIALLY_STATED target_provenance requires a numeric target_value."
                )
            if not target_source_reference or len(target_source_reference.strip()) < 5:
                raise ValueError(
                    "Epistemic violation: OFFICIALLY_STATED target requires a verifiable documentary "
                    "target_source_reference (e.g., GO number, Policy Note page, Budget Speech citation). "
                    "Never invent an official policy target."
                )
            return float(target_value), prov, target_source_reference.strip()

        if prov == TargetProvenanceType.ANALYST_PROPOSED_BENCHMARK:
            if target_value is None:
                raise ValueError(
                    "Validation error: ANALYST_PROPOSED_BENCHMARK requires a numeric target_value."
                )
            if not target_source_reference or len(target_source_reference.strip()) < 5:
                raise ValueError(
                    "Validation error: ANALYST_PROPOSED_BENCHMARK requires an explicit analytical basis/rationale "
                    "in target_source_reference to distinguish it from official targets."
                )
            return float(target_value), prov, target_source_reference.strip()

        raise ValueError(f"Unsupported TargetProvenanceType: {target_provenance}")

    @classmethod
    def validate_stated_targets_list(cls, stated_targets: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Validates a list of stated target dictionaries stored on PolicyRegistryEntry.
        Each entry must specify 'target_provenance', 'target_value', and 'source_reference' (if non-null).
        """
        if not stated_targets:
            return []

        validated: List[Dict[str, Any]] = []
        for idx, item in enumerate(stated_targets):
            if not isinstance(item, dict):
                raise ValueError(f"stated_targets[{idx}] must be a dictionary.")

            prov_raw = item.get("target_provenance", TargetProvenanceType.OFFICIALLY_STATED.value)
            val_raw = item.get("target_value")
            ref_raw = item.get("source_reference") or item.get("target_source_reference")

            val, prov, ref = cls.validate_target_provenance(val_raw, prov_raw, ref_raw)
            normalized_entry = dict(item)
            normalized_entry["target_value"] = val
            normalized_entry["target_provenance"] = prov.value
            normalized_entry["source_reference"] = ref
            validated.append(normalized_entry)

        return validated

    # -----------------------------------------------------------------------
    # 3. Policy Registry Creation & Canonical Phase 1–3 Linking
    # -----------------------------------------------------------------------
    @classmethod
    def register_policy(
        cls,
        db: Session,
        *,
        policy_id: str,
        policy_name: str,
        canonical_scheme_code: Optional[str] = None,
        budget_scheme_id: Optional[int] = None,
        historical_scheme_id: Optional[int] = None,
        promise_id: Optional[str] = None,
        policy_name_ta: Optional[str] = None,
        aliases: Optional[List[str]] = None,
        responsible_department: Optional[str] = None,
        department_id: Optional[int] = None,
        objectives_summary: Optional[str] = None,
        original_objective_wording: Optional[str] = None,
        is_objective_ambiguous: Optional[bool] = None,
        ambiguity_review_notes: Optional[str] = None,
        intended_beneficiaries: Optional[str] = None,
        geographic_scope: str = "STATEWIDE",
        covered_districts: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        implementation_rules: Optional[Dict[str, Any]] = None,
        stated_targets: Optional[List[Dict[str, Any]]] = None,
        source_documents: Optional[List[str]] = None,
        evaluation_status: PolicyEvaluationStatus | str = PolicyEvaluationStatus.NOT_STARTED,
        is_test_fixture: bool = False,
    ) -> PolicyRegistryEntry:
        """
        Creates or updates a canonical PolicyRegistryEntry linked to Phase 1–3 entities.
        Enforces canonical linkage, target provenance validation, and ambiguity preservation.
        """
        # Resolve Phase 1–3 entities if IDs are provided
        if budget_scheme_id is not None:
            b_scheme = db.query(BudgetScheme).filter_by(id=budget_scheme_id).first()
            if not b_scheme:
                raise ValueError(f"BudgetScheme id={budget_scheme_id} does not exist.")
            if not canonical_scheme_code:
                canonical_scheme_code = f"BUD-SCH-{b_scheme.id}"
            if not department_id:
                department_id = b_scheme.department_id
            if not responsible_department and b_scheme.department:
                responsible_department = b_scheme.department.name

        if historical_scheme_id is not None:
            h_scheme = db.query(HistoricalScheme).filter_by(id=historical_scheme_id).first()
            if not h_scheme:
                raise ValueError(f"HistoricalScheme id={historical_scheme_id} does not exist.")
            if not canonical_scheme_code:
                canonical_scheme_code = h_scheme.original_source_identifier or f"HIST-SCH-{h_scheme.id}"
            if not department_id:
                department_id = h_scheme.department_id
            if not objectives_summary and h_scheme.objectives:
                objectives_summary = h_scheme.objectives
            if not original_objective_wording and h_scheme.objectives:
                original_objective_wording = h_scheme.objectives
            if not intended_beneficiaries and h_scheme.target_beneficiaries:
                intended_beneficiaries = h_scheme.target_beneficiaries

        if promise_id is not None:
            promise_obj = db.query(PoliticalPromise).filter_by(promise_id=promise_id).first()
            if promise_obj:
                if not canonical_scheme_code:
                    canonical_scheme_code = f"PROM-POL-{promise_obj.promise_id}"
                if not original_objective_wording:
                    original_objective_wording = promise_obj.original_text
                if not objectives_summary:
                    objectives_summary = promise_obj.normalized_text

        # Enforce canonical linkage requirement
        if not canonical_scheme_code and not any([budget_scheme_id, historical_scheme_id, promise_id]):
            raise ValueError(
                "Every policy registry entry must refer to an existing canonical scheme or policy entity "
                "(canonical_scheme_code, budget_scheme_id, historical_scheme_id, or promise_id)."
            )

        if not original_objective_wording and objectives_summary:
            original_objective_wording = objectives_summary
        elif not objectives_summary and original_objective_wording:
            objectives_summary = original_objective_wording

        if not original_objective_wording:
            raise ValueError("Policy registration requires original_objective_wording or objectives_summary.")

        if not intended_beneficiaries:
            raise ValueError("Policy registration requires intended_beneficiaries specification.")

        # Validate stated targets (Never invent a target)
        validated_targets = cls.validate_stated_targets_list(stated_targets)

        # Assess objective ambiguity and preserve original wording
        is_ambig, rev_status, rev_notes = cls.assess_objective_ambiguity(
            original_wording=original_objective_wording,
            stated_targets=validated_targets,
            explicit_is_ambiguous=is_objective_ambiguous,
            explicit_notes=ambiguity_review_notes,
        )

        eval_status_enum = PolicyEvaluationStatus.from_string(evaluation_status)
        if is_ambig and eval_status_enum == PolicyEvaluationStatus.NOT_STARTED:
            eval_status_enum = PolicyEvaluationStatus.FLAGGED_FOR_REVIEW

        entry = PolicyRegistryEntry(
            policy_id=policy_id,
            budget_scheme_id=budget_scheme_id,
            historical_scheme_id=historical_scheme_id,
            promise_id=promise_id,
            canonical_scheme_code=canonical_scheme_code,
            policy_name=policy_name,
            policy_name_ta=policy_name_ta,
            aliases=aliases or [],
            responsible_department=responsible_department,
            department_id=department_id,
            objectives_summary=objectives_summary,
            original_objective_wording=original_objective_wording,
            is_objective_ambiguous=is_ambig,
            ambiguity_review_notes=rev_notes,
            objective_review_status=rev_status,
            intended_beneficiaries=intended_beneficiaries,
            geographic_scope=geographic_scope,
            covered_districts=covered_districts or [],
            start_date=start_date,
            end_date=end_date,
            implementation_rules=implementation_rules or {},
            stated_targets=validated_targets,
            source_documents=source_documents or [],
            evaluation_status=eval_status_enum,
            is_test_fixture=is_test_fixture,
        )

        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @staticmethod
    def resolve_policy(db: Session, query: str) -> Optional[PolicyRegistryEntry]:
        """
        Resolves a PolicyRegistryEntry by policy_id, canonical_scheme_code, exact name, or alias.
        """
        q_clean = query.strip()
        direct = (
            db.query(PolicyRegistryEntry)
            .filter(
                (PolicyRegistryEntry.policy_id == q_clean)
                | (PolicyRegistryEntry.canonical_scheme_code == q_clean)
                | (PolicyRegistryEntry.policy_name == q_clean)
                | (PolicyRegistryEntry.policy_name_ta == q_clean)
            )
            .first()
        )
        if direct:
            return direct

        q_lower = q_clean.lower()
        all_entries = db.query(PolicyRegistryEntry).all()
        for entry in all_entries:
            if entry.policy_name and entry.policy_name.lower() == q_lower:
                return entry
            for alias in entry.aliases or []:
                if str(alias).strip().lower() == q_lower:
                    return entry
        return None

    # -----------------------------------------------------------------------
    # 4. Evaluation Plan Builder
    # -----------------------------------------------------------------------
    @classmethod
    def create_evaluation_plan(
        cls,
        db: Session,
        *,
        plan_id: str,
        policy_id: str,
        evaluation_question: str,
        objective_being_assessed: str,
        indicator_definition: str,
        baseline_period: str,
        comparison_period: str,
        data_source: str,
        calculation_method: str,
        geographic_level: str,
        limitations: str,
        evaluation_type: EvaluationType | str = EvaluationType.EVIDENCE_BASED_OUTCOME,
        indicator_type: IndicatorType | str = IndicatorType.OUTCOME,
        unit: str = "PERCENT",
        objective_id: Optional[str] = None,
        indicator_id: Optional[str] = None,
        original_objective_wording: Optional[str] = None,
        is_objective_ambiguous: Optional[bool] = None,
        baseline_value: Optional[float] = None,
        target_value: Optional[float] = None,
        target_provenance: TargetProvenanceType | str = TargetProvenanceType.NO_PUBLISHED_TARGET,
        target_source_reference: Optional[str] = None,
        actual_value: Optional[float] = None,
        source_document_ids: Optional[List[str]] = None,
        is_test_fixture: bool = False,
    ) -> PolicyEvaluationPlan:
        """
        Builds and validates a structured PolicyEvaluationPlan.
        Enforces all 11 mandatory plan components, validates target provenance,
        and preserves ambiguous objective warnings.
        """
        policy_entry = db.query(PolicyRegistryEntry).filter_by(policy_id=policy_id).first()
        if not policy_entry:
            raise ValueError(f"PolicyRegistryEntry '{policy_id}' not found. Every evaluation plan must link to a registered policy.")

        # Validate required text fields
        required_text_fields = {
            "evaluation_question": evaluation_question,
            "objective_being_assessed": objective_being_assessed,
            "indicator_definition": indicator_definition,
            "baseline_period": baseline_period,
            "comparison_period": comparison_period,
            "data_source": data_source,
            "calculation_method": calculation_method,
            "geographic_level": geographic_level,
            "limitations": limitations,
        }
        for field_name, field_val in required_text_fields.items():
            if not field_val or not str(field_val).strip():
                raise ValueError(f"Evaluation plan missing required field: '{field_name}'.")

        # Validate target provenance (Never invent an official target)
        val_target, val_prov, val_ref = cls.validate_target_provenance(
            target_value=target_value,
            target_provenance=target_provenance,
            target_source_reference=target_source_reference,
        )

        # Check objective ambiguity from linked objective or policy
        effective_original_wording = original_objective_wording or policy_entry.original_objective_wording
        effective_ambiguous = (
            is_objective_ambiguous
            if is_objective_ambiguous is not None
            else policy_entry.is_objective_ambiguous
        )

        if objective_id:
            obj_record = db.query(PolicyObjective).filter_by(objective_id=objective_id).first()
            if obj_record:
                if not original_objective_wording and obj_record.original_wording:
                    effective_original_wording = obj_record.original_wording
                if obj_record.is_ambiguous:
                    effective_ambiguous = True

        plan_status = "FLAGGED_AMBIGUOUS_OBJECTIVE" if effective_ambiguous else "ACTIVE"

        plan = PolicyEvaluationPlan(
            plan_id=plan_id,
            policy_id=policy_id,
            objective_id=objective_id,
            indicator_id=indicator_id,
            evaluation_question=evaluation_question.strip(),
            evaluation_type=EvaluationType.from_string(evaluation_type),
            objective_being_assessed=objective_being_assessed.strip(),
            original_objective_wording=effective_original_wording,
            is_objective_ambiguous=bool(effective_ambiguous),
            indicator_definition=indicator_definition.strip(),
            indicator_type=IndicatorType.from_string(indicator_type),
            unit=unit,
            baseline_period=baseline_period.strip(),
            comparison_period=comparison_period.strip(),
            baseline_value=baseline_value,
            target_value=val_target,
            target_provenance=val_prov,
            target_source_reference=val_ref,
            actual_value=actual_value,
            data_source=data_source.strip(),
            source_document_ids=source_document_ids or [],
            calculation_method=calculation_method.strip(),
            geographic_level=geographic_level.strip().upper(),
            limitations=limitations.strip(),
            plan_status=plan_status,
            is_test_fixture=is_test_fixture,
        )

        db.add(plan)

        # Update parent policy status if it was NOT_STARTED
        if policy_entry.evaluation_status == PolicyEvaluationStatus.NOT_STARTED:
            policy_entry.evaluation_status = PolicyEvaluationStatus.PLAN_DEFINED

        db.commit()
        db.refresh(plan)
        return plan

    @staticmethod
    def compute_plan_assessment_summary(plan: PolicyEvaluationPlan) -> Dict[str, Any]:
        """
        Computes descriptive change and target comparison for a PolicyEvaluationPlan
        while strictly distinguishing official targets from analyst benchmarks.
        """
        summary: Dict[str, Any] = {
            "plan_id": plan.plan_id,
            "policy_id": plan.policy_id,
            "indicator_type": plan.indicator_type.value if hasattr(plan.indicator_type, "value") else str(plan.indicator_type),
            "target_provenance": plan.target_provenance.value if hasattr(plan.target_provenance, "value") else str(plan.target_provenance),
            "is_official_target": plan.target_provenance == TargetProvenanceType.OFFICIALLY_STATED,
            "is_analyst_benchmark": plan.target_provenance == TargetProvenanceType.ANALYST_PROPOSED_BENCHMARK,
            "is_objective_ambiguous": plan.is_objective_ambiguous,
            "baseline_to_actual_change": None,
            "baseline_to_actual_pct_change": None,
            "target_realization_pct": None,
            "epistemic_note": "",
        }

        if plan.baseline_value is not None and plan.actual_value is not None:
            diff = plan.actual_value - plan.baseline_value
            summary["baseline_to_actual_change"] = round(diff, 4)
            if plan.baseline_value != 0:
                summary["baseline_to_actual_pct_change"] = round((diff / plan.baseline_value) * 100.0, 2)

        if plan.target_value is not None and plan.actual_value is not None and plan.target_value != 0:
            summary["target_realization_pct"] = round((plan.actual_value / plan.target_value) * 100.0, 2)

        if plan.target_provenance == TargetProvenanceType.NO_PUBLISHED_TARGET:
            summary["epistemic_note"] = (
                "No official quantitative target was published by the Government; evaluation is strictly "
                "descriptive (baseline vs comparison period) without an invented target."
            )
        elif plan.target_provenance == TargetProvenanceType.ANALYST_PROPOSED_BENCHMARK:
            summary["epistemic_note"] = (
                f"Target ({plan.target_value} {plan.unit}) is an ANALYST-PROPOSED BENCHMARK "
                f"({plan.target_source_reference}), NOT an officially stated government commitment."
            )
        else:
            summary["epistemic_note"] = (
                f"Target ({plan.target_value} {plan.unit}) is OFFICIALLY STATED in {plan.target_source_reference}."
            )

        if plan.indicator_type in (IndicatorType.INPUT, IndicatorType.ACTIVITY, IndicatorType.OUTPUT):
            summary["results_chain_warning"] = (
                f"Indicator measures {summary['indicator_type']} delivery, which does NOT by itself prove public outcome benefit."
            )

        return summary

    # -----------------------------------------------------------------------
    # 5. Unified Evidence Graph Synchronization
    # -----------------------------------------------------------------------
    @staticmethod
    def sync_policy_and_plan_to_graph(
        db: Session,
        policy: PolicyRegistryEntry,
        plan: Optional[PolicyEvaluationPlan] = None,
        source_document_hash: str = "0" * 64,
    ) -> Tuple[CivicGraphNode, Optional[CivicGraphNode]]:
        """
        Registers PolicyRegistryEntry and PolicyEvaluationPlan as nodes in the Phase 9
        Unified Civic Intelligence & Evidence Graph without creating a separate graph.
        """
        policy_node_id = f"NODE:POLICY:{policy.policy_id}"
        policy_node = db.query(CivicGraphNode).filter_by(node_id=policy_node_id).first()
        if not policy_node:
            policy_node = CivicGraphNode(
                node_id=policy_node_id,
                entity_type=GraphEntityType.POLICY_REGISTRY_ENTRY,
                canonical_id=policy.policy_id,
                label=policy.policy_name,
                label_ta=policy.policy_name_ta,
                source_phase="PHASE_10",
                attributes_json={
                    "canonical_scheme_code": policy.canonical_scheme_code,
                    "department": policy.responsible_department,
                    "geographic_scope": policy.geographic_scope,
                    "evaluation_status": (
                        policy.evaluation_status.value
                        if hasattr(policy.evaluation_status, "value")
                        else str(policy.evaluation_status)
                    ),
                    "is_objective_ambiguous": policy.is_objective_ambiguous,
                },
                is_test_fixture=policy.is_test_fixture,
            )
            db.add(policy_node)

        plan_node: Optional[CivicGraphNode] = None
        if plan:
            plan_node_id = f"NODE:EVALPLAN:{plan.plan_id}"
            plan_node = db.query(CivicGraphNode).filter_by(node_id=plan_node_id).first()
            if not plan_node:
                plan_node = CivicGraphNode(
                    node_id=plan_node_id,
                    entity_type=GraphEntityType.POLICY_EVALUATION_PLAN,
                    canonical_id=plan.plan_id,
                    label=f"Eval Plan: {plan.evaluation_question[:80]}",
                    source_phase="PHASE_10",
                    attributes_json={
                        "evaluation_type": (
                            plan.evaluation_type.value
                            if hasattr(plan.evaluation_type, "value")
                            else str(plan.evaluation_type)
                        ),
                        "target_provenance": (
                            plan.target_provenance.value
                            if hasattr(plan.target_provenance, "value")
                            else str(plan.target_provenance)
                        ),
                        "geographic_level": plan.geographic_level,
                    },
                    is_test_fixture=plan.is_test_fixture,
                )
                db.add(plan_node)

            edge_id = f"EDGE:EVALUATES:{plan.plan_id}:{policy.policy_id}"
            existing_edge = db.query(CivicEvidenceEdge).filter_by(edge_id=edge_id).first()
            if not existing_edge:
                doc_id = (plan.source_document_ids[0] if plan.source_document_ids else "DOC-POLICY-EVAL-PLAN")
                edge = CivicEvidenceEdge(
                    edge_id=edge_id,
                    source_node_id=plan_node_id,
                    target_node_id=policy_node_id,
                    relationship_type=GraphRelationshipType.EVALUATES,
                    evidence_reference=f"Evaluation Question: {plan.evaluation_question} | Data Source: {plan.data_source}",
                    source_document_id=doc_id,
                    source_document_hash=source_document_hash,
                    matching_method=MatchingMethod.DETERMINISTIC_ID,
                    confidence_score=1.0,
                    review_status=(
                        GraphReviewStatus.PENDING_REVIEW
                        if plan.is_objective_ambiguous
                        else GraphReviewStatus.VERIFIED
                    ),
                    provenance_status=GraphProvenanceStatus.VALID,
                    epistemic_notes=plan.limitations,
                    is_test_fixture=plan.is_test_fixture,
                )
                db.add(edge)

        db.commit()
        return policy_node, plan_node
