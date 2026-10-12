"""
Phase 9.2 — Cross-Phase Entity Registry & Identity Resolution Tests.
=====================================================================

Validates:
1. Name normalization & transliteration across Tamil and English.
2. Resolution of spelling variations (e.g. 'M. K. Stalin' vs 'MK Stalin' vs 'M.K.Stalin').
3. Bilingual alias lookup ('சென்னை' vs 'Chennai', 'மு.க. ஸ்டாலின்' vs 'M. K. Stalin').
4. Renamed entities and time-bounded validity ('Madras' -> 'Chennai' in 1996).
5. False match prevention:
   - Distinct politicians with similar names (e.g. R. Murugesan vs K. Murugesan).
   - Homonymous locations in different districts (e.g. Anna Nagar in Chennai vs Madurai).
6. Duplicate candidate detection with explicit divergence reasons (never auto-merged).
7. Entity merge operation with audit history and source mapping preservation.
8. Entity split operation with audit history.
9. Preservation of original source names across mappings.
10. Entity lookup REST API integration.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base_class import Base
from backend.models.entity_registry import (
    CanonicalEntity,
    SourceIdentifierMapping,
    EntityAlias,
    EntityAuditRecord,
    DuplicateCandidateReview,
    RegistryEntityType,
    EntityLifecycleStatus,
    ResolutionMethod,
    ReviewStatusEnum,
    AliasTypeEnum,
    DuplicateReviewStatus,
)
from backend.services.entity_resolution_service import EntityResolutionService
from backend.api.app import create_app


@pytest.fixture
def db_session():
    """In-memory SQLite database session for unit tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def resolution_service(db_session):
    return EntityResolutionService(db_session)


@pytest.fixture
def seeded_service(db_session):
    """Seeds test entities across representatives, places, schemes, and departments."""
    service = EntityResolutionService(db_session)

    # 1. Representative: M. K. Stalin
    stalin = service.register_canonical_entity(
        entity_id="ENT:REP:MK-STALIN",
        entity_type=RegistryEntityType.REPRESENTATIVE,
        name_en="M. K. Stalin",
        name_ta="மு.க. ஸ்டாலின்",
        category_or_subtype="MLA",
        metadata={"district": "Chennai", "constituency_code": "AC-013", "party_code": "DMK"},
        is_test_fixture=True,
    )
    service.add_alias(stalin.entity_id, "MK Stalin", language="en", alias_type=AliasTypeEnum.SPELLING_VARIANT)
    service.add_alias(stalin.entity_id, "M.K.Stalin", language="en", alias_type=AliasTypeEnum.SPELLING_VARIANT)
    service.add_alias(stalin.entity_id, "மு.க. ஸ்டாலின்", language="ta", alias_type=AliasTypeEnum.TRANSLITERATION)
    service.add_source_mapping(
        entity_id=stalin.entity_id,
        source_system="TN_ASSEMBLY",
        source_record_id="MLA-2021-013",
        source_record_name="Thiru M.K. Stalin (Chief Minister)",
    )

    # 2. Location with historical renaming: Chennai / Madras
    chennai = service.register_canonical_entity(
        entity_id="ENT:AREA:CHENNAI",
        entity_type=RegistryEntityType.ADMINISTRATIVE_AREA,
        name_en="Chennai",
        name_ta="சென்னை",
        category_or_subtype="DISTRICT",
        metadata={"district": "Chennai"},
        is_test_fixture=True,
    )
    service.add_alias(
        entity_id=chennai.entity_id,
        alias_name="Madras",
        language="en",
        alias_type=AliasTypeEnum.HISTORICAL_NAME,
        valid_from="1639",
        valid_to="1996-07-17",
    )
    service.add_alias(
        entity_id=chennai.entity_id,
        alias_name="மதராஸ்",
        language="ta",
        alias_type=AliasTypeEnum.HISTORICAL_NAME,
        valid_from="1639",
        valid_to="1996-07-17",
    )

    # 3. Homonymous Locations: Anna Nagar in Chennai vs Anna Nagar in Madurai
    service.register_canonical_entity(
        entity_id="ENT:AREA:ANNA_NAGAR_CHN",
        entity_type=RegistryEntityType.ADMINISTRATIVE_AREA,
        name_en="Anna Nagar",
        name_ta="அண்ணா நகர்",
        category_or_subtype="ZONE",
        metadata={"district": "Chennai", "zone_code": "GCC-Z08"},
        is_test_fixture=True,
    )
    service.register_canonical_entity(
        entity_id="ENT:AREA:ANNA_NAGAR_MDU",
        entity_type=RegistryEntityType.ADMINISTRATIVE_AREA,
        name_en="Anna Nagar",
        name_ta="அண்ணா நகர்",
        category_or_subtype="LOCALITY",
        metadata={"district": "Madurai"},
        is_test_fixture=True,
    )

    # 4. Distinct Politicians with Similar Names (Murugesan)
    service.register_canonical_entity(
        entity_id="ENT:REP:MURUGESAN_R",
        entity_type=RegistryEntityType.REPRESENTATIVE,
        name_en="R. Murugesan",
        name_ta="ஆர். முருகேசன்",
        metadata={"district": "Salem", "constituency_code": "AC-088", "party_code": "DMK"},
        is_test_fixture=True,
    )
    service.register_canonical_entity(
        entity_id="ENT:REP:MURUGESAN_K",
        entity_type=RegistryEntityType.REPRESENTATIVE,
        name_en="K. Murugesan",
        name_ta="கே. முருகேசன்",
        metadata={"district": "Coimbatore", "constituency_code": "AC-118", "party_code": "AIADMK"},
        is_test_fixture=True,
    )

    # 5. Department: MAWS
    maws = service.register_canonical_entity(
        entity_id="ENT:DEPT:MAWS-034",
        entity_type=RegistryEntityType.GOVERNMENT_DEPARTMENT,
        name_en="Municipal Administration and Water Supply Department",
        name_ta="நகராட்சி நிர்வாகம் மற்றும் குடிநீர் வழங்கல் துறை",
        metadata={"demand_code": "34"},
        is_test_fixture=True,
    )
    service.add_alias(maws.entity_id, "MAWS", alias_type=AliasTypeEnum.ACRONYM)
    service.add_source_mapping(
        entity_id=maws.entity_id,
        source_system="TN_BUDGET_DDG",
        source_record_id="DEMAND_34",
        source_record_name="DEMAND 34 - MUNICIPAL ADMINISTRATION AND WATER SUPPLY DEPARTMENT",
    )

    return service


