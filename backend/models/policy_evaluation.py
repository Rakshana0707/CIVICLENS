"""
Phase 10 — Public Policy Outcome & Impact Evaluation Database Models.
=====================================================================

Defines canonical SQLAlchemy ORM entities for:
1. PolicyObjective: Stated programmatic or statutory goals.
2. BeneficiaryGroup: Intended target demographic population & eligibility criteria.
3. ImplementationActivity: Administrative workflows, tenders, operational drives.
4. PolicyIndicator: Metrics across Results Chain (INPUT, ACTIVITY, OUTPUT, OUTCOME, IMPACT).
5. IndicatorObservation: Empirical observations (BASELINE, INTERMEDIATE, FOLLOW_UP, TARGET).
6. EvaluationStudy: Structured evaluations classified across 9 evaluation types and causal rigor grades.
7. EvaluationFinding: Synthesized findings with effect sizes, significance, and confidence.
8. FindingEvidenceLink: Supporting and contradicting evidence excerpts with source document references.
9. EvaluationLimitation: Caveats, confounders, data gaps, and uncertainty notes.

Guiding Principles:
- Reuses existing models (Phases 1–9) for budgets, schemes, promises, claims, and civic issues.
- Enforces Results Chain discipline: expenditure or activity completion is NOT proof of public benefit.
- Supports 9 evaluation types with strict causal validation and downgrading rules.
- Fully compatible with the Unified Civic Intelligence & Evidence Graph (CivicGraphNode / CivicEvidenceEdge).
- Zero-fabrication compliance: all test data explicitly marked with is_test_fixture=True.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, Enum, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.database.base_class import Base


class IndicatorType(str, enum.Enum):
    """
    Standardized classification across the Five-Tier Results Chain.
    """
    INPUT = "INPUT"          # Financial, human, or material resources committed
    ACTIVITY = "ACTIVITY"    # Administrative actions, procurement, campaigns
    OUTPUT = "OUTPUT"        # Direct physical deliverables or transaction counts
    OUTCOME = "OUTCOME"      # Intermediate utilization, access, or behavioral changes
    IMPACT = "IMPACT"        # Long-term societal, demographic, or economic changes

    @classmethod
    def from_string(cls, val: Any) -> "IndicatorType":
        if isinstance(val, cls):
            return val
        s = str(val).strip().upper()
        for member in cls:
            if member.value == s:
                return member
        raise ValueError(f"Unknown IndicatorType: {val}")


class ObservationStage(str, enum.Enum):
    """
    Temporal measurement stage of an indicator observation.
    """
    BASELINE = "BASELINE"            # Pre-intervention benchmark
    INTERMEDIATE = "INTERMEDIATE"    # Midline or operational progress check
    FOLLOW_UP = "FOLLOW_UP"          # Post-intervention endline or evaluation point
    TARGET = "TARGET"                # Formally announced policy target

    @classmethod
    def from_string(cls, val: Any) -> "ObservationStage":
        if isinstance(val, cls):
            return val
        s = str(val).strip().upper()
        for member in cls:
            if member.value == s:
                return member
        raise ValueError(f"Unknown ObservationStage: {val}")


class EvaluationType(str, enum.Enum):
    """
    Nine standardized policy evaluation types in Phase 10.
    """
    IMPLEMENTATION_PROGRESS = "IMPLEMENTATION_PROGRESS"
    BUDGET_EXECUTION = "BUDGET_EXECUTION"
    TARGET_VERSUS_ACTUAL = "TARGET_VERSUS_ACTUAL"
    BEFORE_AND_AFTER_DESCRIPTIVE = "BEFORE_AND_AFTER_DESCRIPTIVE"
    GEOGRAPHIC_COMPARISON = "GEOGRAPHIC_COMPARISON"
    BENEFICIARY_COVERAGE = "BENEFICIARY_COVERAGE"
    AUDIT_FINDING = "AUDIT_FINDING"
    EVIDENCE_BASED_OUTCOME = "EVIDENCE_BASED_OUTCOME"
    CAUSAL_EVALUATION = "CAUSAL_EVALUATION"

    @classmethod
    def from_string(cls, val: Any) -> "EvaluationType":
        if isinstance(val, cls):
            return val
        s = str(val).strip().upper()
        for member in cls:
            if member.value == s:
                return member
        raise ValueError(f"Unknown EvaluationType: {val}")


class CausalRigorGrade(str, enum.Enum):
    """
    Hierarchical assessment of methodological credibility for causal inference.
    """
    GRADE_A_EXPERIMENTAL = "GRADE_A_EXPERIMENTAL"              # Randomized Controlled Trial
    GRADE_B_QUASI_EXPERIMENTAL = "GRADE_B_QUASI_EXPERIMENTAL"  # DiD, RDD, IV with verified assumptions
    GRADE_C_MATCHED_OBSERVATIONAL = "GRADE_C_MATCHED_OBSERVATIONAL" # Propensity score or covariate matching
    GRADE_D_DESCRIPTIVE_CORRELATIONAL = "GRADE_D_DESCRIPTIVE_CORRELATIONAL" # Before/after without control
    GRADE_E_ANECDOTAL_UNSUBSTANTIATED = "GRADE_E_ANECDOTAL_UNSUBSTANTIATED" # Uncorroborated narrative

    @classmethod
    def from_string(cls, val: Any) -> "CausalRigorGrade":
        if isinstance(val, cls):
            return val
        s = str(val).strip().upper()
        for member in cls:
            if member.value == s:
                return member
        raise ValueError(f"Unknown CausalRigorGrade: {val}")


class FindingType(str, enum.Enum):
    """
    Qualitative trajectory of an evaluation finding.
    """
    POSITIVE_IMPACT = "POSITIVE_IMPACT"
    NEUTRAL_OR_INSIGNIFICANT = "NEUTRAL_OR_INSIGNIFICANT"
    NEGATIVE_OR_ADVERSE = "NEGATIVE_OR_ADVERSE"
    MIXED_RESULTS = "MIXED_RESULTS"
    INCONCLUSIVE_DATA = "INCONCLUSIVE_DATA"


class ConfidenceLevel(str, enum.Enum):
    """
    Statistical confidence band associated with an evaluation finding.
    """
    VERY_HIGH = "VERY_HIGH"    # p < 0.01 with robust standard errors
    HIGH = "HIGH"              # p < 0.05
    MODERATE = "MODERATE"      # p < 0.10 or strong descriptive triangulation
    LOW = "LOW"                # Descriptive with sample or measurement caveats
    VERY_LOW = "VERY_LOW"      # Fragmentary or disputed data


class EvidenceStance(str, enum.Enum):
    """
    Directional relationship of an evidence passage relative to a finding or official claim.
    """
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    QUALIFIES = "QUALIFIES"
    NEUTRAL = "NEUTRAL"


class LimitationCategory(str, enum.Enum):
    """
    Categorization of methodological or data limitations.
    """
    DATA_COMPLETENESS = "DATA_COMPLETENESS"
    MEASUREMENT_ERROR = "MEASUREMENT_ERROR"
    EXTERNAL_CONFOUNDING = "EXTERNAL_CONFOUNDING"
    SELECTION_BIAS = "SELECTION_BIAS"
    ATTRITION = "ATTRITION"
    ABSENCE_OF_CONTROL_GROUP = "ABSENCE_OF_CONTROL_GROUP"
    AGGREGATION_BIAS = "AGGREGATION_BIAS"


class PolicyEvaluationStatus(str, enum.Enum):
    """
    Lifecycle status of a policy in the Policy Evaluation Registry.
    """
    NOT_STARTED = "NOT_STARTED"
    PLAN_DEFINED = "PLAN_DEFINED"
    DATA_COLLECTION = "DATA_COLLECTION"
    IN_PROGRESS = "IN_PROGRESS"
    EVALUATED = "EVALUATED"
    INCONCLUSIVE = "INCONCLUSIVE"
    FLAGGED_FOR_REVIEW = "FLAGGED_FOR_REVIEW"
    ARCHIVED = "ARCHIVED"

    @classmethod
    def from_string(cls, val: Any) -> "PolicyEvaluationStatus":
        if isinstance(val, cls):
            return val
        s = str(val).strip().upper()
        for member in cls:
            if member.value == s:
                return member
        raise ValueError(f"Unknown PolicyEvaluationStatus: {val}")


class TargetProvenanceType(str, enum.Enum):
    """
    Distinguishes officially stated government targets from analyst-proposed benchmarks
    or policies with no published quantitative target.
    Never invent an official policy target.
    """
    OFFICIALLY_STATED = "OFFICIALLY_STATED"                      # Explicitly published in GO, Budget, Policy Note, or Manifesto
    ANALYST_PROPOSED_BENCHMARK = "ANALYST_PROPOSED_BENCHMARK"    # Explicitly labelled analytical comparison benchmark
    NO_PUBLISHED_TARGET = "NO_PUBLISHED_TARGET"                  # No target published; target_value must be None

    @classmethod
    def from_string(cls, val: Any) -> "TargetProvenanceType":
        if isinstance(val, cls):
            return val
        s = str(val).strip().upper()
        for member in cls:
            if member.value == s:
                return member
        raise ValueError(f"Unknown TargetProvenanceType: {val}")


class ObjectiveReviewStatus(str, enum.Enum):
    """
    Review status for policy objectives, flagging ambiguous or underspecified wording.
    """
    VERIFIED_CLEAR = "VERIFIED_CLEAR"
    FLAGGED_AMBIGUOUS = "FLAGGED_AMBIGUOUS"
    PENDING_HUMAN_REVIEW = "PENDING_HUMAN_REVIEW"


# ===========================================================================
# Core Models
# ===========================================================================

class PolicyRegistryEntry(Base):
    """
    Phase 10.3 — Canonical Policy Evaluation Registry Entry.
    Links directly to existing Phase 1 (BudgetScheme), Phase 2 (HistoricalScheme),
    and Phase 3 (PoliticalPromise) models wherever available.
    """
    __tablename__ = "policy_registry"

    policy_id = Column(String, primary_key=True, index=True)

    # Canonical links to Phase 1–3 entities
    budget_scheme_id = Column(Integer, ForeignKey("budget_schemes.id", ondelete="SET NULL"), nullable=True, index=True)
    historical_scheme_id = Column(Integer, ForeignKey("historical_schemes.id", ondelete="SET NULL"), nullable=True, index=True)
    promise_id = Column(String, ForeignKey("political_promises.promise_id", ondelete="SET NULL"), nullable=True, index=True)
    canonical_scheme_code = Column(String, nullable=False, index=True)

    # Names & Aliases
    policy_name = Column(String, nullable=False, index=True)
    policy_name_ta = Column(String, nullable=True)
    aliases = Column(JSON, default=list)

    # Department & Governance
    responsible_department = Column(String, nullable=True, index=True)
    department_id = Column(Integer, ForeignKey("budget_departments.id", ondelete="SET NULL"), nullable=True, index=True)

    # Objectives & Ambiguity Preservation
    objectives_summary = Column(Text, nullable=False)
    original_objective_wording = Column(Text, nullable=False)
    is_objective_ambiguous = Column(Boolean, default=False, index=True)
    ambiguity_review_notes = Column(Text, nullable=True)
    objective_review_status = Column(
        Enum(ObjectiveReviewStatus),
        nullable=False,
        default=ObjectiveReviewStatus.VERIFIED_CLEAR,
        index=True,
    )

    # Beneficiaries, Scope, and Timeline
    intended_beneficiaries = Column(Text, nullable=False)
    geographic_scope = Column(String, nullable=False, default="STATEWIDE", index=True)
    covered_districts = Column(JSON, default=list)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)

    # Rules, Targets, and Provenance
    implementation_rules = Column(JSON, default=dict)
    stated_targets = Column(JSON, default=list)
    source_documents = Column(JSON, default=list)
    evaluation_status = Column(
        Enum(PolicyEvaluationStatus),
        nullable=False,
        default=PolicyEvaluationStatus.NOT_STARTED,
        index=True,
    )

    is_test_fixture = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    objectives = relationship("PolicyObjective", back_populates="policy_entry", cascade="all, delete-orphan")
    evaluation_plans = relationship("PolicyEvaluationPlan", back_populates="policy_entry", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "budget_scheme_id": self.budget_scheme_id,
            "historical_scheme_id": self.historical_scheme_id,
            "promise_id": self.promise_id,
            "canonical_scheme_code": self.canonical_scheme_code,
            "policy_name": self.policy_name,
            "policy_name_ta": self.policy_name_ta,
            "aliases": self.aliases or [],
            "responsible_department": self.responsible_department,
            "department_id": self.department_id,
            "objectives_summary": self.objectives_summary,
            "original_objective_wording": self.original_objective_wording,
            "is_objective_ambiguous": self.is_objective_ambiguous,
            "ambiguity_review_notes": self.ambiguity_review_notes,
            "objective_review_status": (
                self.objective_review_status.value
                if hasattr(self.objective_review_status, "value")
                else str(self.objective_review_status)
            ),
            "intended_beneficiaries": self.intended_beneficiaries,
            "geographic_scope": self.geographic_scope,
            "covered_districts": self.covered_districts or [],
            "start_date": self.start_date,
            "end_date": self.end_date,
            "implementation_rules": self.implementation_rules or {},
            "stated_targets": self.stated_targets or [],
            "source_documents": self.source_documents or [],
            "evaluation_status": (
                self.evaluation_status.value
                if hasattr(self.evaluation_status, "value")
                else str(self.evaluation_status)
            ),
            "is_test_fixture": self.is_test_fixture,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PolicyObjective(Base):
    """
    Formal policy or programmatic objective announced by the Government of Tamil Nadu.
    Preserves exact original wording and flags ambiguous objectives for human review.
    """
    __tablename__ = "policy_objectives"

    objective_id = Column(String, primary_key=True, index=True)
    policy_id = Column(String, ForeignKey("policy_registry.policy_id", ondelete="SET NULL"), nullable=True, index=True)
    scheme_id = Column(String, nullable=True, index=True)      # FK reference to schemes table if present
    promise_id = Column(String, nullable=True, index=True)     # FK reference to political_promises if present
    
    title = Column(String, nullable=False, index=True)
    title_ta = Column(String, nullable=True)                   # Tamil title
    description = Column(Text, nullable=False)
    original_wording = Column(Text, nullable=True)             # Verbatim source text preserved
    sector = Column(String, nullable=False, index=True)        # Education, Health, Social Welfare, Infrastructure
    
    is_statutory = Column(Boolean, default=False)              # Backed by legislation vs executive order
    target_metrics = Column(JSON, default=dict)                # Quantitative milestone definitions
    is_ambiguous = Column(Boolean, default=False, index=True)
    ambiguity_flag_reason = Column(Text, nullable=True)
    review_status = Column(
        Enum(ObjectiveReviewStatus),
        nullable=False,
        default=ObjectiveReviewStatus.VERIFIED_CLEAR,
        index=True,
    )
    
    is_test_fixture = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    policy_entry = relationship("PolicyRegistryEntry", back_populates="objectives")
    indicators = relationship("PolicyIndicator", back_populates="policy_objective", cascade="all, delete-orphan")
    beneficiary_groups = relationship("BeneficiaryGroup", back_populates="policy_objective", cascade="all, delete-orphan")
    evaluation_plans = relationship("PolicyEvaluationPlan", back_populates="objective")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "policy_id": self.policy_id,
            "scheme_id": self.scheme_id,
            "promise_id": self.promise_id,
            "title": self.title,
            "title_ta": self.title_ta,
            "description": self.description,
            "original_wording": self.original_wording or self.description,
            "sector": self.sector,
            "is_statutory": self.is_statutory,
            "target_metrics": self.target_metrics,
            "is_ambiguous": self.is_ambiguous,
            "ambiguity_flag_reason": self.ambiguity_flag_reason,
            "review_status": (
                self.review_status.value
                if hasattr(self.review_status, "value")
                else str(self.review_status)
            ),
            "is_test_fixture": self.is_test_fixture,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PolicyEvaluationPlan(Base):
    """
    Phase 10.3 — Structured Policy Evaluation Plan.
    Connects an evaluation question, objective, indicator definition, baseline/comparison periods,
    target provenance (officially stated vs analyst benchmark vs none), actual values,
    data source, calculation method, geographic level, and explicit limitations.
    """
    __tablename__ = "policy_evaluation_plans"

    plan_id = Column(String, primary_key=True, index=True)
    policy_id = Column(String, ForeignKey("policy_registry.policy_id", ondelete="CASCADE"), nullable=False, index=True)
    objective_id = Column(String, ForeignKey("policy_objectives.objective_id", ondelete="SET NULL"), nullable=True, index=True)
    indicator_id = Column(String, ForeignKey("policy_indicators.indicator_id", ondelete="SET NULL"), nullable=True, index=True)

    evaluation_question = Column(Text, nullable=False)
    evaluation_type = Column(Enum(EvaluationType), nullable=False, default=EvaluationType.EVIDENCE_BASED_OUTCOME, index=True)
    objective_being_assessed = Column(Text, nullable=False)
    original_objective_wording = Column(Text, nullable=True)
    is_objective_ambiguous = Column(Boolean, default=False, index=True)

    indicator_definition = Column(Text, nullable=False)
    indicator_type = Column(Enum(IndicatorType), nullable=False, default=IndicatorType.OUTCOME, index=True)
    unit = Column(String, nullable=False, default="PERCENT")

    baseline_period = Column(String, nullable=False)
    comparison_period = Column(String, nullable=False)
    baseline_value = Column(Float, nullable=True)

    # Target provenance — strictly distinguishes official vs analyst vs none
    target_value = Column(Float, nullable=True)
    target_provenance = Column(
        Enum(TargetProvenanceType),
        nullable=False,
        default=TargetProvenanceType.NO_PUBLISHED_TARGET,
        index=True,
    )
    target_source_reference = Column(String, nullable=True)

    actual_value = Column(Float, nullable=True)

    data_source = Column(String, nullable=False)
    source_document_ids = Column(JSON, default=list)
    calculation_method = Column(Text, nullable=False)
    geographic_level = Column(String, nullable=False, index=True)
    limitations = Column(Text, nullable=False)

    plan_status = Column(String, nullable=False, default="ACTIVE", index=True)
    is_test_fixture = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    policy_entry = relationship("PolicyRegistryEntry", back_populates="evaluation_plans")
    objective = relationship("PolicyObjective", back_populates="evaluation_plans")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "policy_id": self.policy_id,
            "objective_id": self.objective_id,
            "indicator_id": self.indicator_id,
            "evaluation_question": self.evaluation_question,
            "evaluation_type": (
                self.evaluation_type.value
                if hasattr(self.evaluation_type, "value")
                else str(self.evaluation_type)
            ),
            "objective_being_assessed": self.objective_being_assessed,
            "original_objective_wording": self.original_objective_wording,
            "is_objective_ambiguous": self.is_objective_ambiguous,
            "indicator_definition": self.indicator_definition,
            "indicator_type": (
                self.indicator_type.value
                if hasattr(self.indicator_type, "value")
                else str(self.indicator_type)
            ),
            "unit": self.unit,
            "baseline_period": self.baseline_period,
            "comparison_period": self.comparison_period,
            "baseline_value": self.baseline_value,
            "target_value": self.target_value,
            "target_provenance": (
                self.target_provenance.value
                if hasattr(self.target_provenance, "value")
                else str(self.target_provenance)
            ),
            "target_source_reference": self.target_source_reference,
            "actual_value": self.actual_value,
            "data_source": self.data_source,
            "source_document_ids": self.source_document_ids or [],
            "calculation_method": self.calculation_method,
            "geographic_level": self.geographic_level,
            "limitations": self.limitations,
            "plan_status": self.plan_status,
            "is_test_fixture": self.is_test_fixture,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class BeneficiaryGroup(Base):
    """
    Target population group defined with specific eligibility criteria and demographic universe.
    """
    __tablename__ = "beneficiary_groups"

    group_id = Column(String, primary_key=True, index=True)
    objective_id = Column(String, ForeignKey("policy_objectives.objective_id", ondelete="CASCADE"), nullable=False, index=True)
    scheme_id = Column(String, nullable=True, index=True)
    
    name = Column(String, nullable=False, index=True)
    name_ta = Column(String, nullable=True)
    eligibility_criteria = Column(Text, nullable=False)
    exclusion_criteria = Column(Text, nullable=True)
    estimated_eligible_population = Column(Integer, nullable=True)
    geographic_focus = Column(String, nullable=True)           # Statewide, Rural, Urban, Specific Districts
    
    is_test_fixture = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    policy_objective = relationship("PolicyObjective", back_populates="beneficiary_groups")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "objective_id": self.objective_id,
            "scheme_id": self.scheme_id,
            "name": self.name,
            "name_ta": self.name_ta,
            "eligibility_criteria": self.eligibility_criteria,
            "exclusion_criteria": self.exclusion_criteria,
            "estimated_eligible_population": self.estimated_eligible_population,
            "geographic_focus": self.geographic_focus,
            "is_test_fixture": self.is_test_fixture,
        }


class ImplementationActivity(Base):
    """
    Operational workflow, tendering, construction, or distribution activity executed under a policy.
    """
    __tablename__ = "implementation_activities"

    activity_id = Column(String, primary_key=True, index=True)
    scheme_id = Column(String, nullable=False, index=True)
    activity_name = Column(String, nullable=False, index=True)
    activity_type = Column(String, nullable=False)             # PROCUREMENT, CONSTRUCTION, TRAINING, REGISTRATION
    
    scheduled_start = Column(String, nullable=True)            # YYYY-MM-DD
    scheduled_end = Column(String, nullable=True)              # YYYY-MM-DD
    actual_end = Column(String, nullable=True)                 # YYYY-MM-DD
    status = Column(String, nullable=False, default="IN_PROGRESS") # PLANNED, IN_PROGRESS, COMPLETED, DELAYED
    
    budget_allocated = Column(Float, default=0.0)              # In Crores ₹
    expenditure_incurred = Column(Float, default=0.0)          # In Crores ₹
    implementing_agency = Column(String, nullable=True)        # PWD, TWAD, Health Dept
    
    source_document_id = Column(String, nullable=True)
    is_test_fixture = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "activity_id": self.activity_id,
            "scheme_id": self.scheme_id,
            "activity_name": self.activity_name,
            "activity_type": self.activity_type,
            "scheduled_start": self.scheduled_start,
            "scheduled_end": self.scheduled_end,
            "actual_end": self.actual_end,
            "status": self.status,
            "budget_allocated": self.budget_allocated,
            "expenditure_incurred": self.expenditure_incurred,
            "implementing_agency": self.implementing_agency,
            "is_test_fixture": self.is_test_fixture,
        }


class PolicyIndicator(Base):
    """
    Measurable quantitative metric situated strictly along the Five-Tier Results Chain.
    """
    __tablename__ = "policy_indicators"

    indicator_id = Column(String, primary_key=True, index=True)
    objective_id = Column(String, ForeignKey("policy_objectives.objective_id", ondelete="CASCADE"), nullable=False, index=True)
    scheme_id = Column(String, nullable=True, index=True)
    
    indicator_name = Column(String, nullable=False, index=True)
    indicator_name_ta = Column(String, nullable=True)
    indicator_type = Column(Enum(IndicatorType), nullable=False, index=True) # INPUT, ACTIVITY, OUTPUT, OUTCOME, IMPACT
    unit = Column(String, nullable=False)                      # PERCENT, COUNT, RUPEES_CRORE, RATIO, PER_1000
    
    direction_of_improvement = Column(String, default="INCREASE") # INCREASE, DECREASE
    aggregation_method = Column(String, default="SUM")         # SUM, MEAN, WEIGHTED_AVERAGE, MEDIAN
    description = Column(Text, nullable=True)
    
    is_test_fixture = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    policy_objective = relationship("PolicyObjective", back_populates="indicators")
    observations = relationship("IndicatorObservation", back_populates="policy_indicator", cascade="all, delete-orphan")
    findings = relationship("EvaluationFinding", back_populates="policy_indicator")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "indicator_id": self.indicator_id,
            "objective_id": self.objective_id,
            "scheme_id": self.scheme_id,
            "indicator_name": self.indicator_name,
            "indicator_name_ta": self.indicator_name_ta,
            "indicator_type": self.indicator_type.value if hasattr(self.indicator_type, "value") else str(self.indicator_type),
            "unit": self.unit,
            "direction_of_improvement": self.direction_of_improvement,
            "aggregation_method": self.aggregation_method,
            "description": self.description,
            "is_test_fixture": self.is_test_fixture,
        }


class IndicatorObservation(Base):
    """
    Discrete empirical observation recorded at a specific time and geographic level.
    """
    __tablename__ = "indicator_observations"

    observation_id = Column(String, primary_key=True, index=True)
    indicator_id = Column(String, ForeignKey("policy_indicators.indicator_id", ondelete="CASCADE"), nullable=False, index=True)
    
    value = Column(Float, nullable=False)
    reference_period = Column(String, nullable=False, index=True)  # e.g., "2018", "2021", "2023-24"
    geographic_level = Column(String, nullable=False, index=True)  # STATE, DISTRICT, BLOCK, CONSTITUENCY
    geographic_unit_id = Column(String, nullable=False, index=True) # e.g., "TN", "DISTRICT-03", "AC-013"
    
    stage = Column(Enum(ObservationStage), nullable=False, index=True) # BASELINE, INTERMEDIATE, FOLLOW_UP, TARGET
    
    source_document_id = Column(String, nullable=True, index=True)
    source_reference = Column(String, nullable=True)               # e.g., "NFHS-5 Factsheet Table 2"
    source_url = Column(String, nullable=True)
    document_hash = Column(String, nullable=True)                  # SHA-256 digest
    
    data_quality_status = Column(String, default="VERIFIED")       # VERIFIED, PROVISIONAL, ESTIMATED
    is_test_fixture = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    policy_indicator = relationship("PolicyIndicator", back_populates="observations")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "indicator_id": self.indicator_id,
            "value": self.value,
            "reference_period": self.reference_period,
            "geographic_level": self.geographic_level,
            "geographic_unit_id": self.geographic_unit_id,
            "stage": self.stage.value if hasattr(self.stage, "value") else str(self.stage),
            "source_document_id": self.source_document_id,
            "source_reference": self.source_reference,
            "source_url": self.source_url,
            "document_hash": self.document_hash,
            "data_quality_status": self.data_quality_status,
            "is_test_fixture": self.is_test_fixture,
        }


class EvaluationStudy(Base):
    """
    Structured policy evaluation study or statutory audit inquiry.
    """
    __tablename__ = "evaluation_studies"

    study_id = Column(String, primary_key=True, index=True)
    scheme_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    
    evaluation_type = Column(Enum(EvaluationType), nullable=False, index=True)
    conducting_agency = Column(String, nullable=False)             # CAG, State Planning Commission, Academic Institute
    publication_date = Column(String, nullable=False)              # YYYY-MM-DD
    
    methodology_description = Column(Text, nullable=False)
    causal_rigor_grade = Column(Enum(CausalRigorGrade), nullable=False, default=CausalRigorGrade.GRADE_D_DESCRIPTIVE_CORRELATIONAL)
    is_causally_identified = Column(Boolean, default=False)
    identification_strategy = Column(String, nullable=True)        # DID, RDD, IV, NONE
    
    source_document_id = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    document_hash = Column(String, nullable=True)
    
    is_test_fixture = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    findings = relationship("EvaluationFinding", back_populates="study", cascade="all, delete-orphan")
    limitations = relationship("EvaluationLimitation", back_populates="study", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "study_id": self.study_id,
            "scheme_id": self.scheme_id,
            "title": self.title,
            "evaluation_type": self.evaluation_type.value if hasattr(self.evaluation_type, "value") else str(self.evaluation_type),
            "conducting_agency": self.conducting_agency,
            "publication_date": self.publication_date,
            "methodology_description": self.methodology_description,
            "causal_rigor_grade": self.causal_rigor_grade.value if hasattr(self.causal_rigor_grade, "value") else str(self.causal_rigor_grade),
            "is_causally_identified": self.is_causally_identified,
            "identification_strategy": self.identification_strategy,
            "source_document_id": self.source_document_id,
            "is_test_fixture": self.is_test_fixture,
        }


class EvaluationFinding(Base):
    """
    Synthesized empirical conclusion regarding effect size, direction, and significance.
    """
    __tablename__ = "evaluation_findings"

    finding_id = Column(String, primary_key=True, index=True)
    study_id = Column(String, ForeignKey("evaluation_studies.study_id", ondelete="CASCADE"), nullable=False, index=True)
    indicator_id = Column(String, ForeignKey("policy_indicators.indicator_id", ondelete="SET NULL"), nullable=True, index=True)
    
    finding_type = Column(Enum(FindingType), nullable=False, index=True)
    finding_text = Column(Text, nullable=False)
    
    quantified_effect = Column(Float, nullable=True)               # e.g., +5.9 (percentage points or effect size)
    p_value = Column(Float, nullable=True)                         # Statistical p-value
    confidence_level = Column(Enum(ConfidenceLevel), nullable=False, default=ConfidenceLevel.MODERATE)
    
    has_contradicting_evidence = Column(Boolean, default=False)
    is_test_fixture = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    study = relationship("EvaluationStudy", back_populates="findings")
    policy_indicator = relationship("PolicyIndicator", back_populates="findings")
    evidence_links = relationship("FindingEvidenceLink", back_populates="finding", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "study_id": self.study_id,
            "indicator_id": self.indicator_id,
            "finding_type": self.finding_type.value if hasattr(self.finding_type, "value") else str(self.finding_type),
            "finding_text": self.finding_text,
            "quantified_effect": self.quantified_effect,
            "p_value": self.p_value,
            "confidence_level": self.confidence_level.value if hasattr(self.confidence_level, "value") else str(self.confidence_level),
            "has_contradicting_evidence": self.has_contradicting_evidence,
            "is_test_fixture": self.is_test_fixture,
        }


class FindingEvidenceLink(Base):
    """
    Granular supporting or contradicting documentary evidence backing an evaluation finding.
    """
    __tablename__ = "finding_evidence_links"

    link_id = Column(String, primary_key=True, index=True)
    finding_id = Column(String, ForeignKey("evaluation_findings.finding_id", ondelete="CASCADE"), nullable=False, index=True)
    
    source_document_id = Column(String, nullable=False, index=True)
    source_passage_id = Column(String, nullable=True)
    page_number = Column(Integer, nullable=True)
    table_reference = Column(String, nullable=True)
    
    stance = Column(Enum(EvidenceStance), nullable=False, default=EvidenceStance.SUPPORTS)
    quotation_excerpt = Column(Text, nullable=False)
    source_credibility_tier = Column(String, default="TIER_1_STATUTORY") # TIER_1 to TIER_5
    
    alignment_score = Column(Float, default=1.0)                  # 0.0 to 1.0
    document_hash = Column(String, nullable=True)                 # SHA-256
    
    is_test_fixture = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    finding = relationship("EvaluationFinding", back_populates="evidence_links")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "link_id": self.link_id,
            "finding_id": self.finding_id,
            "source_document_id": self.source_document_id,
            "source_passage_id": self.source_passage_id,
            "page_number": self.page_number,
            "table_reference": self.table_reference,
            "stance": self.stance.value if hasattr(self.stance, "value") else str(self.stance),
            "quotation_excerpt": self.quotation_excerpt,
            "source_credibility_tier": self.source_credibility_tier,
            "alignment_score": self.alignment_score,
            "document_hash": self.document_hash,
            "is_test_fixture": self.is_test_fixture,
        }


class EvaluationLimitation(Base):
    """
    Methodological caveat, potential confounding factor, or data gap.
    """
    __tablename__ = "evaluation_limitations"

    limitation_id = Column(String, primary_key=True, index=True)
    study_id = Column(String, ForeignKey("evaluation_studies.study_id", ondelete="CASCADE"), nullable=False, index=True)
    
    category = Column(Enum(LimitationCategory), nullable=False, index=True)
    description = Column(Text, nullable=False)
    confounding_factors = Column(Text, nullable=True)
    severity = Column(String, default="MODERATE")                 # LOW, MODERATE, HIGH, CRITICAL
    
    is_test_fixture = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    study = relationship("EvaluationStudy", back_populates="limitations")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "limitation_id": self.limitation_id,
            "study_id": self.study_id,
            "category": self.category.value if hasattr(self.category, "value") else str(self.category),
            "description": self.description,
            "confounding_factors": self.confounding_factors,
            "severity": self.severity,
            "is_test_fixture": self.is_test_fixture,
        }
