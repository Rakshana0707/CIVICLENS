"""
Phase 7 — Political Claim Verification REST API Router.

Endpoints:
- GET  /api/claims/                     List and search claims with category/verdict/party filters
- GET  /api/claims/<claim_id>           Full claim profile, decomposed subjects, evidence, results
- POST /api/claims/                     Register a new claim (immutable original text preserved)
- POST /api/claims/<claim_id>/version   Add edited transcription or transliteration version
- POST /api/claims/<claim_id>/decompose Decompose claim into atomic subjects/entities
- POST /api/claims/<claim_id>/evidence  Link evidence passage with support/contradiction score
- POST /api/claims/<claim_id>/verify    Execute automated verification run and generate verdict
- POST /api/claims/<claim_id>/review    Submit human expert review decision or override
- GET  /api/claims/<claim_id>/audit-trail Provenance, history, and verification audit log
- GET  /api/claims/stats                Aggregate statistics across categories and verdicts
"""

from datetime import datetime, timezone
from flask import Blueprint, request
from sqlalchemy import desc

from backend.api.responses import success_response, error_response
from backend.database.session import SessionLocal
from backend.models.claim import (
    Claim,
    ClaimCategory,
    ClaimStatus,
    VerificationVerdict,
    EvidenceRelationshipType,
    ReviewStatus,
    SubjectType,
    AttributionType,
    CandidateSourceType,
    VerificationResult
)
from backend.services.claim_verification import ClaimVerificationService
from backend.services.claim_ingestion import ClaimIngestionService

claims_bp = Blueprint("claims", __name__, url_prefix="/claims")


@claims_bp.route("/", methods=["GET"])
def list_claims():
    """
    List registered claims with optional filtering by category, verdict, party, or keyword search.
    """
    category_param = request.args.get("category")
    status_param = request.args.get("status")
    party_param = request.args.get("party")
    speaker_param = request.args.get("speaker")
    search_query = request.args.get("q")
    skip = request.args.get("skip", default=0, type=int)
    limit = request.args.get("limit", default=50, type=int)

    db = SessionLocal()
    try:
        query = db.query(Claim)
        if category_param:
            try:
                cat_enum = ClaimCategory(category_param)
                query = query.filter(Claim.claim_category == cat_enum)
            except ValueError:
                return error_response(f"Invalid category: {category_param}", status_code=400)

        if status_param:
            try:
                st_enum = ClaimStatus(status_param)
                query = query.filter(Claim.status == st_enum)
            except ValueError:
                return error_response(f"Invalid status: {status_param}", status_code=400)

        if party_param:
            query = query.filter(Claim.speaker_party == party_param)

        if speaker_param:
            query = query.filter(Claim.speaker_name.ilike(f"%{speaker_param}%"))

        if search_query:
            query = query.filter(Claim.original_text.ilike(f"%{search_query}%"))

        total = query.count()
        claims = query.order_by(desc(Claim.created_at)).offset(skip).limit(limit).all()

        results = []
        for c in claims:
            current_res = next((r for r in c.verification_results if r.is_current), None)
            results.append({
                "claim_id": c.claim_id,
                "original_text": c.original_text,
                "language": c.language,
                "claim_category": c.claim_category.value,
                "speaker_name": c.speaker_name,
                "speaker_party": c.speaker_party,
                "claim_date": c.claim_date.isoformat() if c.claim_date else None,
                "status": c.status.value,
                "verdict": current_res.verdict.value if current_res else None,
                "confidence_score": current_res.confidence_score if current_res else None
            })

        return success_response(
            data={"total": total, "claims": results, "skip": skip, "limit": limit},
            message="Claims retrieved successfully"
        )
    finally:
        db.close()


