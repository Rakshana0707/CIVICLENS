import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion
from sklearn.metrics.pairwise import cosine_similarity

with open('data/processed/promises/validated_promises.json', 'r', encoding='utf-8') as f:
    promises = json.load(f)

from backend.database.base import Base
from backend.database.session import SessionLocal
from backend.models.budget import HistoricalScheme

db = SessionLocal()
schemes = db.query(HistoricalScheme).all()

scheme_texts = []
for s in schemes:
    stext = f"{s.scheme_name} {s.description or ''} {s.objectives or ''} {s.target_beneficiaries or ''} {s.sector_category or ''}"
    scheme_texts.append(stext)

promise_texts = []
for p in promises:
    ptext = f"{p['normalized_text']} {p.get('category', '')}"
    promise_texts.append(ptext)

union = FeatureUnion([
    ('word', TfidfVectorizer(ngram_range=(1, 2), analyzer='word', stop_words='english', min_df=1)),
    ('char', TfidfVectorizer(ngram_range=(3, 5), analyzer='char_wb', min_df=1))
])

union.fit(scheme_texts + promise_texts)

s_vecs = union.transform(scheme_texts).toarray()
p_vecs = union.transform(promise_texts).toarray()

sims = cosine_similarity(p_vecs, s_vecs)

for threshold in [0.40, 0.30, 0.20, 0.15, 0.10]:
    matched_p = sum(1 for row in sims if np.max(row) >= threshold)
    total_links = sum(sum(1 for val in row if val >= threshold) for row in sims)
    print(f"Hybrid Vectorizer Threshold >= {threshold:.2f}: {matched_p} promises matched ({matched_p/len(promises)*100:.1f}%), {total_links} total links")
