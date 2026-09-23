from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.repositories.common import model_evaluation_repo
from backend.models.common import ModelEvaluation

class ModelEvaluationService:
    """
    Business logic for storing Model Evaluation metrics.
    """

    @staticmethod
    def record_evaluation(db: Session, *, obj_in: Dict[str, Any]) -> ModelEvaluation:
        """
        Records the performance metric of an ML Model.
        """
        required_fields = ["model_name", "model_version", "evaluation_metric", "score"]
        for field in required_fields:
            if field not in obj_in:
                raise ValueError(f"Missing required evaluation field: {field}")
                
        # Ensure score is numeric
        try:
            obj_in["score"] = float(obj_in["score"])
        except ValueError:
            raise ValueError("Evaluation score must be a number.")
        
        return model_evaluation_repo.create(db, obj_in=obj_in)
