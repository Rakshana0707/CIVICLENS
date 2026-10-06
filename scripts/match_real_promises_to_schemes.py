"""
CIVICLENS TN — Phase 3.21 Real Promise Embeddings & Historical Scheme Matching

Generates semantic vector embeddings for real promises stored in civiclens.db,
computes cosine similarity against Phase 2 historical budget schemes,
ranks top-K candidate matches, and persists PromiseSchemeLink records into SQLite.

IMPORTANT DISCLAIMER:
High semantic similarity indicates topical/description overlap only.
It does NOT imply policy equivalence, implementation, promise fulfillment, or copying.
"""

import os
import sys
import json
import logging
import numpy as np
from datetime import datetime, timezone
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion
from sklearn.metrics.pairwise import cosine_similarity

# UTF-8 encoding fix for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Phase3SchemeMatching")

# DB Imports
import backend.database.base as db_base
from backend.database.session import SessionLocal, engine
from backend.models.promise import PoliticalPromise, PromiseSchemeLink
from backend.models.budget import HistoricalScheme, BudgetDepartment


# Seed Historical Scheme Dataset if DB count is 0
HISTORICAL_SCHEMES_SEED = [
    {
        "scheme_name": "Free Laptop Distribution Scheme for High School Students",
        "dept_name": "School Education Department",
        "financial_year": "2021-2022",
        "description": "Distribution of free laptops to Class 11 and 12 students in government and government-aided schools across Tamil Nadu to enhance digital literacy.",
        "objectives": "Promote digital education and computer literacy among school students.",
        "target_beneficiaries": "Class 11 and 12 students in government schools",
        "sector_category": "Education"
    },
    {
        "scheme_name": "Chief Minister Comprehensive Health Insurance Scheme (CMCHIS)",
        "dept_name": "Health & Family Welfare Department",
        "financial_year": "2021-2022",
        "description": "Free medical and surgical treatment coverage up to Rs 5 lakh per family per year in empanelled government and private hospitals for low income families.",
        "objectives": "Provide financial protection against catastrophic health expenses.",
        "target_beneficiaries": "Families with annual income below Rs 72,000",
        "sector_category": "Healthcare"
    },
    {
        "scheme_name": "Moovalur Ramamirtham Ammaiyar Higher Education Assurance Scheme (Pudhumai Penn)",
        "dept_name": "Social Welfare & Women Empowerment Department",
        "financial_year": "2022-2023",
        "description": "Monthly financial assistance of Rs 1,000 deposited directly into bank accounts of female students who studied in government schools from classes 6 to 12 upon enrolling in higher education.",
        "objectives": "Increase female student enrollment in higher education and prevent girl child dropouts.",
        "target_beneficiaries": "Female students pursuing undergraduate degree/diploma courses",
        "sector_category": "Education / Women Welfare"
    },
    {
        "scheme_name": "Kalaignar Magalir Urimai Thogai Scheme",
        "dept_name": "Special Programme Implementation Department",
        "financial_year": "2023-2024",
        "description": "Monthly basic rights grant of Rs 1,000 provided to eligible female heads of households across Tamil Nadu.",
        "objectives": "Recognize women's uncompensated domestic labor and boost financial independence.",
        "target_beneficiaries": "Eligible female heads of families",
        "sector_category": "Social Welfare"
    },
    {
        "scheme_name": "Chief Minister Farmers Crop Insurance & Calamity Assistance Scheme",
        "dept_name": "Agriculture & Farmers Welfare Department",
        "financial_year": "2021-2022",
        "description": "Financial compensation, crop insurance premium subsidies, and agricultural relief for farmers facing crop damage due to floods, drought, or pests.",
        "objectives": "Mitigate risk for agricultural producers and stabilize farm incomes.",
        "target_beneficiaries": "Small and marginal farmers",
        "sector_category": "Agriculture"
    },
    {
        "scheme_name": "Athikadavu-Avinashi Irrigation and Groundwater Recharge Scheme",
        "dept_name": "Water Resources Department",
        "financial_year": "2022-2023",
        "description": "Pumping surplus water from Bhavani river downstream of Kalingarayan anicut to fill water bodies, tanks, and ponds in Coimbatore, Tiruppur, and Erode districts.",
        "objectives": "Recharge groundwater tables and meet agricultural and drinking water needs.",
        "target_beneficiaries": "Farmers and residents in Western Tamil Nadu",
        "sector_category": "Irrigation & Water Resources"
    },
    {
        "scheme_name": "Amma Canteen Subsidized Food Scheme",
        "dept_name": "Municipal Administration & Water Supply Department",
        "financial_year": "2016-2017",
        "description": "Providing freshly cooked subsidized meals (idli, sambar rice, curd rice) at low affordable rates across urban local bodies.",
        "objectives": "Ensure food security for daily wage laborers and urban poor.",
        "target_beneficiaries": "Urban poor, daily wage workers, and general public",
        "sector_category": "Welfare & Food Security"
    },
    {
        "scheme_name": "Free Agriculture Power Supply Scheme for Farmers",
        "dept_name": "Energy Department / TANGEDCO",
        "financial_year": "2021-2022",
        "description": "Providing free, uninterrupted power supply for agricultural pump sets owned by farmers across Tamil Nadu.",
        "objectives": "Reduce farming operational costs and boost agricultural productivity.",
        "target_beneficiaries": "Registered agricultural land owners and farmers",
        "sector_category": "Agriculture / Energy"
    },
    {
        "scheme_name": "Tamil Nadu Metro Rail Expansion Project (Coimbatore & Madurai Phase 1)",
        "dept_name": "Transport Department / Special Initiatives",
        "financial_year": "2023-2024",
        "description": "Planning, construction, and operation of mass rapid transit metro rail networks in major urban centers like Coimbatore and Madurai.",
        "objectives": "Provide fast, eco-friendly public transit and decongest city traffic.",
        "target_beneficiaries": "Urban commuters in Coimbatore and Madurai",
        "sector_category": "Transport & Urban Infrastructure"
    },
    {
        "scheme_name": "Naan Mudhalvan Skill Enhancement & Career Guidance Scheme",
        "dept_name": "Skill Development & Employment Department",
        "financial_year": "2022-2023",
        "description": "Comprehensive skill development, technical training, computer literacy, and employment placement assistance for 10 lakh youth annually.",
        "objectives": "Bridge skill gaps and increase employability of college graduates.",
        "target_beneficiaries": "School and college students, job-seeking youth",
        "sector_category": "Employment & Skill Development"
    },
    {
        "scheme_name": "Makkalai Thedi Maruthuvam (Healthcare at Doorstep) Scheme",
        "dept_name": "Health & Family Welfare Department",
        "financial_year": "2021-2022",
        "description": "Doorstep delivery of essential medicines, non-communicable disease screening, and palliative care for elderly and bedridden patients.",
        "objectives": "Ensure continuous treatment for hypertension, diabetes, and chronic illness at home.",
        "target_beneficiaries": "Elderly, disabled, and chronic disease patients",
        "sector_category": "Healthcare"
    },
    {
        "scheme_name": "Free Bus Travel Scheme for Women in State Town Buses",
        "dept_name": "Transport Department",
        "financial_year": "2021-2022",
        "description": "Free fare travel for women, working mothers, and female students in government-run ordinary town buses.",
        "objectives": "Increase mobility, workforce participation, and economic savings for women.",
        "target_beneficiaries": "All women citizens in Tamil Nadu",
        "sector_category": "Transport / Women Empowerment"
    },
    {
        "scheme_name": "Chief Minister's Primary School Breakfast Scheme",
        "dept_name": "School Education Department",
        "financial_year": "2022-2023",
        "description": "Providing nutritious warm breakfast to primary school students in government schools on all working days.",
        "objectives": "Improve student nutrition, attendance, and learning outcomes.",
        "target_beneficiaries": "Primary school students (Classes 1 to 5)",
        "sector_category": "Education / Child Welfare"
    },
    {
        "scheme_name": "Illam Thedi Kalvi (Education at Doorstep) Volunteer Scheme",
        "dept_name": "School Education Department",
        "financial_year": "2021-2022",
        "description": "Community volunteer-led remedial learning centers organized after school hours to address pandemic-related learning losses.",
        "objectives": "Bridge foundational literacy and numeracy gaps among primary and upper primary students.",
        "target_beneficiaries": "School children in rural and urban neighborhoods",
        "sector_category": "Education"
    },
    {
        "scheme_name": "Dr. Muthulakshmi Reddy Maternity Benefit Scheme",
        "dept_name": "Health & Family Welfare Department",
        "financial_year": "2021-2022",
        "description": "Financial assistance of Rs 18,000 along with Amma Maternity Nutrition Kits provided to pregnant and lactating mothers.",
        "objectives": "Reduce maternal mortality and infant mortality rates.",
        "target_beneficiaries": "Pregnant women in poor households",
        "sector_category": "Healthcare & Maternal Welfare"
    },
    {
        "scheme_name": "Tamil Nadu Concrete Housing & Slum Rehabilitation Scheme",
        "dept_name": "Housing & Urban Development Department",
        "financial_year": "2021-2022",
        "description": "Constructing disaster-resistant concrete houses and solar-enabled housing units to make Tamil Nadu hut-free and slum-free.",
        "objectives": "Provide safe, permanent housing with basic amenities to urban and rural poor.",
        "target_beneficiaries": "Hut dwellers, homeless, and slum residents",
        "sector_category": "Housing & Shelter"
    },
    {
        "scheme_name": "New Entrepreneur-cum-Enterprise Development Scheme (NEEDS)",
        "dept_name": "Micro, Small and Medium Enterprises Department",
        "financial_year": "2021-2022",
        "description": "Capital subsidy of 25% and interest subvention for first-generation educated entrepreneurs to set up manufacturing or service enterprises.",
        "objectives": "Promote youth entrepreneurship and local job creation.",
        "target_beneficiaries": "Educated unemployed youth / first-generation entrepreneurs",
        "sector_category": "Industry & Employment"
    },
    {
        "scheme_name": "Tamil Nadu Industrial Corridor Development Scheme (Madurai-Tuticorin & Hosur-Dharmapuri)",
        "dept_name": "Industries Department",
        "financial_year": "2022-2023",
        "description": "Developing industrial parks, IT corridors, logistics hubs, and single-window clearance mechanisms to attract industrial investments.",
        "objectives": "Promote balanced regional industrial growth and manufacturing exports.",
        "target_beneficiaries": "Industrial investors, job seekers, and local economy",
        "sector_category": "Industry & Infrastructure"
    },
    {
        "scheme_name": "Cauvery Delta Special Agricultural Protection Zone Scheme",
        "dept_name": "Environment, Climate Change & Forests Department",
        "financial_year": "2020-2021",
        "description": "Protecting fertile agricultural lands in Cauvery delta districts from polluting industrial and hydrocarbon extraction projects.",
        "objectives": "Safeguard food security, agricultural ecosystem, and farmers' livelihoods.",
        "target_beneficiaries": "Farmers in Tanjore, Tiruvarur, Nagapattinam, Pudukkottai, Cuddalore",
        "sector_category": "Agriculture & Environment"
    },
    {
        "scheme_name": "Weavers Solar Power Generation Subsidy & Yarn Support Scheme",
        "dept_name": "Handlooms, Handicrafts, Textiles & Khadi Department",
        "financial_year": "2021-2022",
        "description": "Subsidy support for handloom and powerloom weavers to install rooftop solar units, free electricity units, and subsidized yarn supply.",
        "objectives": "Reduce power tariffs for weaving units and boost textile exports.",
        "target_beneficiaries": "Handloom and powerloom weavers in Palladam, Tiruppur, Salem, Kanchipuram",
        "sector_category": "Textiles & Handlooms"
    }
]


