"""
Phase 7.5 — Claim-to-Evidence Retrieval Engine.

Implements a multi-signal hybrid evidence retrieval pipeline for atomic political claims:
1. Keyword and exact phrase search.
2. Entity and date matching.
3. Structured database lookup (EvidenceDocuments, EvidencePassages, HistoricalSchemes).
4. Semantic similarity (Sentence-BERT embeddings or fallback multilingual n-gram vectors).
5. Source-specific search and statutory tier authority weighting.
6. Retrieval of potentially contradictory evidence via counter-query expansion.

IMPORTANT DISCLAIMER:
Retrieval rank reflects topical relevance to the query proposition, NOT empirical veracity or truth.
"""

import re
import math
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.models.claim import (
    Claim,
    AtomicClaim,
    EvidenceDocument,
    EvidencePassage,
    ClaimRetrievalCandidate,
    SourceTier,
    ClaimEvidenceRelationship,
    EvidenceRelationshipType
)
from backend.nlp.preprocessing import normalize_unicode, normalize_whitespace
from backend.nlp.claim_decomposition import (
    LanguageDetector,
    TextNormalizer,
    KNOWN_ENTITIES,
    EntityAndNegationExtractor
)
from backend.core.logger import setup_logger

logger = setup_logger("civiclens.phase7.retrieval")

RETRIEVAL_DISCLAIMER = (
    "Candidate retrieval rank reflects topical relevance to the query proposition, "
    "NOT empirical veracity or truth. Do not interpret retrieval rank as evidence of truth."
)


# ---------------------------------------------------------------------------
# 1. Multilingual Semantic Scorer (Sentence-BERT with N-gram Vector Fallback)
# ---------------------------------------------------------------------------
class MultilingualSemanticScorer:
    """
    Computes semantic similarity between query proposition and candidate evidence passage.
    Supports SentenceTransformer multilingual model or deterministic character n-gram cosine fallback.
    """
    DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(self, model_name: str = DEFAULT_MODEL, use_transformer: bool = False):
        self.model_name = model_name
        self.use_transformer = use_transformer
        self._transformer = None

    def _get_transformer(self):
        if self._transformer is None and self.use_transformer:
            try:
                from sentence_transformers import SentenceTransformer
                self._transformer = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer ({e}). Using n-gram semantic fallback.")
                self.use_transformer = False
        return self._transformer

    @staticmethod
    def _ngram_vector(text: str, n: int = 3) -> Dict[str, float]:
        """Builds normalized subword n-gram TF vector supporting Tamil and English."""
        norm = TextNormalizer.normalize(text).lower()
        tokens = [t for t in norm.split() if len(t) > 1]
        vec: Dict[str, float] = {}

        # Token frequencies
        for tok in tokens:
            vec[tok] = vec.get(tok, 0.0) + 1.5

        # Character n-grams for morphology and agglutination in Tamil
        for tok in tokens:
            if len(tok) >= n:
                for i in range(len(tok) - n + 1):
                    sub = tok[i:i+n]
                    vec[sub] = vec.get(sub, 0.0) + 1.0

        # L2 normalize
        length = math.sqrt(sum(v * v for v in vec.values()))
        if length > 0:
            for k in vec:
                vec[k] /= length
        return vec

    def compute_similarity(self, text1: str, text2: str) -> float:
        """Computes cosine similarity in range [0.0, 1.0]."""
        if not text1.strip() or not text2.strip():
            return 0.0

        model = self._get_transformer()
        if model is not None:
            try:
                emb1 = model.encode(text1, convert_to_numpy=True)
                emb2 = model.encode(text2, convert_to_numpy=True)
                dot = float(sum(a * b for a, b in zip(emb1, emb2)))
                norm1 = math.sqrt(sum(a * a for a in emb1))
                norm2 = math.sqrt(sum(b * b for b in emb2))
                if norm1 > 0 and norm2 > 0:
                    cos = dot / (norm1 * norm2)
                    return max(0.0, min(1.0, float(cos)))
            except Exception as e:
                logger.debug(f"Transformer inference error: {e}")

        # Deterministic multilingual subword vector cosine similarity
        v1 = self._ngram_vector(text1)
        v2 = self._ngram_vector(text2)
        dot = sum(v1[k] * v2[k] for k in v1 if k in v2)
        return max(0.0, min(1.0, float(dot)))


