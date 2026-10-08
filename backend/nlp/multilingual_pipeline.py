import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from backend.core.logger import setup_logger

logger = setup_logger("civiclens.nlp.multilingual_pipeline")

# NLP Pipeline Version Identifier
NLP_PROCESSING_VERSION = "nlp_v1.0"

# Predefined Stopwords Dictionary
TAMIL_STOPWORDS = {
    "மற்றும்", "ஆனால்", "எனவே", "அல்லது", "என்று", "என", "ஒரு", "இந்த", "அந்த", "இது", "அது",
    "உள்ள", "ஆகிய", "குறித்து", "மேலும்", "கொண்டு", "மூலம்", "பற்றி", "இவர்", "அவர்", "இவர்கள்",
    "இருந்து", "செய்து", "வந்த", "தற்போது", "அனைத்து", "பல", "சில", "மிக", "அங்கு", "இங்கு",
    "எங்கு", "எனப்படும்", "ஆகும்", "உளது", "உள்ளன", "இருக்கிறது", "இருக்கின்றன"
}

ENGLISH_STOPWORDS = {
    "the", "is", "at", "which", "on", "a", "an", "and", "or", "in", "for", "to", "with", "as",
    "by", "that", "this", "it", "from", "are", "be", "was", "were", "has", "have", "had", "been",
    "will", "would", "shall", "should", "can", "could", "may", "might", "must", "of", "about",
    "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down"
}

# Common English Abbreviations (do NOT split sentences on these dots)
ENGLISH_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "govt", "dept", "inc", "ltd", "corp",
    "rs", "no", "vol", "vs", "etc", "i.e", "e.g", "m.k", "k.a", "c.m", "p.m", "a.m"
}


# Tamil Inflectional Suffixes for Rule-Based Stemming
TAMIL_SUFFIXES = [
    "கொண்டிருக்கின்றது", "கொண்டிருந்தனர்", "கொண்டிருந்தன", "கொண்டிருக்கிறது",
    "பட்டது", "பட்டன", "பட்டான்", "பட்டாள்", "பட்டார்",
    "கிறது", "கின்றன", "கிறான்", "கிறாள்", "கிறார்கள்",
    "ந்தது", "ந்தன", "ந்தான்", "ந்தாள்", "ந்தார்",
    "இருந்து", "மூலம்", "ஆகிய",
    "களுக்கு", "களின்", "களை", "கள்",
    "இலிருந்து", "உடன்", "ஆக", "இல்", "க்கு", "யை", "ஐ", "ஆல்", "இன்",
    "உம்", "ஏ", "ஓ"
]



@dataclass
class ProcessedArticlePayload:
    """
    Data container holding all NLP pipeline outputs while preserving original raw text.
    """
    original_text: str
    cleaned_text: str
    normalized_text: str
    language: str
    processing_version: str = NLP_PROCESSING_VERSION
    sentences: List[str] = field(default_factory=list)
    tokens: List[str] = field(default_factory=list)
    filtered_tokens: List[str] = field(default_factory=list)
    stems: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_text": self.original_text,
            "cleaned_text": self.cleaned_text,
            "normalized_text": self.normalized_text,
            "language": self.language,
            "processing_version": self.processing_version,
            "sentence_count": len(self.sentences),
            "token_count": len(self.tokens),
            "filtered_token_count": len(self.filtered_tokens),
            "sentences": self.sentences,
            "tokens": self.tokens,
            "filtered_tokens": self.filtered_tokens,
            "stems": self.stems,
            "stats": self.stats
        }


class TextCleaner:
    """Strips HTML chrome, sanitizes entities, and standardizes whitespace."""

    @staticmethod
    def clean(text: str) -> str:
        if not text or not isinstance(text, str):
            return ""

        # Remove HTML scripts and style blocks
        cleaned = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', text, flags=re.I | re.S)
        # Remove HTML tags
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        # Unescape basic HTML entities
        cleaned = cleaned.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        cleaned = cleaned.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
        # Collapse multi-spaces while preserving line breaks
        lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in cleaned.splitlines()]

        cleaned = "\n".join(line for line in lines if line)
        return cleaned.strip()