@claims_bp.route("/<string:claim_id>", methods=["GET"])
def get_claim(claim_id: str):
    """
    Get full profile for a specific claim including versions, evidence, results, and reviews.
    """
    db = SessionLocal()
    try:
        service = ClaimVerificationService(db=db)
        profile = service.get_claim_profile(claim_id)
        if not profile:
            return error_response(f"Claim '{claim_id}' not found", status_code=404)
        return success_response(data=profile, message="Claim profile retrieved")
    finally:
        db.close()


@claims_bp.route("/", methods=["POST"])
def register_claim():
    """
    Register a new political claim with immutable original text preservation.
    """
    payload = request.get_json(silent=True) or {}
    claim_id = payload.get("claim_id")
    original_text = payload.get("original_text")
    category_str = payload.get("claim_category")

    if not claim_id or not original_text or not category_str:
        return error_response("claim_id, original_text, and claim_category are required", status_code=400)

    try:
        category_enum = ClaimCategory(category_str)
    except ValueError:
        return error_response(f"Invalid claim_category: {category_str}", status_code=400)

    db = SessionLocal()
    try:
        service = ClaimVerificationService(db=db)
        claim = service.register_claim(
            claim_id=claim_id,
            original_text=original_text,
            claim_category=category_enum,
            speaker_name=payload.get("speaker_name"),
            speaker_party=payload.get("speaker_party"),
            context_text=payload.get("context_text"),
            language=payload.get("language", "ta"),
            temporal_scope=payload.get("temporal_scope"),
            geographic_scope=payload.get("geographic_scope", "Tamil Nadu"),
            source_id=payload.get("source_id"),
            is_test_fixture=payload.get("is_test_fixture", False),
            metadata_json=payload.get("metadata_json")
        )
        return success_response(
            data={"claim_id": claim.claim_id, "status": claim.status.value},
            message="Claim registered successfully",
            status_code=201
        )
    except ValueError as e:
        return error_response(str(e), status_code=400)
    finally:
        db.close()


@claims_bp.route("/ingest", methods=["POST"])
def ingest_claim():
    """
    Ingest a candidate claim through the multi-channel ingestion pipeline.
    Applies deduplication, attribution classification, and non-inference checks.
    """
    payload = request.get_json(silent=True) or {}
    claim_id = payload.get("claim_id")
    original_text = payload.get("original_text")
    category_str = payload.get("claim_category")
    source_type_str = payload.get("candidate_source_type", "PUBLIC_SPEECH")
    attr_type_str = payload.get("attribution_type", "DIRECT_QUOTE")

    if not claim_id or not original_text or not category_str:
        return error_response("claim_id, original_text, and claim_category are required", status_code=400)

    try:
        category_enum = ClaimCategory(category_str)
        source_type_enum = CandidateSourceType(source_type_str)
        attr_type_enum = AttributionType(attr_type_str)
    except ValueError as e:
        return error_response(f"Invalid enum parameter: {str(e)}", status_code=400)

    # Parse optional dates
    claim_date = None
    if payload.get("claim_date"):
        try:
            claim_date = datetime.fromisoformat(payload["claim_date"])
        except ValueError:
            return error_response("Invalid ISO format for claim_date", status_code=400)

    publication_date = None
    if payload.get("publication_date"):
        try:
            publication_date = datetime.fromisoformat(payload["publication_date"])
        except ValueError:
            return error_response("Invalid ISO format for publication_date", status_code=400)

    db = SessionLocal()
    try:
        service = ClaimIngestionService(db=db)
        result = service.ingest_claim(
            claim_id=claim_id,
            original_text=original_text,
            claim_category=category_enum,
            candidate_source_type=source_type_enum,
            attribution_type=attr_type_enum,
            language=payload.get("language", "ta"),
            speaker_name=payload.get("speaker_name"),
            speaker_role=payload.get("speaker_role"),
            party=payload.get("party"),
            claim_date=claim_date,
            publication_date=publication_date,
            claim_source_url=payload.get("claim_source_url"),
            source_document_id=payload.get("source_document_id"),
            geographic_scope=payload.get("geographic_scope", "Tamil Nadu"),
            extraction_method=payload.get("extraction_method", "MANUAL"),
            context_text=payload.get("context_text"),
            temporal_scope=payload.get("temporal_scope"),
            is_correction_for_claim_id=payload.get("is_correction_for_claim_id"),
            correction_rationale=payload.get("correction_rationale"),
            transliteration=payload.get("transliteration"),
            is_test_fixture=payload.get("is_test_fixture", False),
            metadata_json=payload.get("metadata_json")
        )
        return success_response(data=result, message=f"Ingestion completed with status: {result.get('status')}")
    except ValueError as e:
        return error_response(str(e), status_code=400)
    finally:
        db.close()


