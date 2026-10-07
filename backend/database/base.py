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
from backend.models.budget import (
    BudgetDepartment,
    BudgetScheme,
    BudgetSourceDocument,
    BudgetImportBatch,
    BudgetRecord,
    HistoricalScheme,
    SchemeCategory
)
from backend.models.manifesto import (
    ManifestoSource,
    ManifestoDocument,
    Manifesto
)
from backend.models.promise import (
    PoliticalPromise,
    PromiseCategory,
    PromiseCategoryMapping,
    PromiseEvidenceLink,
    PromiseSchemeLink,
    PromiseAssessment,
    PromiseAssessmentHistory,
    PromiseStatus
)
from backend.models.news import (
    NewsSource,
    Article,
    ArticleVersion,
    PoliticalParty,
    PoliticalPerson,
    PoliticalEntity,
    PoliticalEvent,
    Topic,
    ArticleEntity,
    ArticleTopic,
    ArticleEvent,
    ArticleFeature,
    CoverageMetric,
    BiasIndicator,
    SourceSnapshot,
    SourceType,
    ActiveStatus
)

