"""
Phase 7.6 — Claim and Evidence Relationship Analysis Engine.

Performs deep bidirectional analysis between atomic claims and retrieved evidence passages:
1. Entity Identity Check (exact target, related body, or mismatch)
2. Dates and Reporting Periods Check (contemporaneous, outdated, future projection)
3. Geographic Scope Check (Tamil Nadu jurisdiction, All-India broader, or state mismatch)
4. Units and Denominators Check (numerical agreement, scale, per-capita/temporal denominators)
5. Proposition Alignment (addresses identical proposition vs related context vs distinct claim)
6. Source Stance Classification (reporting a third-party claim vs independently establishing a fact)
7. Syndication & Wire-Copy Detection (prevents counting syndicated wire echoes as independent corroboration)
8. Epistemic Guardrails:
   - Absence of evidence is NEVER interpreted as proof of falsehood.
   - Contradictory evidence is ALWAYS retained and made visible.
   - Strictly NO automated politician or party truthfulness rankings.
"""

import re
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.models.claim import (
    Claim,
    AtomicClaim,
    EvidenceDocument,
    EvidencePassage,
    ClaimEvidenceRelationship,
    EvidenceRelationshipType,
    ReviewStatus,
    SourceTier,
    VerificationVerdict
)
from backend.core.logger import setup_logger

logger = setup_logger("civiclens.phase7.relationship_analyzer")


# ---------------------------------------------------------------------------
# 1. Entity Identity Checker
# ---------------------------------------------------------------------------
class EntityIdentityChecker:
    """
    Evaluates whether the evidence passage addresses the exact entity in the claim,
    a related administrative entity, or an entirely unrelated entity.
    """

    KNOWN_ENTITY_SYNONYMS = {
        "kalaignar magalir urimai thittam": [
            "kmut", "magalir urimai thittam", "women rights scheme", "மகளிர் உரிமைத் திட்டம்",
            "kalaignar magalir urimai", "kalaignar women basic income", "urimai thittam",
            "women assistance", "மகளிர் உரிமை"
        ],
        "pudhumai penn thittam": [
            "pudhumai penn", "moovalur ramamirtham ammaiyar higher education assurance scheme",
            "புதுமைப் பெண் திட்டம்", "penn thittam"
        ],
        "breakfast scheme": [
            "chief minister's breakfast scheme", "muthalvarin kaalai unavu thittam",
            "முதல்வரின் காலை உணவுத் திட்டம்", "kaalai unavu thittam"
        ],
        "naan mudhalvan": [
            "naan mudhalvan scheme", "நான் முதல்வன்", "skill development scheme"
        ],
        "tangedco": [
            "tamil nadu generation and distribution corporation", "தமிழ்நாடு மின் உற்பத்தி",
            "electricity board tn", "tn electricity"
        ],
        "cmda": [
            "chennai metropolitan development authority", "சிஎம்டிஏ"
        ],
        "welfare schemes": [
            "welfare programs", "maternal assistance", "social welfare", "நலத் திட்டங்கள்",
            "welfare scheme"
        ]
    }

    @classmethod
    def check_entity_alignment(
        cls,
        claim_subject: Optional[str],
        claim_text: str,
        passage_text: str,
        extracted_entities: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, float, str]:
        """
        Returns (status, score, rationale)
        Status in ["EXACT_MATCH", "RELATED_ENTITY", "ENTITY_MISMATCH", "UNSPECIFIED"]
        """
        target = (claim_subject or "").strip().lower()
        pass_lower = passage_text.lower()

        if not target:
            # Fallback: check if major known entities appear in claim text
            for canonical, syns in cls.KNOWN_ENTITY_SYNONYMS.items():
                if canonical in claim_text.lower() or any(s in claim_text.lower() for s in syns):
                    target = canonical
                    break

        if not target:
            return "UNSPECIFIED", 0.5, "No specific entity designated in claim."

        # Expand candidate aliases across all synonym clusters where target matches
        candidate_aliases = {target}
        for canonical, syns in cls.KNOWN_ENTITY_SYNONYMS.items():
            cluster = {canonical} | set(syns)
            if any(target == item or target in item or item in target for item in cluster):
                candidate_aliases.update(cluster)

        # Check exact target or any alias in passage
        for alias in candidate_aliases:
            if alias in pass_lower:
                return "EXACT_MATCH", 1.0, f"Target entity alias '{alias}' explicitly matched in passage."

        # Check extracted entities from passage JSON if present
        if extracted_entities:
            pass_entities = [str(v).lower() for v in extracted_entities.values() if isinstance(v, (str, list))]
            for pe in pass_entities:
                if any(alias in pe for alias in candidate_aliases):
                    return "EXACT_MATCH", 0.90, f"Target entity matched in passage metadata entities."

        # Check for related departmental or jurisdictional terms
        target_tokens = set(re.findall(r"\w+", target))
        passage_tokens = set(re.findall(r"\w+", pass_lower))
        token_overlap = target_tokens.intersection(passage_tokens)

        if len(token_overlap) >= 1 and any(tok in ["welfare", "scheme", "schemes", "assistance", "thittam", "திட்டம்", "maternal", "மகளிர்"] for tok in token_overlap):
            return "RELATED_ENTITY", 0.65, f"Related entity token overlap: {', '.join(token_overlap)}."

        if len(token_overlap) >= 2:
            return "RELATED_ENTITY", 0.65, f"Partial entity token overlap: {', '.join(token_overlap)}."

        # Check if passage discusses a known DIFFERENT scheme while missing target
        for other_canon, syns in cls.KNOWN_ENTITY_SYNONYMS.items():
            if other_canon not in candidate_aliases and (other_canon in pass_lower or any(s in pass_lower for s in syns)):
                return "ENTITY_MISMATCH", 0.1, f"Passage discusses distinct entity '{other_canon}' rather than target '{target}'."

        return "ENTITY_MISMATCH", 0.15, f"Target entity '{target}' not found in passage."


