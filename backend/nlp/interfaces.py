from abc import ABC, abstractmethod
from typing import List
from backend.nlp.core import NLPResult

class BaseTokenizer(ABC):
    """
    Abstract interface for text tokenization.
    Implementations could wrap HuggingFace Tokenizers (like IndicBERT's tokenizer) or spaCy.
    """
    @abstractmethod
    def tokenize(self, text: str) -> List[str]:
        pass

class BaseEmbeddingModel(ABC):
    """
    Abstract interface for Embedding models.
    Future implementations will wrap Sentence-BERT or mBERT architectures.
    """
    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """Convert text into a dense vector representation."""
        pass
        
    @abstractmethod
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch process texts into embeddings for efficient processing."""
        pass
