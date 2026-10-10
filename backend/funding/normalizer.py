"""
Phase 5 — Financial Data Normalization Module.

Normalizes extracted records into canonical schemas for Political Parties,
Contributions, Financial Statements, and Election Expenditure.

STRICT DISAMBIGUATION DIRECTIVE:
Preserves original raw values alongside normalized values.
Does NOT automatically merge donors with similar spellings without explicit, verified evidence.
"""

import re
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from backend.schemas.funding import (
    PoliticalPartySchema,
    ContributionSchema,
    FinancialStatementSchema,
    ElectionExpenditureSchema
)
from backend.funding.processor import AmountNormalizer, AmountStatus

logger = logging.getLogger("civiclens.funding.normalizer")


class PartyRegistryNormalizer:
    """Master registry mapping party variations to canonical party profiles."""

    CANONICAL_PARTIES: Dict[str, PoliticalPartySchema] = {
        "PARTY_TN_DMK": PoliticalPartySchema(
            party_id="PARTY_TN_DMK",
            official_name="Dravida Munnetra Kazhagam",
            aliases=["DMK", "D.M.K.", "Dravida Munnetra Kazhagam"],
            recognition_status="STATE_RECOGNIZED_TN",
            valid_from="1949-09-17",
            source_references=["ECI Notification Gazette 2021", "TN Election Registry"]
        ),
        "PARTY_TN_AIADMK": PoliticalPartySchema(
            party_id="PARTY_TN_AIADMK",
            official_name="All India Anna Dravida Munnetra Kazhagam",
            aliases=["AIADMK", "A.I.A.D.M.K.", "All India Anna Dravida Munnetra Kazhagam"],
            recognition_status="STATE_RECOGNIZED_TN",
            valid_from="1972-10-17",
            source_references=["ECI Notification Gazette 2021"]
        ),
        "PARTY_NAT_INC": PoliticalPartySchema(
            party_id="PARTY_NAT_INC",
            official_name="Indian National Congress",
            aliases=["INC", "I.N.C.", "Congress", "Indian National Congress"],
            recognition_status="NATIONAL",
            valid_from="1885-12-28",
            source_references=["ECI National Party List"]
        ),
        "PARTY_NAT_BJP": PoliticalPartySchema(
            party_id="PARTY_NAT_BJP",
            official_name="Bharatiya Janata Party",
            aliases=["BJP", "B.J.P.", "Bharatiya Janata Party"],
            recognition_status="NATIONAL",
            valid_from="1980-04-06",
            source_references=["ECI National Party List"]
        ),
        "PARTY_TN_PMK": PoliticalPartySchema(
            party_id="PARTY_TN_PMK",
            official_name="Pattali Makkal Katchi",
            aliases=["PMK", "P.M.K.", "Pattali Makkal Katchi"],
            recognition_status="STATE_RECOGNIZED_TN",
            valid_from="1989-07-16",
            source_references=["ECI TN Party List"]
        ),
        "PARTY_TN_VCK": PoliticalPartySchema(
            party_id="PARTY_TN_VCK",
            official_name="Viduthalai Chiruthaigal Katchi",
            aliases=["VCK", "V.C.K.", "Viduthalai Chiruthaigal Katchi"],
            recognition_status="STATE_RECOGNIZED_TN",
            source_references=["ECI TN Party List"]
        ),
        "PARTY_TN_NTK": PoliticalPartySchema(
            party_id="PARTY_TN_NTK",
            official_name="Naam Tamilar Katchi",
            aliases=["NTK", "N.T.K.", "Naam Tamilar Katchi"],
            recognition_status="STATE_RECOGNIZED_TN",
            source_references=["ECI TN Party List"]
        ),
        "PARTY_TN_DMDK": PoliticalPartySchema(
            party_id="PARTY_TN_DMDK",
            official_name="Desiya Murpokku Dravida Kazhagam",
            aliases=["DMDK", "D.M.D.K.", "Desiya Murpokku Dravida Kazhagam"],
            recognition_status="STATE_RECOGNIZED_TN",
            source_references=["ECI TN Party List"]
        )
    }

    @classmethod
    def resolve_party(cls, party_name_or_code: Optional[str]) -> Tuple[str, str]:
        """Resolves party input to (canonical_party_id, official_name). Defaults to UNKNOWN."""
        if not party_name_or_code:
            return "PARTY_UNKNOWN", "Unknown Political Party"

        clean = party_name_or_code.strip()
        clean_lowered = clean.lower()

        for party_id, profile in cls.CANONICAL_PARTIES.items():
            if clean_lowered == profile.official_name.lower():
                return party_id, profile.official_name
            for alias in profile.aliases:
                if clean_lowered == alias.lower():
                    return party_id, profile.official_name

        return "PARTY_UNKNOWN", clean