class MultilingualLanguageDetector:
    """High-precision script and character analyzer supporting Tamil (ta), English (en), and Mixed (mixed)."""

    @staticmethod
    def detect(text: str) -> str:
        if not text or not isinstance(text, str):
            return "en"

        tamil_chars = sum(1 for c in text if '\u0B80' <= c <= '\u0BFF')
        english_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
        total_alpha = sum(1 for c in text if c.isalpha())

        if total_alpha == 0:
            return "en"

        tam_ratio = tamil_chars / total_alpha
        eng_ratio = english_chars / total_alpha

        if tam_ratio > 0.35 and eng_ratio > 0.15:
            return "mixed"
        elif tam_ratio > 0.15:
            return "ta"
        else:
            return "en"


class TamilUnicodeNormalizer:
    """Performs Unicode NFKC normalization, zero-width stripping, and script standardization."""

    @staticmethod
    def normalize(text: str) -> str:
        if not text or not isinstance(text, str):
            return ""

        # NFKC Normalization
        norm = unicodedata.normalize("NFKC", text)

        # Remove zero-width characters (\u200C, \u200D, \u200B, soft hyphen \u00AD)
        norm = re.sub(r'[\u200c\u200d\u200b\u00ad]', '', norm)

        # Standardize smart quotes and dashes
        norm = norm.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
        norm = norm.replace("–", "-").replace("—", "-")

        # Standardize whitespace
        norm = re.sub(r'\s+', ' ', norm).strip()
        return norm


class SentenceSegmenter:
    """Language-aware sentence splitter supporting Tamil and English abbreviation safeguards."""

    def __init__(self):
        self.abbreviations = ENGLISH_ABBREVIATIONS

    def segment(self, text: str, language: str = "ta") -> List[str]:
        if not text or not isinstance(text, str):
            return []

        # Split into raw paragraphs first
        paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
        sentences = []

        for p in paragraphs:
            # Protect dots in known abbreviations (e.g., "M.K. Stalin" -> "M_K_ Stalin")
            protected = p
            for abbr in self.abbreviations:
                pattern = r'\b(' + re.escape(abbr) + r')\.'
                protected = re.sub(pattern, r'\1___DOT___', protected, flags=re.I)

            # Protect decimal numbers (e.g., "Rs 500.50" -> "Rs 500___DOT___50")
            protected = re.sub(r'(\d+)\.(\d+)', r'\1___DOT___\2', protected)

            # Split on Tamil/English sentence terminators (. ! ? | \n)
            raw_sents = re.split(r'(?<=[.!?|\n])\s+', protected)

            for sent in raw_sents:
                sent = sent.replace("___DOT___", ".").strip()
                if sent and len(sent.split()) >= 2:
                    sentences.append(sent)

        return sentences


class ScriptTokenizer:
    """Script-aware tokenizer preserving Tamil compound script tokens and English word tokens."""

    @staticmethod
    def tokenize(text: str) -> List[str]:
        if not text or not isinstance(text, str):
            return []

        # Match Tamil script blocks or English/numeric alphanumeric tokens
        # Tamil Unicode range: \u0B80-\u0BFF
        pattern = r'[\u0B80-\u0BFF]+|[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*'
        tokens = re.findall(pattern, text)
        return [t.strip() for t in tokens if t.strip()]


class StopwordProcessor:
    """Filters Tamil and English stopwords based on language mode."""

    def __init__(self):
        self.tamil_stopwords = TAMIL_STOPWORDS
        self.english_stopwords = ENGLISH_STOPWORDS

    def filter_stopwords(self, tokens: List[str], language: str = "ta") -> List[str]:
        filtered = []
        for token in tokens:
            t_lower = token.lower()
            if language == "ta" and t_lower in self.tamil_stopwords:
                continue
            elif language == "en" and t_lower in self.english_stopwords:
                continue
            elif language == "mixed":
                if t_lower in self.tamil_stopwords or t_lower in self.english_stopwords:
                    continue
            filtered.append(token)
        return filtered


