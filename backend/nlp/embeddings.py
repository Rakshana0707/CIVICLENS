import json
import logging
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
import torch

# We lazily load sentence_transformers to avoid massive memory overhead on simple API boots
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

from backend.models.budget import HistoricalScheme
from backend.nlp.scheme_preprocessing import SchemeTextPreprocessor

logger = logging.getLogger(__name__)

class HistoricalSchemeEmbedder:
    """
    Generates and manages semantic vector embeddings for historical schemes.
    Utilizes a multilingual model to handle Tamil and English text cohesively.
    """
    
    # We choose a fast, effective multilingual model. 
    # It balances size (smaller, faster) with the ability to map English & Tamil in the same space.
    DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
    MODEL_VERSION = "1.0.0"
    
    def __init__(self, model_name: str = DEFAULT_MODEL):
        if not HAS_SENTENCE_TRANSFORMERS:
            raise RuntimeError("sentence-transformers is not installed. Cannot generate embeddings.")
            
        self.model_name = model_name
        self.preprocessor = SchemeTextPreprocessor()
        self._model = None
        
    @property
    def model(self):
        # Lazy load the model
        if self._model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self._model = SentenceTransformer(self.model_name, device=device)
        return self._model
        
    def _compute_text_hash(self, text: str) -> str:
        """Computes a SHA-256 hash of the semantic text to detect changes."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def generate_embedding(self, text: str) -> List[float]:
        """Generates a dense vector embedding for a given string."""
        if not text.strip():
            return []
        
        # encode() returns a numpy array, we convert to standard float list for JSON storage
        vector = self.model.encode(text, convert_to_numpy=True).tolist()
        return vector

    def update_database_embeddings(self, db_session: Session, force_regenerate: bool = False) -> Dict[str, int]:
        """
        Scans all historical schemes in the database. If the semantic text has changed 
        (or if force_regenerate is True), it generates a new embedding and stores it.
        """
        report = {
            "processed": 0,
            "generated": 0,
            "skipped_unchanged": 0,
            "errors": 0
        }
        
        schemes = db_session.query(HistoricalScheme).all()
        
        for scheme in schemes:
            report["processed"] += 1
            
            try:
                # 1. Prepare raw dictionary for the preprocessor
                raw_dict = {
                    "scheme_name": scheme.scheme_name,
                    "description": scheme.description,
                    "objectives": scheme.objectives,
                    "target_beneficiaries": scheme.target_beneficiaries,
                    "sector_category": scheme.sector_category,
                    "department_name": scheme.department.name if scheme.department else ""
                }
                
                # 2. Extract normalized semantic text
                processed_dict = self.preprocessor.process_record(raw_dict)
                semantic_text = processed_dict.get("semantic_text", "")
                
                if not semantic_text:
                    continue
                    
                text_hash = self._compute_text_hash(semantic_text)
                
                # 3. Check if we can skip regeneration
                existing_payload = scheme.embedding
                if not force_regenerate and existing_payload and isinstance(existing_payload, dict):
                    if existing_payload.get("text_hash") == text_hash and existing_payload.get("model_name") == self.model_name:
                        report["skipped_unchanged"] += 1
                        continue
                        
                # 4. Generate Vector
                vector = self.generate_embedding(semantic_text)
                
                if not vector:
                    continue
                    
                # 5. Store efficiently in JSON format
                # Using the JSON column avoids requiring heavy PGVector/Qdrant setups for initial phases.
                scheme.embedding = {
                    "model_name": self.model_name,
                    "model_version": self.MODEL_VERSION,
                    "dim": len(vector),
                    "timestamp": datetime.utcnow().isoformat(),
                    "text_hash": text_hash,
                    "vector": vector
                }
                
                report["generated"] += 1
                
            except Exception as e:
                logger.error(f"Failed to generate embedding for scheme ID {scheme.id}: {str(e)}")
                report["errors"] += 1
                
        db_session.commit()
        return report
