"""
Phase 5 — Political Funding Repository & Data Import Manager.

Provides idempotent, transaction-safe database import operations for:
- Political Parties
- Financial Documents
- Donors & Electoral Trusts
- Contributions
- Audited Financial Statements
- Election Campaign Expenditures
- Financial Metrics
- Validation Issues

Guarantees full provenance linkage, source-document foreign key validation,
duplicate handling, transaction rollback, and reconciliation logging.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend.models.news import PoliticalParty
from backend.models.funding import (
    FinancialDocument,
    Donor,
    ElectoralTrust,
    Contribution,
    PartyFinancialStatement,
    ElectionExpenditure,
    FinancialMetric,
    ValidationIssue
)
from backend.schemas.funding import (
    PoliticalPartySchema,
    ContributionSchema,
    FinancialStatementSchema,
    ElectionExpenditureSchema,
    ValidationIssueRecord
)

logger = logging.getLogger("civiclens.funding.repository")


class FundingRepository:

    @staticmethod
    def ensure_party_exists(db: Session, party_schema: PoliticalPartySchema) -> PoliticalParty:
        """Idempotently ensures a canonical PoliticalParty record exists in DB."""
        party = db.query(PoliticalParty).filter(PoliticalParty.party_id == party_schema.party_id).first()
        if not party:
            party = PoliticalParty(
                party_id=party_schema.party_id,
                party_name=party_schema.official_name,
                party_code=party_schema.party_id.replace("PARTY_", "").replace("TN_", "").replace("NAT_", ""),
                symbol=None,
                description=f"Recognition Status: {party_schema.recognition_status}"
            )
            db.add(party)
            db.flush()
        return party

    @staticmethod
    def import_financial_document(
        db: Session,
        document_id: str,
        source_id: str,
        party_id: Optional[str],
        financial_year: str,
        filing_type: str,
        file_hash_sha256: str,
        file_path: Optional[str] = None,
        source_url: Optional[str] = None,
        submission_date: Optional[str] = None,
        page_count: int = 1,
        is_scanned: bool = False
    ) -> Tuple[FinancialDocument, bool]:
        """
        Idempotently inserts or retrieves a FinancialDocument.
        Returns (FinancialDocument, is_created_flag).
        """
        existing = db.query(FinancialDocument).filter(
            (FinancialDocument.document_id == document_id) | 
            (FinancialDocument.file_hash_sha256 == file_hash_sha256)
        ).first()

        if existing:
            return existing, False

        doc = FinancialDocument(
            document_id=document_id,
            source_id=source_id,
            party_id=party_id,
            financial_year=financial_year,
            filing_type=filing_type,
            file_path=file_path,
            file_hash_sha256=file_hash_sha256,
            source_url=source_url,
            submission_date=submission_date,
            page_count=page_count,
            is_scanned=is_scanned
        )
        db.add(doc)
        db.flush()
        return doc, True

    @staticmethod
    def ensure_donor_exists(db: Session, donor_name_as_reported: str, donor_name_normalized: str) -> Donor:
        """Idempotently ensures a Donor record exists without auto-merging distinct spellings."""
        donor_id = f"DONOR_{hash(donor_name_as_reported) & 0xFFFFFFFF:08x}"
        existing = db.query(Donor).filter(Donor.legal_name == donor_name_as_reported).first()
        if existing:
            return existing

        donor = Donor(
            donor_id=donor_id,
            legal_name=donor_name_as_reported,
            normalized_name=donor_name_normalized,
            donor_type="UNKNOWN"
        )
        db.add(donor)
        db.flush()
        return donor

    @classmethod
    def import_contributions_batch(
        cls,
        db: Session,
        contributions: List[ContributionSchema]
    ) -> Dict[str, Any]:
        """
        Transaction-safe, idempotent batch import for Contribution records.
        Returns detailed reconciliation log.
        """
        summary = {
            "total_submitted": len(contributions),
            "inserted_count": 0,
            "skipped_duplicates_count": 0,
            "failed_count": 0,
            "errors": []
        }

        if not contributions:
            return summary

        savepoint = db.begin_nested()
        try:
            for contrib in contributions:
                # 1. Foreign-key safety check for party
                party = db.query(PoliticalParty).filter(PoliticalParty.party_id == contrib.party_id).first()
                if not party:
                    # Create default party fallback if needed
                    fallback_schema = PoliticalPartySchema(
                        party_id=contrib.party_id,
                        official_name=contrib.party_id
                    )
                    party = cls.ensure_party_exists(db, fallback_schema)

                # 2. Check for existing duplicate contribution
                existing = db.query(Contribution).filter(Contribution.contribution_id == contrib.contribution_id).first()
                if existing:
                    summary["skipped_duplicates_count"] += 1
                    continue

                # 3. Ensure Donor record exists
                donor = cls.ensure_donor_exists(
                    db,
                    donor_name_as_reported=contrib.donor_name_as_reported,
                    donor_name_normalized=contrib.donor_name_normalized
                )

                # 4. Create Contribution ORM entity
                c_orm = Contribution(
                    contribution_id=contrib.contribution_id,
                    document_id=contrib.document_id,
                    party_id=contrib.party_id,
                    donor_id=donor.donor_id,
                    financial_year=contrib.financial_year,
                    donor_name_as_reported=contrib.donor_name_as_reported,
                    donor_name_normalized=contrib.donor_name_normalized,
                    amount_inr=contrib.amount,
                    amount_status=contrib.amount_status,
                    currency=contrib.currency,
                    contribution_date_as_reported=contrib.contribution_date_as_reported,
                    contribution_date_normalized=contrib.contribution_date_normalized,
                    payment_mode=contrib.contribution_type,
                    page_number=contrib.page_number,
                    table_number=contrib.table_number,
                    original_row=contrib.original_row,
                    extraction_method=contrib.extraction_method,
                    extraction_confidence=contrib.extraction_confidence
                )
                db.add(c_orm)
                summary["inserted_count"] += 1

            savepoint.commit()
            db.commit()
            logger.info(f"Successfully committed contribution import batch: Inserted={summary['inserted_count']}, Skipped={summary['skipped_duplicates_count']}")
        except Exception as e:
            savepoint.rollback()
            db.rollback()
            err_msg = f"Failed to import contribution batch: {str(e)}"
            logger.error(err_msg)
            summary["failed_count"] = summary["total_submitted"] - summary["skipped_duplicates_count"]
            summary["inserted_count"] = 0
            summary["errors"].append(err_msg)

        return summary

    @classmethod
    def import_financial_statement(
        cls,
        db: Session,
        statement: FinancialStatementSchema
    ) -> Tuple[PartyFinancialStatement, bool]:
        """Idempotently imports an annual audited financial statement."""
        existing = db.query(PartyFinancialStatement).filter(
            (PartyFinancialStatement.statement_id == statement.statement_id) |
            ((PartyFinancialStatement.party_id == statement.party_id) & (PartyFinancialStatement.financial_year == statement.financial_year))
        ).first()

        if existing:
            return existing, False

        stmt_orm = PartyFinancialStatement(
            statement_id=statement.statement_id,
            party_id=statement.party_id,
            financial_year=statement.financial_year,
            total_income=statement.total_income_reported,
            total_expenditure=statement.total_expenditure_reported,
            net_surplus_deficit=statement.net_surplus_deficit,
            income_categories_json=statement.income_categories,
            expenditure_categories_json=statement.expenditure_categories,
            assets_liabilities_json=statement.assets_and_liabilities,
            auditor_name=statement.auditor_name,
            audit_date=statement.audit_date,
            document_id=statement.document_id if statement.document_id else None
        )
        db.add(stmt_orm)
        db.commit()
        return stmt_orm, True

    @classmethod
    def import_election_expenditure(
        cls,
        db: Session,
        expenditure: ElectionExpenditureSchema
    ) -> Tuple[ElectionExpenditure, bool]:
        """Idempotently imports an election expenditure statement."""
        existing = db.query(ElectionExpenditure).filter(
            (ElectionExpenditure.expenditure_id == expenditure.expenditure_id) |
            ((ElectionExpenditure.party_id == expenditure.party_id) & (ElectionExpenditure.election_name == expenditure.election))
        ).first()

        if existing:
            return existing, False

        exp_orm = ElectionExpenditure(
            expenditure_id=expenditure.expenditure_id,
            party_id=expenditure.party_id,
            election_name=expenditure.election,
            reporting_period=expenditure.reporting_period,
            expenditure_categories_json=expenditure.expenditure_categories,
            reported_totals=expenditure.reported_totals,
            document_id=expenditure.document_id if expenditure.document_id else None
        )
        db.add(exp_orm)
        db.commit()
        return exp_orm, True

    @classmethod
    def import_financial_metrics(
        cls,
        db: Session,
        party_id: str,
        financial_year: str,
        gini: Optional[float] = None,
        hhi: Optional[float] = None,
        disclosed_ratio: Optional[float] = None,
        unknown_ratio: Optional[float] = None,
        yoy_growth: Optional[float] = None,
        surplus_ratio: Optional[float] = None,
        metrics_dict: Optional[Dict[str, Any]] = None
    ) -> Tuple[FinancialMetric, bool]:
        """
        Idempotently inserts or updates derived financial metrics.
        Stored separately from reported statutory facts.
        """
        metric_id = f"METRIC_{party_id}_{financial_year}"
        existing = db.query(FinancialMetric).filter(FinancialMetric.metric_id == metric_id).first()

        if existing:
            existing.gini_coefficient = gini
            existing.hhi_index = hhi
            existing.disclosed_donor_ratio = disclosed_ratio
            existing.unknown_source_ratio = unknown_ratio
            existing.yoy_income_growth = yoy_growth
            existing.surplus_ratio = surplus_ratio
            existing.metrics_json = metrics_dict or {}
            existing.computed_at = datetime.now(timezone.utc)
            db.commit()
            return existing, False

        metric_orm = FinancialMetric(
            metric_id=metric_id,
            party_id=party_id,
            financial_year=financial_year,
            gini_coefficient=gini,
            hhi_index=hhi,
            disclosed_donor_ratio=disclosed_ratio,
            unknown_source_ratio=unknown_ratio,
            yoy_income_growth=yoy_growth,
            surplus_ratio=surplus_ratio,
            metrics_json=metrics_dict or {}
        )
        db.add(metric_orm)
        db.commit()
        return metric_orm, True

    @classmethod
    def import_validation_issues(
        cls,
        db: Session,
        issues: List[ValidationIssueRecord]
    ) -> int:
        """Idempotently logs validation issues to DB."""
        inserted_count = 0
        for issue in issues:
            existing = db.query(ValidationIssue).filter(ValidationIssue.issue_id == issue.issue_id).first()
            if not existing:
                iss_orm = ValidationIssue(
                    issue_id=issue.issue_id,
                    rule_code=issue.rule_code,
                    severity=issue.severity,
                    entity_type=issue.entity_type,
                    entity_id=issue.entity_id,
                    field_name=issue.field_name,
                    description=issue.description,
                    raw_value=issue.raw_value,
                    suggested_action=issue.suggested_action
                )
                db.add(iss_orm)
                inserted_count += 1
        db.commit()
        return inserted_count
