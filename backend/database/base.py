# This file imports the Base class and all models.
# By importing this file, Alembic (or create_all) can discover all models.

from backend.database.base_class import Base  # noqa
# Import specific models here so Alembic can discover them
from backend.models.common import (
    Source, 
    DataSource, 
    Document, 
    Evidence, 
    ProcessingStatus, 
    ModelPrediction, 
    ModelEvaluation
)
