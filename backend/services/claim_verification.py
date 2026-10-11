"""
Phase 7 — Political Claim Verification & Evidence Intelligence Service.

Implements the end-to-end verification pipeline:
1. Claim Registration (Verbatim original preservation)
2. Claim Versioning (Immutable original, auditable edits)
3. Claim Decomposition (Atomic subject & proposition extraction)
4. Source Quality Assessment (5-tier objective credibility scoring)
5. Evidence Linking & Contradiction Analysis (Bidirectional scoring)
6. Automated Verification Run & Verdict Generation
7. Human Review Management & Audit History
8. Strictly NO political truthfulness rankings or leaderboards
"""

import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.models.claim import (
    Claim,
    ClaimVersion,
    ClaimSubject,
    ClaimSource,
    EvidenceDocument,
    EvidencePassage,
    ClaimEvidenceRelationship,
    VerificationRun,
    VerificationResult,
    VerificationHistory,
    SourceAssessment,
    ReviewRecord,
    ClaimCategory,
    ClaimStatus,
    SourceTier,
    EvidenceRelationshipType,
    VerificationVerdict,
    ReviewStatus,
    SubjectType,
    AttributionType,
    CandidateSourceType
)
from backend.core.logger import setup_logger

logger = setup_logger("civiclens.phase7.verification")


