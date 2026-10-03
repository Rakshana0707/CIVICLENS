import numpy as np
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.models.budget import HistoricalScheme, SchemeSourceRelationship, BudgetSourceDocument
from backend.nlp.embeddings import HistoricalSchemeEmbedder

logger = logging.getLogger(__name__)

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
        
    return float(np.dot(v1, v2) / (norm1 * norm2))


class SemanticSchemeSearcher:
    """
    Service for finding historically similar schemes using semantic embeddings.
    Important: Similarity is NOT equivalence. A high score indicates semantic 
    overlap in the description, not that the schemes have identical policy mechanics.
    """
    def __init__(self, db_session: Session, embedder: Optional[HistoricalSchemeEmbedder] = None):
        self.db = db_session
        self.embedder = embedder or HistoricalSchemeEmbedder()
        
    def _get_sources_for_scheme(self, scheme_id: int) -> List[Dict[str, Any]]:
        rels = self.db.query(SchemeSourceRelationship).filter(SchemeSourceRelationship.historical_scheme_id == scheme_id).all()
        sources = []
        for rel in rels:
            doc = self.db.query(BudgetSourceDocument).filter(BudgetSourceDocument.id == rel.source_document_id).first()
            if doc:
                sources.append({
                    "document_title": doc.title,
                    "page_number": rel.source_page_number
                })
        return sources

    def _get_candidates(self, department_id: Optional[int] = None, year: Optional[str] = None, category_id: Optional[int] = None) -> List[HistoricalScheme]:
        query = self.db.query(HistoricalScheme)
        if department_id:
            query = query.filter(HistoricalScheme.department_id == department_id)
        if year:
            query = query.filter(HistoricalScheme.financial_year == year)
        if category_id:
            query = query.filter(HistoricalScheme.category_id == category_id)
        return query.all()

    def _rank_candidates(self, query_vector: List[float], candidate_schemes: List[HistoricalScheme], 
                         threshold: float, exclude_id: Optional[int] = None) -> List[Dict[str, Any]]:
        results = []
        
        for scheme in candidate_schemes:
            if exclude_id and scheme.id == exclude_id:
                continue
                
            payload = scheme.embedding
            if not payload or not isinstance(payload, dict) or "vector" not in payload:
                continue
                
            target_vector = payload["vector"]
            score = cosine_similarity(query_vector, target_vector)
            
            if score >= threshold:
                dept_name = scheme.department.name if scheme.department else "Unknown"
                results.append({
                    "id": scheme.id,
                    "scheme_name": scheme.scheme_name,
                    "financial_year": scheme.financial_year,
                    "department": dept_name,
                    "department_id": scheme.department_id,
                    "category_id": scheme.category_id,
                    "similarity_score": round(score, 4),
                    "description": scheme.description or scheme.objectives or "No description available",
                    "sources": self._get_sources_for_scheme(scheme.id),
                    "disclaimer": "Similarity score indicates topical overlap, not policy equivalence."
                })
                
        # Sort descending by score
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results

    def search_by_text(self, query_text: str, top_k: int = 5, threshold: float = 0.3, page: int = 1,
                       department_id: Optional[int] = None, year: Optional[str] = None, category_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Takes an arbitrary text string, generates its semantic embedding, and searches 
        for overlapping historical schemes, applying database filters.
        """
        query_vector = self.embedder.generate_embedding(query_text)
        if not query_vector:
            return {"query": query_text, "items": [], "total": 0, "page": page, "limit": top_k}
            
        candidate_schemes = self._get_candidates(department_id, year, category_id)
        ranked = self._rank_candidates(query_vector, candidate_schemes, threshold)
        
        total = len(ranked)
        start_idx = (page - 1) * top_k
        end_idx = start_idx + top_k
        items = ranked[start_idx:end_idx]
        
        return {
            "query": query_text,
            "items": items,
            "total": total,
            "page": page,
            "limit": top_k
        }
        
    def search_by_scheme_id(self, scheme_id: int, top_k: int = 5, threshold: float = 0.3, page: int = 1,
                            department_id: Optional[int] = None, year: Optional[str] = None, category_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Uses an existing scheme's pre-calculated embedding to find similar historical schemes.
        """
        source_scheme = self.db.query(HistoricalScheme).filter(HistoricalScheme.id == scheme_id).first()
        if not source_scheme:
            raise ValueError(f"Scheme ID {scheme_id} not found.")
            
        payload = source_scheme.embedding
        if not payload or not isinstance(payload, dict) or "vector" not in payload:
            raise ValueError(f"Scheme ID {scheme_id} has no pre-calculated embeddings.")
            
        query_vector = payload["vector"]
        candidate_schemes = self._get_candidates(department_id, year, category_id)
        
        ranked = self._rank_candidates(query_vector, candidate_schemes, threshold, exclude_id=scheme_id)
        
        total = len(ranked)
        start_idx = (page - 1) * top_k
        end_idx = start_idx + top_k
        items = ranked[start_idx:end_idx]
        
        return {
            "query_scheme": {
                "id": source_scheme.id,
                "scheme_name": source_scheme.scheme_name,
                "financial_year": source_scheme.financial_year
            },
            "items": items,
            "total": total,
            "page": page,
            "limit": top_k
        }
