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
