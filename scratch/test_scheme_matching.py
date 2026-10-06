import json
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

with open('data/processed/promises/validated_promises.json', 'r', encoding='utf-8') as f:
    promises = json.load(f)

# Filter out invalid promises
valid_promises = [p for p in promises if p.get('validation_status') != 'invalid']
print(f"Total valid promises to embed & match: {len(valid_promises)}")

# Historical Schemes seed data
sample_schemes = [
    {
        "id": 1,
        "name": "Free Laptop Distribution Scheme for High School Students",
        "department": "School Education",
        "description": "Laptops distributed to Class 11 and 12 students studying in government and government-aided schools to enhance digital skills."
    },
    {
        "id": 2,
        "name": "Chief Minister Comprehensive Health Insurance Scheme (CMCHIS)",
        "department": "Health & Family Welfare",
        "description": "Free cashless hospitalization and medical coverage up to 5 lakh rupees per family per year for low income households."
    },
    {
        "id": 3,
        "name": "Moovalur Ramamirtham Ammaiyar Higher Education Assurance Scheme (Pudhumai Penn)",
        "department": "Social Welfare & Women Empowerment",
        "description": "Monthly financial assistance of 1000 rupees to female students who completed schooling in government schools to pursue higher education."
    },
    {
        "id": 4,
        "name": "Kalaignar Magalir Urimai Thogai Scheme",
        "department": "Special Program Implementation / Social Welfare",
        "description": "Monthly rights grant of 1000 rupees provided to eligible female heads of households across Tamil Nadu."
    },
    {
        "id": 5,
        "name": "Chief Minister Farmers Crop Insurance & Loss Compensation Scheme",
        "department": "Agriculture & Farmers Welfare",
        "description": "Financial compensation and crop insurance subsidies to protect farmers against drought, floods, and natural calamities."
    },
    {
        "id": 6,
        "name": "Athikadavu-Avinashi Irrigation and Groundwater Recharge Project",
        "department": "Water Resources / Irrigation",
        "description": "Pumping surplus water from Bhavani river to feed water bodies, tanks, and ponds in Coimbatore, Tiruppur, and Erode districts."
    },
    {
        "id": 7,
        "name": "Amma Canteen Subsidized Food Scheme",
        "department": "Municipal Administration & Water Supply",
        "description": "Providing freshly cooked subsidized meals at low cost to daily wage workers, urban poor, and needy citizens."
    },
    {
        "id": 8,
        "name": "Free Agriculture Power Supply Scheme for Farmers",
        "department": "Energy / TANGEDCO",
        "description": "Uninterrupted free electricity provided to small and marginal farmers for agricultural pump sets."
    },
    {
        "id": 9,
        "name": "Tamil Nadu Metro Rail Expansion Project (Coimbatore & Madurai Phase 1)",
        "department": "Special Initiatives / Transport",
        "description": "Implementation and expansion of rapid transit metro rail corridors across major tier-2 cities in Tamil Nadu."
    },
    {
        "id": 10,
        "name": "Naan Mudhalvan Skill Enhancement & Career Guidance Program",
        "department": "Skill Development / Higher Education",
        "description": "Industrial training, technical skill development, and employment placement assistance for college students across Tamil Nadu."
    }
]

# Build TF-IDF vectorizer
corpus = [s["name"] + " " + s["description"] for s in sample_schemes]
promise_texts = [p["normalized_text"] for p in valid_promises]

vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, stop_words='english')
vectorizer.fit(corpus + promise_texts)

scheme_vecs = vectorizer.transform(corpus).toarray()
promise_vecs = vectorizer.transform(promise_texts).toarray()

# Cosine similarity matrix
from sklearn.metrics.pairwise import cosine_similarity
sim_matrix = cosine_similarity(promise_vecs, scheme_vecs)

matches = []
for i, p in enumerate(valid_promises):
    scores = sim_matrix[i]
    top_indices = np.argsort(scores)[::-1][:3]
    top_matches = []
    for idx in top_indices:
        score = float(scores[idx])
        if score >= 0.25:
            top_matches.append({
                "scheme_id": sample_schemes[idx]["id"],
                "scheme_name": sample_schemes[idx]["name"],
                "department": sample_schemes[idx]["department"],
                "similarity_score": round(score, 4)
            })
    if top_matches:
        matches.append({
            "promise_id": p["promise_id"],
            "promise_text": p["normalized_text"][:80],
            "top_matches": top_matches
        })

print(f"Total promises with scheme candidate matches (threshold >= 0.25): {len(matches)}")
print("\nSample Matches:")
for m in matches[:5]:
    print(f"Promise: {m['promise_text']}")
    for tm in m['top_matches']:
        print(f"  -> Match: {tm['scheme_name']} (Score: {tm['similarity_score']})")
    print('-'*60)
