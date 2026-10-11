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
from typing import Optional, Dict, Any, List
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
    VerificationResult,
    VerificationOutcome,
    AtomicClaim,
    ClaimSource,
    EvidenceDocument,
    EvidencePassage,
    ClaimEvidenceRelationship,
    ClaimCrossPhaseLink,
    SourceTier
)
from backend.services.claim_verification import ClaimVerificationService
from backend.services.claim_ingestion import ClaimIngestionService

claims_bp = Blueprint("claims", __name__, url_prefix="/claims")

AUTHORIZED_REVIEW_ROLES = {
    "LEAD_REVIEWER",
    "SENIOR_FACT_CHECKER",
    "DOMAIN_EXPERT",
    "AUDITOR",
    "RESEARCHER",
    "ADMIN"
}


def verify_reviewer_access(req, payload: Dict[str, Any]) -> Optional[str]:
    """
    Validates reviewer role from header X-Reviewer-Role or payload reviewer_role.
    Returns error string if unauthorized, None if authorized.
    """
    role = req.headers.get("X-Reviewer-Role") or payload.get("reviewer_role") or "DOMAIN_EXPERT"
    role_clean = role.strip().upper()
    if role_clean not in AUTHORIZED_REVIEW_ROLES:
        return f"Access Denied: Role '{role}' is not authorized to perform review operations. Authorized roles: {sorted(list(AUTHORIZED_REVIEW_ROLES))}"
    return None


def resolve_cross_phase_entities(db, claim: Claim) -> Dict[str, Any]:
    """
    Resolves linked entities from existing Phase 2-6 modules via stable identifiers
    without copying datasets into a separate database.
    """
    resolved: Dict[str, Any] = {
        "historical_scheme": None,
        "promise": None,
        "news_article": None,
        "financial_document": None,
        "representative": None,
        "constituency": None
    }
    # Phase 2: Historical Scheme
    if getattr(claim, "historical_scheme_id", None):
        try:
            from backend.models.budget import HistoricalScheme
            hs = db.query(HistoricalScheme).filter(HistoricalScheme.id == claim.historical_scheme_id).first()
            if hs:
                resolved["historical_scheme"] = {
                    "id": hs.id,
                    "scheme_name": hs.scheme_name,
                    "financial_year": hs.financial_year,
                    "department": hs.department.name if hs.department else None,
                    "objectives": hs.objectives
                }
        except Exception:
            pass

    # Phase 3: Political Promise
    if getattr(claim, "promise_id", None):
        try:
            from backend.models.promise import PoliticalPromise
            p = db.query(PoliticalPromise).filter(PoliticalPromise.promise_id == claim.promise_id).first()
            if p:
                resolved["promise"] = {
                    "promise_id": p.promise_id,
                    "original_text": p.original_text,
                    "classification": p.classification,
                    "manifesto_id": p.manifesto_id
                }
        except Exception:
            pass

    # Phase 4: News Article
    if getattr(claim, "news_article_id", None):
        try:
            from backend.models.news import Article
            art = db.query(Article).filter(Article.article_id == claim.news_article_id).first()
            if art:
                resolved["news_article"] = {
                    "article_id": art.article_id,
                    "title": art.title,
                    "url": art.url,
                    "source_name": art.source.source_name if art.source else None,
                    "publication_date": art.publication_date.isoformat() if getattr(art, "publication_date", None) else None
                }
        except Exception:
            pass

    # Phase 5: Financial Document
    if getattr(claim, "financial_document_id", None):
        try:
            from backend.models.funding import FinancialDocument
            fd = db.query(FinancialDocument).filter(FinancialDocument.document_id == claim.financial_document_id).first()
            if fd:
                resolved["financial_document"] = {
                    "document_id": fd.document_id,
                    "financial_year": fd.financial_year,
                    "filing_type": fd.filing_type,
                    "source_url": fd.source_url,
                    "submission_date": fd.submission_date
                }
        except Exception:
            pass

    # Phase 6: Representative
    if getattr(claim, "representative_id", None):
        try:
            from backend.models.representative import Representative
            rep = db.query(Representative).filter(Representative.representative_id == claim.representative_id).first()
            if rep:
                resolved["representative"] = {
                    "representative_id": rep.representative_id,
                    "official_name": rep.official_name,
                    "representative_type": rep.representative_type,
                    "party_id": rep.party_id,
                    "constituency_id": rep.constituency_id,
                    "term_start": rep.term_start,
                    "term_end": rep.term_end
                }
        except Exception:
            pass

    # Phase 6: Constituency
    if getattr(claim, "constituency_id", None):
        try:
            from backend.models.representative import Constituency
            con = db.query(Constituency).filter(Constituency.constituency_id == claim.constituency_id).first()
            if con:
                resolved["constituency"] = {
                    "constituency_id": con.constituency_id,
                    "name": getattr(con, "official_name", None) or getattr(con, "name", None),
                    "official_name": getattr(con, "official_name", None) or getattr(con, "name", None),
                    "constituency_type": con.constituency_type.value if hasattr(con.constituency_type, "value") else str(con.constituency_type),
                    "district": getattr(con, "district", None)
                }
        except Exception:
            pass

    return resolved