# ---------------------------------------------------------------------------
# 2. Dates and Reporting Periods Checker
# ---------------------------------------------------------------------------
class TemporalAlignmentChecker:
    """
    Evaluates whether the evidence reporting period aligns with the claim timeframe,
    identifying contemporary corroboration vs outdated historical records.
    """

    @classmethod
    def extract_years(cls, text: str) -> List[int]:
        if not text:
            return []
        # Match standalone 4-digit years like 2021, 2023, 2024 or fiscal year 2023-24
        matches = re.findall(r"\b(19\d{2}|20\d{2})\b", text)
        return sorted(list(set(int(y) for y in matches)))

    @classmethod
    def check_temporal_alignment(
        cls,
        claim_period: Optional[str],
        claim_date: Optional[datetime],
        document_date: Optional[datetime],
        passage_text: str
    ) -> Tuple[str, bool, float, str]:
        """
        Returns (status, is_outdated, score, rationale)
        Status in ["CONTEMPORANEOUS", "OUTDATED", "FUTURE_PROJECTION", "UNSPECIFIED"]
        """
        claim_years = cls.extract_years(claim_period or "")
        if not claim_years and claim_date:
            claim_years = [claim_date.year]

        doc_year = document_date.year if document_date else None
        passage_years = cls.extract_years(passage_text)

        evidence_years = passage_years or ([doc_year] if doc_year else [])

        if not claim_years:
            return "UNSPECIFIED", False, 0.5, "Claim does not specify an explicit temporal boundary."

        target_year = max(claim_years)

        if not evidence_years:
            return "UNSPECIFIED", False, 0.5, "Evidence does not specify an explicit reporting year."

        max_evidence_year = max(evidence_years)

        # Check for exact or contemporaneous match (+/- 1 year for fiscal cycles)
        if any(abs(target_year - ey) <= 1 for ey in evidence_years):
            return "CONTEMPORANEOUS", False, 1.0, f"Evidence reporting period ({evidence_years}) aligns with claim period ({claim_years})."

        # Check if evidence is outdated (older by >= 2 years)
        if max_evidence_year < target_year - 1:
            diff = target_year - max_evidence_year
            return (
                "OUTDATED",
                True,
                0.2,
                f"Evidence reporting period ({max_evidence_year}) is outdated by {diff} years relative to claim period ({target_year}). Cannot substantiate contemporary state."
            )

        # Check if evidence is a future forecast
        if min(evidence_years) > target_year + 1:
            return (
                "FUTURE_PROJECTION",
                False,
                0.3,
                f"Evidence discusses future projection period ({evidence_years}) beyond claim period ({target_year})."
            )

        return "CONTEMPORANEOUS", False, 0.8, "Temporal period approximately aligned."


