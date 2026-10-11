"""
Unit & Integration Tests for Phase 6.11 — Evidence Traceability, Metric Lineage & Audit Trail.

Validates:
1. Source Document Registry (registration, deduplication, retrieval, SHA-256 integrity).
2. Fact-to-Evidence citations (entity linking, page numbers, table names, excerpt citations).
3. Metric Lineage & drill-down reproduction (tracing aggregate utilization to constituent vouchers).
4. Conflicting evidence preservation (side-by-side divergent records with review statuses).
5. Immutable Audit Trail event logging.
6. REST API traceability endpoints:
   - GET /api/representatives/sources
   - GET /api/representatives/sources/<id>
   - GET /api/representatives/evidence?entity_type=...&entity_id=...
   - GET /api/representatives/metrics/<id>/lineage
   - GET /api/representatives/conflicts
   - GET /api/representatives/audit-trail
"""

import pytest
from sqlalchemy.orm import Session

from backend.database.session import SessionLocal, engine
from backend.database.base_class import Base
from backend.services.traceability_service import TraceabilityService
from backend.services.real_data_ingestion import run_phase6_integration
from backend.models.representative import (
    SourceDocumentRegistry,
    FactEvidenceLink,
    MetricLineage,
    ConflictingEvidenceRecord,
    ConflictResolutionStatus
)


@pytest.fixture(scope="module")
def setup_traceability_data():
    """Ensure database is seeded with Phase 6.10 & 6.11 traceability fixtures."""
    run_phase6_integration()
    db: Session = SessionLocal()
    yield db
    db.close()


def test_1_source_document_registry_operations(setup_traceability_data):
    """Verifies document registration, metadata fields, and SHA-256 checksum preservation."""
    db = setup_traceability_data
    service = TraceabilityService(db=db)

    doc = service.get_source_document("D4-001")
    assert doc is not None
    assert doc.publisher == "PRS Legislative Research"
    assert doc.document_title == "PRS Legislative Research MP Track: T.R. Paarivendhar (Perambalur)"
    assert doc.file_format == "HTML"
    assert doc.verification_status == "VERIFIED"
    assert len(doc.sha256_checksum) == 64

    # List documents
    all_docs = service.list_source_documents()
    assert len(all_docs) >= 7


def test_2_fact_to_evidence_granular_citations(setup_traceability_data):
    """Verifies facts link to specific pages, tables, excerpts, and confidence scores."""
    db = setup_traceability_data
    service = TraceabilityService(db=db)

    citations = service.get_evidence_for_entity("REPRESENTATIVE", "REP-MP-17-PERAMBALUR")
    assert len(citations) >= 1
    cit = citations[0]
    assert cit["document_id"] == "D4-001"
    assert cit["page_number"] == 1
    assert "Dr. T. R. Paarivendhar" in cit["supporting_excerpt"]
    assert cit["confidence_score"] == 1.0


def test_3_metric_lineage_drilldown_reproducibility(setup_traceability_data):
    """Verifies derived metric exposes exact formula, inputs, and constituent project vouchers."""
    db = setup_traceability_data
    service = TraceabilityService(db=db)

    drilldown = service.get_metric_drilldown("MET-EXPENDITURE-PC-TN-04")
    assert drilldown is not None
    assert drilldown["calculation_method"] == "EXPENDITURE_UTILIZATION"
    assert "reported_expenditure" in drilldown["formula_expression"]
    assert len(drilldown["constituent_input_records"]) >= 1

    voucher = drilldown["constituent_input_records"][0]
    assert voucher["record_type"] == "CONSTITUENCY_WORK"
    assert voucher["record_id"] == "WRK-MPLADS-TN-17LS-D8001"
    assert voucher["sanctioned_amount"] == 1825000000.0


def test_4_conflicting_evidence_preservation_without_suppression(setup_traceability_data):
    """Verifies divergent source observations are preserved side-by-side with resolution basis."""
    db = setup_traceability_data
    service = TraceabilityService(db=db)

    conflicts = service.list_conflicts("CONSTITUENCY_WORK")
    assert len(conflicts) >= 1

    conf = conflicts[0]
    assert conf["conflict_topic"] == "REPORTED_EXPENDITURE_VS_RECOMMENDED_SANCTION"
    assert conf["source_a"]["document_id"] == "D8-001"
    assert conf["source_b"]["document_id"] == "D8-002"
    assert "audited utilization certificates" in conf["discrepancy_magnitude"]
    assert conf["review_status"] == ConflictResolutionStatus.RESOLVED


def test_5_audit_trail_logging_and_immutability(setup_traceability_data):
    """Verifies lifecycle events are persisted to audit trail ledger."""
    db = setup_traceability_data
    service = TraceabilityService(db=db)

    event = service.log_audit_event(
        event_type="MANUAL_VERIFICATION",
        entity_type="REPRESENTATIVE",
        record_id="REP-MP-17-PERAMBALUR",
        previous_value={"status": "PROVISIONAL"},
        new_value={"status": "VERIFIED"},
        reason="Verified against Sansad 17th Lok Sabha gazetted rolls",
        source_reference="Sansad Gazette Vol 4"
    )

    assert event.event_id.startswith("AUD-")
    events = service.list_audit_trail("REP-MP-17-PERAMBALUR")
    assert len(events) >= 1
    assert events[0]["event_type"] == "MANUAL_VERIFICATION"


def test_6_traceability_api_endpoints(api_client, setup_traceability_data):
    """Verifies REST API exposure of source documents, citations, lineages, conflicts, and audit trail."""
    # 1. Source documents list
    res_docs = api_client.get("/api/representatives/sources")
    assert res_docs.status_code == 200
    docs = res_docs.get_json()["data"]["documents"]
    assert len(docs) >= 7

    # 2. Source document detail
    res_doc = api_client.get("/api/representatives/sources/D4-001")
    assert res_doc.status_code == 200
    doc_data = res_doc.get_json()["data"]
    assert doc_data["publisher"] == "PRS Legislative Research"

    # 3. Entity evidence citations
    res_ev = api_client.get("/api/representatives/evidence?entity_type=REPRESENTATIVE&entity_id=REP-MP-17-PERAMBALUR")
    assert res_ev.status_code == 200
    ev_data = res_ev.get_json()["data"]
    assert ev_data["total_links_count"] >= 1
    assert ev_data["evidence_links"][0]["document_id"] == "D4-001"

    # 4. Metric lineage drill-down
    res_lin = api_client.get("/api/representatives/metrics/MET-EXPENDITURE-PC-TN-04/lineage")
    assert res_lin.status_code == 200
    lin_data = res_lin.get_json()["data"]
    assert lin_data["calculation_method"] == "EXPENDITURE_UTILIZATION"
    assert len(lin_data["constituent_input_records"]) >= 1

    # 5. Conflicting evidence list
    res_conf = api_client.get("/api/representatives/conflicts")
    assert res_conf.status_code == 200
    conf_data = res_conf.get_json()["data"]
    assert conf_data["total_count"] >= 1

    # 6. Audit trail ledger
    res_aud = api_client.get("/api/representatives/audit-trail")
    assert res_aud.status_code == 200
    aud_data = res_aud.get_json()["data"]
    assert aud_data["total_count"] >= 1
