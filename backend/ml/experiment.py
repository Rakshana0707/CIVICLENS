from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any

@dataclass
class ExperimentTrackingMetadata:
    """
    Data structure for tracking Machine Learning experiment lifecycle metadata.
    Designed to be easily serialized and pushed to a central database or MLFlow.
    """
    experiment_id: str
    model_name: str
    model_version: str
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    training_time_seconds: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
