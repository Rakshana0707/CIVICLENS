"""
Phase 10.7 — Policy Evaluation Findings and Evidence Synthesis Unit Tests.
=========================================================================

Validates:
1. All 12 required attributes per `EvaluationFinding` and all 6 Phase 10.7
   evidence-classification finding types.
2. Rejection of unsupported conclusions (`STRONGER_THAN_EVIDENCE`), political
   verdicts (`POLITICAL_VERDICT_PROHIBITED`), and unsupported "why" explanations
   (`UNSUPPORTED_CAUSAL_EXPLANATION`).
3. Conflicting documents handling (`UNACKNOWLEDGED_CONFLICTING_EVIDENCE` vs
   `CONFLICTING_FINDINGS` preserving both supporting and contradicting documents).
4. Numerical consistency (`NUMERICAL_MISMATCH`) and strict distinction between
   `EXTRACTED_FROM_SOURCE_DOCUMENT` statements and `DETERMINISTIC_CALCULATION` metrics.
5. Source traceability (`MISSING_SOURCE_DOCUMENT_ID`, `UNREFERENCED_SUMMARY_STATEMENT`)
   and integration with Phase 9's Evidence Graph (`CivicGraphNode`, `CivicEvidenceEdge`).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.budget import BudgetDepartment, BudgetScheme, HistoricalScheme
from backend.models.manifesto import Manifesto, ManifestoDocument, ManifestoSource
from backend.models.promise import PoliticalPromise
from backend.models.policy_evaluation import (
    PolicyRegistryEntry,
    PolicyObjective,
    PolicyIndicator,
    EvaluationStudy,
    EvaluationFinding,
    FindingEvidenceLink,
    FindingType,
    FindingReviewStatus,
    EvaluationType,
    CausalRigorGrade,
    ConfidenceLevel,
    EvidenceStance,
    IndicatorType,
)
from backend.models.graph import (
    CivicGraphNode,
    CivicEvidenceEdge,
    GraphEntityType,
    GraphRelationshipType,
)
from backend.services.policy_evidence_synthesis_service import (
    PolicyEvidenceSynthesisService,
    UnsupportedFindingConclusionError,
    NumericalInconsistencyError,
    UntraceableSourceError,
)


@pytest.fixture
def db_session():
    """In-memory SQLite session for testing Phase 10.7 Evidence Synthesis."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    pol = PolicyRegistryEntry(
        policy_id="POL-TEST-107-PUDHUMAI",
        canonical_scheme_code="SCH-TEST-107-PUDHUMAI",
        policy_name="[TEST FIXTURE] Pudhumai Penn Higher Education Scheme",
        objectives_summary="Provide ₹1,000/month to government-school alumnae in college.",
        original_objective_wording="Provide ₹1,000/month to government-school alumnae in college.",
        intended_beneficiaries="Girls from government schools (Classes 6-12)",
        is_test_fixture=True,
    )
    obj = PolicyObjective(
        objective_id="OBJ-TEST-107",
        policy_id=pol.policy_id,
        scheme_id="SCH-TEST-107-PUDHUMAI",
        title="[TEST FIXTURE] Higher Education Enrollment Objective",
        description="Increase female transition to undergraduate degrees.",
        sector="Higher Education",
        is_test_fixture=True,
    )
    ind = PolicyIndicator(
        indicator_id="IND-TEST-107-GER",
        objective_id=obj.objective_id,
        scheme_id="SCH-TEST-107-PUDHUMAI",
        indicator_name="[TEST FIXTURE] Female College Enrollment Rate",
        indicator_type=IndicatorType.OUTCOME,
        unit="PERCENTAGE",
        definition="Share of 18-23 female cohort enrolled in higher education.",
        is_test_fixture=True,
    )
    study_desc = EvaluationStudy(
        study_id="EVAL-TEST-107-DESC",
        scheme_id="SCH-TEST-107-PUDHUMAI",
        title="[TEST FIXTURE] Descriptive Pre-Post Outcome Review 2024",
        evaluation_type=EvaluationType.EVIDENCE_BASED_OUTCOME,
        conducting_agency="State Planning Commission (Test Fixture)",
        publication_date="2024-08-15",
        methodology_description="Descriptive comparison of administrative and AISHE records.",
        causal_rigor_grade=CausalRigorGrade.GRADE_D_DESCRIPTIVE_CORRELATIONAL,
        is_causally_identified=False,
        identification_strategy="NONE",
        source_document_id="DOC-TEST-SPC-2024",
        is_test_fixture=True,
    )
    session.add_all([pol, obj, ind, study_desc])
    session.commit()
    try:
        yield session
    finally:
        session.close()