def test_1_normalization_and_spelling_variations(seeded_service):
    """Verify that spelling variants with initials and honorifics resolve to the canonical representative."""
    test_queries = [
        "M. K. Stalin",
        "MK Stalin",
        "M.K.Stalin",
        "Thiru M.K. Stalin",
        "Hon'ble M. K. Stalin",
        "m k stalin",
    ]
    for query in test_queries:
        res = seeded_service.resolve_entity(query)
        assert res["resolved"] is True, f"Failed for query '{query}'"
        assert res["entity"]["entity_id"] == "ENT:REP:MK-STALIN"
        assert res["entity"]["canonical_name_en"] == "M. K. Stalin"


def test_2_tamil_transliteration_and_aliases(seeded_service):
    """Verify bilingual resolution of Tamil names and transliterated queries."""
    res_ta = seeded_service.resolve_entity("மு.க. ஸ்டாலின்")
    assert res_ta["resolved"] is True
    assert res_ta["entity"]["entity_id"] == "ENT:REP:MK-STALIN"

    # Department acronym and Tamil name
    res_acronym = seeded_service.resolve_entity("MAWS")
    assert res_acronym["resolved"] is True
    assert res_acronym["entity"]["entity_id"] == "ENT:DEPT:MAWS-034"

    res_dept_ta = seeded_service.resolve_entity("நகராட்சி நிர்வாகம் மற்றும் குடிநீர் வழங்கல்")
    assert res_dept_ta["resolved"] is True
    assert res_dept_ta["entity"]["entity_id"] == "ENT:DEPT:MAWS-034"


def test_3_historical_name_lookups(seeded_service):
    """Verify time-bounded resolution of historical place names (Madras -> Chennai)."""
    # Query historical name 'Madras'
    res = seeded_service.resolve_entity("Madras", context={"year": "1990"})
    assert res["resolved"] is True
    assert res["entity"]["entity_id"] == "ENT:AREA:CHENNAI"
    assert res["is_historical"] is True
    assert res["matching_method"] == ResolutionMethod.HISTORICAL_NAME_MATCH.value

    # Query Tamil historical name 'மதராஸ்'
    res_ta = seeded_service.resolve_entity("மதராஸ்")
    assert res_ta["resolved"] is True
    assert res_ta["entity"]["entity_id"] == "ENT:AREA:CHENNAI"


