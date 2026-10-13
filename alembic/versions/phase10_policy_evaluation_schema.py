"""Create Phase 10 Policy Evaluation Registry, Plans, Indicators, and Findings Tables

Revision ID: phase10_policy_evaluation_schema
Revises: phase5_funding_schema
Create Date: 2026-10-13 09:12:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'phase10_policy_evaluation_schema'
down_revision: Union[str, Sequence[str], None] = 'phase5_funding_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema for Phase 10 Policy Registry & Outcome Evaluation."""
    op.create_table(
        'policy_registry',
        sa.Column('policy_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('budget_scheme_id', sa.Integer(), sa.ForeignKey('budget_schemes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('historical_scheme_id', sa.Integer(), sa.ForeignKey('historical_schemes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('promise_id', sa.String(), sa.ForeignKey('political_promises.promise_id', ondelete='SET NULL'), nullable=True),
        sa.Column('canonical_scheme_code', sa.String(), nullable=False),
        sa.Column('policy_name', sa.String(), nullable=False),
        sa.Column('policy_name_ta', sa.String(), nullable=True),
        sa.Column('aliases', sa.JSON(), nullable=True),
        sa.Column('responsible_department', sa.String(), nullable=True),
        sa.Column('department_id', sa.Integer(), sa.ForeignKey('budget_departments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('objectives_summary', sa.Text(), nullable=False),
        sa.Column('original_objective_wording', sa.Text(), nullable=False),
        sa.Column('is_objective_ambiguous', sa.Boolean(), default=False),
        sa.Column('ambiguity_review_notes', sa.Text(), nullable=True),
        sa.Column('objective_review_status', sa.String(), nullable=False, default='VERIFIED_CLEAR'),
        sa.Column('intended_beneficiaries', sa.Text(), nullable=False),
        sa.Column('geographic_scope', sa.String(), nullable=False, default='STATEWIDE'),
        sa.Column('covered_districts', sa.JSON(), nullable=True),
        sa.Column('start_date', sa.String(), nullable=True),
        sa.Column('end_date', sa.String(), nullable=True),
        sa.Column('implementation_rules', sa.JSON(), nullable=True),
        sa.Column('stated_targets', sa.JSON(), nullable=True),
        sa.Column('source_documents', sa.JSON(), nullable=True),
        sa.Column('evaluation_status', sa.String(), nullable=False, default='NOT_STARTED'),
        sa.Column('is_test_fixture', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'policy_objectives',
        sa.Column('objective_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('policy_id', sa.String(), sa.ForeignKey('policy_registry.policy_id', ondelete='SET NULL'), nullable=True),
        sa.Column('scheme_id', sa.String(), nullable=True),
        sa.Column('promise_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('title_ta', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('original_wording', sa.Text(), nullable=True),
        sa.Column('sector', sa.String(), nullable=False),
        sa.Column('is_statutory', sa.Boolean(), default=False),
        sa.Column('target_metrics', sa.JSON(), nullable=True),
        sa.Column('is_ambiguous', sa.Boolean(), default=False),
        sa.Column('ambiguity_flag_reason', sa.Text(), nullable=True),
        sa.Column('review_status', sa.String(), nullable=False, default='VERIFIED_CLEAR'),
        sa.Column('is_test_fixture', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'beneficiary_groups',
        sa.Column('group_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('objective_id', sa.String(), sa.ForeignKey('policy_objectives.objective_id', ondelete='CASCADE'), nullable=False),
        sa.Column('scheme_id', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('name_ta', sa.String(), nullable=True),
        sa.Column('eligibility_criteria', sa.Text(), nullable=False),
        sa.Column('exclusion_criteria', sa.Text(), nullable=True),
        sa.Column('estimated_eligible_population', sa.Integer(), nullable=True),
        sa.Column('geographic_focus', sa.String(), nullable=True),
        sa.Column('is_test_fixture', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'implementation_activities',
        sa.Column('activity_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('scheme_id', sa.String(), nullable=False),
        sa.Column('activity_name', sa.String(), nullable=False),
        sa.Column('activity_type', sa.String(), nullable=False),
        sa.Column('scheduled_start', sa.String(), nullable=True),
        sa.Column('scheduled_end', sa.String(), nullable=True),
        sa.Column('actual_end', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, default='IN_PROGRESS'),
        sa.Column('budget_allocated', sa.Float(), default=0.0),
        sa.Column('expenditure_incurred', sa.Float(), default=0.0),
        sa.Column('implementing_agency', sa.String(), nullable=True),
        sa.Column('source_document_id', sa.String(), nullable=True),
        sa.Column('is_test_fixture', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'policy_indicators',
        sa.Column('indicator_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('objective_id', sa.String(), sa.ForeignKey('policy_objectives.objective_id', ondelete='CASCADE'), nullable=False),
        sa.Column('scheme_id', sa.String(), nullable=True),
        sa.Column('indicator_name', sa.String(), nullable=False),
        sa.Column('indicator_name_ta', sa.String(), nullable=True),
        sa.Column('indicator_type', sa.String(), nullable=False),
        sa.Column('unit', sa.String(), nullable=False),
        sa.Column('direction_of_improvement', sa.String(), default='INCREASE'),
        sa.Column('aggregation_method', sa.String(), default='SUM'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_test_fixture', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'indicator_observations',
        sa.Column('observation_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('indicator_id', sa.String(), sa.ForeignKey('policy_indicators.indicator_id', ondelete='CASCADE'), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('reference_period', sa.String(), nullable=False),
        sa.Column('geographic_level', sa.String(), nullable=False),
        sa.Column('geographic_unit_id', sa.String(), nullable=False),
        sa.Column('stage', sa.String(), nullable=False),
        sa.Column('source_document_id', sa.String(), nullable=True),
        sa.Column('source_reference', sa.String(), nullable=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('document_hash', sa.String(), nullable=True),
        sa.Column('data_quality_status', sa.String(), default='VERIFIED'),
        sa.Column('is_test_fixture', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'policy_evaluation_plans',
        sa.Column('plan_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('policy_id', sa.String(), sa.ForeignKey('policy_registry.policy_id', ondelete='CASCADE'), nullable=False),
        sa.Column('objective_id', sa.String(), sa.ForeignKey('policy_objectives.objective_id', ondelete='SET NULL'), nullable=True),
        sa.Column('indicator_id', sa.String(), sa.ForeignKey('policy_indicators.indicator_id', ondelete='SET NULL'), nullable=True),
        sa.Column('evaluation_question', sa.Text(), nullable=False),
        sa.Column('evaluation_type', sa.String(), nullable=False),
        sa.Column('objective_being_assessed', sa.Text(), nullable=False),
        sa.Column('original_objective_wording', sa.Text(), nullable=True),
        sa.Column('is_objective_ambiguous', sa.Boolean(), default=False),
        sa.Column('indicator_definition', sa.Text(), nullable=False),
        sa.Column('indicator_type', sa.String(), nullable=False, default='OUTCOME'),
        sa.Column('unit', sa.String(), nullable=False, default='PERCENT'),
        sa.Column('baseline_period', sa.String(), nullable=False),
        sa.Column('comparison_period', sa.String(), nullable=False),
        sa.Column('baseline_value', sa.Float(), nullable=True),
        sa.Column('target_value', sa.Float(), nullable=True),
        sa.Column('target_provenance', sa.String(), nullable=False, default='NO_PUBLISHED_TARGET'),
        sa.Column('target_source_reference', sa.String(), nullable=True),
        sa.Column('actual_value', sa.Float(), nullable=True),
        sa.Column('data_source', sa.String(), nullable=False),
        sa.Column('source_document_ids', sa.JSON(), nullable=True),
        sa.Column('calculation_method', sa.Text(), nullable=False),
        sa.Column('geographic_level', sa.String(), nullable=False),
        sa.Column('limitations', sa.Text(), nullable=False),
        sa.Column('plan_status', sa.String(), nullable=False, default='ACTIVE'),
        sa.Column('is_test_fixture', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'evaluation_studies',
        sa.Column('study_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('scheme_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('evaluation_type', sa.String(), nullable=False),
        sa.Column('conducting_agency', sa.String(), nullable=False),
        sa.Column('publication_date', sa.String(), nullable=False),
        sa.Column('methodology_description', sa.Text(), nullable=False),
        sa.Column('causal_rigor_grade', sa.String(), nullable=False),
        sa.Column('is_causally_identified', sa.Boolean(), default=False),
        sa.Column('identification_strategy', sa.String(), nullable=True),
        sa.Column('source_document_id', sa.String(), nullable=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('document_hash', sa.String(), nullable=True),
        sa.Column('is_test_fixture', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'evaluation_findings',
        sa.Column('finding_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('study_id', sa.String(), sa.ForeignKey('evaluation_studies.study_id', ondelete='CASCADE'), nullable=False),
        sa.Column('indicator_id', sa.String(), sa.ForeignKey('policy_indicators.indicator_id', ondelete='SET NULL'), nullable=True),
        sa.Column('finding_type', sa.String(), nullable=False),
        sa.Column('finding_text', sa.Text(), nullable=False),
        sa.Column('quantified_effect', sa.Float(), nullable=True),
        sa.Column('p_value', sa.Float(), nullable=True),
        sa.Column('confidence_level', sa.String(), nullable=False),
        sa.Column('has_contradicting_evidence', sa.Boolean(), default=False),
        sa.Column('is_test_fixture', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'finding_evidence_links',
        sa.Column('link_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('finding_id', sa.String(), sa.ForeignKey('evaluation_findings.finding_id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_document_id', sa.String(), nullable=False),
        sa.Column('source_passage_id', sa.String(), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('table_reference', sa.String(), nullable=True),
        sa.Column('stance', sa.String(), nullable=False),
        sa.Column('quotation_excerpt', sa.Text(), nullable=False),
        sa.Column('source_credibility_tier', sa.String(), default='TIER_1_STATUTORY'),
        sa.Column('alignment_score', sa.Float(), default=1.0),
        sa.Column('document_hash', sa.String(), nullable=True),
        sa.Column('is_test_fixture', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'evaluation_limitations',
        sa.Column('limitation_id', sa.String(), nullable=False, primary_key=True),
        sa.Column('study_id', sa.String(), sa.ForeignKey('evaluation_studies.study_id', ondelete='CASCADE'), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('confounding_factors', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(), default='MODERATE'),
        sa.Column('is_test_fixture', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade database schema for Phase 10."""
    op.drop_table('evaluation_limitations')
    op.drop_table('finding_evidence_links')
    op.drop_table('evaluation_findings')
    op.drop_table('evaluation_studies')
    op.drop_table('policy_evaluation_plans')
    op.drop_table('indicator_observations')
    op.drop_table('policy_indicators')
    op.drop_table('implementation_activities')
    op.drop_table('beneficiary_groups')
    op.drop_table('policy_objectives')
    op.drop_table('policy_registry')
