import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
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

vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english')
vectorizer.fit(scheme_texts + promise_texts)

s_vecs = vectorizer.transform(scheme_texts).toarray()
p_vecs = vectorizer.transform(promise_texts).toarray()

sims = cosine_similarity(p_vecs, s_vecs)

for threshold in [0.30, 0.20, 0.15, 0.10, 0.05]:
    matched_p = sum(1 for row in sims if np.max(row) >= threshold)
    total_links = sum(sum(1 for val in row if val >= threshold) for row in sims)
    print(f"Threshold >= {threshold:.2f}: {matched_p} promises matched ({matched_p/len(promises)*100:.1f}%), {total_links} total links")
