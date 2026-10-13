"""
Phase 10.7 — Policy Evaluation Findings and Evidence Synthesis Service.
=======================================================================

Connects policy evaluation results to original source documents and Phase 9's
Unified Civic Intelligence & Evidence Graph (`CivicGraphNode`, `CivicEvidenceEdge`).

Enforces 5 core epistemic and methodological guarantees:
1. All 12 required attributes are recorded per finding:
   - `evaluation_id` (`study_id`), `policy_id`, `evaluation_question`, `finding_statement`,
     `evidence_references`, `indicator_values_used`, `calculation_method`,
     `supporting_evidence`, `contradicting_or_contextual_evidence`, `limitations`,
     `review_status`, and `created_at`.
2. Supports all Phase 10.7 evidence-classification finding types:
   - `IMPLEMENTATION_EVIDENCE_AVAILABLE`
   - `TARGET_ACHIEVEMENT_DOCUMENTED`
   - `OUTCOME_CHANGE_OBSERVED`
   - `CONFLICTING_FINDINGS`
   - `INSUFFICIENT_EVIDENCE`
   - `EVALUATION_PENDING_REVIEW`
   These are strictly evidence classifications, NOT political verdicts.
3. A finding must NEVER be stronger than the evidence supporting it:
   - Rejects or downgrades substantive conclusions when supporting evidence is missing.
   - Rejects one-sided positive conclusions when contradicting documentary evidence exists
     unless classified as `CONFLICTING_FINDINGS`.
4. Deterministic numerical calculations & LLM/extraction separation:
   - Verifies that any numerical metric claimed in a finding matches the deterministic
     formula applied to `indicator_values_used`.
   - Preserves the strict distinction between `"EXTRACTED_FROM_SOURCE_DOCUMENT"` statements
     and `"DETERMINISTIC_CALCULATION"` metrics, requiring valid source document citations
     for any extracted or summarized statement.
5. No unsupported "why" explanations:
   - Rejects speculative explanations for why an outcome occurred unless backed by a
     verified causal identification design and explicit documentary evidence.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.models.policy_evaluation import (
    PolicyRegistryEntry,
    PolicyIndicator,
    EvaluationStudy,
    EvaluationFinding,
    FindingEvidenceLink,
    FindingType,
    FindingReviewStatus,
    ConfidenceLevel,
    EvidenceStance,
    CausalRigorGrade,
    EvaluationType,
)
from backend.models.graph import (
    CivicGraphNode,
    CivicEvidenceEdge,
    GraphEntityType,
    GraphRelationshipType,
    MatchingMethod,
    GraphReviewStatus,
    GraphProvenanceStatus,
)


class UnsupportedFindingConclusionError(ValueError):
    """
    Raised when a finding is stronger than its supporting evidence, ignores conflicting
    evidence, uses political verdict language, or generates an unsupported causal explanation.
    """

    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        super().__init__(f"{error_code}: {message}")


class NumericalInconsistencyError(ValueError):
    """
    Raised when a finding's claimed numerical effect conflicts with the deterministic
    calculation from its `indicator_values_used`.
    """

    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        super().__init__(f"{error_code}: {message}")


class UntraceableSourceError(ValueError):
    """
    Raised when an evidence reference, link, or extracted/summarized statement lacks
    traceable `source_document_id` and `quotation_excerpt`.
    """

    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        super().__init__(f"{error_code}: {message}")


# Prohibited political verdict phrases (findings are evidence classifications, not political verdicts)
_POLITICAL_VERDICT_PATTERNS = [
    re.compile(r"\bhistoric\s+triumph\b", re.IGNORECASE),
    re.compile(r"\btotal\s+failure\b", re.IGNORECASE),
    re.compile(r"\bcomplete\s+failure\b", re.IGNORECASE),
    re.compile(r"\bcorrupt\s+scheme\b", re.IGNORECASE),
    re.compile(r"\bpolitical\s+masterstroke\b", re.IGNORECASE),
    re.compile(r"\bbest\s+government\b", re.IGNORECASE),
    re.compile(r"\bworst\s+government\b", re.IGNORECASE),
]

# Causal explanation ("why") phrases that require verified causal identification + mechanism evidence
_CAUSAL_WHY_PATTERNS = [
    re.compile(r"\bbecause\s+of\b", re.IGNORECASE),
    re.compile(r"\bcaused\s+by\b", re.IGNORECASE),
    re.compile(r"\bdue\s+to\b", re.IGNORECASE),
    re.compile(r"\bdriven\s+by\b", re.IGNORECASE),
    re.compile(r"\battributable\s+to\b", re.IGNORECASE),
    re.compile(r"\bas\s+a\s+direct\s+result\s+of\b", re.IGNORECASE),
]

SUBSTANTIVE_FINDING_TYPES = {
    FindingType.IMPLEMENTATION_EVIDENCE_AVAILABLE,
    FindingType.TARGET_ACHIEVEMENT_DOCUMENTED,
    FindingType.OUTCOME_CHANGE_OBSERVED,
    FindingType.POSITIVE_IMPACT,
    FindingType.NEGATIVE_OR_ADVERSE,
}

ONE_SIDED_FINDING_TYPES = {
    FindingType.IMPLEMENTATION_EVIDENCE_AVAILABLE,
    FindingType.TARGET_ACHIEVEMENT_DOCUMENTED,
    FindingType.OUTCOME_CHANGE_OBSERVED,
    FindingType.POSITIVE_IMPACT,
}


class PolicyEvidenceSynthesisService:
    """
    Phase 10.7 service for synthesizing evidence-backed evaluation findings, enforcing
    numerical and epistemic consistency, and linking findings into the Phase 9 Evidence Graph.
    """

    # -----------------------------------------------------------------------
    # 1. Political Verdict & Unsupported "Why" Explanation Guardrails
    # -----------------------------------------------------------------------
    @staticmethod
    def validate_not_political_verdict(finding_statement: str) -> None:
        """
        Ensures the finding statement is an objective evidence classification rather than
        a partisan or rhetorical political verdict.
        """
        for pat in _POLITICAL_VERDICT_PATTERNS:
            if pat.search(finding_statement):
                raise UnsupportedFindingConclusionError(
                    "POLITICAL_VERDICT_PROHIBITED",
                    f"Finding statement contains prohibited political verdict language matching '{pat.pattern}'. "
                    "Findings must be objective evidence classifications, not political verdicts.",
                )

    @staticmethod
    def validate_no_unsupported_why_explanation(
        finding_statement: str,
        study: EvaluationStudy,
        supporting_evidence: List[Dict[str, Any]],
    ) -> None:
        """
        Enforces: 'Do not generate unsupported explanations for why an outcome occurred.'
        If `finding_statement` contains causal mechanism ("why") phrasing ('because of',
        'caused by', 'due to', 'driven by', 'attributable to'), it is rejected unless:
        1. `study` has verified causal identification (`is_causally_identified=True` and Grade A/B), AND
        2. At least one supporting evidence passage explicitly documents the mechanism
           (`documents_causal_mechanism=True`).
        """
        has_why_phrase = any(pat.search(finding_statement) for pat in _CAUSAL_WHY_PATTERNS)
        if not has_why_phrase:
            return

        rigor = (
            study.causal_rigor_grade
            if isinstance(study.causal_rigor_grade, CausalRigorGrade)
            else CausalRigorGrade.from_string(study.causal_rigor_grade)
        )
        is_causal_study = bool(study.is_causally_identified) and rigor in (
            CausalRigorGrade.GRADE_A_EXPERIMENTAL,
            CausalRigorGrade.GRADE_B_QUASI_EXPERIMENTAL,
        )
        has_mechanism_evidence = any(
            bool(item.get("documents_causal_mechanism")) for item in supporting_evidence
        )

        if not (is_causal_study and has_mechanism_evidence):
            raise UnsupportedFindingConclusionError(
                "UNSUPPORTED_CAUSAL_EXPLANATION",
                "Finding statement contains an unsupported causal explanation ('why' an outcome occurred) "
                "without both a verified Grade A/B causal study design and documentary mechanism evidence.",
            )

    # -----------------------------------------------------------------------
    # 2. Source Traceability & Extracted vs Calculated Distinction
    # -----------------------------------------------------------------------
    @staticmethod
    def validate_and_normalize_evidence_items(
        items: List[Dict[str, Any]],
        *,
        default_stance: EvidenceStance,
    ) -> List[Dict[str, Any]]:
        """
        Validates that every evidence item has a traceable `source_document_id`,
        `quotation_excerpt`, and explicit `statement_origin` (`EXTRACTED_FROM_SOURCE_DOCUMENT`
        or `DETERMINISTIC_CALCULATION`).
        """
        normalized: List[Dict[str, Any]] = []
        for idx, item in enumerate(items):
            doc_id = str(item.get("source_document_id") or "").strip()
            excerpt = str(item.get("quotation_excerpt") or "").strip()
            if not doc_id:
                raise UntraceableSourceError(
                    "MISSING_SOURCE_DOCUMENT_ID",
                    f"Evidence item at index {idx} is missing a traceable 'source_document_id'.",
                )
            if not excerpt:
                raise UntraceableSourceError(
                    "MISSING_QUOTATION_EXCERPT",
                    f"Evidence item for document '{doc_id}' is missing a verbatim 'quotation_excerpt'.",
                )

            stance_raw = item.get("stance", default_stance.value)
            stance_enum = (
                stance_raw
                if isinstance(stance_raw, EvidenceStance)
                else EvidenceStance(str(stance_raw).strip().upper())
            )
            origin = str(item.get("statement_origin") or "EXTRACTED_FROM_SOURCE_DOCUMENT").strip().upper()
            if origin not in ("EXTRACTED_FROM_SOURCE_DOCUMENT", "DETERMINISTIC_CALCULATION"):
                raise ValueError(f"Invalid statement_origin: {origin}")

            normalized.append(
                {
                    "link_id": item.get("link_id") or f"LNK-{doc_id}-{idx+1:02d}",
                    "source_document_id": doc_id,
                    "source_passage_id": item.get("source_passage_id"),
                    "page_number": item.get("page_number"),
                    "table_reference": item.get("table_reference"),
                    "stance": stance_enum.value,
                    "quotation_excerpt": excerpt,
                    "statement_origin": origin,
                    "source_credibility_tier": item.get("source_credibility_tier", "TIER_1_STATUTORY"),
                    "alignment_score": float(item.get("alignment_score", 1.0)),
                    "document_hash": item.get("document_hash"),
                    "documents_causal_mechanism": bool(item.get("documents_causal_mechanism", False)),
                }
            )
        return normalized

    @staticmethod
    def validate_extracted_vs_calculated_statements(
        extracted_statements: Optional[List[Dict[str, Any]]],
        known_document_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """
        If extracted or LLM-summarized document statements are attached, requires that
        each statement cites a `source_document_id` present in the finding's `evidence_references`
        and is explicitly tagged `statement_origin = "EXTRACTED_FROM_SOURCE_DOCUMENT"`.
        """
        if not extracted_statements:
            return []

        known_set = set(known_document_ids)
        verified_statements: List[Dict[str, Any]] = []
        for idx, stmt in enumerate(extracted_statements):
            doc_id = str(stmt.get("source_document_id") or "").strip()
            text = str(stmt.get("statement_text") or "").strip()
            if not doc_id or doc_id not in known_set:
                raise UntraceableSourceError(
                    "UNREFERENCED_SUMMARY_STATEMENT",
                    f"Summarized/extracted statement at index {idx} references document '{doc_id}', "
                    "which is not in the finding's verified evidence_references.",
                )
            if not text:
                raise UntraceableSourceError(
                    "EMPTY_SUMMARY_STATEMENT",
                    f"Summarized statement for document '{doc_id}' cannot be empty.",
                )
            verified_statements.append(
                {
                    "statement_text": text,
                    "source_document_id": doc_id,
                    "page_number": stmt.get("page_number"),
                    "statement_origin": "EXTRACTED_FROM_SOURCE_DOCUMENT",
                }
            )
        return verified_statements

    # -----------------------------------------------------------------------
    # 3. Deterministic Calculation & Numerical Consistency Verifier
    # -----------------------------------------------------------------------
    @staticmethod
    def verify_and_compute_deterministic_metrics(
        indicator_values_used: Optional[Dict[str, Any]],
        calculation_method: Optional[str],
        quantified_effect: Optional[float] = None,
    ) -> Tuple[Dict[str, Any], Optional[float]]:
        """
        Performs deterministic arithmetic on `indicator_values_used` and verifies that
        any caller-supplied `quantified_effect` or `claimed_result` is numerically
        consistent with the deterministic formula.
        Supported deterministic `calculation_method` codes:
        - `ABSOLUTE_CHANGE`: `followup_value - baseline_value`
        - `PERCENTAGE_CHANGE`: `((followup_value - baseline_value) / baseline_value) * 100`
        - `TARGET_REALIZATION_PCT`: `(actual_value / target_value) * 100`
        - `BUDGET_EXECUTION_RATE_PCT`: `(actual_expenditure / budget_estimate) * 100`
        - `DIRECT_OBSERVATION`: `observed_value`
        """
        vals = dict(indicator_values_used or {})
        if not vals:
            return {}, quantified_effect

        method = (calculation_method or "ABSOLUTE_CHANGE").strip().upper()
        computed_val: Optional[float] = None

        if "ABSOLUTE_CHANGE" in method or method == "Y_FOLLOWUP - Y_BASELINE":
            b = vals.get("baseline_value")
            f = vals.get("followup_value")
            if b is not None and f is not None:
                computed_val = round(float(f) - float(b), 4)
        elif "PERCENTAGE_CHANGE" in method:
            b = vals.get("baseline_value")
            f = vals.get("followup_value")
            if b is not None and f is not None and float(b) > 0:
                computed_val = round(((float(f) - float(b)) / float(b)) * 100.0, 2)
        elif "TARGET_REALIZATION_PCT" in method or "PTRR" in method:
            t = vals.get("target_value")
            a = vals.get("actual_value")
            if t is not None and a is not None and float(t) > 0:
                computed_val = round((float(a) / float(t)) * 100.0, 2)
        elif "BUDGET_EXECUTION_RATE_PCT" in method or "BER" in method:
            be = vals.get("budget_estimate")
            act = vals.get("actual_expenditure")
            if be is not None and act is not None and float(be) > 0:
                computed_val = round((float(act) / float(be)) * 100.0, 2)
        elif "DIRECT_OBSERVATION" in method:
            if vals.get("observed_value") is not None:
                computed_val = round(float(vals["observed_value"]), 4)

        if computed_val is not None:
            vals["deterministic_calculated_value"] = computed_val
            vals["value_origin_type"] = "DETERMINISTIC_CALCULATION"

            if quantified_effect is not None and abs(float(quantified_effect) - computed_val) > 0.02:
                raise NumericalInconsistencyError(
                    "NUMERICAL_MISMATCH",
                    f"Claimed quantified_effect ({quantified_effect}) is inconsistent with "
                    f"deterministic calculation ({computed_val}) using method '{calculation_method}' "
                    f"and inputs {vals}.",
                )
            quantified_effect = computed_val

        return vals, quantified_effect

    # -----------------------------------------------------------------------
    # 4. Synthesize Evidence-Backed Evaluation Finding
    # -----------------------------------------------------------------------
    @classmethod
    def synthesize_finding(
        cls,
        db: Session,
        *,
        finding_id: str,
        evaluation_id: str,
        policy_id: str,
        evaluation_question: str,
        finding_statement: str,
        finding_type: FindingType | str,
        indicator_id: Optional[str] = None,
        indicator_values_used: Optional[Dict[str, Any]] = None,
        calculation_method: str = "ABSOLUTE_CHANGE",
        supporting_evidence: Optional[List[Dict[str, Any]]] = None,
        contradicting_or_contextual_evidence: Optional[List[Dict[str, Any]]] = None,
        extracted_document_statements: Optional[List[Dict[str, Any]]] = None,
        limitations: Optional[List[str]] = None,
        review_status: FindingReviewStatus | str = FindingReviewStatus.PENDING_REVIEW,
        quantified_effect: Optional[float] = None,
        p_value: Optional[float] = None,
        confidence_level: ConfidenceLevel | str = ConfidenceLevel.MODERATE,
        allow_auto_downgrade: bool = False,
        is_test_fixture: bool = False,
    ) -> EvaluationFinding:
        """
        Synthesizes, validates, and persists an `EvaluationFinding` along with its
        `FindingEvidenceLink` records.
        Enforces:
        1. Political verdict prohibition.
        2. Unsupported causal "why" explanation prohibition.
        3. Source traceability on all supporting, contradicting, and extracted statements.
        4. Deterministic numerical consistency against `indicator_values_used`.
        5. Evidence-strength ceiling: a finding can never be stronger than its supporting
           evidence, and conflicting documents require `CONFLICTING_FINDINGS` classification.
        """
        if not evaluation_question or not evaluation_question.strip():
            raise ValueError("evaluation_question is required for every evaluation finding.")
        if not finding_statement or not finding_statement.strip():
            raise ValueError("finding_statement is required for every evaluation finding.")

        study = db.query(EvaluationStudy).filter_by(study_id=evaluation_id).first()
        if not study:
            raise ValueError(f"EvaluationStudy '{evaluation_id}' not found.")

        # 1. Validate objective evidence language (no political verdicts)
        cls.validate_not_political_verdict(finding_statement)

        # 2. Validate and normalize supporting & contradicting/contextual evidence links
        norm_supporting = cls.validate_and_normalize_evidence_items(
            supporting_evidence or [], default_stance=EvidenceStance.SUPPORTS
        )
        norm_contra_ctx = cls.validate_and_normalize_evidence_items(
            contradicting_or_contextual_evidence or [], default_stance=EvidenceStance.CONTRADICTS
        )

        # 3. Validate no unsupported causal "why" explanation
        cls.validate_no_unsupported_why_explanation(finding_statement, study, norm_supporting)

        # 4. Collect all verified evidence references and validate any extracted/summarized statements
        all_doc_ids: List[str] = []
        evidence_references: List[Dict[str, Any]] = []
        for item in norm_supporting + norm_contra_ctx:
            doc_id = item["source_document_id"]
            if doc_id not in all_doc_ids:
                all_doc_ids.append(doc_id)
            evidence_references.append(
                {
                    "source_document_id": doc_id,
                    "page_number": item.get("page_number"),
                    "table_reference": item.get("table_reference"),
                    "stance": item["stance"],
                    "document_hash": item.get("document_hash"),
                }
            )

        verified_extracted = cls.validate_extracted_vs_calculated_statements(
            extracted_document_statements, all_doc_ids
        )

        # 5. Verify deterministic numerical consistency
        verified_values, verified_effect = cls.verify_and_compute_deterministic_metrics(
            indicator_values_used=indicator_values_used,
            calculation_method=calculation_method,
            quantified_effect=quantified_effect,
        )
        if verified_extracted:
            verified_values["extracted_document_statements"] = verified_extracted

        # 6. Enforce Evidence-Strength Ceiling: "A finding must never be stronger than the evidence supporting it"
        requested_type = FindingType.from_string(finding_type)
        req_review = FindingReviewStatus.from_string(review_status)
        effective_limitations = list(limitations or [])

        has_hard_contradiction = any(
            item["stance"] == EvidenceStance.CONTRADICTS.value for item in norm_contra_ctx
        )

        # Check A: Substantive finding with zero supporting evidence
        if requested_type in SUBSTANTIVE_FINDING_TYPES and len(norm_supporting) == 0:
            if not allow_auto_downgrade:
                raise UnsupportedFindingConclusionError(
                    "STRONGER_THAN_EVIDENCE",
                    f"Cannot assert finding_type='{requested_type.value}' with zero supporting evidence links. "
                    "A finding must never be stronger than the evidence supporting it.",
                )
            requested_type = FindingType.INSUFFICIENT_EVIDENCE
            req_review = FindingReviewStatus.PENDING_REVIEW
            effective_limitations.append(
                "AUTO_DOWNGRADED_INSUFFICIENT_EVIDENCE: Substantive conclusion downgraded because supporting_evidence is empty."
            )

        # Check B: One-sided positive/substantive finding ignoring contradicting documentary evidence
        if has_hard_contradiction and requested_type in ONE_SIDED_FINDING_TYPES:
            if not allow_auto_downgrade:
                raise UnsupportedFindingConclusionError(
                    "UNACKNOWLEDGED_CONFLICTING_EVIDENCE",
                    f"Cannot assert one-sided finding_type='{requested_type.value}' when contradicting "
                    "documentary evidence is present. Must classify as CONFLICTING_FINDINGS or MIXED_RESULTS.",
                )
            requested_type = FindingType.CONFLICTING_FINDINGS
            req_review = FindingReviewStatus.FLAGGED_CONFLICTING
            effective_limitations.append(
                "AUTO_DOWNGRADED_CONFLICTING_EVIDENCE: Reclassified to CONFLICTING_FINDINGS due to contradicting source documents."
            )

        if has_hard_contradiction and req_review == FindingReviewStatus.VERIFIED:
            req_review = FindingReviewStatus.FLAGGED_CONFLICTING

        statement_origin = (
            "HYBRID_EXTRACTED_AND_CALCULATED"
            if (verified_extracted and "deterministic_calculated_value" in verified_values)
            else (
                "EXTRACTED_FROM_SOURCE_DOCUMENT"
                if verified_extracted
                else "DETERMINISTIC_CALCULATION"
            )
        )

        finding = EvaluationFinding(
            finding_id=finding_id,
            study_id=evaluation_id,
            policy_id=policy_id,
            indicator_id=indicator_id,
            evaluation_question=evaluation_question.strip(),
            finding_type=requested_type,
            finding_text=finding_statement.strip(),
            statement_origin=statement_origin,
            evidence_references=evidence_references,
            indicator_values_used=verified_values,
            calculation_method=calculation_method,
            supporting_evidence=norm_supporting,
            contradicting_or_contextual_evidence=norm_contra_ctx,
            limitations=effective_limitations,
            review_status=req_review,
            quantified_effect=verified_effect,
            p_value=p_value,
            confidence_level=(
                confidence_level
                if isinstance(confidence_level, ConfidenceLevel)
                else ConfidenceLevel(str(confidence_level).strip().upper())
            ),
            has_contradicting_evidence=has_hard_contradiction,
            is_test_fixture=is_test_fixture,
        )
        db.add(finding)

        # Persist granular FindingEvidenceLink rows
        for item in norm_supporting + norm_contra_ctx:
            link_obj = FindingEvidenceLink(
                link_id=f"{finding_id}:{item['link_id']}",
                finding_id=finding_id,
                source_document_id=item["source_document_id"],
                source_passage_id=item.get("source_passage_id"),
                page_number=item.get("page_number"),
                table_reference=item.get("table_reference"),
                stance=EvidenceStance(item["stance"]),
                quotation_excerpt=item["quotation_excerpt"],
                source_credibility_tier=item["source_credibility_tier"],
                alignment_score=item["alignment_score"],
                document_hash=item.get("document_hash"),
                is_test_fixture=is_test_fixture,
            )
            db.add(link_obj)

        db.commit()
        db.refresh(finding)
        return finding

    # -----------------------------------------------------------------------
    # 5. Phase 9 Evidence Graph Integration
    # -----------------------------------------------------------------------
    @staticmethod
    def sync_finding_to_evidence_graph(
        db: Session,
        finding: EvaluationFinding,
    ) -> Dict[str, Any]:
        """
        Connects an `EvaluationFinding` and all its supporting, contradicting, and
        contextual source documents into Phase 9's Unified Civic Intelligence & Evidence Graph
        (`CivicGraphNode` and `CivicEvidenceEdge`) without creating a second graph.
        """
        finding_node_id = f"NODE:FINDING:{finding.finding_id}"
        finding_node = db.query(CivicGraphNode).filter_by(node_id=finding_node_id).first()
        if not finding_node:
            finding_node = CivicGraphNode(
                node_id=finding_node_id,
                entity_type=GraphEntityType.EVALUATION_FINDING,
                canonical_id=finding.finding_id,
                label=f"[{finding.finding_type.value}] {finding.finding_text[:80]}",
                source_phase="PHASE_10",
                attributes_json={
                    "evaluation_id": finding.study_id,
                    "policy_id": finding.policy_id,
                    "finding_type": finding.finding_type.value,
                    "review_status": finding.review_status.value,
                    "has_contradicting_evidence": finding.has_contradicting_evidence,
                    "statement_origin": finding.statement_origin,
                },
                is_test_fixture=finding.is_test_fixture,
            )
            db.add(finding_node)

        created_edges: List[str] = []

        # Link Finding -> Policy node if policy_id is present
        if finding.policy_id:
            policy_node_id = f"NODE:POLICY:{finding.policy_id}"
            policy_node = db.query(CivicGraphNode).filter_by(node_id=policy_node_id).first()
            if not policy_node:
                policy_node = CivicGraphNode(
                    node_id=policy_node_id,
                    entity_type=GraphEntityType.POLICY_REGISTRY_ENTRY,
                    canonical_id=finding.policy_id,
                    label=f"Policy {finding.policy_id}",
                    source_phase="PHASE_10",
                    attributes_json={"policy_id": finding.policy_id},
                    is_test_fixture=finding.is_test_fixture,
                )
                db.add(policy_node)

            eval_edge_id = f"EDGE:EVALUATES:{finding.finding_id}:{finding.policy_id}"
            if not db.query(CivicEvidenceEdge).filter_by(edge_id=eval_edge_id).first():
                primary_doc = (
                    finding.evidence_references[0]["source_document_id"]
                    if finding.evidence_references
                    else f"STUDY:{finding.study_id}"
                )
                edge = CivicEvidenceEdge(
                    edge_id=eval_edge_id,
                    source_node_id=finding_node_id,
                    target_node_id=policy_node_id,
                    relationship_type=GraphRelationshipType.EVALUATES,
                    evidence_reference=finding.finding_text,
                    source_document_id=primary_doc,
                    source_document_hash="0" * 64,
                    matching_method=MatchingMethod.DETERMINISTIC_ID,
                    confidence_score=1.0,
                    review_status=(
                        GraphReviewStatus.VERIFIED
                        if finding.review_status == FindingReviewStatus.VERIFIED
                        else GraphReviewStatus.PENDING_REVIEW
                    ),
                    provenance_status=GraphProvenanceStatus.VALID,
                    epistemic_notes="; ".join(finding.limitations or []),
                    is_test_fixture=finding.is_test_fixture,
                )
                db.add(edge)
                created_edges.append(eval_edge_id)

        # Link each supporting, contradicting, and contextual document node -> Finding node
        all_ev_items = list(finding.supporting_evidence or []) + list(
            finding.contradicting_or_contextual_evidence or []
        )
        for idx, item in enumerate(all_ev_items):
            doc_id = item["source_document_id"]
            doc_node_id = f"NODE:DOC:{doc_id}"
            doc_node = db.query(CivicGraphNode).filter_by(node_id=doc_node_id).first()
            if not doc_node:
                doc_node = CivicGraphNode(
                    node_id=doc_node_id,
                    entity_type=GraphEntityType.EVIDENCE_DOCUMENT,
                    canonical_id=doc_id,
                    label=f"Source Document {doc_id}",
                    source_phase="PHASE_10",
                    attributes_json={
                        "credibility_tier": item.get("source_credibility_tier"),
                        "document_hash": item.get("document_hash"),
                    },
                    is_test_fixture=finding.is_test_fixture,
                )
                db.add(doc_node)

            stance = item.get("stance", "SUPPORTS")
            if stance == EvidenceStance.CONTRADICTS.value:
                rel_type = GraphRelationshipType.CONTRADICTS
            elif stance in (EvidenceStance.QUALIFIES.value, EvidenceStance.NEUTRAL.value):
                rel_type = GraphRelationshipType.CONTEXTUALIZES
            else:
                rel_type = GraphRelationshipType.PROVIDES_EVIDENCE_FOR

            edge_id = f"EDGE:{rel_type.value.upper()}:{doc_id}:{finding.finding_id}:{idx+1}"
            if not db.query(CivicEvidenceEdge).filter_by(edge_id=edge_id).first():
                ev_edge = CivicEvidenceEdge(
                    edge_id=edge_id,
                    source_node_id=doc_node_id,
                    target_node_id=finding_node_id,
                    relationship_type=rel_type,
                    evidence_reference=item["quotation_excerpt"],
                    source_document_id=doc_id,
                    source_document_hash=item.get("document_hash") or ("0" * 64),
                    matching_method=MatchingMethod.DETERMINISTIC_ID,
                    confidence_score=float(item.get("alignment_score", 1.0)),
                    review_status=GraphReviewStatus.VERIFIED,
                    provenance_status=GraphProvenanceStatus.VALID,
                    properties_json={
                        "page_number": item.get("page_number"),
                        "table_reference": item.get("table_reference"),
                    },
                    is_test_fixture=finding.is_test_fixture,
                )
                db.add(ev_edge)
                created_edges.append(edge_id)

        db.commit()
        return {
            "finding_node_id": finding_node_id,
            "edges_created": created_edges,
            "total_edges": len(created_edges),
        }