@claims_bp.route("/check-duplicate", methods=["POST"])
def check_duplicate():
    """
    Pre-check whether a claim candidate matches existing records.
    """
    payload = request.get_json(silent=True) or {}
    text = payload.get("original_text")
    if not text:
        return error_response("original_text is required", status_code=400)

    claim_date = None
    if payload.get("claim_date"):
        try:
            claim_date = datetime.fromisoformat(payload["claim_date"])
        except ValueError:
            return error_response("Invalid ISO format for claim_date", status_code=400)

    db = SessionLocal()
    try:
        service = ClaimIngestionService(db=db)
        dup_info = service.check_duplicate(
            original_text=text,
            speaker_name=payload.get("speaker_name"),
            claim_date=claim_date,
            language=payload.get("language", "ta")
        )
        return success_response(data=dup_info, message="Duplicate check completed")
    finally:
        db.close()


@claims_bp.route("/<string:claim_id>/version", methods=["POST"])
def add_claim_version(claim_id: str):
    """
    Store a new claim version for corrections or additional context without overwriting original wording.
    """
    payload = request.get_json(silent=True) or {}
    edited_text = payload.get("edited_text")
    rationale = payload.get("change_rationale")

    if not edited_text or not rationale:
        return error_response("edited_text and change_rationale are required", status_code=400)

    db = SessionLocal()
    try:
        service = ClaimVerificationService(db=db)
        version = service.add_claim_version(
            claim_id=claim_id,
            edited_text=edited_text,
            change_rationale=rationale,
            transliterated_text=payload.get("transliterated_text"),
            additional_context=payload.get("additional_context"),
            edited_by=payload.get("edited_by", "expert_reviewer")
        )
        return success_response(
            data={"claim_id": claim_id, "version_number": version.version_number},
            message=f"Added version {version.version_number}"
        )
    except ValueError as e:
        return error_response(str(e), status_code=404)
    finally:
        db.close()


@claims_bp.route("/nlp-process", methods=["POST"])
def nlp_process_text():
    """
    Direct multilingual claim processing pipeline:
    Language detection, normalization, verifiability classification, entity extraction,
    quantitative extraction, and atomic proposition decomposition.
    """
    payload = request.get_json(silent=True) or {}
    text = payload.get("text")
    if not text or not text.strip():
        return error_response("'text' is required", status_code=400)

    from backend.nlp.claim_decomposition import MultilingualClaimPipeline
    pipeline = MultilingualClaimPipeline()
    result = pipeline.process_claim(
        claim_id=payload.get("claim_id", "TEMP-CLAIM"),
        original_text=text,
        geographic_scope=payload.get("geographic_scope", "Tamil Nadu"),
        persist_to_db=False
    )
    return success_response(data=result, message="Claim processed via Multilingual NLP Pipeline")