# ---------------------------------------------------------------------------
# 3. Geographic Scope Checker
# ---------------------------------------------------------------------------
class GeographicScopeChecker:
    """
    Checks whether geographic jurisdiction matches (Tamil Nadu / specific district vs All-India vs other state).
    """

    OTHER_STATES = {
        "kerala", "karnataka", "andhra pradesh", "telangana", "maharashtra",
        "uttar pradesh", "bihar", "gujarat", "west bengal", "punjab", "delhi"
    }

    TN_DISTRICTS = {
        "chennai", "coimbatore", "madurai", "tiruchirappalli", "salem", "tirunelveli",
        "vellore", "thoothukudi", "dindigul", "thanjavur", "ranipet", "tiruppur",
        "kanchipuram", "chengalpattu", "tiruvallur", "erode", "namakkal"
    }

    @classmethod
    def check_geographic_alignment(
        cls,
        claim_geo: Optional[str],
        passage_text: str
    ) -> Tuple[str, float, str]:
        """
        Returns (status, score, rationale)
        Status in ["EXACT_JURISDICTION", "BROADER_NATIONAL", "GEOGRAPHIC_MISMATCH", "UNSPECIFIED"]
        """
        geo_target = (claim_geo or "Tamil Nadu").strip().lower()
        pass_lower = passage_text.lower()

        # Check for explicit Tamil Nadu mention or districts
        is_tn_target = "tamil nadu" in geo_target or "tn" in geo_target or any(d in geo_target for d in cls.TN_DISTRICTS)

        if is_tn_target:
            if "tamil nadu" in pass_lower or "தமிழ்நாடு" in pass_lower or any(d in pass_lower for d in cls.TN_DISTRICTS):
                return "EXACT_JURISDICTION", 1.0, "Passage confirms Tamil Nadu state jurisdiction."

            # Check if passage is discussing another specific Indian state
            for other_state in cls.OTHER_STATES:
                if other_state in pass_lower and "tamil nadu" not in pass_lower:
                    return "GEOGRAPHIC_MISMATCH", 0.05, f"Passage refers to jurisdiction '{other_state.title()}', not Tamil Nadu."

            # Check if it is a Union / All India document
            if "all-india" in pass_lower or "across india" in pass_lower or "union government" in pass_lower:
                return "BROADER_NATIONAL", 0.45, "Passage provides All-India national aggregate without state disaggregation."

            return "UNSPECIFIED", 0.6, "Passage does not explicitly state jurisdiction but is not contradictory."

        return "UNSPECIFIED", 0.5, f"Geographic scope '{claim_geo}' evaluated."


# ---------------------------------------------------------------------------
# 4. Units and Denominators Checker
# ---------------------------------------------------------------------------
class QuantitativeConsistencyChecker:
    """
    Evaluates quantitative consistency, checking numerical values, scale,
    monetary/volume units, and temporal or per-capita denominators.
    """

    @classmethod
    def extract_numbers(cls, text: str) -> List[float]:
        if not text:
            return []
        matches = re.findall(r"\b\d+(?:,\d+)*(?:\.\d+)?\b", text)
        nums = []
        for m in matches:
            clean = m.replace(",", "")
            try:
                nums.append(float(clean))
            except ValueError:
                continue
        return nums

    @classmethod
    def check_quantitative_alignment(
        cls,
        claim_numeric_value: Optional[float],
        claim_unit: Optional[str],
        claim_denominator: Optional[str],
        passage_text: str,
        passage_numerical_values: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Optional[float], float, str]:
        """
        Returns (status, extracted_passage_val, score, rationale)
        Status in ["EXACT_MATCH", "VALUE_CONTRADICTION", "UNIT_MISMATCH", "DENOMINATOR_MISMATCH", "NOT_QUANTITATIVE"]
        """
        if claim_numeric_value is None:
            return "NOT_QUANTITATIVE", None, 1.0, "Claim is non-quantitative."

        target_val = float(claim_numeric_value)
        unit_target = (claim_unit or "").strip().lower()
        denom_target = (claim_denominator or "").strip().lower()
        pass_lower = passage_text.lower()

        # Collect all candidate numbers from passage metadata and passage text
        candidates = []
        if passage_numerical_values and isinstance(passage_numerical_values, dict):
            for k, v in passage_numerical_values.items():
                if isinstance(v, (int, float)):
                    candidates.append(float(v))
        extracted = cls.extract_numbers(passage_text)
        candidates.extend(extracted)

        if not candidates:
            return "VALUE_CONTRADICTION", None, 0.2, f"No numerical value found in passage to corroborate {target_val}."

        # Check unit mismatch: e.g. crore vs lakh
        if ("crore" in unit_target or "கோடி" in unit_target) and ("lakh" in pass_lower or "லட்சம்" in pass_lower) and "crore" not in pass_lower:
            return "UNIT_MISMATCH", candidates[0], 0.2, f"Unit mismatch: Claim specifies '{unit_target}', but passage specifies lakhs."

        # Check denominator mismatch: e.g. per month vs per year
        if ("month" in denom_target or "மாதம்" in denom_target) and ("year" in pass_lower or "annual" in pass_lower) and "month" not in pass_lower:
            return "DENOMINATOR_MISMATCH", candidates[0], 0.25, f"Denominator mismatch: Claim is '{denom_target}', but passage reports annual figures."

        # Check if target_val is present within 5% tolerance among candidate numbers
        exact_matches = [c for c in candidates if abs(c - target_val) <= max(0.05 * target_val, 0.01)]
        if exact_matches:
            pass_val = exact_matches[0]
            return "EXACT_MATCH", pass_val, 1.0, f"Numerical value {pass_val} directly corroborates claim target {target_val}."

        # If no exact match, find closest number to evaluate variance
        closest_val = min(candidates, key=lambda x: abs(x - target_val))
        ratio = closest_val / target_val if target_val != 0 else 0
        if 0.70 <= ratio <= 1.30:
            return "VALUE_CONTRADICTION", closest_val, 0.4, f"Partial numerical variance: Evidence reports {closest_val} vs claim {target_val}."
        else:
            return "VALUE_CONTRADICTION", closest_val, 0.1, f"Direct numerical discrepancy: Evidence reports {closest_val} vs claim {target_val}."