class DateNormalizer:
    """Normalizes date strings to ISO YYYY-MM-DD format."""

    @staticmethod
    def normalize_date(raw_date_str: Optional[str]) -> Optional[str]:
        if not raw_date_str:
            return None
        clean = raw_date_str.strip()
        if not clean or clean.lower() in ("n/a", "na", "-", "--", "nil", "none"):
            return None

        # Common Indian statutory formats: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD
        formats_to_try = [
            "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
            "%d/%m/%y", "%d-%m-%y", "%d %b %Y", "%d %B %Y"
        ]

        for fmt in formats_to_try:
            try:
                dt = datetime.strptime(clean, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return None


class DonorNameNormalizer:
    """
    Normalizes donor names for search indexing while strictly adhering to non-merging policies.
    Preserves exact raw donor name in donor_name_as_reported.
    """

    @staticmethod
    def normalize_name(raw_name: Optional[str]) -> str:
        if not raw_name:
            return "UNDISCLOSED_DONOR"

        clean = raw_name.strip()
        if not clean or clean.lower() in ("nil", "none", "undisclosed", "redacted"):
            return "UNDISCLOSED_DONOR"

        # Standardize multiple spaces and uppercase for clean search lookup
        norm = re.sub(r"\s+", " ", clean).strip().upper()
        return norm


class FinancialRecordNormalizer:
    """Converts extracted raw records into canonical schemas."""

    @classmethod
    def normalize_contribution(cls, raw_rec: Dict[str, Any]) -> ContributionSchema:
        party_id, _ = PartyRegistryNormalizer.resolve_party(raw_rec.get("party_code"))
        raw_donor = raw_rec.get("donor_name") or "UNDISCLOSED_DONOR"
        norm_donor = DonorNameNormalizer.normalize_name(raw_donor)

        raw_amount_str = raw_rec.get("raw_amount_str")
        norm_amount = raw_rec.get("normalized_amount_inr")
        amount_status = raw_rec.get("amount_status", AmountStatus.VALID_NUMERIC.value)

        raw_date = raw_rec.get("payment_date")
        norm_date = DateNormalizer.normalize_date(raw_date)

        cont_id = raw_rec.get("record_id") or f"CONT_{raw_rec.get('document_id', 'DOC')}_{raw_rec.get('page_number', 1)}_{raw_rec.get('row_index', 1)}"

        return ContributionSchema(
            contribution_id=cont_id,
            party_id=party_id,
            donor_name_as_reported=raw_donor,
            donor_name_normalized=norm_donor,
            amount=norm_amount,
            amount_status=amount_status,
            currency="INR",
            contribution_date_as_reported=raw_date,
            contribution_date_normalized=norm_date,
            financial_year=raw_rec.get("financial_year", "FY2021-22"),
            contribution_type=raw_rec.get("payment_mode") or "Unknown",
            document_id=raw_rec.get("document_id", ""),
            page_number=raw_rec.get("page_number", 1),
            table_number=raw_rec.get("table_number", 1),
            original_row=raw_rec.get("raw_row", ""),
            extraction_method=raw_rec.get("extraction_method", "PDF_NATIVE_TABLE"),
            extraction_confidence=raw_rec.get("extraction_confidence", 1.0)
        )

    @classmethod
    def normalize_financial_statement(cls, raw_stmt: Dict[str, Any]) -> FinancialStatementSchema:
        party_id, _ = PartyRegistryNormalizer.resolve_party(raw_stmt.get("party_code"))
        stmt_id = raw_stmt.get("statement_id") or f"STMT_{party_id}_{raw_stmt.get('financial_year', 'FY2021-22')}"

        income_cats = raw_stmt.get("income_categories", {})
        expend_cats = raw_stmt.get("expenditure_categories", {})
        assets_cats = raw_stmt.get("assets_and_liabilities", {})

        return FinancialStatementSchema(
            statement_id=stmt_id,
            party_id=party_id,
            financial_year=raw_stmt.get("financial_year", "FY2021-22"),
            income_categories=income_cats,
            expenditure_categories=expend_cats,
            assets_and_liabilities=assets_cats,
            total_income_reported=raw_stmt.get("total_income"),
            total_expenditure_reported=raw_stmt.get("total_expenditure"),
            net_surplus_deficit=raw_stmt.get("net_surplus_deficit"),
            auditor_name=raw_stmt.get("auditor_name"),
            audit_date=raw_stmt.get("audit_date"),
            document_id=raw_stmt.get("document_id", "")
        )

    @classmethod
    def normalize_election_expenditure(cls, raw_exp: Dict[str, Any]) -> ElectionExpenditureSchema:
        party_id, _ = PartyRegistryNormalizer.resolve_party(raw_exp.get("party_code"))
        exp_id = raw_exp.get("expenditure_id") or f"EXP_{party_id}_{raw_exp.get('financial_year', 'FY2021-22')}"

        return ElectionExpenditureSchema(
            expenditure_id=exp_id,
            party_id=party_id,
            election=raw_exp.get("election", "General Election"),
            reporting_period=raw_exp.get("financial_year", "FY2021-22"),
            expenditure_categories=raw_exp.get("expenditure_categories", {}),
            reported_totals=raw_exp.get("total_expenditure"),
            document_id=raw_exp.get("document_id", "")
        )
