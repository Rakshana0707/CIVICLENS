"""
Unit tests for Phase 5 Financial Report Cross-Validation & Reconciliation System.

Verifies:
1. Form 24A vs Audited Account >20k Schedule direct reconciliation (MATCHED, SMALL_DIFFERENCE, MATERIAL_DIFFERENCE, REQUIRES_MANUAL_REVIEW).
2. Form 24A vs Total Gross Income scope rule (NOT_COMPARABLE when subset, MATERIAL_DIFFERENCE when impossible excess).
3. Election Campaign Expenditure vs Annual Operating Expenditure window rule (NOT_COMPARABLE when subset, REQUIRES_MANUAL_REVIEW when excess).
4. Electoral Trust payout report vs Party grant disclosure.
5. Human review audit ticket workflow and state transitions.
"""

from backend.funding.cross_validator import (
    FinancialCrossValidator,
    ValidationStatus,
    HumanReviewWorkflow,
    ReviewQueueStatus
)
from tests.fixtures.phase5_crossval_fixtures import (
    MOCK_CROSSVAL_FORM24A_FY21,
    MOCK_CROSSVAL_AUDIT_MATCHED_FY21,
    MOCK_CROSSVAL_AUDIT_MISMATCH_FY21,
    MOCK_CROSSVAL_AUDIT_IMPOSSIBLE_INCOME_FY21,
    MOCK_CROSSVAL_ELECTION_EXP_TN2021,
    MOCK_CROSSVAL_ELECTION_EXP_EXCESS,
    TRUST_DISBURSEMENT_AMOUNT_MATCHED,
    TRUST_DISBURSEMENT_AMOUNT_MISMATCHED
)