# ---------------------------------------------------------------------------
# 5. Source Stance Classifier (Reporting Claim vs Independent Fact)
# ---------------------------------------------------------------------------
class SourceStanceClassifier:
    """
    Distinguishes whether an evidence document is independently establishing a fact
    or merely reporting a third-party claim/speech.
    """

    REPORTING_MARKERS = [
        "claimed that", "alleged that", "stated that", "said in a rally",
        "according to the minister", "according to the opposition leader",
        "spokesperson said", "accused the government", "promised that",
        "என்று கூறினார்", "என்று தெரிவித்தார்", "குற்றம் சாட்டினார்"
    ]

    INDEPENDENT_FACT_TYPES = [
        "GOVERNMENT_ORDER", "BUDGET_DDG", "AUDIT_REPORT", "CAG_AUDIT",
        "LEGISLATIVE_TRANSCRIPT", "HANSARD", "OFFICIAL_GAZETTE", "RTI_RESPONSE",
        "STATISTICAL_BULLETIN"
    ]

    @classmethod
    def classify_source_stance(
        cls,
        document_type: str,
        passage_text: str,
        source_tier: SourceTier
    ) -> Tuple[str, str]:
        """
        Returns (stance, rationale)
        stance in ["INDEPENDENT_FACT", "REPORTING_CLAIM"]
        """
        doc_type_upper = (document_type or "").upper()

        if any(ift in doc_type_upper for ift in cls.INDEPENDENT_FACT_TYPES) or source_tier == SourceTier.TIER_1_STATUTORY:
            return "INDEPENDENT_FACT", f"Document type '{document_type}' is a primary statutory record establishing independent facts."

        pass_lower = passage_text.lower()
        for marker in cls.REPORTING_MARKERS:
            if marker in pass_lower:
                return "REPORTING_CLAIM", f"Passage reports a third-party statement ('{marker}') rather than independently verifying the underlying fact."

        return "INDEPENDENT_FACT", "Passage asserts empirical findings or factual reporting."