@claims_bp.route("/", methods=["GET"])
@claims_bp.route("/search", methods=["GET"])
def list_claims():
    """
    List and search registered claims with filtering by category, verdict, party,
    speaker, representative, promise, scheme, or keyword search.
    Exposes verification outcome, supporting/contradicting evidence references,
    methodology, and epistemic limitations.
    """
    category_param = request.args.get("category")
    status_param = request.args.get("status")
    outcome_param = request.args.get("outcome") or request.args.get("verdict")
    party_param = request.args.get("party")
    speaker_param = request.args.get("speaker")
    language_param = request.args.get("language")
    search_query = request.args.get("q")
    rep_id = request.args.get("representative_id")
    promise_id = request.args.get("promise_id")
    scheme_id = request.args.get("scheme_id") or request.args.get("historical_scheme_id")
    news_id = request.args.get("news_article_id")
    funding_id = request.args.get("financial_document_id")

    skip = request.args.get("skip", default=0, type=int)
    limit = request.args.get("limit", default=50, type=int)

    if skip < 0:
        return error_response("'skip' must be >= 0", status_code=400)
    if limit < 1 or limit > 100:
        return error_response("'limit' must be between 1 and 100", status_code=400)

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
            query = query.filter((Claim.speaker_party == party_param) | (Claim.party == party_param))

        if speaker_param:
            query = query.filter(Claim.speaker_name.ilike(f"%{speaker_param}%"))

        if language_param:
            query = query.filter(Claim.language == language_param)

        if rep_id:
            query = query.filter(Claim.representative_id == rep_id)

        if promise_id:
            query = query.filter(Claim.promise_id == promise_id)

        if scheme_id:
            try:
                query = query.filter(Claim.historical_scheme_id == int(scheme_id))
            except ValueError:
                pass

        if news_id:
            query = query.filter(Claim.news_article_id == news_id)

        if funding_id:
            query = query.filter(Claim.financial_document_id == funding_id)

        if search_query:
            query = query.filter(
                (Claim.original_text.ilike(f"%{search_query}%")) |
                (Claim.normalized_text.ilike(f"%{search_query}%"))
            )

        if outcome_param:
            query = query.join(VerificationResult).filter(
                VerificationResult.is_current == True,
                (VerificationResult.outcome == VerificationOutcome.from_string(outcome_param)) |
                (VerificationResult.verdict == outcome_param.upper())
            )

        total = query.count()
        claims = query.order_by(desc(Claim.created_at)).offset(skip).limit(limit).all()

        results = []
        for c in claims:
            current_res = next((r for r in c.verification_results if r.is_current), None)
            results.append({
                "claim_id": c.claim_id,
                "original_text": c.original_text,
                "language": c.language,
                "claim_category": c.claim_category.value if hasattr(c.claim_category, "value") else str(c.claim_category),
                "speaker_name": c.speaker_name,
                "speaker_party": c.speaker_party or c.party,
                "party": c.party or c.speaker_party,
                "claim_date": c.claim_date.isoformat() if c.claim_date else None,
                "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                "verdict": current_res.verdict.value if current_res and current_res.verdict else (current_res.outcome.value if current_res and current_res.outcome else None),
                "confidence_score": current_res.confidence_score if current_res else None,
                "cross_phase_identifiers": {
                    "promise_id": c.promise_id,
                    "historical_scheme_id": c.historical_scheme_id,
                    "news_article_id": c.news_article_id,
                    "financial_document_id": c.financial_document_id,
                    "representative_id": c.representative_id,
                    "constituency_id": c.constituency_id
                },
                "verification": current_res.to_dict() if current_res else None
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
    Get full profile for a specific claim including versions, evidence, results,
    reviews, and resolved cross-phase links.
    """
    db = SessionLocal()
    try:
        service = ClaimVerificationService(db=db)
        profile = service.get_claim_profile(claim_id)
        if not profile:
            return error_response(f"Claim '{claim_id}' not found", status_code=404)

        claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if claim:
            profile["resolved_cross_phase_entities"] = resolve_cross_phase_entities(db, claim)
            profile["source"] = claim.source.to_dict() if claim.source else None
            profile["cross_phase_links"] = [l.to_dict() for l in claim.cross_phase_links]
            profile["epistemic_disclaimer"] = "Civil evaluation is proposition-specific. Contradictory evidence remains visible without suppression."

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
            party=payload.get("party") or payload.get("speaker_party"),
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
    err = verify_reviewer_access(request, payload)
    if err:
        return error_response(err, status_code=403)

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


@claims_bp.route("/<string:claim_id>/atomic/<string:atomic_claim_id>", methods=["GET"])
@claims_bp.route("/atomic/<string:atomic_claim_id>", methods=["GET"])
def get_atomic_claim(atomic_claim_id: str, claim_id: Optional[str] = None):
    """
    Get atomic proposition details including semantic frame, quantitative metrics,
    related candidate retrievals, evidence relationships, and cross-phase links.
    """
    db = SessionLocal()
    try:
        ac = db.query(AtomicClaim).filter(AtomicClaim.atomic_claim_id == atomic_claim_id).first()
        if not ac:
            return error_response(f"Atomic claim '{atomic_claim_id}' not found", status_code=404)
        if claim_id and ac.claim_id != claim_id:
            return error_response(f"Atomic claim '{atomic_claim_id}' does not belong to claim '{claim_id}'", status_code=400)

        claim = ac.claim
        retrievals = [c.to_dict() for c in claim.retrieval_candidates if c.atomic_claim_id == atomic_claim_id] if claim else []
        relationships = [r.to_dict() for r in claim.evidence_relationships if r.atomic_claim_id == atomic_claim_id] if claim else []

        return success_response(
            data={
                "atomic_claim": ac.to_dict(),
                "parent_claim_id": ac.claim_id,
                "parent_claim_text": claim.original_text if claim else None,
                "retrieval_candidates": retrievals,
                "evidence_relationships": relationships,
                "cross_phase_links": [l.to_dict() for l in ac.cross_phase_links],
                "epistemic_notice": "Proposition-level assessment is isolated from surrounding speech rhetoric."
            },
            message="Atomic claim details retrieved"
        )
    finally:
        db.close()


@claims_bp.route("/evidence", methods=["GET"])
@claims_bp.route("/evidence/search", methods=["GET"])
def search_evidence():
    """
    Search across ingested evidence documents and passages.
    """
    query_str = request.args.get("q")
    doc_type = request.args.get("document_type")
    source_cat = request.args.get("source_category")
    source_tier_str = request.args.get("source_tier")
    publisher = request.args.get("publisher")
    language = request.args.get("language")
    skip = request.args.get("skip", default=0, type=int)
    limit = request.args.get("limit", default=20, type=int)

    if skip < 0 or limit < 1 or limit > 100:
        return error_response("Invalid pagination params (skip >= 0, 1 <= limit <= 100)", status_code=400)

    db = SessionLocal()
    try:
        q = db.query(EvidenceDocument)
        if query_str:
            q = q.filter(
                (EvidenceDocument.title.ilike(f"%{query_str}%")) |
                (EvidenceDocument.source_name.ilike(f"%{query_str}%")) |
                (EvidenceDocument.publisher.ilike(f"%{query_str}%"))
            )
        if doc_type:
            q = q.filter(EvidenceDocument.document_type == doc_type)
        if source_cat:
            q = q.filter(EvidenceDocument.source_category == source_cat)
        if publisher:
            q = q.filter(EvidenceDocument.publisher.ilike(f"%{publisher}%"))
        if language:
            q = q.filter(EvidenceDocument.language == language)
        if source_tier_str:
            try:
                st_enum = SourceTier(source_tier_str)
                q = q.filter(EvidenceDocument.source_tier == st_enum)
            except ValueError:
                pass

        total = q.count()
        docs = q.order_by(desc(EvidenceDocument.created_at)).offset(skip).limit(limit).all()

        return success_response(
            data={
                "total": total,
                "skip": skip,
                "limit": limit,
                "documents": [d.to_dict() for d in docs]
            },
            message="Evidence documents retrieved successfully"
        )
    finally:
        db.close()


@claims_bp.route("/evidence/documents/<string:document_id>", methods=["GET"])
def get_evidence_document(document_id: str):
    """
    Get evidence document details, passages, file hash, and referencing claims.
    """
    db = SessionLocal()
    try:
        doc = db.query(EvidenceDocument).filter(EvidenceDocument.document_id == document_id).first()
        if not doc:
            return error_response(f"Evidence document '{document_id}' not found", status_code=404)

        passages = [p.to_dict() for p in doc.passages]
        passage_ids = [p.passage_id for p in doc.passages]
        referencing_rels = db.query(ClaimEvidenceRelationship).filter(ClaimEvidenceRelationship.passage_id.in_(passage_ids)).all() if passage_ids else []
        referencing_claim_ids = sorted(list(set(r.claim_id for r in referencing_rels)))

        return success_response(
            data={
                "document": doc.to_dict(),
                "passages": passages,
                "referencing_claim_ids": referencing_claim_ids,
                "referencing_claims_count": len(referencing_claim_ids)
            },
            message="Evidence document details retrieved"
        )
    finally:
        db.close()


@claims_bp.route("/<string:claim_id>/history", methods=["GET"])
@claims_bp.route("/<string:claim_id>/audit-trail", methods=["GET"])
def get_claim_history(claim_id: str):
    """
    Complete audit history for a claim: verification history transitions,
    human review records, verification execution runs, and text versions.
    """
    db = SessionLocal()
    try:
        claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            return error_response(f"Claim '{claim_id}' not found", status_code=404)

        return success_response(
            data={
                "claim_id": claim_id,
                "verification_history": [h.to_dict() for h in claim.verification_history],
                "reviews": [r.to_dict() for r in claim.reviews],
                "verification_runs": [run.to_dict() for run in claim.verification_runs],
                "versions": [v.to_dict() for v in claim.versions],
                "epistemic_disclaimer": "Full revision history is permanently preserved to prevent stealth modifications."
            },
            message="Audit history retrieved successfully"
        )
    finally:
        db.close()


@claims_bp.route("/sources/<string:source_id>", methods=["GET"])
def get_claim_source(source_id: str):
    """
    Get source provenance record and associated registered claims.
    """
    db = SessionLocal()
    try:
        src = db.query(ClaimSource).filter(ClaimSource.source_id == source_id).first()
        if not src:
            return error_response(f"Claim source '{source_id}' not found", status_code=404)

        associated_claims = [
            {
                "claim_id": c.claim_id,
                "original_text": c.original_text,
                "claim_category": c.claim_category.value if hasattr(c.claim_category, "value") else str(c.claim_category),
                "claim_date": c.claim_date.isoformat() if c.claim_date else None,
                "status": c.status.value if hasattr(c.status, "value") else str(c.status)
            }
            for c in src.claims
        ]

        return success_response(
            data={
                "source": src.to_dict(),
                "associated_claims_count": len(associated_claims),
                "associated_claims": associated_claims
            },
            message="Claim source details retrieved"
        )
    finally:
        db.close()


@claims_bp.route("/<string:claim_id>/provenance", methods=["GET"])
def get_claim_provenance(claim_id: str):
    """
    Get provenance profile for a specific claim.
    """
    db = SessionLocal()
    try:
        claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            return error_response(f"Claim '{claim_id}' not found", status_code=404)

        return success_response(
            data={
                "claim_id": claim_id,
                "source": claim.source.to_dict() if claim.source else None,
                "source_id": claim.source_id,
                "claim_source_url": claim.claim_source_url,
                "source_document_id": claim.source_document_id,
                "attribution_type": claim.attribution_type.value if hasattr(claim.attribution_type, "value") else str(claim.attribution_type),
                "candidate_source_type": claim.candidate_source_type.value if hasattr(claim.candidate_source_type, "value") else str(claim.candidate_source_type),
                "extraction_method": claim.extraction_method,
                "content_fingerprint": claim.content_fingerprint,
                "versions_count": len(claim.versions) if claim.versions else 0,
                "versions": [v.to_dict() for v in claim.versions]
            },
            message="Claim provenance retrieved successfully"
        )
    finally:
        db.close()


@claims_bp.route("/<string:claim_id>/cross-phase/link", methods=["POST"])
def link_claim_cross_phase(claim_id: str):
    """
    Link a claim to an existing CIVICLENS TN module record (Phase 2 Schemes,
    Phase 3 Promises, Phase 4 News, Phase 5 Funding, Phase 6 Representatives/Constituencies).
    """
    payload = request.get_json(silent=True) or {}
    err = verify_reviewer_access(request, payload)
    if err:
        return error_response(err, status_code=403)

    target_phase = payload.get("target_phase")
    entity_type = payload.get("entity_type")
    entity_id = payload.get("entity_id")
    relationship_nature = payload.get("relationship_nature", "related_entity")
    atomic_claim_id = payload.get("atomic_claim_id")
    relevance_score = float(payload.get("relevance_score", 1.0))

    if not target_phase or not entity_type or not entity_id:
        return error_response("target_phase, entity_type, and entity_id are required", status_code=400)

    db = SessionLocal()
    try:
        claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            return error_response(f"Claim '{claim_id}' not found", status_code=404)

        entity_resolved_name = None
        if target_phase in ["PHASE_2_SCHEME", "PHASE_2_SCHEMES"]:
            from backend.models.budget import HistoricalScheme
            try:
                hs_id = int(entity_id)
                hs = db.query(HistoricalScheme).filter(HistoricalScheme.id == hs_id).first()
                if not hs:
                    return error_response(f"HistoricalScheme with id '{entity_id}' not found", status_code=404)
                claim.historical_scheme_id = hs_id
                entity_resolved_name = hs.scheme_name
            except ValueError:
                return error_response(f"Invalid integer id for HistoricalScheme: '{entity_id}'", status_code=400)

        elif target_phase in ["PHASE_3_PROMISE", "PHASE_3_PROMISES"]:
            from backend.models.promise import PoliticalPromise
            p = db.query(PoliticalPromise).filter(PoliticalPromise.promise_id == entity_id).first()
            if not p:
                return error_response(f"PoliticalPromise with id '{entity_id}' not found", status_code=404)
            claim.promise_id = entity_id
            entity_resolved_name = p.original_text[:60]

        elif target_phase in ["PHASE_4_NEWS"]:
            from backend.models.news import Article
            art = db.query(Article).filter(Article.article_id == entity_id).first()
            if not art:
                return error_response(f"Article with id '{entity_id}' not found", status_code=404)
            claim.news_article_id = entity_id
            entity_resolved_name = art.title

        elif target_phase in ["PHASE_5_FUNDING"]:
            from backend.models.funding import FinancialDocument
            fd = db.query(FinancialDocument).filter(FinancialDocument.document_id == entity_id).first()
            if not fd:
                return error_response(f"FinancialDocument with id '{entity_id}' not found", status_code=404)
            claim.financial_document_id = entity_id
            entity_resolved_name = f"{fd.filing_type} ({fd.financial_year})"

        elif target_phase in ["PHASE_6_REPRESENTATIVE", "PHASE_6_REPRESENTATIVES"]:
            from backend.models.representative import Representative
            rep = db.query(Representative).filter(Representative.representative_id == entity_id).first()
            if not rep:
                return error_response(f"Representative with id '{entity_id}' not found", status_code=404)
            claim.representative_id = entity_id
            entity_resolved_name = rep.official_name

        elif target_phase in ["PHASE_6_CONSTITUENCY", "PHASE_6_CONSTITUENCIES"]:
            from backend.models.representative import Constituency
            con = db.query(Constituency).filter(Constituency.constituency_id == entity_id).first()
            if not con:
                return error_response(f"Constituency with id '{entity_id}' not found", status_code=404)
            claim.constituency_id = entity_id
            entity_resolved_name = getattr(con, "official_name", None) or getattr(con, "name", None)

        import uuid
        link_id = f"CPL-{claim_id}-{int(datetime.now(timezone.utc).timestamp()*1000)}-{uuid.uuid4().hex[:6]}"
        cross_link = ClaimCrossPhaseLink(
            link_id=link_id,
            claim_id=claim_id,
            atomic_claim_id=atomic_claim_id,
            target_phase=target_phase,
            entity_type=entity_type,
            entity_id=str(entity_id),
            relationship_nature=relationship_nature,
            relevance_score=relevance_score,
            metadata_json={"entity_name": entity_resolved_name}
        )
        db.add(cross_link)
        db.commit()
        db.refresh(cross_link)

        return success_response(
            data=cross_link.to_dict(),
            message=f"Claim linked to {target_phase} record successfully",
            status_code=201
        )
    finally:
        db.close()


@claims_bp.route("/<string:claim_id>/cross-phase", methods=["GET"])
def get_claim_cross_phase(claim_id: str):
    """
    Get all cross-phase relationships and resolved entity details for a claim.
    """
    db = SessionLocal()
    try:
        claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            return error_response(f"Claim '{claim_id}' not found", status_code=404)

        resolved = resolve_cross_phase_entities(db, claim)
        links = [l.to_dict() for l in claim.cross_phase_links]

        return success_response(
            data={
                "claim_id": claim_id,
                "cross_phase_identifiers": {
                    "promise_id": claim.promise_id,
                    "historical_scheme_id": claim.historical_scheme_id,
                    "news_article_id": claim.news_article_id,
                    "financial_document_id": claim.financial_document_id,
                    "representative_id": claim.representative_id,
                    "constituency_id": claim.constituency_id
                },
                "resolved_entities": resolved,
                "cross_phase_links_count": len(links),
                "cross_phase_links": links
            },
            message="Cross-phase intelligence retrieved successfully"
        )
    finally:
        db.close()


@claims_bp.route("/by-representative/<string:representative_id>", methods=["GET"])
def get_claims_by_representative(representative_id: str):
    """
    Get all claims voiced by or attributed to a specific representative.
    """
    skip = request.args.get("skip", default=0, type=int)
    limit = request.args.get("limit", default=20, type=int)
    if skip < 0 or limit < 1 or limit > 100:
        return error_response("Invalid pagination params", status_code=400)

    db = SessionLocal()
    try:
        query = db.query(Claim).filter(Claim.representative_id == representative_id)
        total = query.count()
        claims = query.order_by(desc(Claim.created_at)).offset(skip).limit(limit).all()

        return success_response(
            data={
                "representative_id": representative_id,
                "total": total,
                "skip": skip,
                "limit": limit,
                "claims": [c.to_dict() for c in claims]
            },
            message="Representative claims retrieved"
        )
    finally:
        db.close()


@claims_bp.route("/by-promise/<string:promise_id>", methods=["GET"])
def get_claims_by_promise(promise_id: str):
    """
    Get all claims evaluating or referencing a specific political promise.
    """
    skip = request.args.get("skip", default=0, type=int)
    limit = request.args.get("limit", default=20, type=int)
    if skip < 0 or limit < 1 or limit > 100:
        return error_response("Invalid pagination params", status_code=400)

    db = SessionLocal()
    try:
        query = db.query(Claim).filter(Claim.promise_id == promise_id)
        total = query.count()
        claims = query.order_by(desc(Claim.created_at)).offset(skip).limit(limit).all()

        return success_response(
            data={
                "promise_id": promise_id,
                "total": total,
                "skip": skip,
                "limit": limit,
                "claims": [c.to_dict() for c in claims]
            },
            message="Promise claims retrieved"
        )
    finally:
        db.close()


@claims_bp.route("/by-scheme/<string:scheme_id>", methods=["GET"])
def get_claims_by_scheme(scheme_id: str):
    """
    Get all claims evaluating or referencing a specific budget/historical scheme.
    """
    skip = request.args.get("skip", default=0, type=int)
    limit = request.args.get("limit", default=20, type=int)
    if skip < 0 or limit < 1 or limit > 100:
        return error_response("Invalid pagination params", status_code=400)

    db = SessionLocal()
    try:
        try:
            s_id = int(scheme_id)
            query = db.query(Claim).filter(Claim.historical_scheme_id == s_id)
        except ValueError:
            query = db.query(Claim).filter(False)

        total = query.count()
        claims = query.order_by(desc(Claim.created_at)).offset(skip).limit(limit).all()

        return success_response(
            data={
                "historical_scheme_id": scheme_id,
                "total": total,
                "skip": skip,
                "limit": limit,
                "claims": [c.to_dict() for c in claims]
            },
            message="Scheme claims retrieved"
        )
    finally:
        db.close()