class StemmerLemmatizer:
    """Rule-based inflection stemmer for Tamil and English tokens."""

    @staticmethod
    def stem_tamil_word(word: str) -> str:
        """Rule-based suffix stripping for Tamil inflections."""
        stemmed = word
        for suffix in TAMIL_SUFFIXES:
            if len(stemmed) > len(suffix) + 2 and stemmed.endswith(suffix):
                stemmed = stemmed[:-len(suffix)]
                break
        return stemmed

    @staticmethod
    def stem_english_word(word: str) -> str:
        """Basic Porter-style rule-based stemming for English tokens."""
        w = word.lower()
        if len(w) > 4:
            if w.endswith("ing"):
                w = w[:-3]
            elif w.endswith("ed"):
                w = w[:-2]
            elif w.endswith("es"):
                w = w[:-2]
            elif w.endswith("ly"):
                w = w[:-2]
            elif w.endswith("s") and not w.endswith("ss"):
                w = w[:-1]
        return w

    def stem_tokens(self, tokens: List[str], language: str = "ta") -> List[str]:
        stems = []
        for t in tokens:
            if any('\u0B80' <= c <= '\u0BFF' for c in t):
                stems.append(self.stem_tamil_word(t))
            else:
                stems.append(self.stem_english_word(t))
        return stems


class MultilingualNewsNLPPipeline:
    """
    End-to-End Multilingual News NLP Pipeline implementing:
    RAW ARTICLE -> CLEANING -> LANGUAGE DETECTION -> UNICODE NORMALIZATION ->
    TAMIL NORMALIZATION -> SENTENCE SEGMENTATION -> TOKENIZATION ->
    STOPWORD PROCESSING -> STEM PROCESSING -> PROCESSED ARTICLE
    """

    def __init__(self):
        self.cleaner = TextCleaner()
        self.lang_detector = MultilingualLanguageDetector()
        self.unicode_normalizer = TamilUnicodeNormalizer()
        self.segmenter = SentenceSegmenter()
        self.tokenizer = ScriptTokenizer()
        self.stopword_processor = StopwordProcessor()
        self.stemmer = StemmerLemmatizer()

    def process(self, original_text: str, override_language: Optional[str] = None) -> ProcessedArticlePayload:
        """Executes full NLP processing pipeline while preserving original text completely intact."""
        raw_input = original_text if original_text is not None else ""

        # Step 1: Cleaning
        cleaned = self.cleaner.clean(raw_input)

        # Step 2: Language Detection
        detected_lang = self.lang_detector.detect(cleaned)
        language = override_language or detected_lang

        # Step 3 & 4: Unicode & Tamil Normalization
        normalized = self.unicode_normalizer.normalize(cleaned)

        # Step 5: Sentence Segmentation
        sentences = self.segmenter.segment(normalized, language=language)

        # Step 6: Tokenization
        tokens = self.tokenizer.tokenize(normalized)

        # Step 7: Stopword Processing
        filtered_tokens = self.stopword_processor.filter_stopwords(tokens, language=language)

        # Step 8: Stemming / Lemmatization
        stems = self.stemmer.stem_tokens(filtered_tokens, language=language)

        # Statistical Metrics
        tam_tokens = sum(1 for t in tokens if any('\u0B80' <= c <= '\u0BFF' for c in t))
        eng_tokens = sum(1 for t in tokens if any('a' <= c.lower() <= 'z' for c in t))
        unique_tokens = len(set(t.lower() for t in tokens))

        stats = {
            "tamil_token_count": tam_tokens,
            "english_token_count": eng_tokens,
            "unique_token_count": unique_tokens,
            "vocabulary_richness": round(unique_tokens / max(1, len(tokens)), 3)
        }

        return ProcessedArticlePayload(
            original_text=raw_input,
            cleaned_text=cleaned,
            normalized_text=normalized,
            language=language,
            processing_version=NLP_PROCESSING_VERSION,
            sentences=sentences,
            tokens=tokens,
            filtered_tokens=filtered_tokens,
            stems=stems,
            stats=stats
        )