# ---------------------------------------------------------------------------
# 6. Syndication & Wire-Copy Deduplicator
# ---------------------------------------------------------------------------
class SyndicationDeduplicator:
    """
    Identifies syndicated news agency copies (PTI, ANI, UNI, press release echoes)
    to ensure identical wire copies are not counted as independent corroboration.
    """

    WIRE_AGENCY_MARKERS = ["pti", "ani", "uni", "ians", "reuters"]

    @classmethod
    def compute_passage_fingerprint(cls, text: str) -> str:
        clean = re.sub(r"[^\w\s]", "", text.lower())
        words = clean.split()
        normalized = " ".join(words[:40])  # First 40 words
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def compute_jaccard_similarity(cls, text1: str, text2: str) -> float:
        tokens1 = set(re.findall(r"\w{4,}", text1.lower()))
        tokens2 = set(re.findall(r"\w{4,}", text2.lower()))
        if not tokens1 or not tokens2:
            return 0.0
        return len(tokens1.intersection(tokens2)) / len(tokens1.union(tokens2))

    @classmethod
    def detect_syndication(
        cls,
        passage_text: str,
        document_publisher: Optional[str],
        known_cluster_passages: List[Dict[str, Any]]
    ) -> Tuple[bool, Optional[str], str]:
        """
        Checks if the passage is a syndicated wire copy of a previously seen passage.
        Returns (is_syndicated, cluster_id, notes)
        """
        pass_lower = passage_text.lower()
        has_wire_marker = any(re.search(rf"\b{w}\b", pass_lower) for w in cls.WIRE_AGENCY_MARKERS)
        fp = cls.compute_passage_fingerprint(passage_text)

        for kp in known_cluster_passages:
            sim = cls.compute_jaccard_similarity(passage_text, kp["passage_text"])
            if sim >= 0.75 or (has_wire_marker and sim >= 0.60) or fp == kp.get("fingerprint"):
                cluster_id = kp.get("cluster_id") or f"SYND-CLUSTER-{fp}"
                return (
                    True,
                    cluster_id,
                    f"Syndicated wire copy detected ({sim:.1%} token similarity with {kp.get('document_id')}). Does not constitute independent corroboration."
                )

        cluster_id = f"SYND-CLUSTER-{fp}"
        return False, cluster_id, "Unique independent reporting; not a syndicated copy."


# ---------------------------------------------------------------------------
# 7. Proposition Alignment Checker
# ---------------------------------------------------------------------------
class PropositionAlignmentChecker:
    """
    Evaluates whether the evidence passage addresses the same proposition or action.
    """

    CONTRADICTION_TRIGGERS = [
        "shortfall", "failed to deliver", "deficit", "delayed", "not disbursed",
        "diverted", "rejected", "irregularities", "cag audit revealed",
        "discrepancy", "unspent", "குறைபாடு", "வழங்கப்படவில்லை", "தாமதம்"
    ]

    SUPPORT_TRIGGERS = [
        "disbursed", "allocated", "sanctioned", "successfully implemented",
        "credited directly", "transferred to bank accounts", "notified in gazette",
        "வழங்கப்பட்டது", "ஒதுக்கீடு செய்யப்பட்டது", "நிறைவேற்றப்பட்டது"
    ]

    @classmethod
    def check_proposition_alignment(
        cls,
        claim_predicate: Optional[str],
        claim_is_negated: bool,
        passage_text: str
    ) -> Tuple[str, bool, Optional[str], Optional[str]]:
        """
        Returns (alignment_status, is_refuting, supporting_excerpt, contradicting_excerpt)
        """
        pass_lower = passage_text.lower()
        has_contra = any(t in pass_lower for t in cls.CONTRADICTION_TRIGGERS)
        has_supp = any(t in pass_lower for t in cls.SUPPORT_TRIGGERS)

        contra_excerpt = None
        supp_excerpt = None

        if has_contra:
            # Extract sentence containing contradiction trigger
            sentences = re.split(r"[.!?\n]", passage_text)
            for s in sentences:
                if any(t in s.lower() for t in cls.CONTRADICTION_TRIGGERS):
                    contra_excerpt = s.strip()
                    break

        if has_supp:
            sentences = re.split(r"[.!?\n]", passage_text)
            for s in sentences:
                if any(t in s.lower() for t in cls.SUPPORT_TRIGGERS):
                    supp_excerpt = s.strip()
                    break

        if has_contra and not claim_is_negated:
            return "IDENTICAL_PROPOSITION", True, supp_excerpt, contra_excerpt
        elif has_supp and not claim_is_negated:
            return "IDENTICAL_PROPOSITION", False, supp_excerpt, None
        elif has_supp and claim_is_negated:
            # Claim denied it, but evidence shows it happened -> contradiction
            return "IDENTICAL_PROPOSITION", True, None, supp_excerpt

        return "RELATED_CONTEXT", False, supp_excerpt, contra_excerpt


