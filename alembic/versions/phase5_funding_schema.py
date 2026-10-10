"""Create Phase 5 Political Funding Transparency Tables

Revision ID: phase5_funding_schema
Revises: 7ccfdea60b7f
Create Date: 2026-10-10 17:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'phase5_funding_schema'
down_revision: Union[str, Sequence[str], None] = '7ccfdea60b7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema for Phase 5."""
    op.create_table(
        'financial_documents',
        sa.Column('document_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('source_id', sa.String(), nullable=False),
        sa.Column('party_id', sa.String(), sa.ForeignKey('political_parties.party_id', ondelete='SET NULL'), nullable=True),
        sa.Column('financial_year', sa.String(), nullable=False),
        sa.Column('filing_type', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=True),
        sa.Column('file_hash_sha256', sa.String(), nullable=False, unique=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('submission_date', sa.String(), nullable=True),
        sa.Column('page_count', sa.Integer(), default=1),
        sa.Column('is_scanned', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )

    op.create_table(
        'donors',
        sa.Column('donor_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('legal_name', sa.String(), nullable=False),
        sa.Column('normalized_name', sa.String(), nullable=False),
        sa.Column('donor_type', sa.String(), default='UNKNOWN'),
        sa.Column('cin_number', sa.String(), nullable=True),
        sa.Column('pan_hash', sa.String(), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )

    op.create_table(
        'electoral_trusts',
        sa.Column('trust_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('trust_name', sa.String(), nullable=False),
        sa.Column('registration_no', sa.String(), nullable=True),
        sa.Column('corporate_sponsor', sa.String(), nullable=True),
        sa.Column('nodal_bank', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )

    op.create_table(
        'contributions',
        sa.Column('contribution_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('document_id', sa.String(), sa.ForeignKey('financial_documents.document_id', ondelete='CASCADE'), nullable=False),
        sa.Column('party_id', sa.String(), sa.ForeignKey('political_parties.party_id', ondelete='CASCADE'), nullable=False),
        sa.Column('donor_id', sa.String(), sa.ForeignKey('donors.donor_id', ondelete='SET NULL'), nullable=True),
        sa.Column('financial_year', sa.String(), nullable=False),
        sa.Column('donor_name_as_reported', sa.String(), nullable=False),
        sa.Column('donor_name_normalized', sa.String(), nullable=False),
        sa.Column('amount_inr', sa.Float(), nullable=True),
        sa.Column('amount_status', sa.String(), default='VALID_NUMERIC'),
        sa.Column('currency', sa.String(), default='INR'),
        sa.Column('contribution_date_as_reported', sa.String(), nullable=True),
        sa.Column('contribution_date_normalized', sa.String(), nullable=True),
        sa.Column('payment_mode', sa.String(), nullable=True),
        sa.Column('page_number', sa.Integer(), default=1),
        sa.Column('table_number', sa.Integer(), default=1),
        sa.Column('original_row', sa.Text(), nullable=True),
        sa.Column('extraction_method', sa.String(), default='PDF_NATIVE_TABLE'),
        sa.Column('extraction_confidence', sa.Float(), default=1.0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('document_id', 'page_number', 'table_number', 'contribution_id', name='uq_contribution_provenance')
    )

    op.create_table(
        'party_financial_statements',
        sa.Column('statement_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('party_id', sa.String(), sa.ForeignKey('political_parties.party_id', ondelete='CASCADE'), nullable=False),
        sa.Column('financial_year', sa.String(), nullable=False),
        sa.Column('total_income', sa.Float(), nullable=True),
        sa.Column('total_expenditure', sa.Float(), nullable=True),
        sa.Column('net_surplus_deficit', sa.Float(), nullable=True),
        sa.Column('income_categories_json', sa.JSON(), nullable=True),
        sa.Column('expenditure_categories_json', sa.JSON(), nullable=True),
        sa.Column('assets_liabilities_json', sa.JSON(), nullable=True),
        sa.Column('auditor_name', sa.String(), nullable=True),
        sa.Column('audit_date', sa.String(), nullable=True),
        sa.Column('document_id', sa.String(), sa.ForeignKey('financial_documents.document_id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('party_id', 'financial_year', name='uq_party_financial_statement')
    )

    op.create_table(
        'election_expenditures',
        sa.Column('expenditure_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('party_id', sa.String(), sa.ForeignKey('political_parties.party_id', ondelete='CASCADE'), nullable=False),
        sa.Column('election_name', sa.String(), nullable=False),
        sa.Column('reporting_period', sa.String(), nullable=False),
        sa.Column('expenditure_categories_json', sa.JSON(), nullable=True),
        sa.Column('reported_totals', sa.Float(), nullable=True),
        sa.Column('document_id', sa.String(), sa.ForeignKey('financial_documents.document_id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('party_id', 'election_name', name='uq_party_election_expenditure')
    )

    op.create_table(
        'financial_metrics',
        sa.Column('metric_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('party_id', sa.String(), sa.ForeignKey('political_parties.party_id', ondelete='CASCADE'), nullable=False),
        sa.Column('financial_year', sa.String(), nullable=False),
        sa.Column('gini_coefficient', sa.Float(), nullable=True),
        sa.Column('hhi_index', sa.Float(), nullable=True),
        sa.Column('disclosed_donor_ratio', sa.Float(), nullable=True),
        sa.Column('unknown_source_ratio', sa.Float(), nullable=True),
        sa.Column('yoy_income_growth', sa.Float(), nullable=True),
        sa.Column('surplus_ratio', sa.Float(), nullable=True),
        sa.Column('metrics_json', sa.JSON(), nullable=True),
        sa.Column('computed_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('party_id', 'financial_year', name='uq_party_financial_metric')
    )

    op.create_table(
        'funding_validation_issues',
        sa.Column('issue_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('rule_code', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('document_id', sa.String(), sa.ForeignKey('financial_documents.document_id', ondelete='CASCADE'), nullable=True),
        sa.Column('field_name', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('raw_value', sa.Text(), nullable=True),
        sa.Column('suggested_action', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('funding_validation_issues')
    op.drop_table('financial_metrics')
    op.drop_table('election_expenditures')
    op.drop_table('party_financial_statements')
    op.drop_table('contributions')
    op.drop_table('electoral_trusts')
    op.drop_table('donors')
    op.drop_table('financial_documents')
