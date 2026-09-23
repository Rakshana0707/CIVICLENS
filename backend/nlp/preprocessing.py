import re
import unicodedata
import string

def normalize_whitespace(text: str) -> str:
    """Removes extra whitespace, tabs, and newlines."""
    if not isinstance(text, str):
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def normalize_unicode(text: str, form: str = 'NFC') -> str:
    """
    Normalizes Unicode characters.
    NFC (Normalization Form Canonical Composition) is highly recommended for Tamil 
    and other Indic languages to ensure base characters and vowel modifiers 
    (uyirmei ezhuthukkal) are consistently combined.
    """
    if not isinstance(text, str):
        return ""
    return unicodedata.normalize(form, text)

def remove_punctuation(text: str) -> str:
    """
    Removes standard ASCII punctuation from the string.
    """
    if not isinstance(text, str):
        return ""
    translator = str.maketrans('', '', string.punctuation)
    # Removing extra whitespace that might result from stripping punctuation
    return re.sub(r'\s+', ' ', text.translate(translator)).strip()

def normalize_tamil_text(text: str) -> str:
    """
    Standardized preprocessing pipeline specifically tailored for Tamil text.
    Applies unicode normalization first, followed by punctuation and whitespace cleaning.
    """
    if not text:
        return ""
    
    text = normalize_unicode(text)
    text = remove_punctuation(text)
    text = normalize_whitespace(text)
    return text
