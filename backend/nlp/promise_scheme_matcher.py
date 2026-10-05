"""
Promise-to-Historical-Scheme Matching Engine (Phase 3.8).

Connects Phase 3 political promises with Phase 2 Historical Scheme Intelligence.

Pipeline:
Promise -> Text Preprocessing -> Sentence-BERT Embedding -> Phase 2 Scheme Embeddings -> Cosine Similarity -> Top-K Historical Schemes -> DB Link Creation

IMPORTANT DISCLAIMER:
Semantic similarity indicates topical/description overlap only.
It does NOT imply policy identity, implementation, or promise fulfillment.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.models.promise import PoliticalPromise, PromiseSchemeLink
from backend.models.budget import HistoricalScheme
from backend.nlp.preprocessing import normalize_unicode, normalize_whitespace
from backend.nlp.similarity import cosine_similarity, SemanticSchemeSearcher

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_MODEL_VERSION = "1.0.0"
MATCHING_METHOD = "sentence_bert_cosine_similarity"
DISCLAIMER_NOTE = (
    "Semantic similarity indicates topical/description overlap only. "
    "It does NOT imply policy identity, implementation, or promise fulfillment."
)


class PromiseSchemeMatcher:
    """
    Service that calculates semantic similarity between political promises
    and Phase 2 historical schemes, persisting the top-K matches into PromiseSchemeLink.
    """

    def __init__(
        self,
        db_session: Session,
        model_name: str = DEFAULT_MODEL_NAME,
        model_version: str = DEFAULT_MODEL_VERSION,
        searcher: Optional[SemanticSchemeSearcher] = None
    ):
        self.db = db_session
        self.model_name = model_name
        self.model_version = model_version
        self.searcher = searcher or SemanticSchemeSearcher(db_session=db_session)

    def preprocess_text(self, text: str) -> str:
        """Applies text preprocessing prior to embedding generation."""
        if not text:
            return ""
        return normalize_whitespace(normalize_unicode(text))

    def match_promise(
        self,
        promise: PoliticalPromise,
        top_k: int = 5,
        similarity_threshold: float = 0.3,
        persist_links: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Matches a single PoliticalPromise against Phase 2 historical schemes.

        Returns a list of match dictionaries containing:
        - promise_id
        - scheme_id
        - similarity_score
        - model_name
        - model_version
        - generated_at
        - matching_method
        """
        raw_text = promise.normalized_text or promise.original_text
        preprocessed_text = self.preprocess_text(raw_text)

        if not preprocessed_text:
            logger.warning(f"Promise {promise.promise_id} has empty text. Skipping matching.")
            return []

        # Use Phase 2 SemanticSchemeSearcher to find top matches
        search_result = self.searcher.search_by_text(
            query_text=preprocessed_text,
            top_k=top_k,
            threshold=similarity_threshold
        )

        matches: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)

        for item in search_result.get("items", []):
            scheme_id = item["id"]
            score = item["similarity_score"]

            match_data = {
                "promise_id": promise.promise_id,
                "scheme_id": scheme_id,
                "similarity_score": score,
                "model_name": self.model_name,
                "model_version": self.model_version,
                "generated_at": now.isoformat(),
                "matching_method": MATCHING_METHOD,
                "scheme_name": item.get("scheme_name"),
                "financial_year": item.get("financial_year"),
                "department": item.get("department")
            }
            matches.append(match_data)

            if persist_links:
                # Check if link already exists to handle duplicates cleanly
                existing_link = self.db.query(PromiseSchemeLink).filter(
                    PromiseSchemeLink.promise_id == promise.promise_id,
                    PromiseSchemeLink.historical_scheme_id == scheme_id
                ).first()

                if existing_link:
                    existing_link.similarity_score = score
                    existing_link.matching_method = MATCHING_METHOD
                    existing_link.model_name = self.model_name
                    existing_link.model_version = self.model_version
                    existing_link.notes = DISCLAIMER_NOTE
                else:
                    new_link = PromiseSchemeLink(
                        promise_id=promise.promise_id,
                        historical_scheme_id=scheme_id,
                        similarity_score=score,
                        matching_method=MATCHING_METHOD,
                        match_type="historical_scheme_similarity",
                        model_name=self.model_name,
                        model_version=self.model_version,
                        notes=DISCLAIMER_NOTE
                    )
                    self.db.add(new_link)

        if persist_links:
            self.db.commit()

        return matches

    def match_all_promises(
        self,
        top_k: int = 5,
        similarity_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        Matches all PoliticalPromise records in the DB against historical schemes.
        """
        promises = self.db.query(PoliticalPromise).all()
        summary = {
            "total_promises": len(promises),
            "matched_promises": 0,
            "total_links_created": 0
        }

        for promise in promises:
            matches = self.match_promise(
                promise=promise,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                persist_links=True
            )
            if matches:
                summary["matched_promises"] += 1
                summary["total_links_created"] += len(matches)

        return summary
