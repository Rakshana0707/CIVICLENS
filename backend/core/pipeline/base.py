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
        Executes the full pipeline sequentially, safely wrapped with error tracking.
        """
        from backend.core.logger import setup_logger
        logger = setup_logger("civiclens.pipeline")
        
        try:
            logger.info("Starting pipeline execution: Ingestion")
            data = self.ingest(source)
        except Exception as e:
            logger.error(f"Data ingestion failure: {str(e)}")
            raise
            
        try:
            logger.info("Pipeline stage: Validation")
            if not self.validate(data):
                logger.warning("Data validation failed conditions.")
                raise ValueError("Data validation failed during pipeline execution.")
        except Exception as e:
            logger.error(f"Preprocessing/Validation failure: {str(e)}")
            raise
            
        try:
            logger.info("Pipeline stage: Cleaning")
            data = self.clean(data)
        except Exception as e:
            logger.error(f"Data cleaning failure: {str(e)}")
            raise
            
        try:
            logger.info("Pipeline stage: Transformation")
            data = self.transform(data)
        except Exception as e:
            logger.error(f"Data transformation failure: {str(e)}")
            raise
            
        try:
            logger.info("Pipeline stage: Storage")
            return self.store(data)
        except Exception as e:
            logger.error(f"Database/Storage failure: {str(e)}")
            raise