def test_1_record_all_12_attributes_and_6_evidence_classification_types(db_session):
    """
    Verify that `synthesize_finding` records all 12 required Phase 10.7 attributes
    and supports all 6 evidence-classification finding types.
    """
    finding = PolicyEvidenceSynthesisService.synthesize_finding(
        db_session,
        finding_id="FND-TEST-107-01",
        evaluation_id="EVAL-TEST-107-DESC",
        policy_id="POL-TEST-107-PUDHUMAI",
        indicator_id="IND-TEST-107-GER",
        evaluation_question="What change was observed in female college enrollment between FY2021-22 and FY2023-24?",
        finding_statement="Observed female college enrollment rate increased by 6.0 percentage points from 48.0% to 54.0%.",
        finding_type=FindingType.OUTCOME_CHANGE_OBSERVED,
        indicator_values_used={
            "baseline_period": "FY2021-22",
            "baseline_value": 48.0,
            "followup_period": "FY2023-24",
            "followup_value": 54.0,
            "unit": "PERCENTAGE",
        },
        calculation_method="ABSOLUTE_CHANGE",
        supporting_evidence=[
            {
                "source_document_id": "DOC-TEST-AISHE-2024",
                "page_number": 18,
                "table_reference": "Table 4.2",
                "quotation_excerpt": "Female Gross Enrollment Ratio in Tamil Nadu rose from 48.0% (2021-22) to 54.0% (2023-24).",
                "document_hash": "sha256:testaishe2024",
            }
        ],
        contradicting_or_contextual_evidence=[
            {
                "source_document_id": "DOC-TEST-SPC-NOTE-2024",
                "page_number": 9,
                "stance": "QUALIFIES",
                "quotation_excerpt": "Concurrent expansion of Naan Mudhalvan skill courses also occurred during FY2023-24.",
                "document_hash": "sha256:testspcnote2024",
            }
        ],
        limitations=[
            "Observational pre-post change; does not isolate causal impact from concurrent education schemes."
        ],
        review_status=FindingReviewStatus.VERIFIED,
        quantified_effect=6.0,
        confidence_level=ConfidenceLevel.HIGH,
        is_test_fixture=True,
    )

    d = finding.to_dict()
    assert d["evaluation_id"] == "EVAL-TEST-107-DESC"
    assert d["policy_id"] == "POL-TEST-107-PUDHUMAI"
    assert "What change was observed" in d["evaluation_question"]
    assert "increased by 6.0 percentage points" in d["finding_statement"]
    assert d["finding_type"] == "OUTCOME_CHANGE_OBSERVED"
    assert d["classification_nature"] == "EVIDENCE_CLASSIFICATION_NOT_POLITICAL_VERDICT"
    assert len(d["evidence_references"]) == 2
    assert d["indicator_values_used"]["deterministic_calculated_value"] == 6.0
    assert d["calculation_method"] == "ABSOLUTE_CHANGE"
    assert len(d["supporting_evidence"]) == 1
    assert len(d["contradicting_or_contextual_evidence"]) == 1
    assert len(d["limitations"]) == 1
    assert d["review_status"] == "VERIFIED"
    assert d["created_at"] is not None

    # Verify all 6 Phase 10.7 evidence classification types are valid in FindingType
    for ft_name in [
        "IMPLEMENTATION_EVIDENCE_AVAILABLE",
        "TARGET_ACHIEVEMENT_DOCUMENTED",
        "OUTCOME_CHANGE_OBSERVED",
        "CONFLICTING_FINDINGS",
        "INSUFFICIENT_EVIDENCE",
        "EVALUATION_PENDING_REVIEW",
    ]:
        assert FindingType.from_string(ft_name).value == ft_name


