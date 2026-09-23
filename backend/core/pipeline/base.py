from abc import ABC, abstractmethod
from typing import Any

class BaseDataPipeline(ABC):
    """
    Abstract base class for all CivicLens data processing pipelines.
    Enforces a standardized 5-stage sequential pattern.
    """
    
    @abstractmethod
    def ingest(self, source: Any) -> Any:
        """Stage 1: Load raw data from a source (file, API, DB, etc)."""
        pass
        
    @abstractmethod
    def validate(self, data: Any) -> bool:
        """Stage 2: Validate the ingested data against expected schemas or conditions."""
        pass
        
    @abstractmethod
    def clean(self, data: Any) -> Any:
        """Stage 3: Remove anomalies, impute missing values, drop duplicates."""
        pass
        
    @abstractmethod
    def transform(self, data: Any) -> Any:
        """Stage 4: Convert formats, engineer features, extract NLP embeddings."""
        pass
        
    @abstractmethod
    def store(self, data: Any) -> Any:
        """Stage 5: Persist the transformed data to the target repository/DB."""
        pass

    def run(self, source: Any) -> Any:
        """
        Executes the full pipeline sequentially and safely.
        """
        data = self.ingest(source)
        
        if not self.validate(data):
            raise ValueError("Data validation failed during pipeline execution.")
            
        data = self.clean(data)
        data = self.transform(data)
        
        return self.store(data)