class ClaimVerificationService:
    """
    Core verification intelligence engine managing claims, evidence synthesis,
    contradiction analysis, and human-in-the-loop audit logs.
    """

    def __init__(self, db: Session):
        self.db = db

    # -----------------------------------------------------------------------
    # 1. Claim Registration
    # -----------------------------------------------------------------------
    def register_claim(
        self,
        claim_id: str,
        original_text: str,
        claim_category: ClaimCategory,
        speaker_name: Optional[str] = None,
        speaker_role: Optional[str] = None,
        speaker_party: Optional[str] = None,
        party: Optional[str] = None,
        claim_date: Optional[datetime] = None,
        publication_date: Optional[datetime] = None,
        claim_source_url: Optional[str] = None,
        source_document_id: Optional[str] = None,
        temporal_scope: Optional[str] = None,
        geographic_scope: Optional[str] = "Tamil Nadu",
        context_text: Optional[str] = None,
        language: str = "ta",
        source_id: Optional[str] = None,
        extraction_method: str = "MANUAL",
        review_status: ReviewStatus = ReviewStatus.PENDING_REVIEW,
        attribution_type: AttributionType = AttributionType.DIRECT_QUOTE,
        candidate_source_type: CandidateSourceType = CandidateSourceType.PUBLIC_SPEECH,
        content_fingerprint: Optional[str] = None,
        is_test_fixture: bool = False,
        metadata_json: Optional[Dict[str, Any]] = None
    ) -> Claim:
        """
        Registers a new claim, strictly preserving verbatim original text.
        Never infers speaker, date, party, or context when unverified.
        Initializes ClaimVersion 1.
        """
        existing = self.db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if existing:
            raise ValueError(f"Claim with ID '{claim_id}' already exists.")

        normalized_text = self._normalize_text(original_text)
        canonical_party = party or speaker_party

        claim = Claim(
            claim_id=claim_id,
            source_id=source_id,
            original_text=original_text.strip(),
            normalized_text=normalized_text,
            context_text=context_text.strip() if context_text else None,
            language=language,
            claim_category=claim_category,
            speaker_name=speaker_name,
            speaker_role=speaker_role,
            speaker_party=canonical_party,
            party=canonical_party,
            claim_date=claim_date,  # Preserves exact date; does NOT infer when None
            publication_date=publication_date,
            claim_source_url=claim_source_url,
            source_document_id=source_document_id,
            temporal_scope=temporal_scope,
            geographic_scope=geographic_scope,
            extraction_method=extraction_method,
            attribution_type=attribution_type,
            candidate_source_type=candidate_source_type,
            content_fingerprint=content_fingerprint,
            status=ClaimStatus.PENDING,
            review_status=review_status,
            is_test_fixture=is_test_fixture,
            metadata_json=metadata_json or {}
        )
        self.db.add(claim)

        # Create Version 1
        version_1 = ClaimVersion(
            version_id=f"{claim_id}-v1",
            claim_id=claim_id,
            version_number=1,
            edited_text=original_text.strip(),
            change_rationale="Initial registration of verbatim claim.",
            edited_by="system_intake",
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(version_1)

        self.db.commit()
        self.db.refresh(claim)
        logger.info(f"Registered claim {claim_id} [{claim_category.value}] by {speaker_name or 'Unknown'}")
        return claim

    # -----------------------------------------------------------------------
    # 2. Claim Versioning
    # -----------------------------------------------------------------------
    def add_claim_version(
        self,
        claim_id: str,
        edited_text: str,
        change_rationale: str,
        transliterated_text: Optional[str] = None,
        additional_context: Optional[str] = None,
        edited_by: Optional[str] = "expert_reviewer"
    ) -> ClaimVersion:
        """
        Adds a revised transcription, translation, or additional context without overwriting original_text.
        """
        claim = self.db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim '{claim_id}' not found.")

        current_versions = self.db.query(ClaimVersion).filter(ClaimVersion.claim_id == claim_id).all()
        next_ver = len(current_versions) + 1

        version = ClaimVersion(
            version_id=f"{claim_id}-v{next_ver}",
            claim_id=claim_id,
            version_number=next_ver,
            edited_text=edited_text.strip(),
            transliterated_text=transliterated_text.strip() if transliterated_text else None,
            additional_context=additional_context.strip() if additional_context else None,
            change_rationale=change_rationale.strip(),
            edited_by=edited_by,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(version)
        claim.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(version)
        logger.info(f"Added version {next_ver} for claim {claim_id}: {change_rationale}")
        return version

    # -----------------------------------------------------------------------
    # 3. Claim Decomposition
    # -----------------------------------------------------------------------
    def decompose_claim(
        self,
        claim_id: str,
        subjects: List[Dict[str, Any]]
    ) -> List[ClaimSubject]:
        """
        Decomposes claim into atomic verifiable subjects (politicians, schemes, indicators, etc.).
        """
        claim = self.db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim '{claim_id}' not found.")

        created_subjects = []
        for idx, subj in enumerate(subjects):
            subj_id = f"{claim_id}-SUBJ-{idx+1:02d}"
            subject = ClaimSubject(
                subject_id=subj_id,
                claim_id=claim_id,
                subject_type=subj["subject_type"],
                entity_id=subj.get("entity_id"),
                canonical_name=subj["canonical_name"],
                confidence=float(subj.get("confidence", 1.0))
            )
            self.db.add(subject)
            created_subjects.append(subject)

        claim.status = ClaimStatus.DECOMPOSED
        self.db.commit()
        logger.info(f"Decomposed claim {claim_id} into {len(created_subjects)} subjects.")
        return created_subjects

    # -----------------------------------------------------------------------
    # 4. Source Quality Assessment
    # -----------------------------------------------------------------------
    def assess_source_quality(
        self,
        document_id: str,
        tier_weight: Optional[float] = None,
        primary_source_score: float = 1.0,
        institutional_independence_score: float = 1.0,
        verifiability_score: float = 1.0,
        notes: Optional[str] = None
    ) -> SourceAssessment:
        """
        Evaluates source quality according to the 4-dimension objective scoring rubric.
        """
        doc = self.db.query(EvidenceDocument).filter(EvidenceDocument.document_id == document_id).first()
        if not doc:
            raise ValueError(f"Evidence document '{document_id}' not found.")

        # Default tier weights based on SourceTier
        tier_defaults = {
            SourceTier.TIER_1_STATUTORY: 1.0,
            SourceTier.TIER_2_OFFICIAL_AGENCY: 0.85,
            SourceTier.TIER_3_ACCREDITED_FACTCHECK: 0.70,
            SourceTier.TIER_4_SECONDARY_CIVIC: 0.50,
            SourceTier.TIER_5_UNVERIFIED: 0.20
        }
        w_tier = tier_weight if tier_weight is not None else tier_defaults.get(doc.source_tier, 0.50)

        # Composite score formula: 0.35*tier + 0.25*prim + 0.20*indep + 0.20*verif
        composite = (
            0.35 * w_tier +
            0.25 * primary_source_score +
            0.20 * institutional_independence_score +
            0.20 * verifiability_score
        )
        composite = max(0.0, min(1.0, composite))

        assessment = SourceAssessment(
            assessment_id=f"SASS-{document_id}",
            document_id=document_id,
            source_tier=doc.source_tier,
            tier_weight=w_tier,
            primary_source_score=primary_source_score,
            institutional_independence_score=institutional_independence_score,
            verifiability_score=verifiability_score,
            composite_quality_score=round(composite, 4),
            assessment_notes=notes,
            assessed_at=datetime.now(timezone.utc)
        )
        self.db.merge(assessment)
        self.db.commit()
        logger.info(f"Assessed source {document_id} with composite quality score {composite:.2f}")
        return assessment

    # -----------------------------------------------------------------------
    # 5. Evidence Linking & Contradiction Analysis
    # -----------------------------------------------------------------------
    def link_evidence(
        self,
        claim_id: str,
        passage_id: str,
        relationship_type: EvidenceRelationshipType,
        relevance_score: float = 1.0,
        confidence_score: float = 1.0,
        contradiction_score: float = 0.0,
        matching_method: str = "multi_signal_reconciliation",
        reconciliation_notes: Optional[str] = None
    ) -> ClaimEvidenceRelationship:
        """
        Explicitly links an evidence passage to a claim, registering support vs contradiction signals.
        """
        claim = self.db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim '{claim_id}' not found.")
        passage = self.db.query(EvidencePassage).filter(EvidencePassage.passage_id == passage_id).first()
        if not passage:
            raise ValueError(f"Evidence passage '{passage_id}' not found.")

        rel_id = f"CER-{claim_id}-{passage_id}"
        existing = self.db.query(ClaimEvidenceRelationship).filter(
            ClaimEvidenceRelationship.relationship_id == rel_id
        ).first()

        if existing:
            existing.relationship_type = relationship_type
            existing.relevance_score = relevance_score
            existing.confidence_score = confidence_score
            existing.contradiction_score = contradiction_score
            existing.reconciliation_notes = reconciliation_notes
            rel = existing
        else:
            rel = ClaimEvidenceRelationship(
                relationship_id=rel_id,
                claim_id=claim_id,
                passage_id=passage_id,
                relationship_type=relationship_type,
                relevance_score=relevance_score,
                confidence_score=confidence_score,
                contradiction_score=contradiction_score,
                matching_method=matching_method,
                reconciliation_notes=reconciliation_notes,
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(rel)

        claim.status = ClaimStatus.EVIDENCE_LINKED
        self.db.commit()
        self.db.refresh(rel)
        logger.info(f"Linked evidence {passage_id} to claim {claim_id} as {relationship_type.value}")
        return rel

    # -----------------------------------------------------------------------
    # 6. Automated Verification Engine & Verdict Synthesis
    # -----------------------------------------------------------------------
    def verify_claim(
        self,
        claim_id: str,
        engine_version: str = "v1.0-deterministic",
        manual_rationale: Optional[str] = None,
        manual_findings: Optional[Dict[str, Any]] = None,
        limitations_and_caveats: Optional[str] = None
    ) -> VerificationResult:
        """
        Executes a verification pass against all linked evidence relationships,
        computing support/contradiction balance and deriving standardized verdict.
        """
        claim = self.db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim '{claim_id}' not found.")

        run_id = f"VRUN-{claim_id}-{int(datetime.now(timezone.utc).timestamp())}"
        v_run = VerificationRun(
            run_id=run_id,
            claim_id=claim_id,
            engine_version=engine_version,
            started_at=datetime.now(timezone.utc),
            execution_status="IN_PROGRESS"
        )
        self.db.add(v_run)
        self.db.flush()

        # Fetch all linked evidence relationships
        rels = self.db.query(ClaimEvidenceRelationship).filter(
            ClaimEvidenceRelationship.claim_id == claim_id
        ).all()

        if not rels:
            # Insufficient evidence by default
            verdict = VerificationVerdict.UNVERIFIABLE_INSUFFICIENT_EVIDENCE
            conf = 0.2
            support = 0.0
            contra = 0.0
            uncertainty = 1.0
            rationale = manual_rationale or "No verified documentary evidence could be linked to this proposition."
            findings = manual_findings or {"evidence_count": 0}
        else:
            # Weighted aggregation based on SourceTier & relationship types
            weighted_support = 0.0
            weighted_contra = 0.0
            total_weight = 0.0

            for r in rels:
                doc = r.passage.document if r.passage else None
                weight = 1.0
                if doc:
                    assessment = self.db.query(SourceAssessment).filter(
                        SourceAssessment.document_id == doc.document_id
                    ).first()
                    weight = assessment.composite_quality_score if assessment else 0.8

                total_weight += weight
                if r.relationship_type == EvidenceRelationshipType.SUPPORTS:
                    weighted_support += weight * r.confidence_score
                elif r.relationship_type == EvidenceRelationshipType.CONTRADICTS:
                    weighted_contra += weight * r.contradiction_score
                elif r.relationship_type == EvidenceRelationshipType.PARTIALLY_SUPPORTS:
                    weighted_support += 0.5 * weight * r.confidence_score
                    weighted_contra += 0.3 * weight * (1.0 - r.confidence_score)

            support_ratio = (weighted_support / total_weight) if total_weight > 0 else 0.0
            contra_ratio = (weighted_contra / total_weight) if total_weight > 0 else 0.0

            # Derive standardized verdict
            if contra_ratio >= 0.50:
                verdict = VerificationVerdict.CONTRADICTED
                conf = min(0.95, round(contra_ratio, 2))
                uncertainty = 0.1
                rationale = manual_rationale or f"Direct empirical contradiction found in statutory records (Contradiction weight: {contra_ratio:.2f})."
            elif support_ratio >= 0.70 and contra_ratio < 0.15:
                verdict = VerificationVerdict.SUPPORTED
                conf = min(0.98, round(support_ratio, 2))
                uncertainty = 0.05
                rationale = manual_rationale or f"Corroborated by high-quality official evidence (Support weight: {support_ratio:.2f})."
            elif support_ratio >= 0.40 and contra_ratio >= 0.25:
                verdict = VerificationVerdict.PARTIALLY_SUPPORTED
                conf = 0.75
                uncertainty = 0.25
                rationale = manual_rationale or "Evidence supports parts of the assertion, but significant discrepancies or unverified elements exist."
            elif any(r.relationship_type == EvidenceRelationshipType.CONTEXTUALIZES for r in rels):
                verdict = VerificationVerdict.MISLEADING_CONTEXT
                conf = 0.80
                uncertainty = 0.20
                rationale = manual_rationale or "Numerical claim is technically accurate in isolation, but omits crucial context or baseline data."
            else:
                verdict = VerificationVerdict.UNVERIFIABLE_INSUFFICIENT_EVIDENCE
                conf = 0.40
                uncertainty = 0.70
                rationale = manual_rationale or "Insufficient primary documentation available to establish verification."

            support = round(support_ratio, 2)
            contra = round(contra_ratio, 2)
            findings = manual_findings or {
                "evidence_count": len(rels),
                "support_ratio": support,
                "contradiction_ratio": contra
            }

        # Demote any prior active result
        prior_results = self.db.query(VerificationResult).filter(
            VerificationResult.claim_id == claim_id,
            VerificationResult.is_current == True
        ).all()
        for pr in prior_results:
            pr.is_current = False

        res_id = f"VRES-{claim_id}-{int(datetime.now(timezone.utc).timestamp())}"
        v_res = VerificationResult(
            result_id=res_id,
            claim_id=claim_id,
            run_id=run_id,
            verdict=verdict,
            confidence_score=conf,
            support_score=support,
            contradiction_score=contra,
            uncertainty_score=uncertainty,
            rationale=rationale,
            empirical_findings=findings,
            limitations_and_caveats=limitations_and_caveats,
            is_current=True,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(v_res)

        # Update run status
        v_run.completed_at = datetime.now(timezone.utc)
        v_run.execution_status = "COMPLETED"

        # Record History Entry
        v_hist = VerificationHistory(
            history_id=f"VHIST-{res_id}",
            claim_id=claim_id,
            result_id=res_id,
            previous_verdict=prior_results[-1].verdict.value if prior_results else None,
            new_verdict=verdict.value,
            change_reason="Automated verification run execution",
            triggered_by="AUTOMATED_PIPELINE",
            changed_at=datetime.now(timezone.utc)
        )
        self.db.add(v_hist)

        claim.status = ClaimStatus.VERIFIED
        self.db.commit()
        self.db.refresh(v_res)
        logger.info(f"Verified claim {claim_id}: Result={verdict.value} (conf={conf})")
        return v_res

    # -----------------------------------------------------------------------
    # 7. Human Review Workflow
    # -----------------------------------------------------------------------
    def submit_human_review(
        self,
        claim_id: str,
        reviewer_id: str,
        review_status: ReviewStatus,
        reviewed_verdict: VerificationVerdict,
        review_notes: str,
        override_applied: bool = False,
        reviewer_role: str = "CIVIC_EXPERT"
    ) -> ReviewRecord:
        """
        Records human expert oversight, annotations, or verdict overrides.
        """
        claim = self.db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim '{claim_id}' not found.")

        current_res = self.db.query(VerificationResult).filter(
            VerificationResult.claim_id == claim_id,
            VerificationResult.is_current == True
        ).first()

        original_verdict = current_res.verdict.value if current_res else None

        review_id = f"REV-{claim_id}-{int(datetime.now(timezone.utc).timestamp())}"
        review = ReviewRecord(
            review_id=review_id,
            claim_id=claim_id,
            reviewer_id=reviewer_id,
            reviewer_role=reviewer_role,
            review_status=review_status,
            original_verdict=original_verdict,
            reviewed_verdict=reviewed_verdict.value,
            review_notes=review_notes.strip(),
            override_applied=override_applied,
            reviewed_at=datetime.now(timezone.utc)
        )
        self.db.add(review)

        if override_applied and current_res:
            old_verdict = current_res.verdict.value
            current_res.verdict = reviewed_verdict
            current_res.rationale += f" [Human Review Override by {reviewer_id}: {review_notes}]"

            # History entry for override
            v_hist = VerificationHistory(
                history_id=f"VHIST-OVR-{review_id}",
                claim_id=claim_id,
                result_id=current_res.result_id,
                previous_verdict=old_verdict,
                new_verdict=reviewed_verdict.value,
                change_reason=f"Human Review Override: {review_notes}",
                triggered_by=f"HUMAN_REVIEWER:{reviewer_id}",
                changed_at=datetime.now(timezone.utc)
            )
            self.db.add(v_hist)

        claim.status = ClaimStatus.UNDER_REVIEW if review_status == ReviewStatus.IN_REVIEW else ClaimStatus.VERIFIED
        self.db.commit()
        self.db.refresh(review)
        logger.info(f"Recorded review {review_id} for claim {claim_id} by {reviewer_id} (Override={override_applied})")
        return review

    # -----------------------------------------------------------------------
    # 8. Query & Provenance Audit Trail
    # -----------------------------------------------------------------------
    def get_claim_profile(self, claim_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves complete claim record with versions, subjects, evidence, results, and history.
        """
        claim = self.db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            return None

        current_res = self.db.query(VerificationResult).filter(
            VerificationResult.claim_id == claim_id,
            VerificationResult.is_current == True
        ).first()

        evidence_items = []
        for cer in claim.evidence_relationships:
            passage = cer.passage
            doc = passage.document if passage else None
            evidence_items.append({
                "relationship_id": cer.relationship_id,
                "relationship_type": cer.relationship_type.value,
                "relevance_score": cer.relevance_score,
                "confidence_score": cer.confidence_score,
                "contradiction_score": cer.contradiction_score,
                "notes": cer.reconciliation_notes,
                "passage_text": passage.passage_text if passage else None,
                "page_number": passage.page_number if passage else None,
                "document_title": doc.title if doc else None,
                "source_name": doc.source_name if doc else None,
                "source_tier": doc.source_tier.value if doc else None,
                "file_hash_sha256": doc.file_hash_sha256 if doc else None
            })

        return {
            "claim_id": claim.claim_id,
            "original_text": claim.original_text,
            "normalized_text": claim.normalized_text,
            "context_text": claim.context_text,
            "language": claim.language,
            "claim_category": claim.claim_category.value,
            "speaker_name": claim.speaker_name,
            "speaker_role": claim.speaker_role,
            "speaker_party": claim.speaker_party,
            "party": claim.party,
            "claim_date": claim.claim_date.isoformat() if claim.claim_date else None,
            "publication_date": claim.publication_date.isoformat() if claim.publication_date else None,
            "claim_source_url": claim.claim_source_url,
            "source_document_id": claim.source_document_id,
            "temporal_scope": claim.temporal_scope,
            "geographic_scope": claim.geographic_scope,
            "extraction_method": claim.extraction_method,
            "attribution_type": claim.attribution_type.value if claim.attribution_type else None,
            "candidate_source_type": claim.candidate_source_type.value if claim.candidate_source_type else None,
            "status": claim.status.value,
            "review_status": claim.review_status.value if claim.review_status else None,
            "is_test_fixture": claim.is_test_fixture,
            "created_at": claim.created_at.isoformat() if claim.created_at else None,
            "versions": [
                {
                    "version_number": v.version_number,
                    "edited_text": v.edited_text,
                    "transliterated_text": v.transliterated_text,
                    "change_rationale": v.change_rationale,
                    "edited_by": v.edited_by,
                    "created_at": v.created_at.isoformat() if v.created_at else None
                }
                for v in claim.versions
            ],
            "subjects": [
                {
                    "subject_type": s.subject_type.value,
                    "canonical_name": s.canonical_name,
                    "entity_id": s.entity_id,
                    "confidence": s.confidence
                }
                for s in claim.subjects
            ],
            "atomic_claims": [
                {
                    "atomic_claim_id": ac.atomic_claim_id,
                    "atomic_claim_text": ac.atomic_claim_text,
                    "language": ac.language,
                    "subject": ac.subject,
                    "predicate": ac.predicate,
                    "action": ac.action,
                    "object": ac.object,
                    "time_period": ac.time_period,
                    "geographic_scope": ac.geographic_scope,
                    "numeric_value": ac.numeric_value,
                    "unit": ac.unit,
                    "denominator": ac.denominator,
                    "comparison_operator": ac.comparison_operator,
                    "baseline_value": ac.baseline_value,
                    "claim_type": ac.claim_type,
                    "verifiability_status": ac.verifiability_status,
                    "is_verifiable": ac.is_verifiable,
                    "is_negated": ac.is_negated,
                    "decomposition_method": ac.decomposition_method,
                    "confidence": ac.confidence,
                    "translation_text": ac.translation_text
                }
                for ac in getattr(claim, "atomic_claims", [])
            ],
            "current_result": {
                "result_id": current_res.result_id,
                "verdict": current_res.verdict.value,
                "confidence_score": current_res.confidence_score,
                "support_score": current_res.support_score,
                "contradiction_score": current_res.contradiction_score,
                "uncertainty_score": current_res.uncertainty_score,
                "rationale": current_res.rationale,
                "empirical_findings": current_res.empirical_findings,
                "limitations_and_caveats": current_res.limitations_and_caveats
            } if current_res else None,
            "evidence": evidence_items,
            "reviews": [
                {
                    "review_id": rev.review_id,
                    "reviewer_id": rev.reviewer_id,
                    "review_status": rev.review_status.value,
                    "original_verdict": rev.original_verdict,
                    "reviewed_verdict": rev.reviewed_verdict,
                    "review_notes": rev.review_notes,
                    "override_applied": rev.override_applied,
                    "reviewed_at": rev.reviewed_at.isoformat() if rev.reviewed_at else None
                }
                for rev in claim.reviews
            ],
            "history": [
                {
                    "history_id": h.history_id,
                    "previous_verdict": h.previous_verdict,
                    "new_verdict": h.new_verdict,
                    "change_reason": h.change_reason,
                    "triggered_by": h.triggered_by,
                    "changed_at": h.changed_at.isoformat() if h.changed_at else None
                }
                for h in claim.verification_history
            ]
        }

    # -----------------------------------------------------------------------
    # Helper: Text Normalization
    # -----------------------------------------------------------------------
    def _normalize_text(self, text: str) -> str:
        """
        Cleans and normalizes bilingual text while preserving original semantic roots.
        """
        if not text:
            return ""
        # Remove extra whitespace
        cleaned = re.sub(r"\s+", " ", text.strip())
        return cleaned