def test_4_homonym_disambiguation_safeguard(seeded_service):
    """
    Verify that querying a homonym without context returns AMBIGUOUS_HOMONYM
    and does NOT arbitrarily merge distinct real-world places.
    """
    # Querying 'Anna Nagar' without district context must be ambiguous
    res_ambiguous = seeded_service.resolve_entity("Anna Nagar")
    assert res_ambiguous["resolved"] is False
    assert res_ambiguous["status"] == "AMBIGUOUS_HOMONYM"
    assert len(res_ambiguous["candidates"]) == 2

    # Querying 'Anna Nagar' with district 'Chennai' resolves specifically to Chennai zone
    res_chennai = seeded_service.resolve_entity("Anna Nagar", context={"district": "Chennai"})
    assert res_chennai["resolved"] is True
    assert res_chennai["entity"]["entity_id"] == "ENT:AREA:ANNA_NAGAR_CHN"

    # Querying 'Anna Nagar' with district 'Madurai' resolves specifically to Madurai locality
    res_madurai = seeded_service.resolve_entity("Anna Nagar", context={"district": "Madurai"})
    assert res_madurai["resolved"] is True
    assert res_madurai["entity"]["entity_id"] == "ENT:AREA:ANNA_NAGAR_MDU"


def test_5_distinct_politicians_not_merged(seeded_service):
    """
    Verify that politicians with similar names ('R. Murugesan' vs 'K. Murugesan')
    are never merged, and duplicate detection flags divergence reasons.
    """
    res_r = seeded_service.resolve_entity("R. Murugesan")
    assert res_r["resolved"] is True
    assert res_r["entity"]["entity_id"] == "ENT:REP:MURUGESAN_R"

    res_k = seeded_service.resolve_entity("K. Murugesan")
    assert res_k["resolved"] is True
    assert res_k["entity"]["entity_id"] == "ENT:REP:MURUGESAN_K"

    # Ensure duplicate candidate scanner identifies divergence reasons
    candidates = seeded_service.detect_duplicate_candidates(
        entity_type=RegistryEntityType.REPRESENTATIVE,
        similarity_threshold=0.75,
    )
    assert len(candidates) >= 1
    pair = candidates[0]
    assert any("DIFFERENT_DISTRICT" in r for r in pair["divergence_reasons"])
    assert any("DIFFERENT_PARTY" in r for r in pair["divergence_reasons"])
    assert pair["review_status"] == DuplicateReviewStatus.PENDING_REVIEW.value


def test_6_preservation_of_original_source_names(seeded_service, db_session):
    """Verify that original verbatim source names are preserved uncorrupted."""
    mapping = (
        db_session.query(SourceIdentifierMapping)
        .filter_by(source_system="TN_ASSEMBLY", source_record_id="MLA-2021-013")
        .first()
    )
    assert mapping is not None
    # Verbatim reported text must be preserved exactly
    assert mapping.source_record_name == "Thiru M.K. Stalin (Chief Minister)"
    assert mapping.entity_id == "ENT:REP:MK-STALIN"

    # Deterministic lookup by source ID
    res = seeded_service.resolve_entity(
        query_name="",
        source_system="TN_ASSEMBLY",
        source_record_id="MLA-2021-013",
    )
    assert res["resolved"] is True
    assert res["entity"]["entity_id"] == "ENT:REP:MK-STALIN"


def test_7_entity_merge_with_audit_history(seeded_service, db_session):
    """Verify merge of duplicate entities re-points mappings and records audit trail."""
    # Register duplicate scheme
    dup_scheme = seeded_service.register_canonical_entity(
        entity_id="ENT:SCHEME:TEMP_BREAKFAST",
        entity_type=RegistryEntityType.SCHEME,
        name_en="CM Morning Meal Scheme",
        is_test_fixture=True,
    )
    canonical_scheme = seeded_service.register_canonical_entity(
        entity_id="ENT:SCHEME:CM_BREAKFAST",
        entity_type=RegistryEntityType.SCHEME,
        name_en="Chief Minister's Breakfast Scheme",
        is_test_fixture=True,
    )
    seeded_service.add_source_mapping(
        entity_id=dup_scheme.entity_id,
        source_system="PORTAL_TEMP",
        source_record_id="TMP-001",
        source_record_name="Morning Meal Initiative",
    )

    # Perform Merge
    merge_res = seeded_service.merge_entities(
        primary_entity_id=canonical_scheme.entity_id,
        secondary_entity_id=dup_scheme.entity_id,
        rationale="Consolidating duplicate scheme entries following departmental G.O. verification",
        performed_by="CIVIC_AUDITOR_TEST",
    )
    assert merge_res["status"] == "MERGED"

    # Verify secondary entity is marked MERGED
    db_secondary = db_session.query(CanonicalEntity).filter_by(entity_id=dup_scheme.entity_id).first()
    assert db_secondary.status == EntityLifecycleStatus.MERGED
    assert db_secondary.merged_into_id == canonical_scheme.entity_id

    # Verify mapping was reassigned
    mapping = db_session.query(SourceIdentifierMapping).filter_by(source_record_id="TMP-001").first()
    assert mapping.entity_id == canonical_scheme.entity_id

    # Verify audit record
    audit = db_session.query(EntityAuditRecord).filter_by(audit_id=merge_res["audit_id"]).first()
    assert audit is not None
    assert audit.operation_type.value == "MERGE"
    assert audit.performed_by == "CIVIC_AUDITOR_TEST"

    # Resolving the old ID should automatically redirect to primary
    res_redirect = seeded_service.resolve_entity(dup_scheme.entity_id)
    assert res_redirect["resolved"] is True
    assert res_redirect["entity"]["entity_id"] == canonical_scheme.entity_id