@claims_bp.route("/<string:claim_id>/decompose", methods=["POST"])
def decompose_claim(claim_id: str):
    """
    Decompose claim into atomic verifiable propositions or subjects/entities.
    Supports both automated multilingual NLP decomposition and manual subject submission.
    """
    payload = request.get_json(silent=True) or {}
    subjects_data = payload.get("subjects")

    db = SessionLocal()
    try:
        claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            return error_response(f"Claim '{claim_id}' not found", status_code=404)

        if isinstance(subjects_data, list):
            # Manual / Explicit Subject decomposition
            parsed_subjects = []
            for s in subjects_data:
                try:
                    stype = SubjectType(s.get("subject_type"))
                    parsed_subjects.append({
                        "subject_type": stype,
                        "canonical_name": s.get("canonical_name"),
                        "entity_id": s.get("entity_id"),
                        "confidence": s.get("confidence", 1.0)
                    })
                except ValueError:
                    return error_response(f"Invalid subject_type: {s.get('subject_type')}", status_code=400)

            service = ClaimVerificationService(db=db)
            created = service.decompose_claim(claim_id, parsed_subjects)
            return success_response(
                data={"claim_id": claim_id, "subjects_count": len(created)},
                message="Claim decomposed into subjects successfully"
            )
        else:
            # Automated Multilingual NLP Decomposition
            from backend.nlp.claim_decomposition import MultilingualClaimPipeline
            pipeline = MultilingualClaimPipeline(db=db)
            result = pipeline.process_claim(
                claim_id=claim_id,
                original_text=claim.original_text,
                geographic_scope=claim.geographic_scope,
                persist_to_db=True
            )
            claim.status = ClaimStatus.DECOMPOSED
            db.commit()
            return success_response(
                data=result,
                message="Claim decomposed into atomic verifiable propositions via Multilingual NLP"
            )
    finally:
        db.close()


@claims_bp.route("/<string:claim_id>/verify", methods=["POST"])
def verify_claim(claim_id: str):
    """
    Run automated verification pass against linked evidence using ClaimVerificationEngine.
    Synthesizes outcome, multi-part proposition explanation, source diversity, and confidence.
    """
    payload = request.get_json(silent=True) or {}
    engine_ver = payload.get("engine_version", "v1.0-deterministic")

    db = SessionLocal()
    try:
        from backend.services.claim_verification_engine import ClaimVerificationEngine
        engine = ClaimVerificationEngine(db=db)
        res = engine.verify_claim(claim_id=claim_id, engine_version=engine_ver)
        return success_response(
            data=res.to_dict(),
            message="Verification executed successfully"
        )
    except ValueError as e:
        return error_response(str(e), status_code=404)
    finally:
        db.close()


@claims_bp.route("/<string:claim_id>/review", methods=["POST"])
def review_claim(claim_id: str):
    """
    Submit human review decision or workflow action:
    - accept_assessment
    - correct_claim_decomposition
    - add_evidence
    - mark_evidence_irrelevant
    - revise_outcome
    Preserves automated baseline and audit history.
    """
    payload = request.get_json(silent=True) or {}
    reviewer_id = payload.get("reviewer_id")
    action = payload.get("action")
    review_notes = payload.get("review_notes", "")
    reviewed_outcome_str = payload.get("reviewed_outcome") or payload.get("reviewed_verdict")

    if not reviewer_id:
        return error_response("reviewer_id is required", status_code=400)

    db = SessionLocal()
    try:
        from backend.services.claim_verification_engine import ClaimVerificationEngine
        engine = ClaimVerificationEngine(db=db)

        if action == "accept_assessment":
            res = engine.accept_assessment(
                claim_id=claim_id,
                reviewer_id=reviewer_id,
                review_notes=review_notes or "Assessment validated by human reviewer."
            )
            return success_response(
                data=res.to_dict(),
                message="Assessment accepted successfully"
            )

        elif action == "correct_claim_decomposition":
            corrected = payload.get("corrected_atomics", [])
            res = engine.correct_claim_decomposition(
                claim_id=claim_id,
                reviewer_id=reviewer_id,
                corrected_atomics=corrected,
                review_notes=review_notes
            )
            return success_response(
                data=res.to_dict(),
                message="Claim decomposition corrected successfully"
            )

        elif action == "add_evidence":
            res = engine.add_evidence(
                claim_id=claim_id,
                reviewer_id=reviewer_id,
                document_data=payload.get("document_data", {}),
                passage_data=payload.get("passage_data", {}),
                relationship_type=payload.get("relationship_type", "supports"),
                review_notes=review_notes
            )
            return success_response(
                data=res.to_dict(),
                message="Evidence added successfully"
            )

        elif action == "mark_evidence_irrelevant":
            rel_id = payload.get("relationship_id")
            reason = payload.get("reason", review_notes)
            res = engine.mark_evidence_irrelevant(
                claim_id=claim_id,
                reviewer_id=reviewer_id,
                relationship_id=rel_id,
                reason=reason
            )
            return success_response(
                data=res.to_dict(),
                message="Evidence marked irrelevant successfully"
            )

        elif action == "revise_outcome" or reviewed_outcome_str:
            if not reviewed_outcome_str or not review_notes:
                return error_response("reviewed_outcome and review_notes are required for outcome revision", status_code=400)
            res = engine.revise_outcome(
                claim_id=claim_id,
                reviewer_id=reviewer_id,
                new_outcome=reviewed_outcome_str,
                explanation=payload.get("explanation", review_notes),
                review_notes=review_notes
            )
            return success_response(
                data=res.to_dict(),
                message="Outcome revised successfully"
            )

        else:
            return error_response(f"Unrecognized review action: '{action}'", status_code=400)

    except ValueError as e:
        return error_response(str(e), status_code=404)
    finally:
        db.close()