def test_2_unsupported_conclusions_political_verdicts_and_why_explanations(db_session):
    """
    Verify:
    1. A substantive finding (`TARGET_ACHIEVEMENT_DOCUMENTED`) with zero supporting evidence
       raises `UnsupportedFindingConclusionError("STRONGER_THAN_EVIDENCE")`.
    2. With `allow_auto_downgrade=True`, it is downgraded to `INSUFFICIENT_EVIDENCE`.
    3. Political verdict rhetoric raises `POLITICAL_VERDICT_PROHIBITED`.
    4. Unsupported causal "why" explanation raises `UNSUPPORTED_CAUSAL_EXPLANATION`.
    """
    # 1. Stronger than evidence (empty supporting_evidence) -> raises STRONGER_THAN_EVIDENCE
    with pytest.raises(UnsupportedFindingConclusionError) as exc_strong:
        PolicyEvidenceSynthesisService.synthesize_finding(
            db_session,
            finding_id="FND-TEST-107-UNSUP",
            evaluation_id="EVAL-TEST-107-DESC",
            policy_id="POL-TEST-107-PUDHUMAI",
            evaluation_question="Was the Year-1 beneficiary target achieved?",
            finding_statement="The Year-1 target of 5,00,000 beneficiaries was fully achieved.",
            finding_type=FindingType.TARGET_ACHIEVEMENT_DOCUMENTED,
            supporting_evidence=[],
            allow_auto_downgrade=False,
            is_test_fixture=True,
        )
    assert exc_strong.value.error_code == "STRONGER_THAN_EVIDENCE"

    # 2. Auto-downgrade to INSUFFICIENT_EVIDENCE when supporting_evidence is empty
    f_downgraded = PolicyEvidenceSynthesisService.synthesize_finding(
        db_session,
        finding_id="FND-TEST-107-DOWNGRADED",
        evaluation_id="EVAL-TEST-107-DESC",
        policy_id="POL-TEST-107-PUDHUMAI",
        evaluation_question="Was the Year-1 beneficiary target achieved?",
        finding_statement="Target achievement cannot be confirmed from current filings.",
        finding_type=FindingType.TARGET_ACHIEVEMENT_DOCUMENTED,
        supporting_evidence=[],
        allow_auto_downgrade=True,
        is_test_fixture=True,
    )
    assert f_downgraded.finding_type == FindingType.INSUFFICIENT_EVIDENCE
    assert f_downgraded.review_status == FindingReviewStatus.PENDING_REVIEW

    # 3. Political verdict language -> raises POLITICAL_VERDICT_PROHIBITED
    with pytest.raises(UnsupportedFindingConclusionError) as exc_verdict:
        PolicyEvidenceSynthesisService.synthesize_finding(
            db_session,
            finding_id="FND-TEST-107-VERDICT",
            evaluation_id="EVAL-TEST-107-DESC",
            policy_id="POL-TEST-107-PUDHUMAI",
            evaluation_question="What was the scheme's enrollment performance?",
            finding_statement="The scheme is a historic triumph and a political masterstroke.",
            finding_type=FindingType.IMPLEMENTATION_EVIDENCE_AVAILABLE,
            supporting_evidence=[
                {
                    "source_document_id": "DOC-TEST-01",
                    "quotation_excerpt": "4.75 lakh students enrolled.",
                }
            ],
            is_test_fixture=True,
        )
    assert exc_verdict.value.error_code == "POLITICAL_VERDICT_PROHIBITED"

    # 4. Unsupported "why" explanation on a descriptive study -> raises UNSUPPORTED_CAUSAL_EXPLANATION
    with pytest.raises(UnsupportedFindingConclusionError) as exc_why:
        PolicyEvidenceSynthesisService.synthesize_finding(
            db_session,
            finding_id="FND-TEST-107-WHY",
            evaluation_id="EVAL-TEST-107-DESC",
            policy_id="POL-TEST-107-PUDHUMAI",
            evaluation_question="Did enrollment change?",
            finding_statement="Enrollment increased by 6.0 points because of reduced household credit constraints.",
            finding_type=FindingType.OUTCOME_CHANGE_OBSERVED,
            supporting_evidence=[
                {
                    "source_document_id": "DOC-TEST-AISHE-2024",
                    "quotation_excerpt": "GER increased from 48% to 54%.",
                }
            ],
            is_test_fixture=True,
        )
    assert exc_why.value.error_code == "UNSUPPORTED_CAUSAL_EXPLANATION"


