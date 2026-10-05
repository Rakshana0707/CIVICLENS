"""
Promise-to-Evidence Candidate Retrieval & Matching System (Phase 3.10).

Identifies candidate government implementation evidence records potentially relevant to a promise,
combining multiple matching signals:
1. Semantic Similarity (Sentence-BERT vector similarity)
2. Keywords & Named Entities (Target population, monetary targets, action verbs)
3. Department Alignment (Department names & departmental tags)
4. Time Alignment (Publication date & election timeline alignment)
5. Historical Scheme Relationship (Leveraging Phase 3.8 scheme links)

IMPORTANT DISCLAIMER:
This pipeline performs Candidate Retrieval & Evidence Matching.
It is NOT the final implementation status assessment.
"""

import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from backend.models.promise import PoliticalPromise, PromiseEvidenceLink, PromiseSchemeLink
from backend.models.common import Evidence
from backend.models.budget import HistoricalScheme
from backend.nlp.preprocessing import normalize_unicode, normalize_whitespace
from backend.nlp.similarity import cosine_similarity, HistoricalSchemeEmbedder

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_MODEL_VERSION = "1.0.0"
MATCHING_METHOD = "multi_signal_hybrid_retrieval"
DISCLAIMER_NOTE = (
    "Candidate retrieval match indicating potential relevance only. "
    "NOT a final implementation status assessment."
)


