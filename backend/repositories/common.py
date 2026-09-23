from backend.repositories.base import CRUDBase
from backend.models.common import (
    Source, 
    DataSource, 
    Document, 
    Evidence, 
    ModelPrediction, 
    ModelEvaluation
)

# Export instantiated repositories for the common models
source_repo = CRUDBase[Source](Source)
data_source_repo = CRUDBase[DataSource](DataSource)
document_repo = CRUDBase[Document](Document)
evidence_repo = CRUDBase[Evidence](Evidence)
model_prediction_repo = CRUDBase[ModelPrediction](ModelPrediction)
model_evaluation_repo = CRUDBase[ModelEvaluation](ModelEvaluation)