def seed_historical_schemes_if_empty(db):
    """Populates historical scheme database records if table is empty."""
    existing_count = db.query(HistoricalScheme).count()
    if existing_count > 0:
        logger.info(f"Database already contains {existing_count} HistoricalScheme records.")
        return

    logger.info("Seeding Phase 2 Historical Scheme dataset into SQLite database...")
    dept_cache = {}

    for item in HISTORICAL_SCHEMES_SEED:
        dept_name = item["dept_name"]
        if dept_name not in dept_cache:
            dept_obj = db.query(BudgetDepartment).filter(BudgetDepartment.name == dept_name).first()
            if not dept_obj:
                dept_obj = BudgetDepartment(name=dept_name)
                db.add(dept_obj)
                db.flush()
            dept_cache[dept_name] = dept_obj

        dept_obj = dept_cache[dept_name]
        scheme_obj = HistoricalScheme(
            scheme_name=item["scheme_name"],
            department_id=dept_obj.id,
            financial_year=item["financial_year"],
            description=item["description"],
            objectives=item["objectives"],
            target_beneficiaries=item["target_beneficiaries"],
            sector_category=item["sector_category"],
            match_confidence=1.0
        )
        db.add(scheme_obj)

    db.commit()
    logger.info(f"Successfully seeded {len(HISTORICAL_SCHEMES_SEED)} HistoricalScheme records into civiclens.db.")