@claims_bp.route("/<string:claim_id>/verification", methods=["GET"])
def get_claim_verification(claim_id: str):
    """
    Get full current verification outcome, proposition breakdown, evidence references,
    source diversity metrics, and complete human review history.
    """
    db = SessionLocal()
    try:
        claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            return error_response(f"Claim '{claim_id}' not found", status_code=404)

        current_res = next((r for r in claim.verification_results if r.is_current), None)
        reviews = [r.to_dict() for r in claim.reviews]
        history = [h.to_dict() for h in claim.verification_history]

        return success_response(
            data={
                "claim_id": claim_id,
                "verification": current_res.to_dict() if current_res else None,
                "review_records": reviews,
                "verification_history": history,
                "epistemic_disclaimer": "Outcomes represent evidence assessments based on indexed public records, not personal intent."
            },
            message="Verification profile retrieved successfully"
        )
    finally:
        db.close()


@claims_bp.route("/stats", methods=["GET"])
def get_claim_stats():
    """
    Get aggregate summary statistics across categories, verdict distribution, and review statuses.
    Strictly forbids politician or party honesty rankings.
    """
    db = SessionLocal()
    try:
        total_claims = db.query(Claim).count()
        by_category = {}
        for cat in ClaimCategory:
            count = db.query(Claim).filter(Claim.claim_category == cat).count()
            by_category[cat.value] = count

        by_verdict = {}
        for v in VerificationVerdict:
            count = db.query(VerificationResult).filter(
                VerificationResult.verdict == v,
                VerificationResult.is_current == True
            ).count()
            by_verdict[v.value] = count

        return success_response(
            data={
                "total_claims": total_claims,
                "claims_by_category": by_category,
                "verdicts_distribution": by_verdict,
                "ranking_policy": "Automated politician or party truthfulness rankings are strictly prohibited."
            },
            message="Claim statistics retrieved successfully"
        )
    finally:
        db.close()


