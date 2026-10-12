"""
Phase 9.2 — Cross-Phase Entity Registry and Identity Resolution Service.
========================================================================

Core service providing:
1. Canonical entity registration and identifier mapping across Phases 1–8.
2. Multilingual name normalization (Tamil and English).
3. Transliteration equivalence and alternate name/alias resolution.
4. Homonym detection and anti-false-merge safeguards.
5. Duplicate candidate detection with divergence analysis.
6. Time-bounded historical name lookups.
7. Entity merge and split operations with full audit trails.
8. Human review workflow for uncertain matches.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Set

from sqlalchemy import or_, and_, desc
from sqlalchemy.orm import Session

from backend.models.entity_registry import (
    CanonicalEntity,
    SourceIdentifierMapping,
    EntityAlias,
    EntityAuditRecord,
    DuplicateCandidateReview,
    RegistryEntityType,
    EntityLifecycleStatus,
    ResolutionMethod,
    ReviewStatusEnum,
    AliasTypeEnum,
    EntityOperationType,
    DuplicateReviewStatus,
)

logger = logging.getLogger("civiclens.phase9.resolution")


# ---------------------------------------------------------------------------
# Phonetic & Transliteration Equivalences for Tamil Nadu Entities
# ---------------------------------------------------------------------------
TAMIL_ENGLISH_TRANSLITERATION_MAP = {
    # Key political & administrative entities
    "சென்னை": "chennai",
    "மதராஸ்": "madras",
    "மதுரை": "madurai",
    "கோயம்புத்தூர்": "coimbatore",
    "கோவை": "coimbatore",
    "திருச்சிராப்பள்ளி": "tiruchirappalli",
    "திருச்சி": "trichy",
    "சேலம்": "salem",
    "திருநெல்வேலி": "tirunelveli",
    "நெல்லை": "tirunelveli",
    "கொளத்தூர்": "kolathur",
    "செங்கல்பட்டு": "chengalpattu",
    "காஞ்சிபுரம்": "kancheepuram",
    "காஞ்சி": "kancheepuram",
    "திமுக": "dmk",
    "அதிமுக": "aiadmk",
    "காங்கிரஸ்": "inc",
    "பாஜக": "bjp",
    "மு.க. ஸ்டாலின்": "m k stalin",
    "மு.க.ஸ்டாலின்": "m k stalin",
    "எடப்பாடி கே. பழனிசாமி": "edappadi k palaniswami",
    "எடப்பாடி பழனிசாமி": "edappadi k palaniswami",
    "ஓ. பன்னீர்செல்வம்": "o panneerselvam",
    "கலைஞர் மகளிர் உரிமைத் திட்டம்": "kalaignar magalir urimai thittam",
    "முதலமைச்சரின் காலை உணவுத் திட்டம்": "chief minister breakfast scheme",
    "நகராட்சி நிர்வாகம் மற்றும் குடிநீர் வழங்கல்": "municipal administration and water supply",
    "நெடுஞ்சாலைகள் துறை": "highways and minor ports",
    "பொதுப்பணித்துறை": "public works department",
}


class EntityResolutionService:
    """
    Unified cross-phase identity resolution and entity registry service.
    """

    def __init__(self, db: Session):
        self.db = db

    # -----------------------------------------------------------------------
    # 1. Normalization & Preprocessing Utilities
    # -----------------------------------------------------------------------
    @staticmethod
    def normalize_name(text: Optional[str]) -> str:
        """
        Deep normalization of personal, administrative, and scheme names.
        - Strips honorifics in English and Tamil.
        - Replaces periods, hyphens, and punctuation with spaces.
        - Collapses whitespaces and lowercases text.
        """
        if not text:
            return ""

        s = str(text).strip().lower()

        # Check direct transliteration dictionary first
        for ta_term, en_equiv in TAMIL_ENGLISH_TRANSLITERATION_MAP.items():
            if ta_term in s:
                s = s.replace(ta_term, en_equiv)

        # English honorifics
        s = re.sub(
            r'^(thiru|tmt|selvi|mr\.?|mrs\.?|ms\.?|dr\.?|prof\.?|hon\'ble|shri|smt\.?)\s+',
            '',
            s,
            flags=re.IGNORECASE,
        )

        # Tamil honorifics
        s = re.sub(
            r'^(திரு|திருமதி|செல்வி|முனைவர்|மாண்புமிகு|பேராசிரியர்)\s+',
            '',
            s,
        )

        # Remove administrative noise suffixes/prefixes for clean tokens
        s = s.replace(".", " ")
        s = s.replace(",", " ")
        s = s.replace("-", " ")
        s = s.replace("_", " ")
        s = s.replace("/", " ")
        s = s.replace("(", " ")
        s = s.replace(")", " ")

        # Collapse whitespace
        tokens = s.split()
        return " ".join(tokens)

    @staticmethod
    def calculate_similarity(s1: str, s2: str) -> float:
        """
        Calculates hybrid token-Jaccard and character Bigram overlap similarity (0.0 to 1.0).
        """
        norm1 = EntityResolutionService.normalize_name(s1)
        norm2 = EntityResolutionService.normalize_name(s2)

        if not norm1 or not norm2:
            return 0.0
        if norm1 == norm2:
            return 1.0

        # Exact substring inclusion (e.g. acronyms or full vs initial name)
        if norm1 in norm2 or norm2 in norm1:
            len_ratio = min(len(norm1), len(norm2)) / max(len(norm1), len(norm2))
            if len_ratio > 0.6:
                return 0.85 + (0.15 * len_ratio)

        # Token Jaccard
        tokens1 = set(norm1.split())
        tokens2 = set(norm2.split())
        jaccard = len(tokens1 & tokens2) / len(tokens1 | tokens2) if (tokens1 | tokens2) else 0.0

        # Core non-initial tokens (tokens with length > 1, e.g. 'murugesan' vs 'murugesan')
        core1 = set(t for t in tokens1 if len(t) > 1)
        core2 = set(t for t in tokens2 if len(t) > 1)
        core_jaccard = (
            len(core1 & core2) / len(core1 | core2)
            if (core1 and core2)
            else 0.0
        )

        # Bigram character similarity
        bigrams1 = set(norm1[i : i + 2] for i in range(len(norm1) - 1))
        bigrams2 = set(norm2[i : i + 2] for i in range(len(norm2) - 1))
        bigram_score = (
            2 * len(bigrams1 & bigrams2) / (len(bigrams1) + len(bigrams2))
            if (bigrams1 or bigrams2)
            else 0.0
        )

        # If core names match exactly with only different initials (e.g. R. Murugesan vs K. Murugesan)
        if core1 and core2 and core_jaccard == 1.0:
            return round(max(0.80, 0.4 * jaccard + 0.6 * bigram_score), 4)

        return round(0.5 * jaccard + 0.5 * bigram_score, 4)


    # -----------------------------------------------------------------------
    # 2. Canonical Entity Management
    # -----------------------------------------------------------------------
    def register_canonical_entity(
        self,
        entity_id: str,
        entity_type: RegistryEntityType,
        name_en: str,
        name_ta: Optional[str] = None,
        category_or_subtype: Optional[str] = None,
        valid_from: Optional[str] = None,
        valid_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        is_test_fixture: bool = False,
        performed_by: str = "SYSTEM_INITIALIZER",
    ) -> CanonicalEntity:
        """
        Creates or updates a canonical entity record in the registry.
        """
        existing = self.db.query(CanonicalEntity).filter_by(entity_id=entity_id).first()
        normalized = self.normalize_name(name_en)

        if existing:
            existing.canonical_name_en = name_en
            if name_ta:
                existing.canonical_name_ta = name_ta
            existing.normalized_name = normalized
            existing.category_or_subtype = category_or_subtype or existing.category_or_subtype
            existing.valid_from = valid_from or existing.valid_from
            existing.valid_to = valid_to or existing.valid_to
            if metadata:
                existing.metadata_json = metadata
            existing.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            return existing

        entity = CanonicalEntity(
            entity_id=entity_id,
            entity_type=entity_type,
            canonical_name_en=name_en,
            canonical_name_ta=name_ta,
            normalized_name=normalized,
            category_or_subtype=category_or_subtype,
            valid_from=valid_from,
            valid_to=valid_to,
            status=EntityLifecycleStatus.ACTIVE,
            metadata_json=metadata or {},
            is_test_fixture=is_test_fixture,
        )
        self.db.add(entity)

        # Record audit log
        audit = EntityAuditRecord(
            audit_id=f"AUDIT-CREATE-{uuid.uuid4().hex[:10]}",
            operation_type=EntityOperationType.CREATE,
            primary_entity_id=entity_id,
            rationale=f"Registered canonical entity {entity_id} ({name_en})",
            performed_by=performed_by,
            new_state_json=entity.to_dict(),
        )
        self.db.add(audit)
        self.db.commit()
        return entity

    def add_source_mapping(
        self,
        entity_id: str,
        source_system: str,
        source_record_id: str,
        source_record_name: str,
        matching_method: ResolutionMethod = ResolutionMethod.DETERMINISTIC_ID,
        confidence_score: float = 1.0,
        review_status: ReviewStatusEnum = ReviewStatusEnum.VERIFIED,
        notes: Optional[str] = None,
        is_test_fixture: bool = False,
    ) -> SourceIdentifierMapping:
        """
        Maps an upstream system identifier to the canonical entity, preserving the verbatim source name.
        """
        existing = (
            self.db.query(SourceIdentifierMapping)
            .filter_by(source_system=source_system, source_record_id=source_record_id)
            .first()
        )
        if existing:
            existing.entity_id = entity_id
            existing.source_record_name = source_record_name
            existing.matching_method = matching_method
            existing.confidence_score = confidence_score
            existing.review_status = review_status
            existing.notes = notes
            self.db.commit()
            return existing

        mapping = SourceIdentifierMapping(
            mapping_id=f"MAP-{uuid.uuid4().hex[:10].upper()}",
            entity_id=entity_id,
            source_system=source_system,
            source_record_id=source_record_id,
            source_record_name=source_record_name,
            matching_method=matching_method,
            confidence_score=confidence_score,
            review_status=review_status,
            notes=notes,
            is_test_fixture=is_test_fixture,
        )
        self.db.add(mapping)
        self.db.commit()
        return mapping

    def add_alias(
        self,
        entity_id: str,
        alias_name: str,
        language: str = "en",
        alias_type: AliasTypeEnum = AliasTypeEnum.OFFICIAL_ALIAS,
        valid_from: Optional[str] = None,
        valid_to: Optional[str] = None,
        source_reference: Optional[str] = None,
        is_test_fixture: bool = False,
    ) -> EntityAlias:
        """
        Adds an alternate, historical, acronym, or transliterated alias.
        """
        norm_alias = self.normalize_name(alias_name)
        existing = (
            self.db.query(EntityAlias)
            .filter_by(entity_id=entity_id, alias_name=alias_name, alias_type=alias_type)
            .first()
        )
        if existing:
            existing.normalized_alias = norm_alias
            existing.language = language
            existing.valid_from = valid_from
            existing.valid_to = valid_to
            existing.source_reference = source_reference
            self.db.commit()
            return existing

        alias = EntityAlias(
            alias_id=f"ALIAS-{uuid.uuid4().hex[:10].upper()}",
            entity_id=entity_id,
            alias_name=alias_name,
            normalized_alias=norm_alias,
            language=language,
            alias_type=alias_type,
            valid_from=valid_from,
            valid_to=valid_to,
            source_reference=source_reference,
            is_test_fixture=is_test_fixture,
        )
        self.db.add(alias)
        self.db.commit()
        return alias

    # -----------------------------------------------------------------------
    # 3. Entity Resolution & Disambiguation Engine
    # -----------------------------------------------------------------------
    def resolve_entity(
        self,
        query_name: str,
        entity_type: Optional[RegistryEntityType] = None,
        source_system: Optional[str] = None,
        source_record_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        min_confidence: float = 0.70,
    ) -> Dict[str, Any]:
        """
        Resolves an input query to a canonical entity using multi-stage matching:
        1. Deterministic source ID lookup
        2. Exact canonical entity ID match
        3. Normalized canonical name exact match
        4. Normalized alias exact match (including Tamil transliteration)
        5. Fuzzy candidate matching with contextual disambiguation (district, party, year)

        SAFEGUARD: Does NOT merge two distinct entities merely because names are similar.
        If multiple valid homonyms exist, returns an AMBIGUOUS result with candidates.
        """
        context = context or {}

        # Stage 1: Deterministic Source Mapping
        if source_system and source_record_id:
            mapping = (
                self.db.query(SourceIdentifierMapping)
                .filter_by(source_system=source_system, source_record_id=source_record_id)
                .first()
            )
            if mapping:
                entity = self._get_active_entity(mapping.entity_id)
                if entity:
                    return {
                        "resolved": True,
                        "entity": entity.to_dict(),
                        "matching_method": ResolutionMethod.DETERMINISTIC_ID.value,
                        "confidence": 1.0,
                        "matched_by": f"source_mapping:{source_system}:{source_record_id}",
                        "is_historical": False,
                    }

        # Stage 2: Direct Canonical ID
        clean_query = query_name.strip()
        direct_ent = self._get_active_entity(clean_query)
        if direct_ent:
            return {
                "resolved": True,
                "entity": direct_ent.to_dict(),
                "matching_method": ResolutionMethod.DETERMINISTIC_ID.value,
                "confidence": 1.0,
                "matched_by": "canonical_id",
                "is_historical": False,
            }

        norm_query = self.normalize_name(clean_query)
        if not norm_query:
            return {"resolved": False, "candidates": [], "message": "Empty query name"}

        # Base query filter
        q_filter = [CanonicalEntity.status.in_([EntityLifecycleStatus.ACTIVE, EntityLifecycleStatus.MERGED])]
        if entity_type:
            q_filter.append(CanonicalEntity.entity_type == entity_type)

        # Stage 3: Exact Normalized Name Match
        name_matches = (
            self.db.query(CanonicalEntity)
            .filter(*q_filter)
            .filter(
                or_(
                    CanonicalEntity.normalized_name == norm_query,
                    CanonicalEntity.canonical_name_en.ilike(clean_query),
                    CanonicalEntity.canonical_name_ta == clean_query,
                )
            )
            .all()
        )

        if len(name_matches) == 1:
            matched_ent = self._get_active_entity(name_matches[0].entity_id)
            # Verify context if given (e.g. district check for places/reps)
            if self._satisfies_context(matched_ent, context):
                return {
                    "resolved": True,
                    "entity": matched_ent.to_dict(),
                    "matching_method": ResolutionMethod.EXACT_NAME.value,
                    "confidence": 1.0,
                    "matched_by": "canonical_name",
                    "is_historical": False,
                }

        # Stage 4: Exact Alias Match (including Tamil aliases & historical names)
        alias_query = (
            self.db.query(EntityAlias, CanonicalEntity)
            .join(CanonicalEntity, EntityAlias.entity_id == CanonicalEntity.entity_id)
            .filter(*q_filter)
            .filter(
                or_(
                    EntityAlias.normalized_alias == norm_query,
                    EntityAlias.alias_name.ilike(clean_query),
                    EntityAlias.alias_name == clean_query,
                )
            )
            .all()
        )

        valid_alias_entities = []
        for alias, ent in alias_query:
            active_ent = self._get_active_entity(ent.entity_id)
            if active_ent and self._satisfies_context(active_ent, context):
                # Check time-bounded validity for historical names
                is_hist = False
                if alias.alias_type == AliasTypeEnum.HISTORICAL_NAME:
                    is_hist = True

                method = (
                    ResolutionMethod.HISTORICAL_NAME_MATCH
                    if is_hist
                    else (
                        ResolutionMethod.TRANSLITERATION_MATCH
                        if alias.language == "ta" or alias.alias_type == AliasTypeEnum.TRANSLITERATION
                        else ResolutionMethod.ALIAS_MATCH
                    )
                )

                valid_alias_entities.append((active_ent, alias, method, is_hist))

        # Group matches by distinct canonical entity_id
        entity_matches: Dict[str, Tuple[CanonicalEntity, Optional[EntityAlias], ResolutionMethod, bool]] = {}

        # Add name matches
        for ent in name_matches:
            active_ent = self._get_active_entity(ent.entity_id)
            if active_ent and self._satisfies_context(active_ent, context):
                entity_matches[active_ent.entity_id] = (
                    active_ent, None, ResolutionMethod.EXACT_NAME, False
                )

        # Add alias matches
        for active_ent, alias, method, is_hist in valid_alias_entities:
            existing_match = entity_matches.get(active_ent.entity_id)
            if not existing_match or is_hist:
                entity_matches[active_ent.entity_id] = (active_ent, alias, method, is_hist)

        # If exactly 1 real-world entity matched (either directly or via multiple aliases)
        if len(entity_matches) == 1:
            active_ent, alias, method, is_hist = list(entity_matches.values())[0]
            matched_by = f"alias:{alias.alias_name}:{alias.alias_type.value}" if alias else "canonical_name"
            return {
                "resolved": True,
                "entity": active_ent.to_dict(),
                "matching_method": method.value,
                "confidence": 0.98 if is_hist else 1.0,
                "matched_by": matched_by,
                "is_historical": is_hist,
            }

        # Stage 5: Homonym & Disambiguation Check
        # If multiple entities matched exactly (e.g. multiple "Anna Nagar" or "S. Murugesan")
        combined_exact = {ent_tuple[0].entity_id: ent_tuple[0] for ent_tuple in entity_matches.values()}


        if len(combined_exact) > 1:
            # Context-based disambiguation
            filtered = [
                e for e in combined_exact.values() if self._satisfies_context(e, context)
            ]
            if len(filtered) == 1:
                return {
                    "resolved": True,
                    "entity": filtered[0].to_dict(),
                    "matching_method": ResolutionMethod.EXACT_NAME.value,
                    "confidence": 0.95,
                    "matched_by": "disambiguated_by_context",
                    "is_historical": False,
                }
            # Ambiguous: do NOT merge! Return candidates.
            return {
                "resolved": False,
                "status": "AMBIGUOUS_HOMONYM",
                "message": f"Multiple entities named '{clean_query}' exist across different jurisdictions or tenures.",
                "candidates": [e.to_dict() for e in combined_exact.values()],
            }

        # Stage 6: Fuzzy Candidate Retrieval
        all_candidates = (
            self.db.query(CanonicalEntity)
            .filter(*q_filter)
            .limit(500)
            .all()
        )

        scored_candidates = []
        for candidate in all_candidates:
            active_c = self._get_active_entity(candidate.entity_id)
            score = self.calculate_similarity(clean_query, active_c.canonical_name_en)
            if active_c.canonical_name_ta:
                ta_score = self.calculate_similarity(clean_query, active_c.canonical_name_ta)
                score = max(score, ta_score)

            if score >= min_confidence and self._satisfies_context(active_c, context):
                scored_candidates.append((score, active_c))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        if scored_candidates:
            top_score, top_ent = scored_candidates[0]
            # High-confidence single candidate
            if top_score >= 0.88 and (
                len(scored_candidates) == 1 or (top_score - scored_candidates[1][0] > 0.15)
            ):
                return {
                    "resolved": True,
                    "entity": top_ent.to_dict(),
                    "matching_method": ResolutionMethod.FUZZY_MATCH.value,
                    "confidence": top_score,
                    "matched_by": "fuzzy_single_top_match",
                    "is_historical": False,
                }

            return {
                "resolved": False,
                "status": "CANDIDATE_MATCHES",
                "message": "Potential candidates found below automatic match threshold.",
                "candidates": [
                    {"entity": c.to_dict(), "similarity_score": s}
                    for s, c in scored_candidates[:5]
                ],
            }

        return {
            "resolved": False,
            "status": "NOT_FOUND",
            "message": f"No entity matching '{clean_query}' could be verified.",
            "candidates": [],
        }

    # -----------------------------------------------------------------------
    # 4. Duplicate Candidate Detection
    # -----------------------------------------------------------------------
    def detect_duplicate_candidates(
        self,
        entity_type: Optional[RegistryEntityType] = None,
        similarity_threshold: float = 0.80,
    ) -> List[Dict[str, Any]]:
        """
        Scans registered active entities for potential duplicate pairs.
        Analyzes divergence rationale (different district, different party, distinct dates)
        to prevent false merges.
        """
        q = self.db.query(CanonicalEntity).filter_by(status=EntityLifecycleStatus.ACTIVE)
        if entity_type:
            q = q.filter_by(entity_type=entity_type)

        entities = q.all()
        candidate_results = []

        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                e1 = entities[i]
                e2 = entities[j]

                if e1.entity_type != e2.entity_type:
                    continue

                sim = self.calculate_similarity(e1.canonical_name_en, e2.canonical_name_en)
                if sim >= similarity_threshold:
                    divergence_reasons = self._find_divergence_reasons(e1, e2)

                    # Check if already reviewed
                    existing_rev = (
                        self.db.query(DuplicateCandidateReview)
                        .filter(
                            or_(
                                and_(
                                    DuplicateCandidateReview.entity_a_id == e1.entity_id,
                                    DuplicateCandidateReview.entity_b_id == e2.entity_id,
                                ),
                                and_(
                                    DuplicateCandidateReview.entity_a_id == e2.entity_id,
                                    DuplicateCandidateReview.entity_b_id == e1.entity_id,
                                ),
                            )
                        )
                        .first()
                    )

                    candidate_dict = {
                        "entity_a": e1.to_dict(),
                        "entity_b": e2.to_dict(),
                        "similarity_score": sim,
                        "divergence_reasons": divergence_reasons,
                        "review_status": existing_rev.review_status.value if existing_rev else DuplicateReviewStatus.PENDING_REVIEW.value,
                        "candidate_id": existing_rev.candidate_id if existing_rev else None,
                    }

                    if not existing_rev:
                        new_cand = DuplicateCandidateReview(
                            candidate_id=f"CAND-DUP-{uuid.uuid4().hex[:10].upper()}",
                            entity_type=e1.entity_type,
                            entity_a_id=e1.entity_id,
                            entity_b_id=e2.entity_id,
                            similarity_score=sim,
                            matching_method="TOKEN_AND_BIGRAM_SIMILARITY",
                            divergence_reasons=divergence_reasons,
                            review_status=DuplicateReviewStatus.PENDING_REVIEW,
                        )
                        self.db.add(new_cand)
                        self.db.commit()
                        candidate_dict["candidate_id"] = new_cand.candidate_id

                    candidate_results.append(candidate_dict)

        return candidate_results

    # -----------------------------------------------------------------------
    # 5. Merge and Split Operations with Full Audit History
    # -----------------------------------------------------------------------
    def merge_entities(
        self,
        primary_entity_id: str,
        secondary_entity_id: str,
        rationale: str,
        performed_by: str = "SYSTEM_AUDITOR",
    ) -> Dict[str, Any]:
        """
        Merges secondary entity into primary entity.
        - Primary entity survives and inherits all aliases and source mappings.
        - Secondary entity status is set to MERGED, pointing to primary.
        - Complete audit history snapshot recorded.
        """
        if primary_entity_id == secondary_entity_id:
            raise ValueError("Cannot merge an entity into itself.")

        if not rationale or len(rationale.strip()) < 10:
            raise ValueError("A clear, substantive rationale is mandatory for entity merges.")

        primary = self.db.query(CanonicalEntity).filter_by(entity_id=primary_entity_id).first()
        secondary = self.db.query(CanonicalEntity).filter_by(entity_id=secondary_entity_id).first()

        if not primary or not secondary:
            raise ValueError(f"One or both entities not found: {primary_entity_id}, {secondary_entity_id}")

        if primary.entity_type != secondary.entity_type:
            raise ValueError(f"Cannot merge entities of different types ({primary.entity_type} vs {secondary.entity_type}).")

        prev_state = {
            "primary": primary.to_dict(),
            "secondary": secondary.to_dict(),
        }

        # 1. Add secondary canonical name as alias on primary
        self.add_alias(
            entity_id=primary.entity_id,
            alias_name=secondary.canonical_name_en,
            alias_type=AliasTypeEnum.OFFICIAL_ALIAS,
            source_reference=f"Merged from {secondary.entity_id}",
            is_test_fixture=primary.is_test_fixture,
        )
        if secondary.canonical_name_ta:
            self.add_alias(
                entity_id=primary.entity_id,
                alias_name=secondary.canonical_name_ta,
                language="ta",
                alias_type=AliasTypeEnum.TRANSLITERATION,
                source_reference=f"Merged from {secondary.entity_id}",
                is_test_fixture=primary.is_test_fixture,
            )

        # 2. Re-point source mappings
        for mapping in secondary.source_mappings:
            mapping.entity_id = primary.entity_id

        # 3. Re-point aliases
        for alias in secondary.aliases:
            alias.entity_id = primary.entity_id

        # 4. Mark secondary as MERGED
        secondary.status = EntityLifecycleStatus.MERGED
        secondary.merged_into_id = primary.entity_id
        secondary.updated_at = datetime.now(timezone.utc)
        primary.updated_at = datetime.now(timezone.utc)

        # 5. Audit Ledger
        audit = EntityAuditRecord(
            audit_id=f"AUDIT-MERGE-{uuid.uuid4().hex[:10].upper()}",
            operation_type=EntityOperationType.MERGE,
            primary_entity_id=primary.entity_id,
            secondary_entity_id=secondary.entity_id,
            rationale=rationale,
            performed_by=performed_by,
            previous_state_json=prev_state,
            new_state_json={"primary": primary.to_dict(), "secondary": secondary.to_dict()},
        )
        self.db.add(audit)
        self.db.commit()

        return {
            "status": "MERGED",
            "primary_entity": primary.to_dict(),
            "merged_entity": secondary.to_dict(),
            "audit_id": audit.audit_id,
        }

    def split_entity(
        self,
        original_entity_id: str,
        new_entity_data: Dict[str, Any],
        split_mapping_ids: List[str],
        rationale: str,
        performed_by: str = "SYSTEM_AUDITOR",
    ) -> Dict[str, Any]:
        """
        Splits an over-aggregated entity into two distinct entities with full audit record.
        """
        if not rationale or len(rationale.strip()) < 10:
            raise ValueError("A clear, substantive rationale is mandatory for entity splits.")

        original = self.db.query(CanonicalEntity).filter_by(entity_id=original_entity_id).first()
        if not original:
            raise ValueError(f"Entity {original_entity_id} not found.")

        prev_state = original.to_dict()

        # Create new entity
        new_entity = self.register_canonical_entity(
            entity_id=new_entity_data["entity_id"],
            entity_type=RegistryEntityType.from_string(new_entity_data.get("entity_type", original.entity_type)),
            name_en=new_entity_data["canonical_name_en"],
            name_ta=new_entity_data.get("canonical_name_ta"),
            category_or_subtype=new_entity_data.get("category_or_subtype"),
            valid_from=new_entity_data.get("valid_from"),
            valid_to=new_entity_data.get("valid_to"),
            metadata=new_entity_data.get("metadata", {}),
            is_test_fixture=original.is_test_fixture,
            performed_by=performed_by,
        )

        # Move specified mappings
        for m_id in split_mapping_ids:
            mapping = self.db.query(SourceIdentifierMapping).filter_by(mapping_id=m_id).first()
            if mapping and mapping.entity_id == original.entity_id:
                mapping.entity_id = new_entity.entity_id

        # Update original entity status if required
        original.updated_at = datetime.now(timezone.utc)

        audit = EntityAuditRecord(
            audit_id=f"AUDIT-SPLIT-{uuid.uuid4().hex[:10].upper()}",
            operation_type=EntityOperationType.SPLIT,
            primary_entity_id=original.entity_id,
            secondary_entity_id=new_entity.entity_id,
            rationale=rationale,
            performed_by=performed_by,
            previous_state_json=prev_state,
            new_state_json={"original": original.to_dict(), "new_entity": new_entity.to_dict()},
        )
        self.db.add(audit)
        self.db.commit()

        return {
            "status": "SPLIT",
            "original_entity": original.to_dict(),
            "new_entity": new_entity.to_dict(),
            "audit_id": audit.audit_id,
        }

    def review_duplicate_candidate(
        self,
        candidate_id: str,
        disposition: DuplicateReviewStatus,
        reviewer: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Records human expert decision on an uncertain match or duplicate candidate.
        """
        cand = self.db.query(DuplicateCandidateReview).filter_by(candidate_id=candidate_id).first()
        if not cand:
            raise ValueError(f"Candidate review {candidate_id} not found.")

        cand.review_status = disposition
        cand.reviewed_by = reviewer
        cand.reviewer_notes = notes
        cand.reviewed_at = datetime.now(timezone.utc)

        audit = EntityAuditRecord(
            audit_id=f"AUDIT-REVIEW-{uuid.uuid4().hex[:10].upper()}",
            operation_type=EntityOperationType.UNCERTAIN_MATCH_REVIEW,
            primary_entity_id=cand.entity_a_id,
            secondary_entity_id=cand.entity_b_id,
            rationale=f"Review disposition: {disposition.value}. Notes: {notes or 'None'}",
            performed_by=reviewer,
        )
        self.db.add(audit)
        self.db.commit()

        return cand.to_dict()

    # -----------------------------------------------------------------------
    # 6. Helper Guards & Disambiguation Filters
    # -----------------------------------------------------------------------
    def _get_active_entity(self, entity_id: str) -> Optional[CanonicalEntity]:
        """Follows merge pointer if entity was merged into another entity."""
        ent = self.db.query(CanonicalEntity).filter_by(entity_id=entity_id).first()
        if not ent:
            return None
        if ent.status == EntityLifecycleStatus.MERGED and ent.merged_into_id:
            return self._get_active_entity(ent.merged_into_id)
        return ent

    @staticmethod
    def _satisfies_context(entity: CanonicalEntity, context: Dict[str, Any]) -> bool:
        """
        Validates whether candidate satisfies contextual criteria (district, party, tenure).
        Prevents homonymous confusion (e.g. Anna Nagar Chennai vs Anna Nagar Madurai).
        """
        if not context:
            return True

        meta = entity.metadata_json or {}

        # District check
        req_district = context.get("district")
        if req_district and "district" in meta:
            if str(meta["district"]).strip().lower() != str(req_district).strip().lower():
                return False

        # Party check
        req_party = context.get("party") or context.get("party_code")
        if req_party and "party_code" in meta:
            if str(meta["party_code"]).strip().lower() != str(req_party).strip().lower():
                return False

        # Constituency check
        req_const = context.get("constituency") or context.get("constituency_code")
        if req_const and "constituency_code" in meta:
            if str(meta["constituency_code"]).strip().lower() != str(req_const).strip().lower():
                return False

        return True

    @staticmethod
    def _find_divergence_reasons(e1: CanonicalEntity, e2: CanonicalEntity) -> List[str]:
        """Identifies specific factual reasons why two similar-named entities must NOT be merged."""
        reasons = []
        m1 = e1.metadata_json or {}
        m2 = e2.metadata_json or {}

        # Different geographic districts
        d1 = m1.get("district")
        d2 = m2.get("district")
        if d1 and d2 and str(d1).lower() != str(d2).lower():
            reasons.append(f"DIFFERENT_DISTRICT: '{d1}' vs '{d2}'")

        # Different political parties for representatives
        p1 = m1.get("party_code")
        p2 = m2.get("party_code")
        if p1 and p2 and str(p1).lower() != str(p2).lower():
            reasons.append(f"DIFFERENT_PARTY: '{p1}' vs '{p2}'")

        # Different constituencies
        c1 = m1.get("constituency_code")
        c2 = m2.get("constituency_code")
        if c1 and c2 and str(c1).lower() != str(c2).lower():
            reasons.append(f"DIFFERENT_CONSTITUENCY: '{c1}' vs '{c2}'")

        # Different time validity windows
        if e1.valid_to and e2.valid_from and str(e1.valid_to) < str(e2.valid_from):
            reasons.append(f"NON_OVERLAPPING_TIME_PERIODS: {e1.valid_to} vs {e2.valid_from}")

        return reasons
