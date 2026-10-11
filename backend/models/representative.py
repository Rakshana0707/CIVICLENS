"""
Phase 6 — Public Representative, Constituency, Election, and Term Models.

Defines canonical SQLAlchemy ORM entities for:
- Representative
- Constituency
- Election
- RepresentativeTerm
- ConstituencyBoundaryHistory
"""

import enum
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, JSON
)
from sqlalchemy.orm import relationship
from backend.database.base_class import Base


class RepresentativeType(str, enum.Enum):
    MLA = "MLA"
    LOK_SABHA_MP = "LOK_SABHA_MP"
    RAJYA_SABHA_MP = "RAJYA_SABHA_MP"


class ConstituencyType(str, enum.Enum):
    ASSEMBLY = "ASSEMBLY"
    PARLIAMENTARY = "PARLIAMENTARY"


class ElectionType(str, enum.Enum):
    STATE_ASSEMBLY = "STATE_ASSEMBLY"
    LOK_SABHA = "LOK_SABHA"
    RAJYA_SABHA = "RAJYA_SABHA"


class Representative(Base):
    """
    Canonical elected representative entity (MLA, Lok Sabha MP, Rajya Sabha MP).
    Maintains official name, known aliases, primary/current affiliation, and links to terms.
    """
    __tablename__ = "representatives"

    representative_id = Column(String, primary_key=True, index=True)
    official_name = Column(String, nullable=False, index=True)
    aliases = Column(JSON, default=list)  # e.g. ["M.K. Stalin", "MK Stalin", "மு.க. ஸ்டாலின்"]
    representative_type = Column(String, nullable=False, index=True)  # MLA, LOK_SABHA_MP, RAJYA_SABHA_MP
    
    party_id = Column(String, ForeignKey("political_parties.party_id", ondelete="SET NULL"), nullable=True, index=True)
    constituency_id = Column(String, ForeignKey("constituencies.constituency_id", ondelete="SET NULL"), nullable=True, index=True)
    election_id = Column(String, ForeignKey("elections.election_id", ondelete="SET NULL"), nullable=True, index=True)
    
    term_start = Column(String, nullable=True)
    term_end = Column(String, nullable=True)  # NULL if currently active
    source_document_ids = Column(JSON, default=list)

    person_id = Column(String, ForeignKey("political_persons.person_id", ondelete="SET NULL"), nullable=True, index=True)
    date_of_birth = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    party = relationship("PoliticalParty", foreign_keys=[party_id])
    constituency = relationship("Constituency", foreign_keys=[constituency_id], back_populates="representatives")
    election = relationship("Election", foreign_keys=[election_id])
    terms = relationship("RepresentativeTerm", back_populates="representative", cascade="all, delete-orphan")
    legislative_activities = relationship("LegislativeActivity", back_populates="representative", cascade="all, delete-orphan")


class Constituency(Base):
    """
    State Assembly or Parliamentary electoral constituency in Tamil Nadu.
    Preserves historical validity periods and delimitation boundaries.
    """
    __tablename__ = "constituencies"

    constituency_id = Column(String, primary_key=True, index=True)
    official_name = Column(String, nullable=False, index=True)
    constituency_type = Column(String, nullable=False, index=True)  # ASSEMBLY, PARLIAMENTARY
    district = Column(String, nullable=False, index=True)
    state = Column(String, default="Tamil Nadu")
    
    valid_from = Column(String, nullable=False, default="2008")  # Date or Year string
    valid_to = Column(String, nullable=True)  # NULL if currently active
    source_document_ids = Column(JSON, default=list)

    reservation_status = Column(String, default="GENERAL")  # GENERAL, SC, ST
    delimitation_year = Column(Integer, default=2008)
    predecessor_id = Column(String, nullable=True)
    successor_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    representatives = relationship("Representative", foreign_keys="[Representative.constituency_id]", back_populates="constituency")
    terms = relationship("RepresentativeTerm", back_populates="constituency")
    boundary_history = relationship("ConstituencyBoundaryHistory", back_populates="constituency", cascade="all, delete-orphan")


class Election(Base):
    """
    State Assembly or Parliamentary general/bye-election cycle.
    """
    __tablename__ = "elections"

    election_id = Column(String, primary_key=True, index=True)
    election_name = Column(String, nullable=False)
    election_type = Column(String, nullable=False, index=True)  # STATE_ASSEMBLY, LOK_SABHA, RAJYA_SABHA
    election_year = Column(Integer, nullable=False, index=True)
    poll_date = Column(String, nullable=True)
    counting_date = Column(String, nullable=True)
    total_turnout_pct = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    terms = relationship("RepresentativeTerm", back_populates="election")