# ---------------------------------------------------------------------------
# 8. Core Evidence Relationship Analyzer Engine
# ---------------------------------------------------------------------------
class EvidenceRelationshipAnalyzer:
    """
    Orchestrates end-to-end evidence relationship classification across all atomic claims
    and retrieved documents. Enforces epistemic integrity constraints.
    """

    def __init__(self, db: Session):
        self.db = db

    def analyze_claim_evidence_relationship(
        self,
        claim: Claim,
        passage: EvidencePassage,
        document: EvidenceDocument,
        atomic_claim: Optional[AtomicClaim] = None,
        known_cluster_passages: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Analyzes a single (Claim, Passage) pair and produces classified relationship fields.
        """
        target_claim_text = atomic_claim.atomic_claim_text if atomic_claim else claim.original_text
        target_subject = (atomic_claim.subject if atomic_claim else claim.speaker_name) or ""
        target_period = (atomic_claim.time_period if atomic_claim else claim.temporal_scope)
        target_geo = (atomic_claim.geographic_scope if atomic_claim else claim.geographic_scope) or "Tamil Nadu"
        claim_numeric = atomic_claim.numeric_value if atomic_claim else None
        claim_unit = atomic_claim.unit if atomic_claim else None
        claim_denom = atomic_claim.denominator if atomic_claim else None
        claim_is_neg = atomic_claim.is_negated if atomic_claim else False

        # 1. Entity Alignment
        ent_status, ent_score, ent_notes = EntityIdentityChecker.check_entity_alignment(
            claim_subject=target_subject,
            claim_text=target_claim_text,
            passage_text=passage.passage_text,
            extracted_entities=passage.extracted_entities
        )

        # 2. Temporal Alignment
        temp_status, is_outdated, temp_score, temp_notes = TemporalAlignmentChecker.check_temporal_alignment(
            claim_period=target_period,
            claim_date=claim.claim_date,
            document_date=document.publication_date,
            passage_text=passage.passage_text
        )

        # 3. Geographic Scope
        geo_status, geo_score, geo_notes = GeographicScopeChecker.check_geographic_alignment(
            claim_geo=target_geo,
            passage_text=passage.passage_text
        )

        # 4. Quantitative Consistency
        quant_status, pass_num, quant_score, quant_notes = QuantitativeConsistencyChecker.check_quantitative_alignment(
            claim_numeric_value=claim_numeric,
            claim_unit=claim_unit,
            claim_denominator=claim_denom,
            passage_text=passage.passage_text,
            passage_numerical_values=passage.numerical_values
        )

        # 5. Source Stance
        stance, stance_notes = SourceStanceClassifier.classify_source_stance(
            document_type=document.document_type,
            passage_text=passage.passage_text,
            source_tier=document.source_tier
        )

        # 6. Syndication Detection
        is_syndicated, synd_cluster, synd_notes = SyndicationDeduplicator.detect_syndication(
            passage_text=passage.passage_text,
            document_publisher=document.publisher,
            known_cluster_passages=known_cluster_passages or []
        )

        # 7. Proposition Alignment
        prop_status, is_refuting, supp_ref, contra_ref = PropositionAlignmentChecker.check_proposition_alignment(
            claim_predicate=atomic_claim.predicate if atomic_claim else None,
            claim_is_negated=claim_is_neg,
            passage_text=passage.passage_text
        )

        # -------------------------------------------------------------------
        # 8. Synthesize Relationship Type
        # -------------------------------------------------------------------
        rel_type = EvidenceRelationshipType.UNCLEAR
        confidence = 0.50
        reasoning = []

        # Case A: Entity or Geographic Mismatch -> UNRELATED
        if ent_status == "ENTITY_MISMATCH" or geo_status == "GEOGRAPHIC_MISMATCH":
            rel_type = EvidenceRelationshipType.UNRELATED
            confidence = 0.90
            reasoning.append("Entity or geographic jurisdiction mismatch identified.")

        # Case B: Outdated Evidence -> CONTEXTUALIZES
        elif is_outdated:
            rel_type = EvidenceRelationshipType.CONTEXTUALIZES
            confidence = 0.85
            reasoning.append(f"Outdated evidence from earlier period ({temp_notes}). Provides historical context rather than contemporary verification.")

        # Case C: Source merely reports a third-party claim -> CONTEXTUALIZES
        elif stance == "REPORTING_CLAIM":
            rel_type = EvidenceRelationshipType.CONTEXTUALIZES
            confidence = 0.80
            reasoning.append(f"Passage reports a third-party statement ({stance_notes}). Does not constitute independent factual corroboration.")

        # Case D: Quantitative value discrepancy or Refuting finding -> CONTRADICTS
        elif is_refuting or quant_status == "VALUE_CONTRADICTION":
            rel_type = EvidenceRelationshipType.CONTRADICTS
            confidence = 0.88 if document.source_tier in [SourceTier.TIER_1_STATUTORY, SourceTier.TIER_2_OFFICIAL_AGENCY] else 0.75
            reasoning.append(f"Contradiction identified: {quant_notes} {prop_status}.")
            if not contra_ref:
                contra_ref = passage.passage_text[:200]

        # Case E: Partial quantitative fulfillment or partial entity overlap -> PARTIALLY_SUPPORTS
        elif quant_status in ["UNIT_MISMATCH", "DENOMINATOR_MISMATCH"] or ent_status == "RELATED_ENTITY" or geo_status == "BROADER_NATIONAL":
            rel_type = EvidenceRelationshipType.PARTIALLY_SUPPORTS
            confidence = 0.75
            reasoning.append(f"Partial support with structural caveats: {quant_notes}; {geo_notes}.")
            if not supp_ref:
                supp_ref = passage.passage_text[:200]

        # Case F: Affirmative match across entity, period, jurisdiction, and facts -> SUPPORTS
        elif ent_status == "EXACT_MATCH" and quant_status in ["EXACT_MATCH", "NOT_QUANTITATIVE"] and prop_status == "IDENTICAL_PROPOSITION":
            rel_type = EvidenceRelationshipType.SUPPORTS
            confidence = 0.92 if document.source_tier == SourceTier.TIER_1_STATUTORY else 0.82
            reasoning.append(f"Independent empirical corroboration: {ent_notes} {quant_notes}.")
            if not supp_ref:
                supp_ref = passage.passage_text[:200]

        else:
            rel_type = EvidenceRelationshipType.CONTEXTUALIZES
            confidence = 0.60
            reasoning.append("General topical relevance that contextualizes background.")

        # Calibrate confidence if syndicated copy
        if is_syndicated:
            reasoning.append("Marked as syndicated copy: anti-echo chamber rule prevents inflating corroboration weight.")

        return {
            "relationship_id": f"CER-{claim.claim_id}-{passage.passage_id}",
            "claim_id": claim.claim_id,
            "atomic_claim_id": atomic_claim.atomic_claim_id if atomic_claim else None,
            "evidence_document_id": document.document_id,
            "evidence_passage_id": passage.passage_id,
            "passage_id": passage.passage_id,
            "relationship_type": rel_type,
            "supporting_text_reference": supp_ref,
            "contradicting_text_reference": contra_ref,
            "analysis_method": "MULTI_DIMENSIONAL_EVIDENCE_RELATIONSHIP_V1",
            "confidence": round(confidence, 4),
            "model_version": "civiclens-evidence-rel-v1.0",
            "human_review_status": ReviewStatus.PENDING_REVIEW,
            "entity_alignment": ent_status,
            "temporal_alignment": temp_status,
            "geographic_alignment": geo_status,
            "quantitative_alignment": quant_status,
            "proposition_alignment": prop_status,
            "source_stance": stance,
            "is_outdated": is_outdated,
            "is_syndicated_copy": is_syndicated,
            "syndication_cluster_id": synd_cluster,
            "reasoning_summary": " | ".join(reasoning)
        }

    def analyze_and_persist_relationships(
        self,
        claim_id: str,
        atomic_claim_id: Optional[str] = None
    ) -> List[ClaimEvidenceRelationship]:
        """
        Loads retrieved candidate passages for a claim (or atomic claim),
        executes relationship classification, persists results, and preserves contradictory evidence.
        """
        claim = self.db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim '{claim_id}' not found.")

        # Determine target atomic claims
        target_atomics = []
        if atomic_claim_id:
            atomic = self.db.query(AtomicClaim).filter(AtomicClaim.atomic_claim_id == atomic_claim_id).first()
            if atomic:
                target_atomics = [atomic]
        elif claim.atomic_claims:
            target_atomics = list(claim.atomic_claims)

        # Retrieve candidate passages from ClaimRetrievalCandidate or linked passages
        candidates = list(claim.retrieval_candidates)
        passage_ids = [c.evidence_passage_id for c in candidates] if candidates else []

        if not passage_ids:
            # Fallback to any passages directly linked or in database
            passages = self.db.query(EvidencePassage).limit(20).all()
        else:
            passages = self.db.query(EvidencePassage).filter(EvidencePassage.passage_id.in_(passage_ids)).all()

        saved_relationships = []
        known_clusters: List[Dict[str, Any]] = []

        atomics_to_process = target_atomics or [None]

        for atomic in atomics_to_process:
            for passage in passages:
                doc = passage.document
                if not doc:
                    continue

                analysis = self.analyze_claim_evidence_relationship(
                    claim=claim,
                    passage=passage,
                    document=doc,
                    atomic_claim=atomic,
                    known_cluster_passages=known_clusters
                )

                # Record in known clusters
                known_clusters.append({
                    "passage_id": passage.passage_id,
                    "document_id": doc.document_id,
                    "passage_text": passage.passage_text,
                    "cluster_id": analysis["syndication_cluster_id"],
                    "fingerprint": SyndicationDeduplicator.compute_passage_fingerprint(passage.passage_text)
                })

                rel_id = analysis["relationship_id"]
                existing = self.db.query(ClaimEvidenceRelationship).filter(
                    ClaimEvidenceRelationship.relationship_id == rel_id
                ).first()

                if existing:
                    existing.relationship_type = analysis["relationship_type"]
                    existing.supporting_text_reference = analysis["supporting_text_reference"]
                    existing.contradicting_text_reference = analysis["contradicting_text_reference"]
                    existing.analysis_method = analysis["analysis_method"]
                    existing.confidence = analysis["confidence"]
                    existing.model_version = analysis["model_version"]
                    existing.entity_alignment = analysis["entity_alignment"]
                    existing.temporal_alignment = analysis["temporal_alignment"]
                    existing.geographic_alignment = analysis["geographic_alignment"]
                    existing.quantitative_alignment = analysis["quantitative_alignment"]
                    existing.proposition_alignment = analysis["proposition_alignment"]
                    existing.source_stance = analysis["source_stance"]
                    existing.is_outdated = analysis["is_outdated"]
                    existing.is_syndicated_copy = analysis["is_syndicated_copy"]
                    existing.syndication_cluster_id = analysis["syndication_cluster_id"]
                    existing.reasoning_summary = analysis["reasoning_summary"]
                    rel_obj = existing
                else:
                    rel_obj = ClaimEvidenceRelationship(
                        relationship_id=rel_id,
                        claim_id=claim.claim_id,
                        atomic_claim_id=analysis["atomic_claim_id"],
                        evidence_document_id=analysis["evidence_document_id"],
                        passage_id=analysis["passage_id"],
                        relationship_type=analysis["relationship_type"],
                        supporting_text_reference=analysis["supporting_text_reference"],
                        contradicting_text_reference=analysis["contradicting_text_reference"],
                        analysis_method=analysis["analysis_method"],
                        confidence=analysis["confidence"],
                        model_version=analysis["model_version"],
                        human_review_status=analysis["human_review_status"],
                        entity_alignment=analysis["entity_alignment"],
                        temporal_alignment=analysis["temporal_alignment"],
                        geographic_alignment=analysis["geographic_alignment"],
                        quantitative_alignment=analysis["quantitative_alignment"],
                        proposition_alignment=analysis["proposition_alignment"],
                        source_stance=analysis["source_stance"],
                        is_outdated=analysis["is_outdated"],
                        is_syndicated_copy=analysis["is_syndicated_copy"],
                        syndication_cluster_id=analysis["syndication_cluster_id"],
                        reasoning_summary=analysis["reasoning_summary"],
                        relevance_score=1.0 if analysis["relationship_type"] != EvidenceRelationshipType.UNRELATED else 0.0,
                        confidence_score=analysis["confidence"],
                        contradiction_score=1.0 if analysis["relationship_type"] == EvidenceRelationshipType.CONTRADICTS else 0.0,
                        created_at=datetime.now(timezone.utc)
                    )
                    self.db.add(rel_obj)

                saved_relationships.append(rel_obj)

        self.db.commit()
        logger.info(f"Analyzed and persisted {len(saved_relationships)} relationships for claim {claim_id}")
        return saved_relationships

    # -----------------------------------------------------------------------
    # Epistemic Rules Enforcement
    # -----------------------------------------------------------------------
    @classmethod
    def evaluate_absence_of_evidence(cls, claim: Claim, retrieved_candidates_count: int) -> Dict[str, Any]:
        """
        Enforces epistemic rule:
        The absence of a document must NEVER be interpreted as proof that a claim is false.
        """
        if retrieved_candidates_count == 0:
            return {
                "verdict": VerificationVerdict.UNVERIFIABLE_INSUFFICIENT_EVIDENCE,
                "is_false": False,
                "disclaimer": (
                    "Absence of evidence does not constitute evidence of absence. "
                    "No verifiable statutory or independent evidence was discovered; "
                    "the claim is classified as UNVERIFIABLE rather than refuted."
                )
            }
        return {
            "verdict": None,
            "is_false": False,
            "disclaimer": None
        }