def test_3_conflicting_documents_handling(db_session):
    """
    Verify handling of conflicting documents (e.g., Departmental Policy Note vs CAG Audit Report):
    1. Attempting to record a one-sided `TARGET_ACHIEVEMENT_DOCUMENTED` finding when
       contradicting evidence exists raises `UNACKNOWLEDGED_CONFLICTING_EVIDENCE`.
    2. Recording as `CONFLICTING_FINDINGS` (or with `allow_auto_downgrade=True`) preserves
       both supporting and contradicting evidence and sets `has_contradicting_evidence = True`.
    """
    sup_ev = [
        {
            "source_document_id": "DOC-TEST-POLICY-NOTE-2024",
            "page_number": 22,
            "stance": "SUPPORTS",
            "quotation_excerpt": "Department Policy Note reports 100% of sanctioned diagnostic units commissioned.",
        }
    ]
    contra_ev = [
        {
            "source_document_id": "DOC-TEST-CAG-AUDIT-2024",
            "page_number": 54,
            "stance": "CONTRADICTS",
            "quotation_excerpt": "CAG physical verification in 8 districts found 24% of delivered diagnostic units uncommissioned due to lack of technicians.",
        }
    ]

    with pytest.raises(UnsupportedFindingConclusionError) as exc_conflict:
        PolicyEvidenceSynthesisService.synthesize_finding(
            db_session,
            finding_id="FND-TEST-107-CONFLICT-ERR",
            evaluation_id="EVAL-TEST-107-DESC",
            policy_id="POL-TEST-107-PUDHUMAI",
            evaluation_question="Were all sanctioned diagnostic units commissioned and operational?",
            finding_statement="100% of sanctioned diagnostic units were commissioned.",
            finding_type=FindingType.TARGET_ACHIEVEMENT_DOCUMENTED,
            supporting_evidence=sup_ev,
            contradicting_or_contextual_evidence=contra_ev,
            allow_auto_downgrade=False,
            is_test_fixture=True,
        )
    assert exc_conflict.value.error_code == "UNACKNOWLEDGED_CONFLICTING_EVIDENCE"

    # Now allow auto-downgrade or classify as CONFLICTING_FINDINGS -> preserves both sides
    f_conflict = PolicyEvidenceSynthesisService.synthesize_finding(
        db_session,
        finding_id="FND-TEST-107-CONFLICT-OK",
        evaluation_id="EVAL-TEST-107-DESC",
        policy_id="POL-TEST-107-PUDHUMAI",
        evaluation_question="Were all sanctioned diagnostic units commissioned and operational?",
        finding_statement=(
            "Department Policy Note reports 100% commissioning, whereas CAG physical audit "
            "documents 24% of units remaining uncommissioned in sampled districts."
        ),
        finding_type=FindingType.TARGET_ACHIEVEMENT_DOCUMENTED,
        supporting_evidence=sup_ev,
        contradicting_or_contextual_evidence=contra_ev,
        allow_auto_downgrade=True,
        is_test_fixture=True,
    )
    assert f_conflict.finding_type == FindingType.CONFLICTING_FINDINGS
    assert f_conflict.has_contradicting_evidence is True
    assert f_conflict.review_status == FindingReviewStatus.FLAGGED_CONFLICTING
    assert len(f_conflict.supporting_evidence) == 1
    assert len(f_conflict.contradicting_or_contextual_evidence) == 1


