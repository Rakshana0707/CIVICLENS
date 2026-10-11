"""
Phase 7.7 — Claim Verification Engine and Human Review Workflow Service.

Synthesizes claim/evidence relationships into standardized evidence assessments:
- supported_by_available_evidence
- contradicted_by_available_evidence
- partially_supported
- missing_important_context
- insufficient_evidence
- disputed_evidence
- unverifiable
- pending_review

Core Guarantees:
1. Outcomes are evidence assessments, NOT judgments about a person's honesty or intent.
2. Explanations explicitly identify which parts of the claim are supported, contradicted, or unresolved.
3. Outcomes are NEVER assigned based solely on a semantic similarity score.
4. If critical evidence is missing or the claim is ambiguous, the engine produces
   insufficient_evidence, unverifiable, or pending_review rather than a false binary verdict.
5. Complete human review workflow (accept, correct decomposition, add evidence, mark irrelevant, revise outcome).
6. Preserves both the automated baseline and subsequent human review audit history.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.models.claim import (
    Claim,
    AtomicClaim,
    EvidenceDocument,
    EvidencePassage,
    ClaimEvidenceRelationship,
    VerificationResult,
    VerificationRun,
    VerificationHistory,
    ReviewRecord,
    VerificationOutcome,
    VerificationVerdict,
    ReviewAction,
    ReviewStatus,
    EvidenceRelationshipType,
    SourceTier,
    ClaimStatus
)
from backend.core.logger import setup_logger

logger = setup_logger("civiclens.phase7.verification_engine")


def _unique_id(prefix: str, claim_id: str) -> str:
    """Generates unique collision-resistant IDs with millisecond timestamp and random suffix."""
    ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    rand_suffix = uuid.uuid4().hex[:6]
    return f"{prefix}-{claim_id}-{ts}-{rand_suffix}"


class ClaimVerificationEngine:
    """
    Core verification synthesis engine and human-in-the-loop audit manager.
    """

    METHODOLOGY_VERSION = "CIVICLENS_VERIFICATION_METHODOLOGY_V1"
    MODEL_VERSION = "civiclens-verifier-v1.0"

    def __init__(self, db: Session):
        self.db = db

    # -----------------------------------------------------------------------
    # 1. Automated Synthesis Logic
    # -----------------------------------------------------------------------
    def synthesize_claim_outcome(
        self,
        claim: Claim,
        relationships: List[ClaimEvidenceRelationship]
    ) -> Dict[str, Any]:
        """
        Synthesizes relationship signals into a standardized evidence outcome,
        multi-part proposition explanation, source diversity breakdown, and confidence indicator.
        """
        # Filter out unrelated or irrelevant relationships
        relevant_rels = [
            r for r in relationships
            if r.relationship_type != EvidenceRelationshipType.UNRELATED
            and not (r.metadata_json and r.metadata_json.get("is_marked_irrelevant"))
        ]

        # Extract atomics
        atomics = list(claim.atomic_claims)

        # Categorize evidence IDs
        supp_ids = [r.relationship_id for r in relevant_rels if r.relationship_type == EvidenceRelationshipType.SUPPORTS]
        contra_ids = [r.relationship_id for r in relevant_rels if r.relationship_type == EvidenceRelationshipType.CONTRADICTS]
        context_ids = [
            r.relationship_id for r in relevant_rels
            if r.relationship_type in [EvidenceRelationshipType.CONTEXTUALIZES, EvidenceRelationshipType.PARTIALLY_SUPPORTS]
        ]

        # Source diversity computation (deduplicating syndicated wire copies)
        distinct_publishers = set()
        distinct_tiers = set()
        non_syndicated_count = 0

        for r in relevant_rels:
            doc = r.passage.document if r.passage else None
            if doc:
                pub = doc.publisher or doc.source_name
                distinct_publishers.add(pub)
                distinct_tiers.add(doc.source_tier.value if hasattr(doc.source_tier, "value") else str(doc.source_tier))
            if not r.is_syndicated_copy:
                non_syndicated_count += 1

        source_diversity = {
            "total_relevant_passages": len(relevant_rels),
            "independent_non_syndicated_sources": non_syndicated_count,
            "distinct_publishers_count": len(distinct_publishers),
            "publishers": sorted(list(distinct_publishers)),
            "source_tiers": sorted(list(distinct_tiers))
        }

        # Multi-part proposition explanation breakdown
        part_explanations = []
        atomic_status_map = {}

        for idx, ac in enumerate(atomics):
            ac_id = ac.atomic_claim_id
            ac_text = getattr(ac, "atomic_claim_text", None) or f"Proposition {idx+1}"
            ac_rels = [r for r in relevant_rels if r.atomic_claim_id == ac_id]

            # If no atomic-specific relationships, fall back to global claim-level rels
            if not ac_rels:
                ac_rels = [r for r in relevant_rels if r.atomic_claim_id is None or len(atomics) == 1]

            has_ac_supp = any(r.relationship_type == EvidenceRelationshipType.SUPPORTS for r in ac_rels)
            has_ac_contra = any(r.relationship_type == EvidenceRelationshipType.CONTRADICTS for r in ac_rels)
            has_ac_part = any(r.relationship_type == EvidenceRelationshipType.PARTIALLY_SUPPORTS for r in ac_rels)

            if has_ac_contra and has_ac_supp:
                status_label = "DISPUTED"
                ref = next(r.contradicting_text_reference or r.passage.passage_text[:100] for r in ac_rels if r.relationship_type == EvidenceRelationshipType.CONTRADICTS)
                part_explanations.append(f"Part {idx+1} ['{ac_text}']: DISPUTED. Conflicting official records found (Ref: {ref}).")
            elif has_ac_contra:
                status_label = "CONTRADICTED"
                ref = next(r.contradicting_text_reference or r.passage.passage_text[:100] for r in ac_rels if r.relationship_type == EvidenceRelationshipType.CONTRADICTS)
                part_explanations.append(f"Part {idx+1} ['{ac_text}']: CONTRADICTED by available evidence. Evidence shows non-fulfillment or shortfall (Ref: {ref}).")
            elif has_ac_supp:
                status_label = "SUPPORTED"
                ref = next(r.supporting_text_reference or r.passage.passage_text[:100] for r in ac_rels if r.relationship_type == EvidenceRelationshipType.SUPPORTS)
                part_explanations.append(f"Part {idx+1} ['{ac_text}']: SUPPORTED by available statutory/empirical evidence (Ref: {ref}).")
            elif has_ac_part:
                status_label = "PARTIALLY_SUPPORTED"
                ref = next(r.supporting_text_reference or r.passage.passage_text[:100] for r in ac_rels if r.relationship_type == EvidenceRelationshipType.PARTIALLY_SUPPORTS)
                part_explanations.append(f"Part {idx+1} ['{ac_text}']: PARTIALLY_SUPPORTED with scope or quantitative qualifications (Ref: {ref}).")
            else:
                status_label = "UNRESOLVED"
                part_explanations.append(f"Part {idx+1} ['{ac_text}']: UNRESOLVED. No conclusive empirical or statutory record identified.")

            atomic_status_map[ac_id] = status_label

        # -------------------------------------------------------------------
        # Synthesize Global Outcome
        # -------------------------------------------------------------------
        # Rule 1: Ambiguous or Non-Verifiable Slogan / Value Judgment
        if claim.metadata_json and claim.metadata_json.get("verifiability_status") in ["SLOGAN", "RHETORICAL_QUESTION", "NON_FACTUAL_OPINION"]:
            outcome = VerificationOutcome.UNVERIFIABLE
            confidence = 0.90
            uncertainty = 0.10
            summary = "The claim represents a political slogan, opinion, or non-verifiable value judgment without empirical metrics."

        # Rule 2: Critical evidence missing / zero relevant records
        elif len(relevant_rels) == 0:
            outcome = VerificationOutcome.INSUFFICIENT_EVIDENCE
            confidence = 0.20
            uncertainty = 0.85
            summary = (
                "Insufficient evidence available in indexed statutory archives, legislative records, or official gazettes. "
                "Absence of evidence is not proof that the statement is false."
            )

        # Rule 3: Disputed Evidence (Strong support AND strong contradiction from statutory sources)
        elif len(supp_ids) > 0 and len(contra_ids) > 0:
            outcome = VerificationOutcome.DISPUTED_EVIDENCE
            confidence = 0.65
            uncertainty = 0.70
            summary = "Direct conflict between available authoritative sources. Official reports and audit scrutiny present diverging empirical findings."

        # Rule 4: Contradicted by Available Evidence
        elif len(contra_ids) > 0 and len(supp_ids) == 0:
            outcome = VerificationOutcome.CONTRADICTED_BY_AVAILABLE_EVIDENCE
            confidence = 0.88 if any(r.passage.document.source_tier == SourceTier.TIER_1_STATUTORY for r in relevant_rels if r.relationship_type == EvidenceRelationshipType.CONTRADICTS) else 0.75
            uncertainty = 0.20
            summary = "Contradicted by available official audits, legislative records, or empirical datasets demonstrating significant discrepancy or non-delivery."

        # Rule 5: Partially Supported
        elif any(s == "PARTIALLY_SUPPORTED" for s in atomic_status_map.values()) or (len(supp_ids) > 0 and any(s == "UNRESOLVED" for s in atomic_status_map.values())):
            outcome = VerificationOutcome.PARTIALLY_SUPPORTED
            confidence = 0.80
            uncertainty = 0.30
            summary = "Partially supported by available records. Key elements of the statement are substantiated, while other metrics or timeframes remain unverified or qualified."

        # Rule 6: Missing Important Context
        elif any(r.relationship_type == EvidenceRelationshipType.CONTEXTUALIZES and r.is_outdated for r in relevant_rels) or (len(context_ids) > 0 and len(supp_ids) == 0):
            outcome = VerificationOutcome.MISSING_IMPORTANT_CONTEXT
            confidence = 0.78
            uncertainty = 0.35
            summary = "The claim omits important fiscal, temporal, or administrative context (e.g. historical baseline vs contemporary state, or restricted pilot scope)."

        # Rule 7: Supported by Available Evidence
        elif len(supp_ids) > 0 and len(contra_ids) == 0:
            outcome = VerificationOutcome.SUPPORTED_BY_AVAILABLE_EVIDENCE
            confidence = 0.92 if non_syndicated_count >= 2 or any(r.passage.document.source_tier == SourceTier.TIER_1_STATUTORY for r in relevant_rels) else 0.82
            uncertainty = 0.15
            summary = "Supported by available statutory notifications, budget line allocations, and official government records."

        else:
            outcome = VerificationOutcome.PENDING_REVIEW
            confidence = 0.50
            uncertainty = 0.60
            summary = "Inconclusive automated alignment; referred for expert human review."

        # Assemble full explanation identifying supported, contradicted, and unresolved components
        full_explanation = f"{summary}\n\nProposition Breakdown:\n" + ("\n".join(part_explanations) if part_explanations else "Single atomic proposition evaluated.")

        return {
            "outcome": outcome,
            "explanation": full_explanation,
            "atomic_claim_ids": [ac.atomic_claim_id for ac in atomics],
            "supporting_evidence_ids": supp_ids,
            "contradicting_evidence_ids": contra_ids,
            "context_evidence_ids": context_ids,
            "source_diversity": source_diversity,
            "confidence": round(confidence, 4),
            "uncertainty_indicator": round(uncertainty, 4),
            "methodology_version": self.METHODOLOGY_VERSION,
            "model_version": self.MODEL_VERSION
        }

    # -----------------------------------------------------------------------
    # 2. End-to-End Automated Verification Run
    # -----------------------------------------------------------------------
    def verify_claim(
        self,
        claim_id: str,
        engine_version: Optional[str] = None
    ) -> VerificationResult:
        """
        Executes an automated verification pass, synthesizing Phase 7.6 relationships
        into an evidence outcome and recording baseline history.
        """
        claim = self.db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim '{claim_id}' not found.")

        relationships = list(claim.evidence_relationships)

        synthesis = self.synthesize_claim_outcome(claim=claim, relationships=relationships)

        run_id = _unique_id("VRUN", claim_id)
        run = VerificationRun(
            run_id=run_id,
            claim_id=claim_id,
            engine_version=engine_version or self.MODEL_VERSION,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            execution_status="SUCCESS"
        )
        self.db.add(run)

        # Legacy verdict mapping
        verdict_map = {
            VerificationOutcome.SUPPORTED_BY_AVAILABLE_EVIDENCE: VerificationVerdict.SUPPORTED,
            VerificationOutcome.CONTRADICTED_BY_AVAILABLE_EVIDENCE: VerificationVerdict.CONTRADICTED,
            VerificationOutcome.PARTIALLY_SUPPORTED: VerificationVerdict.PARTIALLY_SUPPORTED,
            VerificationOutcome.MISSING_IMPORTANT_CONTEXT: VerificationVerdict.MISLEADING_CONTEXT,
            VerificationOutcome.INSUFFICIENT_EVIDENCE: VerificationVerdict.UNVERIFIABLE_INSUFFICIENT_EVIDENCE,
            VerificationOutcome.DISPUTED_EVIDENCE: VerificationVerdict.DISPUTED_METHODOLOGY,
            VerificationOutcome.UNVERIFIABLE: VerificationVerdict.UNVERIFIABLE_INSUFFICIENT_EVIDENCE,
            VerificationOutcome.PENDING_REVIEW: VerificationVerdict.UNVERIFIABLE_INSUFFICIENT_EVIDENCE,
        }
        legacy_verdict = verdict_map.get(synthesis["outcome"], VerificationVerdict.UNVERIFIABLE_INSUFFICIENT_EVIDENCE)

        result_id = _unique_id("VRES", claim_id)
        result = VerificationResult(
            result_id=result_id,
            claim_id=claim_id,
            run_id=run_id,
            outcome=synthesis["outcome"],
            explanation=synthesis["explanation"],
            atomic_claim_ids=synthesis["atomic_claim_ids"],
            supporting_evidence_ids=synthesis["supporting_evidence_ids"],
            contradicting_evidence_ids=synthesis["contradicting_evidence_ids"],
            context_evidence_ids=synthesis["context_evidence_ids"],
            source_diversity=synthesis["source_diversity"],
            confidence=synthesis["confidence"],
            uncertainty_indicator=synthesis["uncertainty_indicator"],
            methodology_version=synthesis["methodology_version"],
            model_version=synthesis["model_version"],
            verification_timestamp=datetime.now(timezone.utc),
            review_status=ReviewStatus.PENDING_REVIEW,
            automated_outcome=synthesis["outcome"],
            automated_explanation=synthesis["explanation"],
            automated_confidence=synthesis["confidence"],
            verdict=legacy_verdict,
            confidence_score=synthesis["confidence"],
            rationale=synthesis["explanation"],
            is_current=True,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(result)

        # Mark previous results as not current
        for prev in claim.verification_results:
            if prev.result_id != result_id:
                prev.is_current = False

        # Add initial audit history
        history_id = _unique_id("VHIST", claim_id)
        history = VerificationHistory(
            history_id=history_id,
            claim_id=claim_id,
            result_id=result_id,
            previous_outcome=None,
            new_outcome=synthesis["outcome"].value,
            previous_verdict=None,
            new_verdict=legacy_verdict.value,
            change_reason="Initial automated verification run",
            triggered_by="AUTOMATED_PIPELINE",
            changed_at=datetime.now(timezone.utc)
        )
        self.db.add(history)

        claim.status = ClaimStatus.VERIFIED
        self.db.commit()
        self.db.refresh(result)
        logger.info(f"Verified claim {claim_id}: {synthesis['outcome'].value} (Confidence: {synthesis['confidence']:.2f})")
        return result

    # -----------------------------------------------------------------------
    # 3. Human Review Workflow
    # -----------------------------------------------------------------------
    def accept_assessment(
        self,
        claim_id: str,
        reviewer_id: str,
        review_notes: str = "Automated evidence assessment validated by human reviewer."
    ) -> VerificationResult:
        """
        Accepts the automated assessment without outcome modification.
        Updates review_status to ACCEPTED and logs review record.
        """
        claim = self.db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim '{claim_id}' not found.")

        result = self.db.query(VerificationResult).filter(
            VerificationResult.claim_id == claim_id,
            VerificationResult.is_current == True
        ).first()
        if not result:
            raise ValueError(f"No current verification result found for claim '{claim_id}'.")

        result.review_status = ReviewStatus.ACCEPTED
        claim.review_status = ReviewStatus.ACCEPTED

        # Record human review entry
        rev_id = _unique_id("REV", claim_id)
        record = ReviewRecord(
            review_id=rev_id,
            claim_id=claim_id,
            verification_id=result.result_id,
            reviewer_id=reviewer_id,
            reviewer_role="SENIOR_FACTCHECK_ANALYST",
            review_status=ReviewStatus.ACCEPTED,
            action=ReviewAction.ACCEPT_ASSESSMENT.value,
            original_outcome=result.automated_outcome.value if result.automated_outcome else result.outcome.value,
            reviewed_outcome=result.outcome.value,
            original_verdict=result.verdict.value if result.verdict else None,
            reviewed_verdict=result.verdict.value if result.verdict else "SUPPORTED",
            review_notes=review_notes,
            explanation=result.explanation,
            override_applied=False,
            reviewed_at=datetime.now(timezone.utc)
        )
        self.db.add(record)

        # Audit history log
        history_id = _unique_id("VHIST", claim_id)
        history = VerificationHistory(
            history_id=history_id,
            claim_id=claim_id,
            result_id=result.result_id,
            previous_outcome=result.outcome.value,
            new_outcome=result.outcome.value,
            previous_verdict=result.verdict.value if result.verdict else None,
            new_verdict=result.verdict.value if result.verdict else "SUPPORTED",
            change_reason=f"Human Reviewer ({reviewer_id}) accepted automated assessment: {review_notes}",
            triggered_by=f"HUMAN_REVIEWER_{reviewer_id}",
            changed_at=datetime.now(timezone.utc)
        )
        self.db.add(history)

        self.db.commit()
        self.db.refresh(result)
        logger.info(f"Reviewer {reviewer_id} accepted verification for claim {claim_id}")
        return result

    def correct_claim_decomposition(
        self,
        claim_id: str,
        reviewer_id: str,
        corrected_atomics: List[Dict[str, Any]],
        review_notes: str
    ) -> VerificationResult:
        """
        Allows human reviewers to correct or add atomic propositions to an ingested claim.
        Preserves original text, updates atomic claims, and re-executes verification.
        """
        claim = self.db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim '{claim_id}' not found.")

        # Remove existing atomics and insert corrected ones
        self.db.query(AtomicClaim).filter(AtomicClaim.claim_id == claim_id).delete()

        new_atomics = []
        for idx, item in enumerate(corrected_atomics):
            ac_id = f"ACM-{claim_id}-REV-{idx+1:02d}"
            ac = AtomicClaim(
                atomic_claim_id=ac_id,
                claim_id=claim_id,
                atomic_claim_text=item["atomic_claim_text"],
                language=item.get("language", claim.language),
                subject=item.get("subject"),
                predicate=item.get("predicate"),
                action=item.get("action"),
                object=item.get("object"),
                time_period=item.get("time_period"),
                geographic_scope=item.get("geographic_scope", "Tamil Nadu"),
                numeric_value=item.get("numeric_value"),
                unit=item.get("unit"),
                denominator=item.get("denominator"),
                claim_type=item.get("claim_type", "NUMERICAL_STATISTIC"),
                verifiability_status=item.get("verifiability_status", "VERIFIABLE_FACTUAL"),
                decomposition_method="HUMAN_EXPERT_CORRECTION"
            )
            self.db.add(ac)
            new_atomics.append(ac)

        self.db.commit()

        # Re-synthesize outcome
        new_result = self.verify_claim(claim_id=claim_id)
        new_result.review_status = ReviewStatus.IN_REVIEW
        new_result.human_revision_notes = f"Decomposition corrected by {reviewer_id}: {review_notes}"

        # Record review entry
        rev_id = _unique_id("REV", claim_id)
        record = ReviewRecord(
            review_id=rev_id,
            claim_id=claim_id,
            verification_id=new_result.result_id,
            reviewer_id=reviewer_id,
            reviewer_role="LEAD_FACTCHECKER",
            review_status=ReviewStatus.IN_REVIEW,
            action=ReviewAction.CORRECT_CLAIM_DECOMPOSITION.value,
            original_outcome=new_result.automated_outcome.value if new_result.automated_outcome else None,
            reviewed_outcome=new_result.outcome.value,
            original_verdict=new_result.verdict.value if new_result.verdict else None,
            reviewed_verdict=new_result.verdict.value if new_result.verdict else "PARTIALLY_SUPPORTED",
            review_notes=review_notes,
            explanation=new_result.explanation,
            override_applied=True,
            reviewed_at=datetime.now(timezone.utc)
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(new_result)
        logger.info(f"Reviewer {reviewer_id} corrected decomposition for claim {claim_id}")
        return new_result

    def add_evidence(
        self,
        claim_id: str,
        reviewer_id: str,
        document_data: Dict[str, Any],
        passage_data: Dict[str, Any],
        relationship_type: str,
        review_notes: str,
        atomic_claim_id: Optional[str] = None
    ) -> VerificationResult:
        """
        Enables human analysts to introduce official documents or passage records.
        Links the new evidence and re-evaluates verification.
        """
        claim = self.db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim '{claim_id}' not found.")

        # Ingest or look up document
        doc_id = document_data["document_id"]
        doc = self.db.query(EvidenceDocument).filter(EvidenceDocument.document_id == doc_id).first()
        if not doc:
            doc = EvidenceDocument(
                document_id=doc_id,
                source_tier=SourceTier[document_data.get("source_tier", "TIER_1_STATUTORY")],
                source_name=document_data["source_name"],
                publisher=document_data.get("publisher"),
                document_type=document_data.get("document_type", "GOVERNMENT_ORDER"),
                source_category=document_data.get("source_category", "OFFICIAL_GOVERNMENT"),
                title=document_data["title"],
                publication_date=document_data.get("publication_date"),
                file_hash_sha256=document_data.get("file_hash_sha256", f"hash-{doc_id}"),
                language=document_data.get("language", "en"),
                is_official=True
            )
            self.db.add(doc)

        # Ingest passage
        pass_id = passage_data["passage_id"]
        passage = self.db.query(EvidencePassage).filter(EvidencePassage.passage_id == pass_id).first()
        if not passage:
            passage = EvidencePassage(
                passage_id=pass_id,
                document_id=doc_id,
                passage_text=passage_data["passage_text"],
                page_number=passage_data.get("page_number"),
                numerical_values=passage_data.get("numerical_values")
            )
            self.db.add(passage)

        rel_type_enum = EvidenceRelationshipType.from_string(relationship_type)
        rel_id = f"CER-{claim_id}-{pass_id}"
        rel = ClaimEvidenceRelationship(
            relationship_id=rel_id,
            claim_id=claim_id,
            atomic_claim_id=atomic_claim_id,
            evidence_document_id=doc_id,
            passage_id=pass_id,
            relationship_type=rel_type_enum,
            supporting_text_reference=passage_data.get("passage_text") if rel_type_enum == EvidenceRelationshipType.SUPPORTS else None,
            contradicting_text_reference=passage_data.get("passage_text") if rel_type_enum == EvidenceRelationshipType.CONTRADICTS else None,
            analysis_method="HUMAN_EXPERT_SUBMISSION",
            confidence=1.0,
            model_version="human-in-the-loop",
            reconciliation_notes=review_notes,
            created_at=datetime.now(timezone.utc)
        )
        self.db.merge(rel)
        self.db.commit()

        # Re-synthesize
        new_result = self.verify_claim(claim_id=claim_id)
        new_result.human_revision_notes = f"Evidence {doc_id} added by {reviewer_id}: {review_notes}"

        # Record review
        rev_id = _unique_id("REV", claim_id)
        record = ReviewRecord(
            review_id=rev_id,
            claim_id=claim_id,
            verification_id=new_result.result_id,
            reviewer_id=reviewer_id,
            reviewer_role="DOMAIN_EXPERT",
            review_status=ReviewStatus.IN_REVIEW,
            action=ReviewAction.ADD_EVIDENCE.value,
            original_outcome=new_result.automated_outcome.value if new_result.automated_outcome else None,
            reviewed_outcome=new_result.outcome.value,
            original_verdict=new_result.verdict.value if new_result.verdict else None,
            reviewed_verdict=new_result.verdict.value if new_result.verdict else "SUPPORTED",
            review_notes=review_notes,
            explanation=new_result.explanation,
            override_applied=True,
            reviewed_at=datetime.now(timezone.utc)
        )
        self.db.add(record)
        self.db.commit()
        return new_result

    def mark_evidence_irrelevant(
        self,
        claim_id: str,
        reviewer_id: str,
        relationship_id: str,
        reason: str
    ) -> VerificationResult:
        """
        Marks a specific candidate passage as irrelevant, excluding it from downstream synthesis.
        """
        rel = self.db.query(ClaimEvidenceRelationship).filter(
            ClaimEvidenceRelationship.relationship_id == relationship_id
        ).first()
        if not rel:
            raise ValueError(f"Relationship '{relationship_id}' not found.")

        rel.relationship_type = EvidenceRelationshipType.UNRELATED
        rel.reconciliation_notes = f"Excluded by human reviewer {reviewer_id}: {reason}"
        if not rel.metadata_json:
            rel.metadata_json = {}
        rel.metadata_json["is_marked_irrelevant"] = True
        rel.metadata_json["exclusion_reason"] = reason

        self.db.commit()

        # Re-synthesize
        new_result = self.verify_claim(claim_id=claim_id)
        new_result.human_revision_notes = f"Evidence {relationship_id} marked irrelevant by {reviewer_id}: {reason}"

        rev_id = _unique_id("REV", claim_id)
        record = ReviewRecord(
            review_id=rev_id,
            claim_id=claim_id,
            verification_id=new_result.result_id,
            reviewer_id=reviewer_id,
            reviewer_role="DOMAIN_EXPERT",
            review_status=ReviewStatus.IN_REVIEW,
            action=ReviewAction.MARK_EVIDENCE_IRRELEVANT.value,
            original_outcome=new_result.automated_outcome.value if new_result.automated_outcome else None,
            reviewed_outcome=new_result.outcome.value,
            original_verdict=new_result.verdict.value if new_result.verdict else None,
            reviewed_verdict=new_result.verdict.value if new_result.verdict else "SUPPORTED",
            review_notes=reason,
            explanation=new_result.explanation,
            override_applied=True,
            reviewed_at=datetime.now(timezone.utc)
        )
        self.db.add(record)
        self.db.commit()
        return new_result

    def revise_outcome(
        self,
        claim_id: str,
        reviewer_id: str,
        new_outcome: str,
        explanation: str,
        review_notes: str
    ) -> VerificationResult:
        """
        Allows human reviewers to override the automated outcome with explicit justification.
        Preserves the automated assessment baseline and logs revision history.
        """
        claim = self.db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim '{claim_id}' not found.")

        result = self.db.query(VerificationResult).filter(
            VerificationResult.claim_id == claim_id,
            VerificationResult.is_current == True
        ).first()
        if not result:
            raise ValueError(f"No active verification result found for claim '{claim_id}'.")

        revised_enum = VerificationOutcome.from_string(new_outcome)
        previous_outcome = result.outcome.value if result.outcome else None

        # Update current result while preserving automated baseline
        result.outcome = revised_enum
        result.explanation = explanation
        result.review_status = ReviewStatus.OVERRIDDEN
        result.human_revision_notes = f"Outcome revised by {reviewer_id}: {review_notes}"
        claim.review_status = ReviewStatus.OVERRIDDEN

        # Log review record
        rev_id = _unique_id("REV", claim_id)
        record = ReviewRecord(
            review_id=rev_id,
            claim_id=claim_id,
            verification_id=result.result_id,
            reviewer_id=reviewer_id,
            reviewer_role="SENIOR_EDITOR",
            review_status=ReviewStatus.OVERRIDDEN,
            action=ReviewAction.REVISE_OUTCOME.value,
            original_outcome=previous_outcome,
            reviewed_outcome=revised_enum.value,
            original_verdict=result.verdict.value if result.verdict else None,
            reviewed_verdict=revised_enum.value,
            review_notes=review_notes,
            explanation=explanation,
            override_applied=True,
            reviewed_at=datetime.now(timezone.utc)
        )
        self.db.add(record)

        # Log audit history
        history_id = _unique_id("VHIST", claim_id)
        history = VerificationHistory(
            history_id=history_id,
            claim_id=claim_id,
            result_id=result.result_id,
            previous_outcome=previous_outcome,
            new_outcome=revised_enum.value,
            previous_verdict=result.verdict.value if result.verdict else None,
            new_verdict=revised_enum.value,
            change_reason=f"Human override by {reviewer_id}: {review_notes}",
            triggered_by=f"HUMAN_REVIEWER_{reviewer_id}",
            changed_at=datetime.now(timezone.utc)
        )
        self.db.add(history)

        self.db.commit()
        self.db.refresh(result)
        logger.info(f"Reviewer {reviewer_id} revised outcome of claim {claim_id} to {revised_enum.value}")
        return result
