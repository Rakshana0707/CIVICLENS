from datetime import date
from backend.database.session import SessionLocal, engine
from backend.database.base_class import Base
from backend.models.common import Source, DataSource, Document, Evidence, ProcessingStatus, ModelPrediction, ModelEvaluation

def test_common_models_creation():
    """
    Test creation and basic relationships for the common domain models.
    """
    # Create all tables (in-memory or test DB depending on configuration, 
    # but for local SQLite this creates the tables in the configured DB)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # 1. Test Source Creation
        source = Source(name="TN Govt Portal", type="Government")
        db.add(source)
        db.commit()
        db.refresh(source)
        assert source.id is not None
        assert source.name == "TN Govt Portal"
        
        # 2. Test DataSource Creation
        ds = DataSource(source_id=source.id, name="Budget 2024", format="CSV", status=ProcessingStatus.COMPLETED)
        db.add(ds)
        
        # 3. Test Document Creation
        doc = Document(source_id=source.id, title="Policy Speech", content="This is a speech.", status=ProcessingStatus.PENDING)
        db.add(doc)
        db.commit()
        db.refresh(ds)
        db.refresh(doc)
        
        # Assert relationship from child to parent
        assert ds.source.name == "TN Govt Portal"
        assert doc.source.name == "TN Govt Portal"
        
        # 4. Test Evidence Creation
        evidence = Evidence(document_id=doc.id, content="Specific policy claim.")
        db.add(evidence)
        db.commit()
        db.refresh(evidence)
        
        # Assert Evidence relationships
        assert evidence.document.title == "Policy Speech"
        assert evidence.document.source.type == "Government"
        
        # 5. Test ModelPrediction Creation
        prediction = ModelPrediction(
            model_name="claim_classifier",
            model_version="v1.0",
            target_type="Claim",
            target_id="123",
            prediction_data={"label": "Actionable", "confidence": 0.95},
            evidence_id=evidence.id
        )
        db.add(prediction)
        
        # 6. Test ModelEvaluation Creation
        eval_metrics = ModelEvaluation(
            model_name="claim_classifier",
            model_version="v1.0",
            evaluation_metric="F1",
            score=0.88,
            dataset_reference="gold_standard_v1"
        )
        db.add(eval_metrics)
        db.commit()
        
        # Assert prediction relationships and JSON storing
        assert prediction.evidence.content == "Specific policy claim."
        assert prediction.prediction_data["label"] == "Actionable"
        
    finally:
        # Cleanup
        db.close()
        # Drop all tables after test so we don't pollute the local DB repeatedly
        # (in a real app, you'd use a dedicated test DB or transactions)
        Base.metadata.drop_all(bind=engine)
