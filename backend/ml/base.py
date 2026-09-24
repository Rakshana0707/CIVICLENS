from abc import ABC, abstractmethod
from typing import Any

class BaseMLModel(ABC):
    """
    Abstract Base Class for all ML Models in CivicLens TN.
    Enforces a strict interface for lifecycle management: Train, Predict, Save, and Load.
    """
    
    @abstractmethod
    def train(self, X: Any, y: Any = None, **kwargs) -> Any:
        """Train or fit the underlying ML model."""
        pass
        
    @abstractmethod
    def predict(self, X: Any) -> Any:
        """Run predictions using the fitted model."""
        pass
        
    @abstractmethod
    def save(self, path: str) -> None:
        """Serialize the model architecture and weights to disk."""
        pass
        
    @abstractmethod
    def load(self, path: str) -> None:
        """Load the model architecture and weights from disk."""
        pass

    def load_safe(self, path: str) -> bool:
        """
        Safely attempts to load the ML model and logs explicit failures, 
        preventing unexpected runtime crashes on corrupted model files.
        """
        from backend.core.logger import setup_logger
        logger = setup_logger("civiclens.ml")
        try:
            logger.info(f"Loading ML model from {path}")
            self.load(path)
            return True
        except Exception as e:
            logger.error(f"Model loading failure from {path}: {str(e)}")
            return False