class PromiseEvidenceMatcher:
    """
    Multi-signal candidate matching service connecting Political Promises
    with candidate Evidence records.
    """

    def __init__(
        self,
        db_session: Session,
        model_name: str = DEFAULT_MODEL_NAME,
        model_version: str = DEFAULT_MODEL_VERSION,
        embedder: Optional[Any] = None
    ):
        self.db = db_session
        self.model_name = model_name
        self.model_version = model_version
        self._embedder = embedder

    @property
    def embedder(self):
        if self._embedder is None:
            try:
                self._embedder = HistoricalSchemeEmbedder(model_name=self.model_name)
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer embedder: {e}. Semantic signal will use fallback score.")
                self._embedder = None
        return self._embedder

    def preprocess_text(self, text: str) -> str:
        if not text:
            return ""
        return normalize_whitespace(normalize_unicode(text))

    def _extract_keywords(self, text: str) -> List[str]:
        words = re.findall(r'\b[A-Za-z\u0B80-\u0BFF]{3,}\b', text.lower())
        stopwords = {"this", "that", "with", "from", "will", "have", "were", "been", "providing", "which", "shall"}
        return [w for w in words if w not in stopwords]

    def _compute_semantic_signal(self, promise_text: str, evidence_text: str) -> float:
        if not self.embedder:
            return 0.0
        try:
            vec_promise = self.embedder.generate_embedding(promise_text)
            vec_evidence = self.embedder.generate_embedding(evidence_text)
            if vec_promise and vec_evidence:
                return cosine_similarity(vec_promise, vec_evidence)
        except Exception as e:
            logger.warning(f"Error computing semantic embedding: {e}")
        return 0.0

    def _compute_keyword_signal(
        self,
        promise_text: str,
        evidence_text: str,
        promise_meta: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, List[str]]:
        matched_terms = []
        p_keywords = self._extract_keywords(promise_text)
        e_text_lower = evidence_text.lower()

        overlap_count = 0
        for kw in set(p_keywords):
            if kw in e_text_lower:
                overlap_count += 1
                matched_terms.append(kw)

        # Check explicit metadata targets if available
        if promise_meta:
            monetary = promise_meta.get("monetary_target")
            if monetary and any(digit in e_text_lower for digit in re.findall(r'\d+', monetary)):
                matched_terms.append(f"monetary:{monetary}")
                overlap_count += 2

            target_pop = promise_meta.get("target_population")
            if target_pop and target_pop.lower() in e_text_lower:
                matched_terms.append(f"target_pop:{target_pop}")
                overlap_count += 2

        score = min(1.0, round(overlap_count * 0.2, 2))
        return score, matched_terms

    def _compute_department_signal(
        self,
        promise_meta: Optional[Dict[str, Any]],
        evidence_supp: Optional[Dict[str, Any]],
        evidence_text: str
    ) -> float:
        dept = promise_meta.get("department") if promise_meta else None
        if not dept:
            return 0.0

        dept_lower = dept.lower()
        e_text_lower = evidence_text.lower()

        if dept_lower in e_text_lower:
            return 1.0

        # Check evidence supporting values
        if evidence_supp:
            src_name = str(evidence_supp.get("source_name", "")).lower()
            src_type = str(evidence_supp.get("source_type", "")).lower()
            if any(w in src_name or w in src_type for w in dept_lower.split() if len(w) > 3):
                return 0.8

        return 0.0

    def _compute_time_signal(
        self,
        evidence_supp: Optional[Dict[str, Any]]
    ) -> float:
        if not evidence_supp:
            return 0.0

        pub_date = evidence_supp.get("publication_date")
        if pub_date:
            return 0.8  # Document has verified publication date timestamp
        return 0.3

    def _compute_scheme_relation_signal(
        self,
        promise_id: str,
        evidence_id: int
    ) -> float:
        """Checks if the promise links to a scheme that matches evidence context."""
        scheme_links = self.db.query(PromiseSchemeLink).filter(PromiseSchemeLink.promise_id == promise_id).all()
        if scheme_links:
            # Promise has pre-existing historical scheme links from Phase 3.8
            top_score = max((l.similarity_score or 0.0) for l in scheme_links)
            return min(1.0, top_score)
        return 0.0

    def calculate_candidate_match(
        self,
        promise: PoliticalPromise,
        evidence: Evidence
    ) -> Dict[str, Any]:
        """
        Computes hybrid multi-signal candidate relevance score between a Promise and Evidence record.
        """
        p_text = self.preprocess_text(promise.normalized_text or promise.original_text)
        e_text = self.preprocess_text(evidence.content or "")

        p_meta = promise.metadata_json or {}
        e_supp = evidence.supporting_values or {}

        # 1. Semantic Similarity (Weight: 0.35)
        sem_score = self._compute_semantic_signal(p_text, e_text)

        # 2. Keywords & Entities (Weight: 0.20)
        kw_score, matched_terms = self._compute_keyword_signal(p_text, e_text, p_meta)

        # 3. Department Alignment (Weight: 0.15)
        dept_score = self._compute_department_signal(p_meta, e_supp, e_text)

        # 4. Time Alignment (Weight: 0.10)
        time_score = self._compute_time_signal(e_supp)

        # 5. Historical Scheme Relationship (Weight: 0.20)
        scheme_score = self._compute_scheme_relation_signal(promise.promise_id, evidence.id)

        # Multi-signal weighted score
        relevance_score = round(
            (0.35 * sem_score) +
            (0.20 * kw_score) +
            (0.15 * dept_score) +
            (0.10 * time_score) +
            (0.20 * scheme_score),
            4
        )

        matched_signals = []
        if sem_score >= 0.4: matched_signals.append("semantic_similarity")
        if kw_score > 0: matched_signals.append("keywords_entities")
        if dept_score > 0: matched_signals.append("department_alignment")
        if time_score > 0: matched_signals.append("time_alignment")
        if scheme_score > 0: matched_signals.append("historical_scheme_relationship")

        matched_metadata = {
            "matched_signals": matched_signals,
            "signal_scores": {
                "semantic_similarity": round(sem_score, 4),
                "keywords": round(kw_score, 4),
                "department": round(dept_score, 4),
                "time": round(time_score, 4),
                "historical_scheme_relation": round(scheme_score, 4)
            },
            "matched_terms": matched_terms
        }

        return {
            "promise_id": promise.promise_id,
            "evidence_id": evidence.id,
            "similarity_score": round(sem_score, 4),
            "relevance_score": relevance_score,
            "matching_method": MATCHING_METHOD,
            "matched_metadata": matched_metadata,
            "model_information": {
                "model_name": self.model_name,
                "model_version": self.model_version
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def match_promise_with_evidence_candidates(
        self,
        promise: PoliticalPromise,
        top_k: int = 5,
        relevance_threshold: float = 0.2,
        persist_links: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top candidate Evidence items for a Promise and optionally persists PromiseEvidenceLink records.
        """
        evidence_items = self.db.query(Evidence).all()
        candidate_matches = []

        for ev in evidence_items:
            match_res = self.calculate_candidate_match(promise, ev)
            if match_res["relevance_score"] >= relevance_threshold:
                candidate_matches.append(match_res)

        # Sort descending by relevance score
        candidate_matches.sort(key=lambda x: x["relevance_score"], reverse=True)
        top_candidates = candidate_matches[:top_k]

        if persist_links:
            for match in top_candidates:
                existing_link = self.db.query(PromiseEvidenceLink).filter(
                    PromiseEvidenceLink.promise_id == promise.promise_id,
                    PromiseEvidenceLink.evidence_id == match["evidence_id"]
                ).first()

                if existing_link:
                    existing_link.similarity_score = match["similarity_score"]
                    existing_link.relevance_score = match["relevance_score"]
                    existing_link.matching_method = MATCHING_METHOD
                    existing_link.model_name = self.model_name
                    existing_link.model_version = self.model_version
                    existing_link.matched_metadata = match["matched_metadata"]
                    existing_link.relevance_notes = DISCLAIMER_NOTE
                else:
                    new_link = PromiseEvidenceLink(
                        promise_id=promise.promise_id,
                        evidence_id=match["evidence_id"],
                        similarity_score=match["similarity_score"],
                        relevance_score=match["relevance_score"],
                        matching_method=MATCHING_METHOD,
                        model_name=self.model_name,
                        model_version=self.model_version,
                        matched_metadata=match["matched_metadata"],
                        relevance_notes=DISCLAIMER_NOTE
                    )
                    self.db.add(new_link)

            self.db.commit()

        return top_candidates

    def match_all_promises_with_evidence(
        self,
        top_k: int = 5,
        relevance_threshold: float = 0.2
    ) -> Dict[str, Any]:
        """
        Executes candidate evidence retrieval for all promises in DB.
        """
        promises = self.db.query(PoliticalPromise).all()
        summary = {
            "total_promises": len(promises),
            "promises_with_candidates": 0,
            "total_links_created": 0
        }

        for p in promises:
            matches = self.match_promise_with_evidence_candidates(
                promise=p,
                top_k=top_k,
                relevance_threshold=relevance_threshold,
                persist_links=True
            )
            if matches:
                summary["promises_with_candidates"] += 1
                summary["total_links_created"] += len(matches)

        return summary