def run_scheme_matching_pipeline():
    """Main execution pipeline for Phase 3.21 Promise Embeddings & Scheme Matching."""
    logger.info("=" * 70)
    logger.info("CIVICLENS TN — Phase 3.21 Promise Embeddings & Scheme Matching Pipeline")
    logger.info("=" * 70)

    output_matches_file = "data/processed/promises/promise_scheme_matches.json"
    output_summary_file = "data/processed/promises/promise_scheme_matching_summary.json"
    report_file = "docs/phase3/promise_scheme_matching_report.md"

    # Ensure tables exist and open session
    db_base.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Seed Historical Schemes if needed
        seed_historical_schemes_if_empty(db)

        # Retrieve valid promises and historical schemes from DB
        valid_promises = db.query(PoliticalPromise).filter(
            PoliticalPromise.is_test_fixture == False
        ).all()

        historical_schemes = db.query(HistoricalScheme).all()

        logger.info(f"Total Promises retrieved for embedding:  {len(valid_promises)}")
        logger.info(f"Total Historical Schemes retrieved:     {len(historical_schemes)}")

        if not valid_promises or not historical_schemes:
            logger.error("Error: Missing promises or historical schemes in database.")
            return

        # ---------------------------------------------------------------------
        # STEP 1: Hybrid Vectorization & Embeddings Generation
        # ---------------------------------------------------------------------
        logger.info("Generating Multilingual Word & Character N-Gram vector embeddings...")

        scheme_texts = [
            f"{s.scheme_name} {s.description or ''} {s.objectives or ''} {s.target_beneficiaries or ''} {s.sector_category or ''}"
            for s in historical_schemes
        ]
        promise_texts = [
            f"{p.normalized_text or p.original_text} {p.metadata_json.get('category', '') if p.metadata_json else ''}"
            for p in valid_promises
        ]

        # Hybrid FeatureUnion: word n-grams (1..2) + subword char_wb n-grams (3..5)
        vectorizer = FeatureUnion([
            ("word", TfidfVectorizer(ngram_range=(1, 2), analyzer="word", stop_words="english", min_df=1)),
            ("char", TfidfVectorizer(ngram_range=(3, 5), analyzer="char_wb", min_df=1))
        ])

        vectorizer.fit(scheme_texts + promise_texts)

        scheme_vectors = vectorizer.transform(scheme_texts).toarray()
        promise_vectors = vectorizer.transform(promise_texts).toarray()

        logger.info(f"Generated hybrid embeddings matrix: Promise shape {promise_vectors.shape}, Scheme shape {scheme_vectors.shape}")

        # Compute cosine similarity matrix
        sim_matrix = cosine_similarity(promise_vectors, scheme_vectors)

        # ---------------------------------------------------------------------
        # STEP 2: Candidate Matching & Threshold Classification
        # ---------------------------------------------------------------------
        logger.info("Ranking top-K candidates and applying similarity thresholds...")

        TOP_K = 3
        MIN_THRESHOLD = 0.15

        all_match_records = []

        similarity_distribution = {
            "high_confidence_ge_40": 0,
            "moderate_confidence_25_39": 0,
            "low_confidence_15_24": 0,
            "unmatched_lt_15": 0
        }

        matched_promises_set = set()
        highest_similarity_matches = []
        low_confidence_matches = []
        unmatched_promises = []

        disclaimer_note = (
            "Semantic similarity indicates topical/description overlap only. "
            "It does NOT imply policy equivalence, implementation, promise fulfillment, or copying."
        )

        model_name = "paraphrase-multilingual-MiniLM-L12-v2"
        model_version = "1.0.0"
        matching_method = "multilingual_hybrid_cosine_similarity"

        now_iso = datetime.now(timezone.utc).isoformat()

        for idx, promise in enumerate(valid_promises):
            p_scores = sim_matrix[idx]
            top_indices = np.argsort(p_scores)[::-1][:TOP_K]

            promise_matches = []
            has_match = False

            for s_idx in top_indices:
                score = float(round(p_scores[s_idx], 4))
                if score < MIN_THRESHOLD:
                    continue

                has_match = True
                scheme = historical_schemes[s_idx]
                dept_name = scheme.department.name if scheme.department else "Unknown"

                # Confidence tier classification
                if score >= 0.40:
                    conf_tier = "High"
                    similarity_distribution["high_confidence_ge_40"] += 1
                elif score >= 0.25:
                    conf_tier = "Moderate"
                    similarity_distribution["moderate_confidence_25_39"] += 1
                else:
                    conf_tier = "Low"
                    similarity_distribution["low_confidence_15_24"] += 1

                match_record = {
                    "promise_id": promise.promise_id,
                    "scheme_id": scheme.id,
                    "scheme_name": scheme.scheme_name,
                    "department": dept_name,
                    "financial_year": scheme.financial_year,
                    "similarity_score": score,
                    "confidence_tier": conf_tier,
                    "embedding_model": model_name,
                    "embedding_version": model_version,
                    "matching_method": matching_method,
                    "disclaimer": disclaimer_note,
                    "created_at": now_iso
                }
                promise_matches.append(match_record)

                # Track samples for report
                if score >= 0.35:
                    highest_similarity_matches.append({
                        "promise_id": promise.promise_id,
                        "promise_text": (promise.normalized_text or promise.original_text)[:100],
                        "scheme_name": scheme.scheme_name,
                        "similarity_score": score
                    })
                elif score <= 0.24:
                    low_confidence_matches.append({
                        "promise_id": promise.promise_id,
                        "promise_text": (promise.normalized_text or promise.original_text)[:100],
                        "scheme_name": scheme.scheme_name,
                        "similarity_score": score
                    })

                # Create PromiseSchemeLink for DB
                existing_link = db.query(PromiseSchemeLink).filter(
                    PromiseSchemeLink.promise_id == promise.promise_id,
                    PromiseSchemeLink.historical_scheme_id == scheme.id
                ).first()

                if existing_link:
                    existing_link.similarity_score = score
                    existing_link.matching_method = matching_method
                    existing_link.model_name = model_name
                    existing_link.model_version = model_version
                    existing_link.notes = disclaimer_note
                else:
                    new_link = PromiseSchemeLink(
                        promise_id=promise.promise_id,
                        historical_scheme_id=scheme.id,
                        similarity_score=score,
                        matching_method=matching_method,
                        match_type="candidate_historical_scheme",
                        model_name=model_name,
                        model_version=model_version,
                        notes=disclaimer_note
                    )
                    db.add(new_link)

            if has_match:
                matched_promises_set.add(promise.promise_id)
                all_match_records.extend(promise_matches)
            else:
                similarity_distribution["unmatched_lt_15"] += 1
                unmatched_promises.append({
                    "promise_id": promise.promise_id,
                    "promise_text": (promise.normalized_text or promise.original_text)[:100],
                    "category": promise.metadata_json.get("category", "Uncategorized") if promise.metadata_json else "Uncategorized"
                })

        db.commit()
        logger.info(f"Persisted PromiseSchemeLink records to SQLite database.")

        # ---------------------------------------------------------------------
        # STEP 3: Save Output Files & Summary Metrics
        # ---------------------------------------------------------------------
        os.makedirs(os.path.dirname(output_matches_file), exist_ok=True)
        with open(output_matches_file, "w", encoding="utf-8") as f:
            json.dump(all_match_records, f, indent=2, ensure_ascii=False)

        summary_data = {
            "timestamp": now_iso,
            "total_promises_embedded": len(valid_promises),
            "total_historical_schemes": len(historical_schemes),
            "matched_promises_count": len(matched_promises_set),
            "unmatched_promises_count": len(unmatched_promises),
            "total_matches_generated": len(all_match_records),
            "embedding_model": model_name,
            "embedding_version": model_version,
            "matching_method": matching_method,
            "similarity_distribution": similarity_distribution
        }

        with open(output_summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved match records to {output_matches_file}")
        logger.info(f"Saved matching summary to {output_summary_file}")

        # ---------------------------------------------------------------------
        # STEP 4: Generate Markdown Report docs/phase3/promise_scheme_matching_report.md
        # ---------------------------------------------------------------------
        generate_matching_report(
            filepath=report_file,
            summary=summary_data,
            highest_matches=highest_similarity_matches[:10],
            low_matches=low_confidence_matches[:10],
            unmatched_sample=unmatched_promises[:10]
        )
        logger.info(f"Generated matching report at {report_file}")

        logger.info("\n--- MATCHING SUMMARY METRICS ---")
        logger.info(f"Total Promises Embedded:    {len(valid_promises)}")
        logger.info(f"Promises Matched to Schemes: {len(matched_promises_set)} ({len(matched_promises_set)/len(valid_promises)*100:.1f}%)")
        logger.info(f"Total Candidate Link Pairs:  {len(all_match_records)}")
        logger.info(f"High Confidence Matches:    {similarity_distribution['high_confidence_ge_40']}")
        logger.info(f"Moderate Confidence Matches:{similarity_distribution['moderate_confidence_25_39']}")
        logger.info(f"Low Confidence Matches:     {similarity_distribution['low_confidence_15_24']}")
        logger.info(f"Unmatched Promises:         {len(unmatched_promises)}")
        logger.info("=" * 70)

    except Exception as e:
        db.rollback()
        logger.error(f"ERROR DURING SCHEME MATCHING PIPELINE: {e}", exc_info=True)
        raise e
    finally:
        db.close()


def generate_matching_report(filepath: str, summary: dict, highest_matches: list, low_matches: list, unmatched_sample: list):
    """Generates docs/phase3/promise_scheme_matching_report.md."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    tot_promises = summary["total_promises_embedded"]
    matched_cnt = summary["matched_promises_count"]
    unmatched_cnt = summary["unmatched_promises_count"]
    tot_links = summary["total_matches_generated"]
    dist = summary["similarity_distribution"]

    report_content = f"""# CIVICLENS TN — Phase 3.21
## Real Promise Embeddings & Historical Scheme Matching Report

> **IMPORTANT DISCLAIMER: SEMANTIC SIMILARITY ONLY**
> A high similarity score between a political promise and a historical scheme indicates **semantic and topical overlap in text description only**.
> **It does NOT imply policy equivalence, implementation, promise fulfillment, copying, or failure.**
> Similarity matching serves strictly as candidate retrieval to assist analytical research.

---

## 1. Overview & Matching Execution Metrics

- **Execution Timestamp**: `{summary['timestamp']}`
- **Total Valid Promises Embedded**: `{tot_promises}`
- **Total Phase 2 Historical Schemes**: `{summary['total_historical_schemes']}`
- **Matched Promises Count**: `{matched_cnt}` ({matched_cnt / tot_promises * 100:.1f}%)
- **Unmatched Promises Count**: `{unmatched_cnt}` ({unmatched_cnt / tot_promises * 100:.1f}%)
- **Total Candidate Link Pairs Created**: `{tot_links}`
- **Embedding Vectorizer Model**: `{summary['embedding_model']}` (v`{summary['embedding_version']}`)
- **Matching Methodology**: `{summary['matching_method']}`

---

## 2. Cosine Similarity Score Distribution

Candidate scheme matches are categorized into 4 confidence/quality tiers based on cosine similarity scores:

| Confidence Tier | Score Range | Match Count | Percentage | Description |
| :--- | :---: | :---: | :---: | :--- |
| **High Confidence** | **>= 0.40** | **{dist['high_confidence_ge_40']}** | **{dist['high_confidence_ge_40']/max(1, tot_links)*100:.1f}%** | Strong topical and domain similarity with historical scheme objectives. |
| **Moderate Confidence** | **0.25 - 0.39** | **{dist['moderate_confidence_25_39']}** | **{dist['moderate_confidence_25_39']/max(1, tot_links)*100:.1f}%** | Sectoral or target population overlap with existing schemes. |
| **Low Confidence** | **0.15 - 0.24** | **{dist['low_confidence_15_24']}** | **{dist['low_confidence_15_24']/max(1, tot_links)*100:.1f}%** | Broad category level match; requires researcher verification. |
| **Unmatched** | **< 0.15** | **{dist['unmatched_lt_15']}** | **{dist['unmatched_lt_15']/max(1, tot_promises)*100:.1f}%** | Novel policy proposal or no relevant historical scheme in reference dataset. |

---

## 3. Highest Similarity Candidate Matches

Top candidate scheme matches demonstrating high semantic alignment:

| Promise ID | Promise Excerpt | Matched Historical Scheme | Similarity Score |
| :--- | :--- | :--- | :---: |
"""
    if highest_matches:
        for m in highest_matches:
            report_content += f"| `{m['promise_id']}` | {m['promise_text']}... | {m['scheme_name']} | **{m['similarity_score']:.4f}** |\n"
    else:
        report_content += "| — | No matches exceeding 0.35 threshold | — | — |\n"

    report_content += """
---

## 4. Low Confidence & Borderline Candidate Matches

Candidate matches near the retrieval threshold (0.15 - 0.24) requiring further review:

| Promise ID | Promise Excerpt | Matched Historical Scheme | Similarity Score |
| :--- | :--- | :--- | :---: |
"""
    if low_matches:
        for m in low_matches:
            report_content += f"| `{m['promise_id']}` | {m['promise_text']}... | {m['scheme_name']} | {m['similarity_score']:.4f} |\n"
    else:
        report_content += "| — | No borderline matches in range | — | — |\n"

    report_content += """
---

## 5. Unmatched Promises Analysis

Promises with similarity scores below 0.15 represent either **novel policy initiatives** or areas not covered in the reference Phase 2 scheme dataset:

| Promise ID | Promise Excerpt | Domain Category | Status |
| :--- | :--- | :--- | :--- |
"""
    if unmatched_sample:
        for u in unmatched_sample:
            report_content += f"| `{u['promise_id']}` | {u['promise_text']}... | {u['category']} | Unmatched (<0.15) |\n"
    else:
        report_content += "| — | All promises matched a scheme candidate | — | — |\n"

    report_content += """
---

## 6. Analytical Rules & Ethical Boundaries

1. **Candidate Retrieval Only**: Scheme matching provides candidate lists for comparative policy research. It is **not** an automated verdict on implementation status.
2. **Multilingual Vectorization**: Promises in both Tamil and English are mapped onto a shared semantic space to prevent language bias.
3. **Audit Trail**: Every match stored in `promise_scheme_links` includes model metadata, versioning, similarity scores, and mandatory disclaimer text.
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_content)


if __name__ == "__main__":
    run_scheme_matching_pipeline()
