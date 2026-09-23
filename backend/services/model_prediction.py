from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.repositories.common import model_prediction_repo
from backend.models.common import ModelPrediction

class ModelPredictionService:
    """
    Business logic for safely recording Model Predictions against generic targets.
    """

    @staticmethod
    def record_prediction(db: Session, *, obj_in: Dict[str, Any]) -> ModelPrediction:
        """
        Records an ML prediction. Requires structural validations.
        """
        required_fields = ["model_name", "target_type", "target_id", "prediction_data"]
        for field in required_fields:
            if field not in obj_in:
                raise ValueError(f"Missing required field for prediction: {field}")
                
        # Additional business rules could go here (e.g. verifying model version format)
        if "model_version" not in obj_in:
            obj_in["model_version"] = "latest"
                
        return model_prediction_repo.create(db, obj_in=obj_in)