def test_4_numerical_consistency_and_extracted_vs_calculated_distinction(db_session):
    """
    Verify:
    1. Claiming `quantified_effect = 15.0` when `baseline_value = 48.0` and `followup_value = 54.0`
       (`ABSOLUTE_CHANGE = 6.0`) raises `NumericalInconsistencyError("NUMERICAL_MISMATCH")`.
    2. Extracted document statements are preserved distinctly from deterministic calculated metrics.
    """
    with pytest.raises(NumericalInconsistencyError) as exc_num:
        PolicyEvidenceSynthesisService.synthesize_finding(
            db_session,
            finding_id="FND-TEST-107-NUM-ERR",
            evaluation_id="EVAL-TEST-107-DESC",
            policy_id="POL-TEST-107-PUDHUMAI",
            evaluation_question="How much did GER change?",
            finding_statement="GER increased between baseline and follow-up.",
            finding_type=FindingType.OUTCOME_CHANGE_OBSERVED,
            indicator_values_used={"baseline_value": 48.0, "followup_value": 54.0},
            calculation_method="ABSOLUTE_CHANGE",
            quantified_effect=15.0,  # Inconsistent with 54.0 - 48.0 = 6.0!
            supporting_evidence=[
                {
                    "source_document_id": "DOC-TEST-AISHE-2024",
                    "quotation_excerpt": "GER rose from 48.0% to 54.0%.",
                }
            ],
            is_test_fixture=True,
        )
    assert exc_num.value.error_code == "NUMERICAL_MISMATCH"

    # Valid hybrid finding with both extracted statements and deterministic calculated metric
    f_hybrid = PolicyEvidenceSynthesisService.synthesize_finding(
        db_session,
        finding_id="FND-TEST-107-HYBRID",
        evaluation_id="EVAL-TEST-107-DESC",
        policy_id="POL-TEST-107-PUDHUMAI",
        evaluation_question="What was the percentage target realization in Year 1?",
        finding_statement="Reported enrollment reached 95.0% of the stated Year-1 target (4,75,000 of 5,00,000).",
        finding_type=FindingType.TARGET_ACHIEVEMENT_DOCUMENTED,
        indicator_values_used={"target_value": 500000.0, "actual_value": 475000.0},
        calculation_method="TARGET_REALIZATION_PCT",
        quantified_effect=95.0,
        supporting_evidence=[
            {
                "source_document_id": "DOC-TEST-PENKALVI-2024",
                "page_number": 4,
                "quotation_excerpt": "Total verified beneficiaries receiving DBT stood at 4,75,000 against the 5,00,000 target.",
            }
        ],
        extracted_document_statements=[
            {
                "statement_text": "4,75,000 girl students received DBT transfers in FY2023-24.",
                "source_document_id": "DOC-TEST-PENKALVI-2024",
                "page_number": 4,
            }
        ],
        is_test_fixture=True,
    )
    assert f_hybrid.statement_origin == "HYBRID_EXTRACTED_AND_CALCULATED"
    assert f_hybrid.indicator_values_used["deterministic_calculated_value"] == 95.0
    assert f_hybrid.indicator_values_used["value_origin_type"] == "DETERMINISTIC_CALCULATION"
    ext = f_hybrid.indicator_values_used["extracted_document_statements"][0]
    assert ext["statement_origin"] == "EXTRACTED_FROM_SOURCE_DOCUMENT"
    assert ext["source_document_id"] == "DOC-TEST-PENKALVI-2024"


