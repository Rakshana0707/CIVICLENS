import pytest
from backend.nlp.embeddings import HistoricalSchemeEmbedder
from backend.database.session import SessionLocal
from backend.models.budget import HistoricalScheme, BudgetDepartment

def test_embedder():
    embedder = HistoricalSchemeEmbedder()
    # Ensure model loads and dimension is correct
    assert embedder.model_name == "paraphrase-multilingual-MiniLM-L12-v2"
    
    vec = embedder.generate_embedding("Tamil Nadu maternity assistance")
    assert len(vec) == 384
    
    # Test hashing
    text_hash = embedder._compute_text_hash("Hello")
    assert text_hash == embedder._compute_text_hash("Hello")
    assert text_hash != embedder._compute_text_hash("Hello ")

    # We won't test DB update here to avoid touching real DB, 
    # but the hash and generation work correctly.
    print("Embedding generation successful.")
    
if __name__ == "__main__":
    test_embedder()
