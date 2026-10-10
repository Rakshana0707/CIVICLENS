"""
Phase 5 — Financial Document Cross-Validation & Reconciliation Engine.

Cross-validates statutory disclosures across disparate sources:
1. ECI Contribution Reports (Form 24A)
2. ECI Annual Audit Reports
3. Electoral Trust Contribution Reports
4. Election Expenditure Statements
5. ADR Analytical Reports

Enforces strict domain rules:
- Does NOT assume identical reporting windows, thresholds, or accounting definitions.
- Distinguishes genuine numerical mismatches from non-comparable reporting scopes.
- Maintains document & page provenance references for every comparison.
- Provides a human-review workflow for unresolved discrepancies.
"""

import math
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from backend.schemas.funding import ContributionSchema, FinancialStatementSchema, ElectionExpenditureSchema

logger = logging.getLogger("civiclens.funding.crossval")


class ValidationStatus:
    MATCHED = "MATCHED"
    SMALL_DIFFERENCE = "SMALL_DIFFERENCE"
    MATERIAL_DIFFERENCE = "MATERIAL_DIFFERENCE"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    REQUIRES_MANUAL_REVIEW = "REQUIRES_MANUAL_REVIEW"


class ReviewQueueStatus:
    QUEUED_FOR_AUDIT = "QUEUED_FOR_AUDIT"
    IN_REVIEW = "IN_REVIEW"
    RESOLUTION_NOTES_ADDED = "RESOLUTION_NOTES_ADDED"
    RESOLVED = "RESOLVED"


@dataclass
class ProvenanceRef:
    document_id: str
    source_name: str
    page_number: Optional[int] = None
    table_number: Optional[int] = None