# ---------------------------------------------------------------------------
# 2. Keyword & Exact Phrase Matcher
# ---------------------------------------------------------------------------
class KeywordAndPhraseMatcher:
    """
    Computes exact phrase matches, multi-word n-grams, and token lexical overlap.
    """
    STOPWORDS = {
        "the", "is", "at", "which", "on", "a", "an", "this", "that", "in", "for",
        "of", "to", "and", "or", "by", "from", "with", "as", "it", "was", "were",
        "இந்த", "அந்த", "ஒரு", "மற்றும்", "ஆகிய", "என்று", "உள்ள", "உள்ளது", "ஆகும்"
    }

    @classmethod
    def extract_keywords(cls, text: str) -> Set[str]:
        tokens = re.findall(r'[\w\u0B80-\u0BFF]+', text.lower())
        return {t for t in tokens if len(t) > 2 and t not in cls.STOPWORDS}

    @classmethod
    def compute_keyword_match(
        cls,
        query_text: str,
        passage_text: str,
        auxiliary_translation: Optional[str] = None
    ) -> float:
        """
        Calculates lexical overlap score between query and passage.
        Includes exact phrase bonus and cross-lingual translation tokens.
        """
        q_norm = TextNormalizer.normalize(query_text).lower()
        p_norm = TextNormalizer.normalize(passage_text).lower()

        # 1. Exact phrase match bonus
        # If full continuous query or significant continuous sub-phrase is found verbatim
        if len(q_norm) > 15 and q_norm in p_norm:
            return 1.0

        q_tokens = cls.extract_keywords(q_norm)
        if auxiliary_translation:
            q_tokens.update(cls.extract_keywords(auxiliary_translation))

        p_tokens = cls.extract_keywords(p_norm)

        if not q_tokens:
            return 0.0

        overlap = q_tokens.intersection(p_tokens)
        score = len(overlap) / len(q_tokens)

        # Check numeric token matches (e.g. 13,720 or 1000)
        q_nums = set(re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', query_text))
        p_nums = set(re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', passage_text))
        if q_nums and q_nums.intersection(p_nums):
            score = min(1.0, score + 0.25)

        return max(0.0, min(1.0, float(score)))


# ---------------------------------------------------------------------------
# 3. Entity & Temporal Matchers
# ---------------------------------------------------------------------------
class EntityAndDateMatcher:
    """
    Matches named political entities (schemes, leaders, parties, departments) and dates.
    """
    @classmethod
    def compute_entity_match(
        cls,
        query_text: str,
        passage_text: str,
        doc_title: str = "",
        doc_publisher: str = "",
        specified_subject: Optional[str] = None
    ) -> float:
        combined_passage = f"{passage_text} {doc_title} {doc_publisher}".lower()

        # Check if specified subject appears in evidence
        if specified_subject and specified_subject.lower() in combined_passage:
            return 1.0

        # Extract entities from query
        query_entities = EntityAndNegationExtractor.extract_entities(query_text)
        total_entities = 0
        matched_entities = 0

        # Check schemes
        for scheme in query_entities["schemes"]:
            total_entities += 1
            aliases = KNOWN_ENTITIES["SCHEMES"].get(scheme, [scheme.lower()])
            if any(alias in combined_passage for alias in aliases):
                matched_entities += 1

        # Check leaders
        for leader in query_entities["leaders"]:
            total_entities += 1
            aliases = KNOWN_ENTITIES["LEADERS"].get(leader, [leader.lower()])
            if any(alias in combined_passage for alias in aliases):
                matched_entities += 1

        # Check parties
        for party in query_entities["parties"]:
            total_entities += 1
            aliases = KNOWN_ENTITIES["PARTIES"].get(party, [party.lower()])
            if any(alias in combined_passage for alias in aliases):
                matched_entities += 1

        if total_entities == 0:
            return 0.5  # Neutral if query has no specific named entity

        return matched_entities / total_entities

    @classmethod
    def compute_date_match(
        cls,
        time_period: Optional[str],
        query_text: str,
        passage_text: str,
        pub_date: Optional[datetime] = None
    ) -> float:
        if not time_period:
            # Check if query contains any 4-digit year
            years = re.findall(r'\b(20\d{2})\b', query_text)
            if not years:
                return 0.5  # Neutral when no date specified
            time_period = years[0]

        clean_period = time_period.lower()
        combined_text = f"{passage_text} {pub_date.isoformat() if pub_date else ''}".lower()

        # Exact match (e.g. 2024-25 in text)
        if clean_period in combined_text:
            return 1.0

        # Partial match on calendar year portion (e.g. 2024 of 2024-25)
        m_year = re.search(r'20\d{2}', clean_period)
        if m_year and m_year.group(0) in combined_text:
            return 0.85

        return 0.0


# ---------------------------------------------------------------------------
# 4. Contradictory Evidence Query Expander
# ---------------------------------------------------------------------------
class ContradictoryEvidenceDetector:
    """
    Identifies whether a candidate passage potentially contradicts the query claim
    via negation terms, antonyms, shortfalls, or audit objections.
    """
    REFUTATION_KEYWORDS = [
        "not allocated", "shortfall", "irregularity", "denied", "delayed",
        "did not disburse", "broken promise", "unfulfilled", "failed",
        "misappropriation", "audit objection", "cag finding", "false claim",
        "இல்லை", "வழங்கப்படவில்லை", "ஒதுக்கப்படவில்லை", "நிறைவேற்றப்படவில்லை",
        "குறைவு", "தாமதம்", "முறைகேடு", "ஊழல்", "பற்றாக்குறை", "பொய்"
    ]

    AFFIRMATION_KEYWORDS = [
        "disbursed", "allocated", "implemented", "transferred", "achieved",
        "fulfilled", "completed", "sanctioned", "வழங்கப்பட்டது", "ஒதுக்கப்பட்டது",
        "செயல்படுத்தப்பட்டது", "நிறைவேறியது"
    ]

    @classmethod
    def is_contradictory(cls, query_is_negated: bool, passage_text: str) -> bool:
        p_lower = passage_text.lower()
        if not query_is_negated:
            # Positive claim: Contradicted if passage mentions refutation/failure/shortfall
            return any(kw in p_lower for kw in cls.REFUTATION_KEYWORDS)
        else:
            # Negative claim: Contradicted if passage mentions direct fulfillment/disbursement
            return any(kw in p_lower for kw in cls.AFFIRMATION_KEYWORDS)


# ---------------------------------------------------------------------------
# 5. Hybrid Evidence Retrieval Engine
# ---------------------------------------------------------------------------
class EvidenceRetrievalEngine:
    """
    Multi-signal hybrid evidence retriever:
    Combines Semantic Similarity, Exact Keyword Matching, Entity Matching,
    Date Matching, and Source Authority to rank candidate evidence.
    """
    MODEL_VERSION = "paraphrase-multilingual-MiniLM-L12-v2"
    RETRIEVAL_METHOD = "HYBRID_MULTI_SIGNAL_V1"

    def __init__(
        self,
        db: Session,
        semantic_scorer: Optional[MultilingualSemanticScorer] = None
    ):
        self.db = db
        self.semantic_scorer = semantic_scorer or MultilingualSemanticScorer()

    def retrieve_candidate_evidence(
        self,
        claim_id: str,
        query_text: str,
        atomic_claim_id: Optional[str] = None,
        subject: Optional[str] = None,
        time_period: Optional[str] = None,
        language: str = "en",
        auxiliary_translation: Optional[str] = None,
        is_negated: bool = False,
        top_k: int = 10,
        min_score_threshold: float = 0.25,
        source_categories: Optional[List[str]] = None,
        persist_candidates: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid retrieval over evidence_passages and evidence_documents.
        Ranks by composite score and flags potentially contradictory evidence.
        """
        query_passages = self.db.query(EvidencePassage).join(EvidenceDocument)

        # Optional source category filtering
        if source_categories:
            query_passages = query_passages.filter(
                EvidenceDocument.source_category.in_(source_categories)
            )

        all_passages = query_passages.all()
        if not all_passages:
            logger.info(f"No evidence passages available in database for claim {claim_id}.")
            return []

        candidates = []
        retrieval_time = datetime.now(timezone.utc)

        for p in all_passages:
            doc = p.document
            p_text = p.passage_text

            # 1. Semantic Similarity
            sem_score = self.semantic_scorer.compute_similarity(query_text, p_text)
            # If auxiliary translation exists, also check similarity against English
            if auxiliary_translation:
                sem_trans = self.semantic_scorer.compute_similarity(auxiliary_translation, p_text)
                sem_score = max(sem_score, sem_trans)

            # 2. Keyword & Exact Phrase Match
            kw_score = KeywordAndPhraseMatcher.compute_keyword_match(
                query_text=query_text,
                passage_text=p_text,
                auxiliary_translation=auxiliary_translation
            )

            # 3. Entity Match
            ent_score = EntityAndDateMatcher.compute_entity_match(
                query_text=query_text,
                passage_text=p_text,
                doc_title=doc.title if doc else "",
                doc_publisher=doc.publisher if doc else "",
                specified_subject=subject
            )

            # 4. Date Match
            date_score = EntityAndDateMatcher.compute_date_match(
                time_period=time_period,
                query_text=query_text,
                passage_text=p_text,
                pub_date=doc.publication_date if doc else None
            )

            # 5. Statutory Source Authority Weight
            tier_weights = {
                SourceTier.TIER_1_STATUTORY: 1.0,
                SourceTier.TIER_2_OFFICIAL_AGENCY: 0.85,
                SourceTier.TIER_3_ACCREDITED_FACTCHECK: 0.75,
                SourceTier.TIER_4_SECONDARY_CIVIC: 0.60,
                SourceTier.TIER_5_UNVERIFIED: 0.40
            }
            tier_weight = tier_weights.get(doc.source_tier, 0.50) if doc else 0.50

            # 6. Check Contradictory Evidence Signal
            is_contra = ContradictoryEvidenceDetector.is_contradictory(
                query_is_negated=is_negated,
                passage_text=p_text
            )

            # Composite Score Formula
            # 0.30 Semantic + 0.25 Keyword + 0.25 Entity + 0.10 Date + 0.10 Tier Authority
            composite_score = round(
                0.30 * sem_score +
                0.25 * kw_score +
                0.25 * ent_score +
                0.10 * date_score +
                0.10 * tier_weight,
                4
            )

            # Gate: If there is neither lexical overlap nor semantic connection,
            # passage has zero topical relevance to the query
            if kw_score < 0.05 and sem_score < 0.08:
                composite_score = 0.0

            # Boost potentially contradictory evidence slightly only if there is genuine topical overlap
            if is_contra and composite_score > 0.20 and (kw_score > 0.15 or ent_score > 0.50):
                composite_score = min(1.0, composite_score + 0.10)

            # Retain only candidates that meet minimum relevance threshold
            if composite_score >= min_score_threshold:
                cand_info = {
                    "claim_id": claim_id,
                    "atomic_claim_id": atomic_claim_id,
                    "evidence_document_id": doc.document_id if doc else "UNKNOWN",
                    "evidence_passage_id": p.passage_id,
                    "retrieval_score": composite_score,
                    "semantic_similarity": round(sem_score, 4),
                    "keyword_match": round(kw_score, 4),
                    "entity_match": round(ent_score, 4),
                    "date_match": round(date_score, 4),
                    "retrieval_method": self.RETRIEVAL_METHOD,
                    "model_version": self.MODEL_VERSION,
                    "retrieval_timestamp": retrieval_time.isoformat(),
                    "is_potentially_contradictory": is_contra,
                    "passage_text": p_text,
                    "document_title": doc.title if doc else "Untitled",
                    "source_url": doc.source_url if doc else None,
                    "source_tier": doc.source_tier.value if doc else SourceTier.TIER_4_SECONDARY_CIVIC.value,
                    "disclaimer": RETRIEVAL_DISCLAIMER
                }
                candidates.append(cand_info)

        # Sort descending by composite relevance score
        candidates.sort(key=lambda c: c["retrieval_score"], reverse=True)
        ranked_candidates = candidates[:top_k]

        # Assign rank numbers
        for rank_idx, cand in enumerate(ranked_candidates):
            cand["rank"] = rank_idx + 1

        # Persist candidates to database if requested
        if persist_candidates and ranked_candidates:
            for cand in ranked_candidates:
                cand_db_id = f"RCAND-{claim_id}-{cand['evidence_passage_id']}"
                existing = self.db.query(ClaimRetrievalCandidate).filter(
                    ClaimRetrievalCandidate.candidate_id == cand_db_id
                ).first()
                if not existing:
                    db_record = ClaimRetrievalCandidate(
                        candidate_id=cand_db_id,
                        claim_id=claim_id,
                        atomic_claim_id=atomic_claim_id,
                        evidence_document_id=cand["evidence_document_id"],
                        evidence_passage_id=cand["evidence_passage_id"],
                        retrieval_score=cand["retrieval_score"],
                        semantic_similarity=cand["semantic_similarity"],
                        keyword_match=cand["keyword_match"],
                        entity_match=cand["entity_match"],
                        date_match=cand["date_match"],
                        retrieval_method=cand["retrieval_method"],
                        model_version=cand["model_version"],
                        retrieval_timestamp=retrieval_time,
                        is_potentially_contradictory=cand["is_potentially_contradictory"],
                        rank=cand["rank"],
                        metadata_json={
                            "document_title": cand["document_title"],
                            "disclaimer": RETRIEVAL_DISCLAIMER
                        }
                    )
                    self.db.add(db_record)
            self.db.commit()

        logger.info(
            f"Retrieved {len(ranked_candidates)} candidate evidence passages for claim {claim_id} "
            f"(top score: {ranked_candidates[0]['retrieval_score'] if ranked_candidates else 0.0})"
        )
        return ranked_candidates

    def retrieve_for_atomic_claim(
        self,
        atomic_claim: AtomicClaim,
        top_k: int = 10,
        min_score_threshold: float = 0.25,
        persist_candidates: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieves evidence tailored to a specific AtomicClaim instance.
        """
        return self.retrieve_candidate_evidence(
            claim_id=atomic_claim.claim_id,
            query_text=atomic_claim.atomic_claim_text,
            atomic_claim_id=atomic_claim.atomic_claim_id,
            subject=atomic_claim.subject,
            time_period=atomic_claim.time_period,
            language=atomic_claim.language,
            auxiliary_translation=atomic_claim.translation_text,
            is_negated=atomic_claim.is_negated,
            top_k=top_k,
            min_score_threshold=min_score_threshold,
            persist_candidates=persist_candidates
        )
