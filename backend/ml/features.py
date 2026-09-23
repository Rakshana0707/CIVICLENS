from abc import ABC, abstractmethod
from typing import Any

class BaseFeatureExtractor(ABC):
    """
    Abstract Base Class for feature preparation and engineering.
    """
    
    @abstractmethod
    def fit(self, data: Any, y: Any = None) -> "BaseFeatureExtractor":
        """Learn parameters from the data."""
        pass
        
    @abstractmethod
    def transform(self, data: Any) -> Any:
        """Transform the data based on learned parameters."""
        pass
        
    def fit_transform(self, data: Any, y: Any = None) -> Any:
        """Convenience method to fit and transform simultaneously."""
        self.fit(data, y)
        return self.transform(data)