class RepresentativeTerm(Base):
    """
    Granular tenure record tying a representative to a specific constituency, election,
    and party affiliation for that specific historical term.
    Guarantees historical party affiliation is never overwritten by current affiliation.
    """
    __tablename__ = "representative_terms"

    term_id = Column(String, primary_key=True, index=True)
    representative_id = Column(String, ForeignKey("representatives.representative_id", ondelete="CASCADE"), nullable=False, index=True)
    constituency_id = Column(String, ForeignKey("constituencies.constituency_id", ondelete="SET NULL"), nullable=True, index=True)
    election_id = Column(String, ForeignKey("elections.election_id", ondelete="SET NULL"), nullable=True, index=True)
    party_id = Column(String, ForeignKey("political_parties.party_id", ondelete="SET NULL"), nullable=True, index=True)

    term_number = Column(Integer, default=1)
    house_type = Column(String, nullable=False)  # TN_ASSEMBLY, LOK_SABHA, RAJYA_SABHA
    term_start = Column(String, nullable=False)
    term_end = Column(String, nullable=True)
    is_active_term = Column(Boolean, default=False)
    source_document_ids = Column(JSON, default=list)

    votes_polled = Column(Integer, nullable=True)
    win_margin_votes = Column(Integer, nullable=True)
    win_margin_percent = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    representative = relationship("Representative", back_populates="terms")
    constituency = relationship("Constituency", back_populates="terms")
    election = relationship("Election", back_populates="terms")
    party = relationship("PoliticalParty", foreign_keys=[party_id])


class ConstituencyBoundaryHistory(Base):
    """
    Tracks historical boundary, delimitation order, or naming changes for constituencies.
    """
    __tablename__ = "constituency_boundary_history"

    history_id = Column(String, primary_key=True, index=True)
    constituency_id = Column(String, ForeignKey("constituencies.constituency_id", ondelete="CASCADE"), nullable=False, index=True)
    historical_name = Column(String, nullable=False)
    delimitation_order = Column(String, nullable=False)  # e.g. "Delimitation 1976", "Delimitation 2008"
    valid_from = Column(String, nullable=False)
    valid_to = Column(String, nullable=True)
    change_summary = Column(Text, nullable=True)
    source_document_ids = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    constituency = relationship("Constituency", back_populates="boundary_history")


class LegislativeActivityType(str, enum.Enum):
    QUESTION_STARRED = "QUESTION_STARRED"
    QUESTION_UNSTARRED = "QUESTION_UNSTARRED"
    DEBATE = "DEBATE"
    ATTENDANCE = "ATTENDANCE"
    COMMITTEE = "COMMITTEE"
    BILL = "BILL"
    CALL_ATTENTION = "CALL_ATTENTION"
    ZERO_HOUR = "ZERO_HOUR"


class DataQualityStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_RECORDED = "NOT_RECORDED"


class LegislativeActivity(Base):
    """
    Granular record of representative parliamentary or assembly activity.
    Stores questions submitted, debates participated, attendance percentage,
    bills introduced, and committee participation with full source provenance.
    """
    __tablename__ = "legislative_activities"

    activity_id = Column(String, primary_key=True, index=True)
    representative_id = Column(String, ForeignKey("representatives.representative_id", ondelete="CASCADE"), nullable=False, index=True)
    legislative_body = Column(String, nullable=False, index=True)  # LOK_SABHA, RAJYA_SABHA, TN_ASSEMBLY
    session = Column(String, nullable=False, index=True)  # e.g. "17th Lok Sabha - Session 11", "16th Assembly - Session 4"
    activity_type = Column(String, nullable=False, index=True)  # QUESTION_STARRED, QUESTION_UNSTARRED, DEBATE, ATTENDANCE, etc.
    activity_date = Column(String, nullable=True, index=True)
    
    count = Column(Integer, default=1)
    value = Column(Float, nullable=True)  # e.g., attendance percentage 85.5
    title_subject = Column(String, nullable=True)
    ministry_or_department = Column(String, nullable=True)
    
    source_document_id = Column(String, nullable=True, index=True)
    source_reference = Column(String, nullable=True)  # e.g. "Q.No 1420", "TNLA Debate Vol 14, p. 52"
    data_quality_status = Column(String, nullable=False, default="VERIFIED")  # VERIFIED, PARTIAL, UNAVAILABLE, NOT_RECORDED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    representative = relationship("Representative", back_populates="legislative_activities")