def test_8_entity_split_with_audit_history(seeded_service, db_session):
    """Verify entity split creates a distinct new entity and logs audit history."""
    combined_dept = seeded_service.register_canonical_entity(
        entity_id="ENT:DEPT:COMBINED_HEALTH",
        entity_type=RegistryEntityType.GOVERNMENT_DEPARTMENT,
        name_en="Department of Health and Family Welfare",
        is_test_fixture=True,
    )
    m1 = seeded_service.add_source_mapping(
        entity_id=combined_dept.entity_id,
        source_system="SYS_A",
        source_record_id="HFW-01",
        source_record_name="Health Directorate",
    )
    m2 = seeded_service.add_source_mapping(
        entity_id=combined_dept.entity_id,
        source_system="SYS_B",
        source_record_id="MED-02",
        source_record_name="Medical Education Directorate",
    )

    split_res = seeded_service.split_entity(
        original_entity_id=combined_dept.entity_id,
        new_entity_data={
            "entity_id": "ENT:DEPT:DIRECTORATE_MED_EDU",
            "entity_type": "government_department",
            "canonical_name_en": "Directorate of Medical Education and Research",
        },
        split_mapping_ids=[m2.mapping_id],
        rationale="Splitting Directorate of Medical Education from administrative Secretariat department",
        performed_by="CIVIC_AUDITOR_TEST",
    )
    assert split_res["status"] == "SPLIT"

    # Verify mapping migration
    db_m2 = db_session.query(SourceIdentifierMapping).filter_by(mapping_id=m2.mapping_id).first()
    assert db_m2.entity_id == "ENT:DEPT:DIRECTORATE_MED_EDU"

    db_m1 = db_session.query(SourceIdentifierMapping).filter_by(mapping_id=m1.mapping_id).first()
    assert db_m1.entity_id == combined_dept.entity_id

    # Verify split audit record
    audit = db_session.query(EntityAuditRecord).filter_by(audit_id=split_res["audit_id"]).first()
    assert audit.operation_type.value == "SPLIT"


def test_9_api_lookup_and_history_endpoints(seeded_service, monkeypatch):
    """Verify Flask REST API endpoints for entity lookup, profile, and history."""
    TestingSessionLocal = sessionmaker(bind=seeded_service.db.bind)

    import backend.database.session
    import backend.api.entities
    monkeypatch.setattr(backend.database.session, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(backend.api.entities, "SessionLocal", TestingSessionLocal)

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    # 1. Test lookup endpoint for representative
    resp = client.get("/api/entities/lookup?name=M.K.+Stalin")
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert json_data["status"] == "success"
    assert json_data["data"]["resolved"] is True
    assert json_data["data"]["entity"]["entity_id"] == "ENT:REP:MK-STALIN"

    # 2. Test lookup with missing params
    err_resp = client.get("/api/entities/lookup")
    assert err_resp.status_code == 400

    # 3. Test profile endpoint
    prof_resp = client.get("/api/entities/ENT:REP:MK-STALIN")
    assert prof_resp.status_code == 200
    assert prof_resp.get_json()["data"]["entity_id"] == "ENT:REP:MK-STALIN"

    # 4. Test duplicates scanning endpoint
    dup_resp = client.get("/api/entities/duplicates")
    assert dup_resp.status_code == 200
    assert "candidates" in dup_resp.get_json()["data"]

