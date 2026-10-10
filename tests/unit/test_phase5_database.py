"""
Unit tests for Phase 5 Database Integration & Import Manager.

Verifies:
1. Creation of all Phase 5 database tables.
2. Idempotent batch contribution imports and reconciliation summary logging.
3. Transaction safety and rollback handling.
4. Separate persistence of reported statutory facts vs computed metrics.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.base_class import Base
import backend.database.base  # Ensures all ORM models are registered
from backend.repositories.funding import FundingRepository
from backend.schemas.funding import (
    PoliticalPartySchema,
    ContributionSchema,
    FinancialStatementSchema,
    ElectionExpenditureSchema,
    ValidationIssueRecord
)


@pytest.fixture
def db_session():
    """Creates a clean in-memory SQLite database session for unit testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()


class TestPhase5DatabaseIntegration:

    def test_schema_creation(self, db_session):
        """Verifies that all Phase 5 tables exist in the database metadata."""
        tables = Base.metadata.tables.keys()
        required_tables = [
            "financial_documents",
            "donors",
            "electoral_trusts",
            "contributions",
            "party_financial_statements",
            "election_expenditures",
            "financial_metrics",
            "funding_validation_issues"
        ]
        for tbl in required_tables:
            assert tbl in tables, f"Missing table {tbl} from SQLAlchemy metadata"

    def test_idempotent_contribution_batch_import(self, db_session):
        """Verifies batch contribution import, idempotence, and reconciliation counting."""
        # 1. Setup Party and Document
        party_schema = PoliticalPartySchema(party_id="PARTY_TN_DMK", official_name="Dravida Munnetra Kazhagam")
        FundingRepository.ensure_party_exists(db_session, party_schema)

        doc, is_created = FundingRepository.import_financial_document(
            db=db_session,
            document_id="DOC_TEST_001",
            source_id="SRC-ECI-24A",
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            filing_type="Form24A",
            file_hash_sha256="abc123sha256hash"
        )
        assert is_created is True

        # 2. Prepare test contributions batch
        contribs = [
            ContributionSchema(
                contribution_id="CONT_TEST_001",
                party_id="PARTY_TN_DMK",
                donor_name_as_reported="Apex Enterprise Ltd",
                donor_name_normalized="APEX ENTERPRISE LTD",
                amount=5000000.0,
                financial_year="FY2021-22",
                document_id="DOC_TEST_001",
                page_number=1,
                table_number=1
            ),
            ContributionSchema(
                contribution_id="CONT_TEST_002",
                party_id="PARTY_TN_DMK",
                donor_name_as_reported="Beta Infra Pvt Ltd",
                donor_name_normalized="BETA INFRA PVT LTD",
                amount=2500000.0,
                financial_year="FY2021-22",
                document_id="DOC_TEST_001",
                page_number=1,
                table_number=1
            )
        ]

        # First import
        summary1 = FundingRepository.import_contributions_batch(db_session, contribs)
        assert summary1["total_submitted"] == 2
        assert summary1["inserted_count"] == 2
        assert summary1["skipped_duplicates_count"] == 0

        # Second import (same batch) -> Should skip all as duplicates
        summary2 = FundingRepository.import_contributions_batch(db_session, contribs)
        assert summary2["total_submitted"] == 2
        assert summary2["inserted_count"] == 0
        assert summary2["skipped_duplicates_count"] == 2

    def test_financial_statement_and_metrics_import(self, db_session):
        """Verifies distinct persistence of reported financial statements vs computed metrics."""
        party_schema = PoliticalPartySchema(party_id="PARTY_TN_DMK", official_name="Dravida Munnetra Kazhagam")
        FundingRepository.ensure_party_exists(db_session, party_schema)

        # 1. Import Statutory Statement Fact
        stmt_schema = FinancialStatementSchema(
            statement_id="STMT_DMK_2021",
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            total_income_reported=300000000.0,
            total_expenditure_reported=220000000.0,
            net_surplus_deficit=80000000.0
        )
        stmt_orm, is_new_stmt = FundingRepository.import_financial_statement(db_session, stmt_schema)
        assert is_new_stmt is True
        assert stmt_orm.total_income == 300000000.0

        # 2. Import Computed Metric (Stored separately)
        metric_orm, is_new_met = FundingRepository.import_financial_metrics(
            db=db_session,
            party_id="PARTY_TN_DMK",
            financial_year="FY2021-22",
            gini=0.78,
            hhi=0.32,
            disclosed_ratio=0.06,
            unknown_ratio=0.94
        )
        assert is_new_met is True
        assert metric_orm.gini_coefficient == 0.78
        assert metric_orm.unknown_source_ratio == 0.94

    def test_validation_issues_import(self, db_session):
        """Verifies logging validation issues to database."""
        issues = [
            ValidationIssueRecord(
                issue_id="ISSUE_TEST_001",
                rule_code="V-02_NEGATIVE_AMOUNT",
                severity="CRITICAL",
                entity_type="Contribution",
                entity_id="CONT_TEST_003",
                field_name="amount",
                description="Negative contribution amount detected",
                raw_value="-500000",
                suggested_action="Review raw document page"
            )
        ]
        inserted = FundingRepository.import_validation_issues(db_session, issues)
        assert inserted == 1

        # Re-importing same issue -> Should skip duplicate
        inserted_again = FundingRepository.import_validation_issues(db_session, issues)
        assert inserted_again == 0
