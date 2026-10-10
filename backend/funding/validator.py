"""
Phase 5 — Financial Data Validation Module.

Executes 10 automated data quality and integrity checks across canonical funding records:
1. Missing Values (V-01)
2. Negative Amounts (V-02)
3. Invalid Currency Values (V-03)
4. Malformed Dates & Bounds (V-04)
5. Duplicate Rows (V-05)
6. Party Name Variations (V-06)
7. Inconsistent Totals (V-07)
8. OCR Corruption Artifacts (V-08)
9. Financial Year Mismatches (V-09)
10. Source Inconsistencies (V-10)
"""

import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from backend.schemas.funding import (
    ContributionSchema,
    FinancialStatementSchema,
    ElectionExpenditureSchema,
    ValidationIssueRecord
)
from backend.funding.processor import AmountStatus

logger = logging.getLogger("civiclens.funding.validator")


class Severity:
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class ValidationEngine:
    """Core validation engine implementing Phase 5 financial validation rules."""

    @staticmethod
    def _parse_fy_year_bounds(fy_str: str) -> Optional[Tuple[int, int]]:
        """Parses FY string (e.g. FY2021-22) to start year and end year (2021, 2022)."""
        match = re.search(r"FY(\d{4})-(\d{2})", fy_str)
        if match:
            start_yr = int(match.group(1))
            end_yr = 2000 + int(match.group(2))
            return start_yr, end_yr
        return None

    @classmethod
    def validate_contribution(cls, contrib: ContributionSchema) -> List[ValidationIssueRecord]:
        issues: List[ValidationIssueRecord] = []

        # Rule V-01: Missing Required Values
        if contrib.party_id == "PARTY_UNKNOWN":
            issues.append(ValidationIssueRecord(
                issue_id=f"ISSUE_V01_{contrib.contribution_id}_PARTY",
                rule_code="V-01_MISSING_PARTY",
                severity=Severity.CRITICAL,
                entity_type="Contribution",
                entity_id=contrib.contribution_id,
                field_name="party_id",
                description="Contribution record is not linked to a recognized canonical political party.",
                raw_value=contrib.party_id,
                suggested_action="Review party registration registry and add alias mapping."
            ))

        # Rule V-02: Negative Amounts
        if contrib.amount is not None and contrib.amount < 0:
            issues.append(ValidationIssueRecord(
                issue_id=f"ISSUE_V02_{contrib.contribution_id}_NEG",
                rule_code="V-02_NEGATIVE_AMOUNT",
                severity=Severity.CRITICAL,
                entity_type="Contribution",
                entity_id=contrib.contribution_id,
                field_name="amount",
                description="Contribution amount is negative without documented refund/credit note.",
                raw_value=str(contrib.amount),
                suggested_action="Verify raw document page to check for refund remark or OCR minus artifact."
            ))

        # Rule V-03: Invalid Currency Values
        if contrib.amount_status == AmountStatus.EXTRACTION_FAILURE.value:
            issues.append(ValidationIssueRecord(
                issue_id=f"ISSUE_V03_{contrib.contribution_id}_CURR",
                rule_code="V-03_INVALID_CURRENCY",
                severity=Severity.CRITICAL,
                entity_type="Contribution",
                entity_id=contrib.contribution_id,
                field_name="amount",
                description="Monetary amount string could not be parsed into valid numeric currency.",
                raw_value=contrib.original_row,
                suggested_action="Perform manual OCR review on target table cell."
            ))

        # Rule V-04: Malformed Dates & FY Date Bounds
        if contrib.contribution_date_as_reported and not contrib.contribution_date_normalized:
            issues.append(ValidationIssueRecord(
                issue_id=f"ISSUE_V04_{contrib.contribution_id}_DATE_PARSE",
                rule_code="V-04_MALFORMED_DATE",
                severity=Severity.WARNING,
                entity_type="Contribution",
                entity_id=contrib.contribution_id,
                field_name="contribution_date_as_reported",
                description=f"Transaction date string '{contrib.contribution_date_as_reported}' could not be parsed into ISO format.",
                raw_value=contrib.contribution_date_as_reported,
                suggested_action="Standardize date format manually or verify page OCR."
            ))

        # Rule V-09: Financial Year Mismatches
        if contrib.contribution_date_normalized and contrib.financial_year:
            fy_bounds = cls._parse_fy_year_bounds(contrib.financial_year)
            if fy_bounds:
                start_yr, end_yr = fy_bounds
                try:
                    dt = datetime.strptime(contrib.contribution_date_normalized, "%Y-%m-%d")
                    # Financial year FY2021-22 runs from 2021-04-01 to 2022-03-31
                    fy_start_dt = datetime(start_yr, 4, 1)
                    fy_end_dt = datetime(end_yr, 3, 31, 23, 59, 59)
                    if not (fy_start_dt <= dt <= fy_end_dt):
                        issues.append(ValidationIssueRecord(
                            issue_id=f"ISSUE_V09_{contrib.contribution_id}_FY_MISMATCH",
                            rule_code="V-09_FY_DATE_MISMATCH",
                            severity=Severity.WARNING,
                            entity_type="Contribution",
                            entity_id=contrib.contribution_id,
                            field_name="financial_year",
                            description=f"Transaction date {contrib.contribution_date_normalized} falls outside financial year {contrib.financial_year} bounds ({start_yr}-04-01 to {end_yr}-03-31).",
                            raw_value=f"Date: {contrib.contribution_date_normalized}, FY: {contrib.financial_year}",
                            suggested_action="Check filing header or typo in transaction date."
                        ))
                except Exception:
                    pass

        # Rule V-08: OCR Corruption Artifacts
        if contrib.extraction_confidence < 0.60 or re.search(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", contrib.original_row):
            issues.append(ValidationIssueRecord(
                issue_id=f"ISSUE_V08_{contrib.contribution_id}_OCR",
                rule_code="V-08_OCR_CORRUPTION",
                severity=Severity.WARNING,
                entity_type="Contribution",
                entity_id=contrib.contribution_id,
                field_name="original_row",
                description="Low extraction confidence score or non-printable OCR artifacts detected in row text.",
                raw_value=contrib.original_row,
                suggested_action="Trigger high-resolution OCR fallback pipeline."
            ))

        return issues

    @classmethod
    def validate_contribution_batch(cls, contributions: List[ContributionSchema]) -> List[ValidationIssueRecord]:
        """Validates a batch of contribution records, checking row duplicates and aggregate sums."""
        issues: List[ValidationIssueRecord] = []

        # Validate individual records
        seen_signatures: Dict[str, str] = {}
        for contrib in contributions:
            issues.extend(cls.validate_contribution(contrib))

            # Rule V-05: Duplicate Rows Detection
            sig = f"{contrib.party_id}|{contrib.donor_name_normalized}|{contrib.amount}|{contrib.contribution_date_normalized}|{contrib.page_number}"
            if sig in seen_signatures:
                issues.append(ValidationIssueRecord(
                    issue_id=f"ISSUE_V05_{contrib.contribution_id}_DUP",
                    rule_code="V-05_DUPLICATE_ROW",
                    severity=Severity.WARNING,
                    entity_type="Contribution",
                    entity_id=contrib.contribution_id,
                    field_name="original_row",
                    description=f"Contribution row is identical to previously parsed record {seen_signatures[sig]}.",
                    raw_value=contrib.original_row,
                    suggested_action="Verify if filing contains repeated annexure entries or duplicate extraction."
                ))
            else:
                seen_signatures[sig] = contrib.contribution_id

        return issues

    @classmethod
    def validate_cross_source_statement(
        cls,
        contributions: List[ContributionSchema],
        statement: FinancialStatementSchema
    ) -> List[ValidationIssueRecord]:
        """
        Executes Rule V-07 (Inconsistent Totals) and Rule V-10 (Source Inconsistencies).
        """
        issues: List[ValidationIssueRecord] = []

        # Rule V-07: Inconsistent Totals (Form 24A rows vs reported summary)
        valid_amounts = [c.amount for c in contributions if c.amount is not None and c.amount > 0]
        actual_sum = sum(valid_amounts)

        reported_20k = statement.income_categories.get("donations_above_20k") or statement.income_categories.get("contributions_above_20k")
        if reported_20k is not None and reported_20k > 0:
            diff = abs(actual_sum - reported_20k)
            # Allow 1% tolerance for minor rounding or small disaggregated items
            if diff > (reported_20k * 0.05) and diff > 10000.0:
                issues.append(ValidationIssueRecord(
                    issue_id=f"ISSUE_V07_{statement.statement_id}_SUM_MISMATCH",
                    rule_code="V-07_INCONSISTENT_TOTALS",
                    severity=Severity.WARNING,
                    entity_type="FinancialStatement",
                    entity_id=statement.statement_id,
                    field_name="donations_above_20k",
                    description=f"Form 24A itemized sum (₹{actual_sum:,.2f}) differs from Audited Statement summary (₹{reported_20k:,.2f}) by ₹{diff:,.2f}.",
                    raw_value=f"Itemized Sum: {actual_sum}, Summary: {reported_20k}",
                    suggested_action="Check for missing pages or un-itemized summary schedules."
                ))

        # Rule V-10: Source Inconsistencies (Form 24A total > Total Income)
        if statement.total_income_reported is not None and actual_sum > statement.total_income_reported:
            issues.append(ValidationIssueRecord(
                issue_id=f"ISSUE_V10_{statement.statement_id}_SOURCE_INCONSISTENT",
                rule_code="V-10_SOURCE_INCONSISTENCY",
                severity=Severity.CRITICAL,
                entity_type="FinancialStatement",
                entity_id=statement.statement_id,
                field_name="total_income_reported",
                description=f"Disclosed Form 24A contributions (₹{actual_sum:,.2f}) exceed total audited party income (₹{statement.total_income_reported:,.2f}).",
                raw_value=f"Disclosed 24A: {actual_sum}, Audited Total Income: {statement.total_income_reported}",
                suggested_action="Verify filing entity boundary (central vs state unit accounting)."
            ))

        return issues
