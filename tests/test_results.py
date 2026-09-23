from backend.core.results import ExplainableResult, EvidenceItem, SourceReference

def test_explainable_result_structure():
    """
    Test that the ExplainableResult correctly accommodates non-binary, 
    evidence-based statistical assessments.
    """
    
    source_ref = SourceReference(
        source_name="TN Finance Dept",
        url="http://tn.gov.in/budget",
        document_title="Budget Speech 2024",
        page_number=12
    )
    
    evidence = EvidenceItem(
        content="The deficit is projected at 3.5%.",
        explanation="This raw statement establishes the numerical projection.",
        supporting_values={"extracted_deficit_percentage": 3.5},
        source_reference=source_ref
    )
    
    result = ExplainableResult(
        result_type="BudgetAnomalyDetection",
        summary="The reported deficit exceeds typical bounds by a slight margin.",
        explanation="Historically, deficit projections hover around 3.0%. A 3.5% projection suggests increased capital outlay or revenue shortfall.",
        numerical_indicators={"historical_average": 3.0, "current_projection": 3.5, "deviation": 0.5},
        model_output={"anomaly_score": 0.65},
        confidence=0.88,
        evidence=[evidence],
        source_references=[source_ref],
        limitations=["Only considers current year projections, excluding revised estimates."]
    )
    
    # Assertions
    assert result.result_type == "BudgetAnomalyDetection"
    assert "deviation" in result.numerical_indicators
    assert result.confidence == 0.88
    assert len(result.evidence) == 1
    assert result.evidence[0].supporting_values["extracted_deficit_percentage"] == 3.5
    assert result.limitations[0].startswith("Only considers")