def test_5_source_traceability_and_phase9_evidence_graph_sync(db_session):
    """
    Verify:
    1. Evidence items missing `source_document_id` or `quotation_excerpt` raise `UntraceableSourceError`.
    2. Extracted/LLM-summarized statements citing an unreferenced document ID raise `UntraceableSourceError`.
    3. `sync_finding_to_evidence_graph` creates `EVALUATION_FINDING`, `POLICY_REGISTRY_ENTRY`, and
       `EVIDENCE_DOCUMENT` nodes and `EVALUATES`, `PROVIDES_EVIDENCE_FOR`, and `CONTRADICTS` edges
       in Phase 9's evidence graph.
    """
    with pytest.raises(UntraceableSourceError) as exc_src:
        PolicyEvidenceSynthesisService.synthesize_finding(
            db_session,
            finding_id="FND-TEST-107-UNTRACEABLE",
            evaluation_id="EVAL-TEST-107-DESC",
            policy_id="POL-TEST-107-PUDHUMAI",
            evaluation_question="Did enrollment increase?",
            finding_statement="Enrollment increased.",
            finding_type=FindingType.OUTCOME_CHANGE_OBSERVED,
            supporting_evidence=[{"source_document_id": "", "quotation_excerpt": "Some quote"}],
            is_test_fixture=True,
        )
    assert exc_src.value.error_code == "MISSING_SOURCE_DOCUMENT_ID"

    with pytest.raises(UntraceableSourceError) as exc_unhedged_llm:
        PolicyEvidenceSynthesisService.synthesize_finding(
            db_session,
            finding_id="FND-TEST-107-UNREF-SUMMARY",
            evaluation_id="EVAL-TEST-107-DESC",
            policy_id="POL-TEST-107-PUDHUMAI",
            evaluation_question="Did enrollment increase?",
            finding_statement="Enrollment increased.",
            finding_type=FindingType.OUTCOME_CHANGE_OBSERVED,
            supporting_evidence=[
                {
                    "source_document_id": "DOC-TEST-AISHE-2024",
                    "quotation_excerpt": "GER rose from 48% to 54%.",
                }
            ],
            extracted_document_statements=[
                {
                    "statement_text": "Hallucinated summary statement from unknown document.",
                    "source_document_id": "DOC-GHOST-999",
                }
            ],
            is_test_fixture=True,
        )
    assert exc_unhedged_llm.value.error_code == "UNREFERENCED_SUMMARY_STATEMENT"

    # Synthesize a finding and sync it into Phase 9's Evidence Graph
    f_graph = PolicyEvidenceSynthesisService.synthesize_finding(
        db_session,
        finding_id="FND-TEST-107-GRAPH",
        evaluation_id="EVAL-TEST-107-DESC",
        policy_id="POL-TEST-107-PUDHUMAI",
        evaluation_question="How did administrative vs audit reports compare?",
        finding_statement="Administrative report and audit report show differing commissioning rates.",
        finding_type=FindingType.CONFLICTING_FINDINGS,
        supporting_evidence=[
            {
                "source_document_id": "DOC-TEST-ADMIN-2024",
                "quotation_excerpt": "100% commissioning reported.",
                "document_hash": "a" * 64,
            }
        ],
        contradicting_or_contextual_evidence=[
            {
                "source_document_id": "DOC-TEST-AUDIT-2024",
                "stance": "CONTRADICTS",
                "quotation_excerpt": "76% commissioning verified on site.",
                "document_hash": "b" * 64,
            }
        ],
        is_test_fixture=True,
    )

    sync_res = PolicyEvidenceSynthesisService.sync_finding_to_evidence_graph(db_session, f_graph)
    assert sync_res["finding_node_id"] == "NODE:FINDING:FND-TEST-107-GRAPH"
    assert sync_res["total_edges"] == 3  # 1 EVALUATES + 1 PROVIDES_EVIDENCE_FOR + 1 CONTRADICTS

    finding_node = (
        db_session.query(CivicGraphNode)
        .filter_by(node_id="NODE:FINDING:FND-TEST-107-GRAPH")
        .first()
    )
    assert finding_node is not None
    assert finding_node.entity_type == GraphEntityType.EVALUATION_FINDING

    edges = (
        db_session.query(CivicEvidenceEdge)
        .filter(
            (CivicEvidenceEdge.source_node_id == "NODE:FINDING:FND-TEST-107-GRAPH")
            | (CivicEvidenceEdge.target_node_id == "NODE:FINDING:FND-TEST-107-GRAPH")
        )
        .all()
    )
    rel_types = {e.relationship_type for e in edges}
    assert GraphRelationshipType.EVALUATES in rel_types
    assert GraphRelationshipType.PROVIDES_EVIDENCE_FOR in rel_types
    assert GraphRelationshipType.CONTRADICTS in rel_types