class TestFinancialCrossValidator:

    def test_form24a_vs_audited_schedule_matched(self):
        rec = FinancialCrossValidator.compare_form24a_vs_audited_schedule_20k(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            form24a_contributions=MOCK_CROSSVAL_FORM24A_FY21,
            audited_statement=MOCK_CROSSVAL_AUDIT_MATCHED_FY21
        )
        assert rec.validation_status == ValidationStatus.MATCHED
        assert rec.value_a == 60130000.0
        assert rec.value_b == 60130000.0
        assert rec.difference == 0.0
        assert rec.provenance_a is not None
        assert rec.provenance_b is not None

    def test_form24a_vs_audited_schedule_mismatch(self):
        rec = FinancialCrossValidator.compare_form24a_vs_audited_schedule_20k(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            form24a_contributions=MOCK_CROSSVAL_FORM24A_FY21,
            audited_statement=MOCK_CROSSVAL_AUDIT_MISMATCH_FY21
        )
        assert rec.validation_status in (ValidationStatus.MATERIAL_DIFFERENCE, ValidationStatus.REQUIRES_MANUAL_REVIEW)
        assert rec.difference > 0.0
        assert rec.difference_percentage > 5.0

    def test_form24a_vs_total_gross_income_scope_rule(self):
        # Scope rule: Form 24A (6.013 Cr) <= Total Gross Income (30 Cr) -> NOT_COMPARABLE
        rec = FinancialCrossValidator.compare_form24a_vs_total_audited_income(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            form24a_contributions=MOCK_CROSSVAL_FORM24A_FY21,
            audited_statement=MOCK_CROSSVAL_AUDIT_MATCHED_FY21
        )
        assert rec.validation_status == ValidationStatus.NOT_COMPARABLE
        assert "Scope Difference" in rec.difference_explanation

    def test_form24a_vs_total_gross_income_impossible_excess(self):
        # Impossible statutory state: Form 24A (6.013 Cr) > Total Gross Income (4 Cr) -> MATERIAL_DIFFERENCE
        rec = FinancialCrossValidator.compare_form24a_vs_total_audited_income(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            form24a_contributions=MOCK_CROSSVAL_FORM24A_FY21,
            audited_statement=MOCK_CROSSVAL_AUDIT_IMPOSSIBLE_INCOME_FY21
        )
        assert rec.validation_status == ValidationStatus.MATERIAL_DIFFERENCE
        assert "Statutory Scope Discrepancy" in rec.difference_explanation

    def test_election_expenditure_vs_annual_audit_window_rule(self):
        # Window rule: Campaign Spending (19 Cr) <= Annual Operating Exp (22 Cr) -> NOT_COMPARABLE
        rec = FinancialCrossValidator.compare_election_expenditure_vs_annual_audit_expenditure(
            party_id="PARTY_TN_DMK",
            election_name="TN Legislative Assembly 2021",
            financial_year="FY2021-22",
            election_exp=MOCK_CROSSVAL_ELECTION_EXP_TN2021,
            annual_statement=MOCK_CROSSVAL_AUDIT_MATCHED_FY21
        )
        assert rec.validation_status == ValidationStatus.NOT_COMPARABLE
        assert "Reporting Window Scope Difference" in rec.difference_explanation

    def test_election_expenditure_vs_annual_audit_excess(self):
        # Window rule anomaly: Campaign Spending (25 Cr) > Annual Operating Exp (22 Cr) -> REQUIRES_MANUAL_REVIEW
        rec = FinancialCrossValidator.compare_election_expenditure_vs_annual_audit_expenditure(
            party_id="PARTY_TN_DMK",
            election_name="TN Legislative Assembly 2021",
            financial_year="FY2021-22",
            election_exp=MOCK_CROSSVAL_ELECTION_EXP_EXCESS,
            annual_statement=MOCK_CROSSVAL_AUDIT_MATCHED_FY21
        )
        assert rec.validation_status == ValidationStatus.REQUIRES_MANUAL_REVIEW
        assert "Reporting Window Discrepancy" in rec.difference_explanation

    def test_electoral_trust_report_vs_party_disclosure(self):
        # Matched Trust payout vs party grant disclosure
        rec_match = FinancialCrossValidator.compare_electoral_trust_report_vs_party_disclosure(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            trust_disbursement_amount=TRUST_DISBURSEMENT_AMOUNT_MATCHED,
            party_disclosed_trust_amount=50000000.0
        )
        assert rec_match.validation_status == ValidationStatus.MATCHED

        # Discrepant Trust payout vs party grant disclosure
        rec_mismatch = FinancialCrossValidator.compare_electoral_trust_report_vs_party_disclosure(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            trust_disbursement_amount=TRUST_DISBURSEMENT_AMOUNT_MISMATCHED,
            party_disclosed_trust_amount=50000000.0
        )
        assert rec_mismatch.validation_status in (ValidationStatus.MATERIAL_DIFFERENCE, ValidationStatus.REQUIRES_MANUAL_REVIEW)

    def test_human_review_workflow(self):
        workflow = HumanReviewWorkflow()

        # Step 1: Comparison with MATCHED status should NOT generate a ticket
        rec_matched = FinancialCrossValidator.compare_form24a_vs_audited_schedule_20k(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            form24a_contributions=MOCK_CROSSVAL_FORM24A_FY21,
            audited_statement=MOCK_CROSSVAL_AUDIT_MATCHED_FY21
        )
        ticket1 = workflow.create_ticket_if_needed(rec_matched)
        assert ticket1 is None

        # Step 2: Comparison with REQUIRES_MANUAL_REVIEW status MUST generate a ticket
        rec_discrepant = FinancialCrossValidator.compare_form24a_vs_audited_schedule_20k(
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            form24a_contributions=MOCK_CROSSVAL_FORM24A_FY21,
            audited_statement=MOCK_CROSSVAL_AUDIT_MISMATCH_FY21
        )
        ticket2 = workflow.create_ticket_if_needed(rec_discrepant)
        assert ticket2 is not None
        assert ticket2.review_status == ReviewQueueStatus.QUEUED_FOR_AUDIT
        assert ticket2.discrepancy_amount == rec_discrepant.difference

        # Step 3: Auditor resolves ticket with notes
        updated_ticket = workflow.update_audit_notes(
            ticket_id=ticket2.ticket_id,
            auditor_name="Senior Financial Auditor A. Kumar",
            notes="Verified against scanned PDF page 14 schedule. Discrepancy due to disaggregated regional trust grant.",
            new_status=ReviewQueueStatus.RESOLVED
        )
        assert updated_ticket is not None
        assert updated_ticket.assigned_auditor == "Senior Financial Auditor A. Kumar"
        assert updated_ticket.review_status == ReviewQueueStatus.RESOLVED
        assert updated_ticket.resolved_at is not None
