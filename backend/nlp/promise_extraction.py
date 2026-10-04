"""
Political promise extraction pipeline (Phase 3.5).

Turns extracted manifesto text segments (output of the document processing
pipeline, see backend/ingestion/processor.py) into individual promise records.

Design rules:
- ``original_text`` is always an exact, unmodified substring of the source segment.
  Character offsets (``char_start``/``char_end``) are stored so this can be checked.
- ``normalized_text`` is derived separately, and only by Unicode NFC + whitespace
  collapsing. Wording is never rewritten.
- Classification is a transparent rule-based heuristic (``rule_based_v1``).
  ``extraction_confidence`` is a heuristic score, NOT a calibrated probability.
  Promises should be human-reviewed before they're used in any assessment.
"""
import enum
import hashlib
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from backend.nlp.preprocessing import normalize_unicode, normalize_whitespace

EXTRACTION_METHOD = "rule_based_v1"
TEST_FIXTURE_PREFIX = "TEST_FIXTURE"


class PromiseClassification(str, enum.Enum):
    SPECIFIC_PROMISE = "specific_promise"
    GENERAL_POLICY = "general_policy"
    VISION = "vision"
    SLOGAN = "slogan"
    AMBIGUOUS = "ambiguous"


@dataclass
class PromiseRecord:
    promise_id: str
    manifesto_id: str
    original_text: str
    normalized_text: str
    page_number: Optional[int]
    section: Optional[str]
    language: str
    extraction_method: str
    extraction_confidence: float
    classification: PromiseClassification
    # Traceability back to the source segment
    segment_index: int = 0
    char_start: int = 0
    char_end: int = 0
    source_extraction_method: Optional[str] = None
    source_ocr_used: bool = False
    classification_signals: List[str] = field(default_factory=list)
    is_test_fixture: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["classification"] = self.classification.value
        return d


# ---------------------------------------------------------------------------
# Lexicons (kept small and explicit so the behaviour is auditable)
# ---------------------------------------------------------------------------

# Commitment markers: future/obligatory phrasing.
_EN_COMMITMENT = re.compile(
    r"\b(we will|we shall|will be|shall be|we promise|we commit|we pledge|"
    r"will (?:provide|give|build|establish|create|set up|introduce|implement|"
    r"increase|reduce|ensure|waive|launch|construct|offer|extend|raise|abolish))\b",
    re.IGNORECASE,
)
# Tamil passive-future forms such as வழங்கப்படும் ("will be provided"),
# and first-person plural future such as செய்வோம் ("we will do").
_TA_COMMITMENT = re.compile(r"(ப்படும்|க்கப்படும்|படும்|வோம்|ப்போம்|உறுதி)")

# Concrete / measurable markers.
_QUANTITY = re.compile(
    r"(\d|₹|\brs\.?\b|\brupees?\b|\blakh|\bcrore|%|\bper cent\b|\bpercent\b|"
    r"ரூ|லட்சம்|கோடி|சதவீத)",
    re.IGNORECASE,
)

_VISION = re.compile(
    r"\b(vision|dream|aspire|aspiration|strive|transform|golden|prosperous|"
    r"inclusive growth|for all|our goal|our aim)\b|கனவு|இலக்கு|தொலைநோக்கு|பொற்கால",
    re.IGNORECASE,
)

_TAMIL_CHAR = re.compile(r"[\u0B80-\u0BFF]")
_LATIN_CHAR = re.compile(r"[A-Za-z]")

# Sentence / list-item boundaries. Tamil manifestos use '.' as the full stop.
_BOUNDARY = re.compile(r"(?<=[.!?;।])\s+|\n+\s*(?=(?:[-•*▪●]|\(?\d{1,3}[.)]|\(?[a-z][.)])\s)")
_LIST_MARKER = re.compile(r"^\s*(?:[-•*▪●]|\(?\d{1,3}[.)]|\(?[a-z][.)])\s+")

MIN_UNIT_CHARS = 4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get(segment: Any, key: str, default=None):
    if isinstance(segment, dict):
        return segment.get(key, default)
    return getattr(segment, key, default)


def detect_language(text: str, fallback: str = "Unknown") -> str:
    ta = len(_TAMIL_CHAR.findall(text))
    en = len(_LATIN_CHAR.findall(text))
    total = ta + en
    if total == 0:
        return fallback
    ratio = ta / total
    if ratio >= 0.8:
        return "Tamil"
    if ratio <= 0.2:
        return "English"
    return "Mixed"


