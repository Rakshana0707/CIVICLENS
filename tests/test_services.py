import pytest
from backend.database.session import SessionLocal, engine
from backend.database.base_class import Base
from backend.services.source import SourceService
from backend.services.document import DocumentService
from backend.services.evidence import EvidenceService
from backend.services.model_prediction import ModelPredictionService
from backend.services.model_evaluation import ModelEvaluationService

def test_service_architecture_and_validation():
    """
    Test the service layer validations and repository delegation.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # --- 1. Source Service ---
        # Test validation fails on missing name
        with pytest.raises(ValueError, match="Source name is strictly required."):
            SourceService.create_source(db, obj_in={"type": "News"})
            
        # Test successful creation and business logic (Capitalization of type)
        source = SourceService.create_source(db, obj_in={"name": "The Hindu", "type": " news "})
        assert source.id is not None
        assert source.type == "News"
        
        # --- 2. Document Service ---
        # Test validation
        with pytest.raises(ValueError, match="Both Document 'title' and 'content' are required."):
            DocumentService.create_document(db, obj_in={"title": "Empty Content"})
            
        # Test successful creation
        doc = DocumentService.create_document(
            db, obj_in={"title": "Policy Document", "content": "Article body.", "source_id": source.id}
        )
        assert doc.id is not None
        
        # --- 3. Evidence Service ---
        # Test validation missing content
        with pytest.raises(ValueError, match="Evidence content cannot be empty."):
            EvidenceService.extract_and_record_evidence(db, document_id=doc.id, content="")
            
        # Test validation missing links
        with pytest.raises(ValueError, match="Evidence must be linked"):
            EvidenceService.extract_and_record_evidence(db, content="A claim.")
            
        # Test successful extraction
        evidence = EvidenceService.extract_and_record_evidence(
            db, document_id=doc.id, content="Extracted claim.", context="Surrounding words."
        )
        assert evidence.id is not None
        
        # --- 4. Model Prediction Service ---
        # Test missing field validation
        with pytest.raises(ValueError, match="Missing required field for prediction: target_type"):
            ModelPredictionService.record_prediction(db, obj_in={"model_name": "classifier"}) 
            
        # Test successful prediction recording
        prediction = ModelPredictionService.record_prediction(db, obj_in={
            "model_name": "claim_classifier",
            "model_version": "v1.2",
            "target_type": "Claim",
            "target_id": "99",
            "prediction_data": {"confidence": 0.9, "class": "Actionable"},
            "evidence_id": evidence.id
        })
        assert prediction.id is not None
        assert prediction.model_version == "v1.2"
        
        # --- 5. Model Evaluation Service ---
        # Test score conversion validation
        with pytest.raises(ValueError, match="Evaluation score must be a number."):
            ModelEvaluationService.record_evaluation(db, obj_in={
                "model_name": "claim_classifier",
                "model_version": "v1",
                "evaluation_metric": "F1",
                "score": "not_a_number"
            })
            
        # Test successful evaluation
        evaluation = ModelEvaluationService.record_evaluation(db, obj_in={
            "model_name": "claim_classifier",
            "model_version": "v1",
            "evaluation_metric": "F1",
            "score": "0.85" # string should be converted to float
        })
        assert evaluation.id is not None
        assert evaluation.score == 0.85
        
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
