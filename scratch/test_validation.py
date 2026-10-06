import json
import re
import unicodedata
from collections import Counter

with open('data/processed/promises/extracted_promises.json', 'r', encoding='utf-8') as f:
    promises = json.load(f)

print(f"Loaded {len(promises)} promises.")

# Check fields
missing_fields_counts = Counter()
status_counts = Counter()
flag_counts = Counter()
language_counts = Counter()
category_counts = Counter()
party_counts = Counter()
year_counts = Counter()

# Tamil diacritics
TAMIL_DIACRITICS = set(range(0x0BCD, 0x0BD8)) | {0x0BBE, 0x0BBF, 0x0BC0, 0x0BC1, 0x0BC2, 0x0BC6, 0x0BC7, 0x0BC8, 0x0BCA, 0x0BCB, 0x0BCC}
TAMIL_CONSONANTS = set(range(0x0B95, 0x0BBA))

def is_tamil_orphan_diacritic(text):
    """Check if Tamil text contains diacritics without preceding base consonant."""
    for i, ch in enumerate(text):
        cp = ord(ch)
        if cp in TAMIL_DIACRITICS:
            if i == 0 or (ord(text[i-1]) not in TAMIL_CONSONANTS):
                return True
    return False

def is_incomplete_sentence(text):
    text_clean = text.strip()
    if len(text_clean) < 15:
        return True
    # Starts lowercase leading verb / conjunction
    if re.match(r'^(will|and|or|that|to|in|for|with|of|is|are|was|were)\b', text_clean, re.IGNORECASE):
        return True
    # Ends dangling
    if re.search(r'\b(and|or|that|to|in|for|with|of|the|a|an)$', text_clean, re.IGNORECASE):
        return True
    return False

def is_page_or_header_artifact(text):
    t = text.strip().lower()
    if re.match(r'^(page\s*\d+|\d+|---|part\s*\d+|manifesto\s*\d*)$', t):
        return True
    return False

seen_exact_texts = set()
seen_tokens_list = []

def get_tokens(text):
    return set(re.findall(r'\w+', text.lower()))

def jaccard_similarity(set1, set2):
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / float(len(set1 | set2))

validated_records = []

for p in promises:
    pid = p.get('promise_id')
    manifesto_id = p.get('manifesto_id')
    doc_id = p.get('document_id')
    orig_text = p.get('original_text', '')
    norm_text = p.get('normalized_text', '')
    lang = p.get('language', 'Unknown')
    cat = p.get('category', 'Uncategorized')
    conf = p.get('confidence', 1.0)
    page = p.get('page_number')
    sec = p.get('section')
    
    # Extract party and year from manifesto_id e.g. MF-PMK-2016
    party = manifesto_id.split('-')[1] if manifesto_id and '-' in manifesto_id else 'Unknown'
    year = manifesto_id.split('-')[2] if manifesto_id and len(manifesto_id.split('-')) > 2 else 'Unknown'
    
    language_counts[lang] += 1
    category_counts[cat] += 1
    party_counts[party] += 1
    year_counts[year] += 1

    flags = []
    
    # Missing fields check
    if not manifesto_id:
        missing_fields_counts['manifesto_id'] += 1
        flags.append('missing_manifesto_id')
    if not doc_id:
        missing_fields_counts['document_id'] += 1
        flags.append('missing_document_id')
    if page is None or page < 1:
        missing_fields_counts['page_number'] += 1
        flags.append('missing_page_number')
    if not sec:
        missing_fields_counts['section'] += 1
        flags.append('missing_section')
    if not orig_text:
        missing_fields_counts['original_text'] += 1
        flags.append('missing_original_text')
    if not norm_text:
        missing_fields_counts['normalized_text'] += 1
        flags.append('missing_normalized_text')
    if conf is None or conf <= 0:
        missing_fields_counts['confidence'] += 1
        flags.append('missing_confidence')

    # OCR / Control / Unicode check
    if '\ufffd' in orig_text or '\ufffd' in norm_text:
        flags.append('ocr_replacement_char')
    if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', orig_text):
        flags.append('unprintable_control_char')
    if is_tamil_orphan_diacritic(orig_text) or is_tamil_orphan_diacritic(norm_text):
        flags.append('broken_tamil_unicode')
        
    # Text quality checks
    if len(orig_text.strip()) == 0:
        flags.append('empty_text')
    if is_page_or_header_artifact(orig_text):
        flags.append('page_or_header_artifact')
    if re.search(r'\b(\w+)\s+\1\s+\1\b', orig_text, re.IGNORECASE):
        flags.append('repeated_text')
    if is_incomplete_sentence(orig_text):
        flags.append('incomplete_sentence')
        
    # Duplicates check
    norm_clean = norm_text.strip().lower()
    is_exact_dup = norm_clean in seen_exact_texts
    tokens = get_tokens(norm_clean)
    
    is_near_dup = False
    if not is_exact_dup and len(tokens) >= 5:
        for prev_tokens in seen_tokens_list:
            if jaccard_similarity(tokens, prev_tokens) >= 0.88:
                is_near_dup = True
                break
                
    if is_exact_dup:
        flags.append('exact_duplicate')
    elif is_near_dup:
        flags.append('near_duplicate')
    else:
        seen_exact_texts.add(norm_clean)
        if len(tokens) >= 5:
            seen_tokens_list.append(tokens)

    # Classification
    if 'empty_text' in flags or 'page_or_header_artifact' in flags or 'missing_manifesto_id' in flags or 'missing_original_text' in flags:
        status = 'invalid'
    elif 'exact_duplicate' in flags:
        status = 'duplicate'
    elif 'near_duplicate' in flags:
        status = 'probable_duplicate'
    elif 'incomplete_sentence' in flags or 'ocr_replacement_char' in flags or 'broken_tamil_unicode' in flags or cat == 'Uncategorized' or conf < 0.5:
        status = 'needs_review'
    else:
        status = 'valid'

    status_counts[status] += 1
    for f in flags:
        flag_counts[f] += 1

print("\n--- STATUS COUNTS ---")
for k, v in status_counts.items():
    print(f"  {k}: {v}")

print("\n--- FLAG COUNTS ---")
for k, v in flag_counts.items():
    print(f"  {f'{k}:':<25} {v}")

print("\n--- MISSING FIELDS COUNTS ---")
for k, v in missing_fields_counts.items():
    print(f"  {f'{k}:':<25} {v}")
