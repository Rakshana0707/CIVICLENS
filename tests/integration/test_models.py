from backend.models.common import Source, DataSource, Document, Evidence, ProcessingStatus, ModelPrediction, ModelEvaluation

def test_common_models_creation(db_session, sample_source, sample_document):
    """
    Test creation and basic relationships for the common domain models using isolated fixtures.
    """
    # 1. Test DataSource Creation linked to sample source
    ds = DataSource(source_id=sample_source.id, name="Budget 2024", format="CSV", status=ProcessingStatus.COMPLETED)
    db_session.add(ds)
    db_session.commit()
    
    assert ds.source.name == "Fixture Source"
    
    # 2. Test Evidence Creation linked to sample document
    evidence = Evidence(document_id=sample_document.id, content="Specific policy claim.")
    db_session.add(evidence)
    db_session.commit()
    
    assert evidence.document.title == "Fixture Document"
    assert evidence.document.source.type == "Government"
    
    # 3. Test ModelPrediction Creation
    prediction = ModelPrediction(
        model_name="claim_classifier",
        model_version="v1.0",
        target_type="Claim",
        target_id="123",
        prediction_data={"label": "Actionable", "confidence": 0.95},
        evidence_id=evidence.id
    )
    db_session.add(prediction)
    
    # 4. Test ModelEvaluation Creation
    eval_metrics = ModelEvaluation(
        model_name="claim_classifier",
        model_version="v1.0",
        evaluation_metric="F1",
        score=0.88,
        dataset_reference="gold_standard_v1"
    )
    db_session.add(eval_metrics)
    db_session.commit()
    
    assert prediction.evidence.content == "Specific policy claim."
    assert prediction.prediction_data["label"] == "Actionable"