@claims_bp.route("/<string:claim_id>/retrieve-evidence", methods=["POST"])
def retrieve_evidence_for_claim(claim_id: str):
    """
    Search for documents and passages relevant to a claim using hybrid multi-signal retrieval:
    Keywords, exact phrases, entities, dates, statutory source authority, and semantic similarity.
    """
    payload = request.get_json(silent=True) or {}
    top_k = payload.get("top_k", 10)
    min_score = payload.get("min_score_threshold", 0.25)
    atomic_id = payload.get("atomic_claim_id")
    source_cats = payload.get("source_categories")

    db = SessionLocal()
    try:
        claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            return error_response(f"Claim '{claim_id}' not found", status_code=404)

        from backend.services.evidence_retrieval import EvidenceRetrievalEngine
        retriever = EvidenceRetrievalEngine(db=db)

        # If atomic_claim_id provided, look up specific atomic proposition
        query_text = claim.original_text
        subject = claim.speaker_name
        time_period = claim.temporal_scope
        aux_trans = None
        is_neg = False

        if atomic_id and claim.atomic_claims:
            matched_atomic = next((ac for ac in claim.atomic_claims if ac.atomic_claim_id == atomic_id), None)
            if matched_atomic:
                query_text = matched_atomic.atomic_claim_text
                subject = matched_atomic.subject
                time_period = matched_atomic.time_period
                aux_trans = matched_atomic.translation_text
                is_neg = matched_atomic.is_negated

        candidates = retriever.retrieve_candidate_evidence(
            claim_id=claim_id,
            query_text=query_text,
            atomic_claim_id=atomic_id,
            subject=subject,
            time_period=time_period,
            language=claim.language,
            auxiliary_translation=aux_trans,
            is_negated=is_neg,
            top_k=top_k,
            min_score_threshold=min_score,
            source_categories=source_cats,
            persist_candidates=True
        )

        return success_response(
            data={
                "claim_id": claim_id,
                "atomic_claim_id": atomic_id,
                "candidates_count": len(candidates),
                "candidates": candidates
            },
            message="Evidence retrieval completed successfully"
        )
    finally:
        db.close()


@claims_bp.route("/<claim_id>/analyze-evidence", methods=["POST"])
def analyze_claim_evidence_relationships(claim_id: str):
    """
    Analyzes the relationship between a claim and retrieved candidate evidence passages.
    Classifies each into: supports, contradicts, partially_supports, contextualizes,
    unrelated, or unclear. Records supporting/contradicting text references, alignment checks,
    and syndication clusters. Keeps contradictory evidence visible.
    """
    payload = request.get_json(silent=True) or {}
    atomic_id = payload.get("atomic_claim_id")

    db = SessionLocal()
    try:
        claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            return error_response(f"Claim '{claim_id}' not found", status_code=404)

        from backend.services.evidence_relationship_analyzer import EvidenceRelationshipAnalyzer
        analyzer = EvidenceRelationshipAnalyzer(db=db)
        relationships = analyzer.analyze_and_persist_relationships(
            claim_id=claim_id,
            atomic_claim_id=atomic_id
        )

        return success_response(
            data={
                "claim_id": claim_id,
                "atomic_claim_id": atomic_id,
                "relationships_count": len(relationships),
                "relationships": [r.to_dict() for r in relationships],
                "epistemic_disclaimer": "Contradictory evidence is retained and displayed alongside supporting findings. Absences of records do not prove falsehood."
            },
            message="Claim-evidence relationship analysis completed successfully"
        )
    finally:
        db.close()


@claims_bp.route("/<claim_id>/relationships", methods=["GET"])
def get_claim_evidence_relationships(claim_id: str):
    """
    Retrieves all established evidence relationships for a claim.
    Ensures contradictory evidence remains visible alongside supporting documents.
    """
    db = SessionLocal()
    try:
        claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            return error_response(f"Claim '{claim_id}' not found", status_code=404)

        rels = list(claim.evidence_relationships)
        return success_response(
            data={
                "claim_id": claim_id,
                "total_relationships": len(rels),
                "relationships": [r.to_dict() for r in rels],
                "epistemic_disclaimer": "Retains all supporting, partially supporting, and contradictory evidence without suppression."
            },
            message="Retrieved claim-evidence relationships successfully"
        )
    finally:
        db.close()