@dataclass
class ComparisonRecord:
    """Standardized comparison object between two financial documents or report sources."""
    comparison_id: str
    party_id: str
    financial_year: str
    source_document_a: str  # Document ID or type of Document A
    source_document_b: str  # Document ID or type of Document B
    metric_name: str
    value_a: Optional[float]
    value_b: Optional[float]
    difference: float
    difference_percentage: float
    difference_explanation: str
    validation_status: str
    provenance_a: Optional[ProvenanceRef] = None
    provenance_b: Optional[ProvenanceRef] = None
    methodology_version: str = "v1.0"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class HumanReviewTicket:
    """Ticket object for the human-review audit workflow."""
    ticket_id: str
    comparison_id: str
    party_id: str
    financial_year: str
    metric_name: str
    discrepancy_amount: float
    review_status: str = ReviewQueueStatus.QUEUED_FOR_AUDIT
    assigned_auditor: Optional[str] = None
    audit_notes: Optional[str] = None
    resolved_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FinancialCrossValidator:
    """Engine for comparing statutory financial disclosures across sources."""

    METHODOLOGY_VERSION = "v1.0"

    @classmethod
    def compare_form24a_vs_audited_schedule_20k(
        cls,
        party_id: str,
        financial_year: str,
        form24a_contributions: List[ContributionSchema],
        audited_statement: FinancialStatementSchema,
        doc_a_id: str = "ECI_Form24A",
        doc_b_id: str = "ECI_Audited_Accounts"
    ) -> ComparisonRecord:
        """
        Cross-validates Form 24A extracted itemized sum against Audited Accounts Schedule for > 20k donations.
        Both sources share identical statutory coverage (> ₹20,000 threshold).
        """
        val_a = sum(c.amount for c in form24a_contributions if c.amount and c.amount > 0)
        
        income_cats = audited_statement.income_categories or {}
        val_b = income_cats.get("donations_above_20k") or income_cats.get("contributions_above_20k")

        comp_id = f"COMP_{party_id}_{financial_year}_24A_VS_AUDIT_20K"

        if val_b is None:
            return ComparisonRecord(
                comparison_id=comp_id,
                party_id=party_id,
                financial_year=financial_year,
                source_document_a=doc_a_id,
                source_document_b=doc_b_id,
                metric_name="CONTRIBUTIONS_ABOVE_20K_SCHEDULE",
                value_a=round(val_a, 2),
                value_b=None,
                difference=0.0,
                difference_percentage=0.0,
                difference_explanation="Audited statement does not disaggregate a specific >20k donation schedule line item.",
                validation_status=ValidationStatus.NOT_COMPARABLE,
                provenance_a=ProvenanceRef(document_id=doc_a_id, source_name="ECI Form 24A"),
                provenance_b=ProvenanceRef(document_id=doc_b_id, source_name="ECI Audit Accounts")
            )

        diff = abs(val_a - val_b)
        diff_pct = (diff / val_b) * 100.0 if val_b > 0 else 0.0

        if diff == 0.0 or diff_pct < 1.0:
            status = ValidationStatus.MATCHED
            exp = "Form 24A itemized sum matches Audited Account reported >20k schedule within 1% tolerance."
        elif diff_pct < 5.0:
            status = ValidationStatus.SMALL_DIFFERENCE
            exp = f"Minor variance of INR {diff:,.2f} ({diff_pct:.2f}%) between Form 24A sum and Audited schedule. Likely attributable to rounding or small disaggregated items."
        elif diff_pct < 15.0:
            status = ValidationStatus.MATERIAL_DIFFERENCE
            exp = f"Material variance of INR {diff:,.2f} ({diff_pct:.2f}%) detected between Form 24A sum and Audited schedule."
        else:
            status = ValidationStatus.REQUIRES_MANUAL_REVIEW
            exp = f"Significant discrepancy of INR {diff:,.2f} ({diff_pct:.2f}%) detected. Requires manual auditor verification of filing pages."

        return ComparisonRecord(
            comparison_id=comp_id,
            party_id=party_id,
            financial_year=financial_year,
            source_document_a=doc_a_id,
            source_document_b=doc_b_id,
            metric_name="CONTRIBUTIONS_ABOVE_20K_SCHEDULE",
            value_a=round(val_a, 2),
            value_b=round(val_b, 2),
            difference=round(diff, 2),
            difference_percentage=round(diff_pct, 2),
            difference_explanation=exp,
            validation_status=status,
            provenance_a=ProvenanceRef(document_id=doc_a_id, source_name="ECI Form 24A"),
            provenance_b=ProvenanceRef(document_id=doc_b_id, source_name="ECI Audit Accounts")
        )

    @classmethod
    def compare_form24a_vs_total_audited_income(
        cls,
        party_id: str,
        financial_year: str,
        form24a_contributions: List[ContributionSchema],
        audited_statement: FinancialStatementSchema,
        doc_a_id: str = "ECI_Form24A",
        doc_b_id: str = "ECI_Audited_Accounts"
    ) -> ComparisonRecord:
        """
        Compares Form 24A disclosed total against Audited Total Gross Income.
        ENFORCES SCOPE RULE: These documents have different reporting scopes!
        Form 24A covers ONLY donations > ₹20k. Audited Income includes coupons, interest, bonds, and small donations.
        """
        val_a = sum(c.amount for c in form24a_contributions if c.amount and c.amount > 0)
        val_b = audited_statement.total_income_reported

        comp_id = f"COMP_{party_id}_{financial_year}_24A_VS_TOTAL_INCOME"

        if val_b is None:
            return ComparisonRecord(
                comparison_id=comp_id,
                party_id=party_id,
                financial_year=financial_year,
                source_document_a=doc_a_id,
                source_document_b=doc_b_id,
                metric_name="FORM24A_VS_TOTAL_GROSS_INCOME",
                value_a=round(val_a, 2),
                value_b=None,
                difference=0.0,
                difference_percentage=0.0,
                difference_explanation="Audited total gross income is missing from statement.",
                validation_status=ValidationStatus.NOT_COMPARABLE
            )

        diff = abs(val_a - val_b)
        diff_pct = (diff / val_b) * 100.0 if val_b > 0 else 0.0

        if val_a <= val_b:
            # Expected Scope Behavior: Form 24A <= Total Audited Income
            status = ValidationStatus.NOT_COMPARABLE
            exp = (
                f"Scope Difference: Form 24A disclosed total (INR {val_a:,.2f}) is a subset of Total Audited Income "
                f"(INR {val_b:,.2f}). Form 24A covers only donations > INR 20,000, whereas Total Income includes "
                f"electoral bonds, coupons, bank interest, and small contributions."
            )
        else:
            # Impossible Statutory State: Form 24A disclosed > Total Audited Income
            status = ValidationStatus.MATERIAL_DIFFERENCE
            exp = (
                f"Statutory Scope Discrepancy: Form 24A disclosed donations (INR {val_a:,.2f}) exceed "
                f"Total Audited Income (INR {val_b:,.2f}) by INR {diff:,.2f}. Indicates possible reporting boundary mismatch or missing income schedules."
            )

        return ComparisonRecord(
            comparison_id=comp_id,
            party_id=party_id,
            financial_year=financial_year,
            source_document_a=doc_a_id,
            source_document_b=doc_b_id,
            metric_name="FORM24A_VS_TOTAL_GROSS_INCOME",
            value_a=round(val_a, 2),
            value_b=round(val_b, 2),
            difference=round(diff, 2),
            difference_percentage=round(diff_pct, 2),
            difference_explanation=exp,
            validation_status=status,
            provenance_a=ProvenanceRef(document_id=doc_a_id, source_name="ECI Form 24A"),
            provenance_b=ProvenanceRef(document_id=doc_b_id, source_name="ECI Audit Accounts")
        )

    @classmethod
    def compare_election_expenditure_vs_annual_audit_expenditure(
        cls,
        party_id: str,
        election_name: str,
        financial_year: str,
        election_exp: ElectionExpenditureSchema,
        annual_statement: FinancialStatementSchema,
        doc_a_id: str = "ECI_Election_Expenditure",
        doc_b_id: str = "ECI_Audited_Accounts"
    ) -> ComparisonRecord:
        """
        Compares Election Campaign Expenditure against Annual Audited Expenditure.
        ENFORCES TIMING & SCOPE RULE: Campaign expenditure covers a specific 75-day election window,
        whereas Annual Audit covers a 12-month fiscal year.
        """
        val_a = election_exp.reported_totals or sum(election_exp.expenditure_categories.values())
        val_b = annual_statement.total_expenditure_reported

        comp_id = f"COMP_{party_id}_{financial_year}_ELECTION_VS_ANNUAL_EXP"

        if val_b is None:
            return ComparisonRecord(
                comparison_id=comp_id,
                party_id=party_id,
                financial_year=financial_year,
                source_document_a=doc_a_id,
                source_document_b=doc_b_id,
                metric_name="ELECTION_VS_ANNUAL_EXPENDITURE",
                value_a=round(val_a, 2),
                value_b=None,
                difference=0.0,
                difference_percentage=0.0,
                difference_explanation="Annual audited expenditure is missing.",
                validation_status=ValidationStatus.NOT_COMPARABLE
            )

        diff = abs(val_a - val_b)
        diff_pct = (diff / val_b) * 100.0 if val_b > 0 else 0.0

        if val_a <= val_b:
            status = ValidationStatus.NOT_COMPARABLE
            exp = (
                f"Reporting Window Scope Difference: Campaign expenditure for {election_name} (INR {val_a:,.2f}) "
                f"represents campaign spending during the election period, which is part of the full annual operating expenditure "
                f"(INR {val_b:,.2f}) for {financial_year}."
            )
        else:
            status = ValidationStatus.REQUIRES_MANUAL_REVIEW
            exp = (
                f"Reporting Window Discrepancy: Declared election campaign expenditure (INR {val_a:,.2f}) "
                f"exceeds total annual operating expenditure (INR {val_b:,.2f}) for {financial_year}. "
                f"Requires manual auditor verification of election filing dates vs accounting year cutoffs."
            )

        return ComparisonRecord(
            comparison_id=comp_id,
            party_id=party_id,
            financial_year=financial_year,
            source_document_a=doc_a_id,
            source_document_b=doc_b_id,
            metric_name="ELECTION_VS_ANNUAL_EXPENDITURE",
            value_a=round(val_a, 2),
            value_b=round(val_b, 2),
            difference=round(diff, 2),
            difference_percentage=round(diff_pct, 2),
            difference_explanation=exp,
            validation_status=status,
            provenance_a=ProvenanceRef(document_id=doc_a_id, source_name=f"ECI Election Expenditure ({election_name})"),
            provenance_b=ProvenanceRef(document_id=doc_b_id, source_name="ECI Audit Accounts")
        )

    @classmethod
    def compare_electoral_trust_report_vs_party_disclosure(
        cls,
        party_id: str,
        financial_year: str,
        trust_disbursement_amount: float,
        party_disclosed_trust_amount: float,
        doc_a_id: str = "ECI_Electoral_Trust_Report",
        doc_b_id: str = "ECI_Form24A"
    ) -> ComparisonRecord:
        """
        Cross-validates Electoral Trust filing (payout to Party X) vs Party Form 24A / Audit (grant from Trust).
        """
        diff = abs(trust_disbursement_amount - party_disclosed_trust_amount)
        diff_pct = (diff / party_disclosed_trust_amount) * 100.0 if party_disclosed_trust_amount > 0 else 0.0

        comp_id = f"COMP_{party_id}_{financial_year}_TRUST_VS_PARTY"

        if diff == 0.0 or diff_pct < 1.0:
            status = ValidationStatus.MATCHED
            exp = "Electoral Trust reported disbursement matches party disclosed grant within 1% tolerance."
        elif diff_pct < 5.0:
            status = ValidationStatus.SMALL_DIFFERENCE
            exp = f"Minor variance of INR {diff:,.2f} ({diff_pct:.2f}%) between Trust report and Party filing. Likely attributable to banking clearance dates."
        elif diff_pct < 15.0:
            status = ValidationStatus.MATERIAL_DIFFERENCE
            exp = f"Material variance of INR {diff:,.2f} ({diff_pct:.2f}%) detected between Trust reported payout and Party disclosed grant."
        else:
            status = ValidationStatus.REQUIRES_MANUAL_REVIEW
            exp = f"Unresolved discrepancy of INR {diff:,.2f} ({diff_pct:.2f}%) detected. Requires manual audit of trust distribution schedule."

        return ComparisonRecord(
            comparison_id=comp_id,
            party_id=party_id,
            financial_year=financial_year,
            source_document_a=doc_a_id,
            source_document_b=doc_b_id,
            metric_name="ELECTORAL_TRUST_DISBURSEMENT_MATCH",
            value_a=round(trust_disbursement_amount, 2),
            value_b=round(party_disclosed_trust_amount, 2),
            difference=round(diff, 2),
            difference_percentage=round(diff_pct, 2),
            difference_explanation=exp,
            validation_status=status,
            provenance_a=ProvenanceRef(document_id=doc_a_id, source_name="ECI Electoral Trust Report"),
            provenance_b=ProvenanceRef(document_id=doc_b_id, source_name="ECI Form 24A / Audit")
        )


