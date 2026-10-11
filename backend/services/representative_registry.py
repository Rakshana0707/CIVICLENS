"""
Phase 6 — Public Representative and Constituency Registry Service.

Provides canonical management, disambiguation, historical term tracking,
and constituency boundary change resolution for MLAs, Lok Sabha MPs, and Rajya Sabha MPs.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.models.representative import (
    Representative,
    Constituency,
    Election,
    RepresentativeTerm,
    ConstituencyBoundaryHistory,
    RepresentativeType,
    ConstituencyType,
    ElectionType
)
from backend.models.news import PoliticalParty

logger = logging.getLogger("civiclens.phase6.registry")
logging.basicConfig(level=logging.INFO)


class AmbiguousIdentityError(Exception):
    """Raised when a representative query matches multiple distinct individuals and cannot be disambiguated."""
    def __init__(self, message: str, candidate_ids: List[str]):
        super().__init__(message)
        self.candidate_ids = candidate_ids


class EntityNotFoundError(Exception):
    """Raised when a requested entity does not exist in the registry."""
    pass


class RepresentativeRegistryService:
    """
    Core service managing canonical representatives, constituencies, elections, and terms.
    Enforces multi-attribute disambiguation and preserves historical affiliations.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalizes representative name by trimming, lowercasing, and stripping punctuation/honorifics."""
        if not name:
            return ""
        s = name.strip().lower()
        # Remove common honorifics
        s = re.sub(r'^(thiru|dr\.?|mr\.?|smt\.?|prof\.?)\s+', '', s)
        # Strip internal periods and excessive whitespaces
        s = s.replace(".", " ")
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    # -------------------------------------------------------------------------
    # Entity Registration Methods
    # -------------------------------------------------------------------------

    def register_representative(
        self,
        representative_id: str,
        official_name: str,
        representative_type: str,
        aliases: Optional[List[str]] = None,
        party_id: Optional[str] = None,
        constituency_id: Optional[str] = None,
        election_id: Optional[str] = None,
        term_start: Optional[str] = None,
        term_end: Optional[str] = None,
        source_document_ids: Optional[List[str]] = None,
        person_id: Optional[str] = None,
        date_of_birth: Optional[str] = None,
        gender: Optional[str] = None
    ) -> Representative:
        """Registers or updates a canonical representative record."""
        aliases_list = list(set(aliases or []))
        if official_name not in aliases_list:
            aliases_list.append(official_name)

        rep = None
        if self.db:
            rep = self.db.query(Representative).filter(Representative.representative_id == representative_id).first()

        if rep:
            rep.official_name = official_name
            rep.aliases = aliases_list
            rep.representative_type = representative_type
            rep.party_id = party_id
            rep.constituency_id = constituency_id
            rep.election_id = election_id
            rep.term_start = term_start
            rep.term_end = term_end
            rep.source_document_ids = source_document_ids or []
            rep.person_id = person_id
            rep.date_of_birth = date_of_birth
            rep.gender = gender
        else:
            rep = Representative(
                representative_id=representative_id,
                official_name=official_name,
                aliases=aliases_list,
                representative_type=representative_type,
                party_id=party_id,
                constituency_id=constituency_id,
                election_id=election_id,
                term_start=term_start,
                term_end=term_end,
                source_document_ids=source_document_ids or [],
                person_id=person_id,
                date_of_birth=date_of_birth,
                gender=gender
            )
            if self.db:
                self.db.add(rep)

        if self.db:
            self.db.commit()
            self.db.refresh(rep)

        logger.info(f"Registered representative {representative_id} ({official_name}, {representative_type})")
        return rep

    def register_constituency(
        self,
        constituency_id: str,
        official_name: str,
        constituency_type: str,
        district: str,
        state: str = "Tamil Nadu",
        valid_from: str = "2008",
        valid_to: Optional[str] = None,
        reservation_status: str = "GENERAL",
        delimitation_year: int = 2008,
        predecessor_id: Optional[str] = None,
        successor_id: Optional[str] = None,
        source_document_ids: Optional[List[str]] = None
    ) -> Constituency:
        """Registers or updates a constituency record with validity boundaries."""
        con = None
        if self.db:
            con = self.db.query(Constituency).filter(Constituency.constituency_id == constituency_id).first()

        if con:
            con.official_name = official_name
            con.constituency_type = constituency_type
            con.district = district
            con.state = state
            con.valid_from = valid_from
            con.valid_to = valid_to
            con.reservation_status = reservation_status
            con.delimitation_year = delimitation_year
            con.predecessor_id = predecessor_id
            con.successor_id = successor_id
            con.source_document_ids = source_document_ids or []
        else:
            con = Constituency(
                constituency_id=constituency_id,
                official_name=official_name,
                constituency_type=constituency_type,
                district=district,
                state=state,
                valid_from=valid_from,
                valid_to=valid_to,
                reservation_status=reservation_status,
                delimitation_year=delimitation_year,
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                source_document_ids=source_document_ids or []
            )
            if self.db:
                self.db.add(con)

        if self.db:
            self.db.commit()
            self.db.refresh(con)

        logger.info(f"Registered constituency {constituency_id} ({official_name}, {district}, valid {valid_from}-{valid_to or 'present'})")
        return con

    def register_election(
        self,
        election_id: str,
        election_name: str,
        election_type: str,
        election_year: int,
        poll_date: Optional[str] = None,
        counting_date: Optional[str] = None,
        total_turnout_pct: Optional[float] = None
    ) -> Election:
        """Registers an election event."""
        el = None
        if self.db:
            el = self.db.query(Election).filter(Election.election_id == election_id).first()

        if el:
            el.election_name = election_name
            el.election_type = election_type
            el.election_year = election_year
            el.poll_date = poll_date
            el.counting_date = counting_date
            el.total_turnout_pct = total_turnout_pct
        else:
            el = Election(
                election_id=election_id,
                election_name=election_name,
                election_type=election_type,
                election_year=election_year,
                poll_date=poll_date,
                counting_date=counting_date,
                total_turnout_pct=total_turnout_pct
            )
            if self.db:
                self.db.add(el)

        if self.db:
            self.db.commit()
            self.db.refresh(el)

        return el

    def register_term(
        self,
        term_id: str,
        representative_id: str,
        house_type: str,
        term_start: str,
        constituency_id: Optional[str] = None,
        election_id: Optional[str] = None,
        party_id: Optional[str] = None,
        term_number: int = 1,
        term_end: Optional[str] = None,
        is_active_term: bool = False,
        votes_polled: Optional[int] = None,
        win_margin_votes: Optional[int] = None,
        win_margin_percent: Optional[float] = None,
        source_document_ids: Optional[List[str]] = None
    ) -> RepresentativeTerm:
        """Registers a specific representative term, strictly preserving historical party affiliation."""
        term = None
        if self.db:
            term = self.db.query(RepresentativeTerm).filter(RepresentativeTerm.term_id == term_id).first()

        if term:
            term.representative_id = representative_id
            term.constituency_id = constituency_id
            term.election_id = election_id
            term.party_id = party_id
            term.term_number = term_number
            term.house_type = house_type
            term.term_start = term_start
            term.term_end = term_end
            term.is_active_term = is_active_term
            term.votes_polled = votes_polled
            term.win_margin_votes = win_margin_votes
            term.win_margin_percent = win_margin_percent
            term.source_document_ids = source_document_ids or []
        else:
            term = RepresentativeTerm(
                term_id=term_id,
                representative_id=representative_id,
                constituency_id=constituency_id,
                election_id=election_id,
                party_id=party_id,
                term_number=term_number,
                house_type=house_type,
                term_start=term_start,
                term_end=term_end,
                is_active_term=is_active_term,
                votes_polled=votes_polled,
                win_margin_votes=win_margin_votes,
                win_margin_percent=win_margin_percent,
                source_document_ids=source_document_ids or []
            )
            if self.db:
                self.db.add(term)

        if self.db:
            self.db.commit()
            self.db.refresh(term)

        logger.info(f"Registered term {term_id} for representative {representative_id} (Party: {party_id}, Constituency: {constituency_id})")
        return term

    def record_boundary_change(
        self,
        history_id: str,
        constituency_id: str,
        historical_name: str,
        delimitation_order: str,
        valid_from: str,
        valid_to: Optional[str] = None,
        change_summary: Optional[str] = None,
        source_document_ids: Optional[List[str]] = None
    ) -> ConstituencyBoundaryHistory:
        """Records a historical delimitation or naming boundary change."""
        rec = ConstituencyBoundaryHistory(
            history_id=history_id,
            constituency_id=constituency_id,
            historical_name=historical_name,
            delimitation_order=delimitation_order,
            valid_from=valid_from,
            valid_to=valid_to,
            change_summary=change_summary,
            source_document_ids=source_document_ids or []
        )
        if self.db:
            self.db.add(rec)
            self.db.commit()
            self.db.refresh(rec)

        return rec

    # -------------------------------------------------------------------------
    # Disambiguation & Resolution Engine
    # -------------------------------------------------------------------------

    def resolve_representative(
        self,
        query_name: str,
        constituency_id: Optional[str] = None,
        election_id: Optional[str] = None,
        term_year: Optional[int] = None,
        party_id: Optional[str] = None,
        representative_type: Optional[str] = None,
        representatives_cache: Optional[List[Representative]] = None
    ) -> Representative:
        """
        Disambiguates and resolves a representative.
        
        CRITICAL CONSTRAINT: Does NOT identify representatives solely by name!
        Uses election, constituency, term, and source information to disambiguate people with similar names.
        Raises AmbiguousIdentityError if query is ambiguous or lacks distinguishing attributes.
        """
        norm_query = self.normalize_name(query_name)
        if not norm_query:
            raise EntityNotFoundError("Query name cannot be empty.")

        all_reps: List[Representative] = []
        if representatives_cache is not None:
            all_reps = representatives_cache
        elif self.db:
            all_reps = self.db.query(Representative).all()

        matching_reps: List[Representative] = []
        for rep in all_reps:
            # Check official name
            if self.normalize_name(rep.official_name) == norm_query:
                matching_reps.append(rep)
                continue
            # Check aliases
            rep_aliases = [self.normalize_name(a) for a in (rep.aliases or [])]
            if norm_query in rep_aliases:
                matching_reps.append(rep)

        if not matching_reps:
            raise EntityNotFoundError(f"No representative found matching name or alias '{query_name}'.")

        # Single match and no conflicting criteria
        if len(matching_reps) == 1:
            rep = matching_reps[0]
            # Verify constituency if provided
            if constituency_id and rep.constituency_id and rep.constituency_id != constituency_id:
                # Check terms for this representative
                has_term_in_const = False
                for t in (rep.terms or []):
                    if t.constituency_id == constituency_id:
                        has_term_in_const = True
                        break
                if not has_term_in_const and rep.representative_type != RepresentativeType.RAJYA_SABHA_MP:
                    raise EntityNotFoundError(f"Representative '{query_name}' does not represent constituency '{constituency_id}'.")
            return rep

        # Multiple representatives share this name/alias -> Disambiguation required!
        has_context = bool(constituency_id or election_id or term_year or party_id or representative_type)
        if not has_context:
            candidate_ids = [r.representative_id for r in matching_reps]
            raise AmbiguousIdentityError(
                f"Multiple representatives found with name '{query_name}'. Contextual attributes (constituency, election, term_year, or party) are required to disambiguate.",
                candidate_ids=candidate_ids
            )

        # Score candidates
        candidate_scores: List[Tuple[Representative, float]] = []
        for rep in matching_reps:
            score = 0.0

            # 1. Representative Type Check
            if representative_type:
                if rep.representative_type == representative_type:
                    score += 25.0
                else:
                    score -= 50.0  # Penalize type mismatch

            # 2. Constituency Check
            if constituency_id:
                if rep.constituency_id == constituency_id:
                    score += 40.0
                else:
                    # Check historical terms for this representative
                    term_match = any(t.constituency_id == constituency_id for t in (rep.terms or []))
                    if term_match:
                        score += 35.0

            # 3. Election Check
            if election_id:
                if rep.election_id == election_id:
                    score += 30.0
                else:
                    term_el_match = any(t.election_id == election_id for t in (rep.terms or []))
                    if term_el_match:
                        score += 25.0

            # 4. Term Year Check
            if term_year:
                for t in (rep.terms or []):
                    try:
                        start_y = int(t.term_start[:4]) if t.term_start else 0
                        end_y = int(t.term_end[:4]) if t.term_end else 9999
                        if start_y <= term_year <= end_y:
                            score += 25.0
                            # If party matches in this specific historical term
                            if party_id and t.party_id == party_id:
                                score += 20.0
                            break
                    except (ValueError, TypeError):
                        pass

            # 5. Party Check
            if party_id:
                if rep.party_id == party_id:
                    score += 15.0
                # Check historical party
                hist_party_match = any(t.party_id == party_id for t in (rep.terms or []))
                if hist_party_match:
                    score += 10.0

            candidate_scores.append((rep, score))

        candidate_scores.sort(key=lambda x: x[1], reverse=True)
        top_rep, top_score = candidate_scores[0]
        runner_up_score = candidate_scores[1][1] if len(candidate_scores) > 1 else -1.0

        # Disambiguation criteria: top score must be positive and strictly higher than runner-up
        if top_score <= 0.0 or (top_score - runner_up_score < 10.0):
            candidate_ids = [r.representative_id for r, s in candidate_scores if s == top_score]
            raise AmbiguousIdentityError(
                f"Unable to uniquely disambiguate representative '{query_name}'. Tied candidates: {candidate_ids}",
                candidate_ids=candidate_ids
            )

        return top_rep

    def get_historical_party_for_term(
        self,
        representative_id: str,
        term_id: Optional[str] = None,
        year: Optional[int] = None
    ) -> Optional[str]:
        """
        Retrieves the historical party affiliation of a representative during a specific term.
        Does NOT assume current party affiliation applies to an entire historical term.
        """
        if not self.db:
            return None

        query = self.db.query(RepresentativeTerm).filter(RepresentativeTerm.representative_id == representative_id)
        if term_id:
            term = query.filter(RepresentativeTerm.term_id == term_id).first()
            return term.party_id if term else None

        if year:
            terms = query.all()
            for t in terms:
                try:
                    sy = int(t.term_start[:4]) if t.term_start else 0
                    ey = int(t.term_end[:4]) if t.term_end else 9999
                    if sy <= year <= ey:
                        return t.party_id
                except (ValueError, TypeError):
                    pass

        # Fallback to current party if no term specified
        rep = self.db.query(Representative).filter(Representative.representative_id == representative_id).first()
        return rep.party_id if rep else None

    def get_constituency_as_of(
        self,
        constituency_id: str,
        as_of_year: int
    ) -> Optional[Constituency]:
        """
        Retrieves constituency details respecting historical validity periods.
        """
        if not self.db:
            return None

        con = self.db.query(Constituency).filter(Constituency.constituency_id == constituency_id).first()
        if not con:
            return None

        try:
            vf = int(con.valid_from[:4])
            vt = int(con.valid_to[:4]) if con.valid_to else 9999
            if vf <= as_of_year <= vt:
                return con
        except (ValueError, TypeError):
            pass

        return con