def normalize_promise_text(text: str) -> str:
    """Conservative normalization: NFC + whitespace only. Never rewrites wording."""
    return normalize_whitespace(normalize_unicode(text))


def split_units(text: str) -> List[Tuple[int, int]]:
    """
    Split a segment into candidate promise units.
    Returns (start, end) offsets into ``text`` so that the exact original
    substring can be recovered. List markers are excluded from the span.
    """
    spans: List[Tuple[int, int]] = []
    pos = 0
    for m in _BOUNDARY.finditer(text):
        spans.append((pos, m.start()))
        pos = m.end()
    spans.append((pos, len(text)))

    cleaned: List[Tuple[int, int]] = []
    for start, end in spans:
        chunk = text[start:end]
        marker = _LIST_MARKER.match(chunk)
        if marker:
            start += marker.end()
            chunk = text[start:end]
        # trim surrounding whitespace while keeping offsets exact
        lstrip = len(chunk) - len(chunk.lstrip())
        rstrip = len(chunk) - len(chunk.rstrip())
        start, end = start + lstrip, end - rstrip
        if end - start >= MIN_UNIT_CHARS:
            cleaned.append((start, end))
    return cleaned


def classify(text: str) -> Tuple[PromiseClassification, float, List[str]]:
    """Rule-based classification. Returns (class, heuristic confidence, signals)."""
    signals: List[str] = []
    commitment = bool(_EN_COMMITMENT.search(text) or _TA_COMMITMENT.search(text))
    quantity = bool(_QUANTITY.search(text))
    vision = bool(_VISION.search(text))
    tokens = text.split()

    if commitment:
        signals.append("commitment_marker")
    if quantity:
        signals.append("quantity_marker")
    if vision:
        signals.append("vision_marker")

    if commitment and quantity:
        return PromiseClassification.SPECIFIC_PROMISE, 0.8, signals
    if commitment:
        return PromiseClassification.GENERAL_POLICY, 0.6, signals
    if vision:
        return PromiseClassification.VISION, 0.55, signals
    if len(tokens) <= 6 or text.rstrip().endswith("!"):
        signals.append("short_or_exclamatory")
        return PromiseClassification.SLOGAN, 0.4, signals
    return PromiseClassification.AMBIGUOUS, 0.3, signals


def make_promise_id(manifesto_id: str, page: Optional[int], segment_index: int,
                    char_start: int, text: str) -> str:
    digest = hashlib.sha256(
        f"{manifesto_id}|{page}|{segment_index}|{char_start}|{text}".encode("utf-8")
    ).hexdigest()[:12]
    return f"{manifesto_id}:p{page if page is not None else 'na'}:{digest}"


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class PromiseExtractor:
    """Extracted manifesto segments -> PromiseRecord objects."""

    def extract_from_segment(self, segment: Any, segment_index: int = 0) -> Iterator[PromiseRecord]:
        text = _get(segment, "original_text", "") or ""
        if not text.strip():
            return
        manifesto_id = _get(segment, "manifesto_id", "unknown")
        page = _get(segment, "page_number")
        section = _get(segment, "section")
        seg_language = _get(segment, "language", "Unknown") or "Unknown"
        ocr_used = bool(_get(segment, "OCR_used", False))
        seg_conf = _get(segment, "extraction_confidence", 1.0)
        seg_conf = 1.0 if seg_conf is None else float(seg_conf)

        for start, end in split_units(text):
            original = text[start:end]
            assert original == text[start:end]  # exact substring by construction
            cls, conf, signals = classify(original)
            if ocr_used:
                signals.append("source_ocr")
            yield PromiseRecord(
                promise_id=make_promise_id(manifesto_id, page, segment_index, start, original),
                manifesto_id=manifesto_id,
                original_text=original,
                normalized_text=normalize_promise_text(original),
                page_number=page,
                section=section,
                language=detect_language(original, fallback=seg_language),
                extraction_method=EXTRACTION_METHOD,
                # Upstream OCR/extraction uncertainty propagates into the score.
                extraction_confidence=round(conf * seg_conf, 3),
                classification=cls,
                segment_index=segment_index,
                char_start=start,
                char_end=end,
                source_extraction_method=_get(segment, "extraction_method"),
                source_ocr_used=ocr_used,
                classification_signals=signals,
                is_test_fixture=str(manifesto_id).startswith(TEST_FIXTURE_PREFIX),
            )

    def extract(self, segments: Iterable[Any]) -> List[PromiseRecord]:
        records: List[PromiseRecord] = []
        for i, seg in enumerate(segments):
            records.extend(self.extract_from_segment(seg, segment_index=i))
        return records