class HumanReviewWorkflow:
    """Manages tickets and review audit notes for unresolved financial discrepancies."""

    def __init__(self):
        self.tickets: Dict[str, HumanReviewTicket] = {}

    def create_ticket_if_needed(self, comparison: ComparisonRecord) -> Optional[HumanReviewTicket]:
        """Creates an audit ticket for MATERIAL_DIFFERENCE or REQUIRES_MANUAL_REVIEW status records."""
        if comparison.validation_status in (ValidationStatus.MATERIAL_DIFFERENCE, ValidationStatus.REQUIRES_MANUAL_REVIEW):
            ticket_id = f"TICKET_{comparison.comparison_id}"
            if ticket_id in self.tickets:
                return self.tickets[ticket_id]

            ticket = HumanReviewTicket(
                ticket_id=ticket_id,
                comparison_id=comparison.comparison_id,
                party_id=comparison.party_id,
                financial_year=comparison.financial_year,
                metric_name=comparison.metric_name,
                discrepancy_amount=comparison.difference,
                review_status=ReviewQueueStatus.QUEUED_FOR_AUDIT
            )
            self.tickets[ticket_id] = ticket
            logger.info(f"Created human-review audit ticket {ticket_id} for discrepancy INR {comparison.difference:,.2f}")
            return ticket
        return None

    def update_audit_notes(self, ticket_id: str, auditor_name: str, notes: str, new_status: str = ReviewQueueStatus.RESOLVED) -> Optional[HumanReviewTicket]:
        """Updates ticket with auditor resolution notes."""
        ticket = self.tickets.get(ticket_id)
        if ticket:
            ticket.assigned_auditor = auditor_name
            ticket.audit_notes = notes
            ticket.review_status = new_status
            if new_status == ReviewQueueStatus.RESOLVED:
                ticket.resolved_at = datetime.now(timezone.utc).isoformat()
            return ticket
        return None
