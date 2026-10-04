from abc import ABC, abstractmethod
from typing import List
from .models import AcquisitionMetadata

class BaseAcquirer(ABC):
    """
    Abstract base class for all acquisition modules (e.g., ManifestoAcquirer, BudgetAcquirer).
    """
    
    @abstractmethod
    def discover_urls(self) -> List[str]:
        """
        Identify and return a list of target URLs to process.
        """
        pass
        
    @abstractmethod
    def acquire(self, url: str) -> AcquisitionMetadata:
        """
        Acquire the document from the given URL and return its provenance metadata.
        """
        pass
