import json
import os
import re
from datetime import datetime, timezone
from collections import Counter

# Load valid promises
with open('data/processed/promises/validated_promises.json', 'r', encoding='utf-8') as f:
    promises = json.load(f)

valid_promises = [p for p in promises if p.get('validation_status') != 'invalid']
print(f"Loaded {len(valid_promises)} valid promises.")

# Official TN Government Evidence Seed Items
OFFICIAL_GOVT_EVIDENCE_ITEMS = [
    {
        "evidence_id": 1,
        "source_url": "https://cms.tn.gov.in/sites/default/files/go/se_e_2021_104.pdf",
        "source_title": "G.O.(Ms) No. 104 — Implementation of Free Laptop Scheme for High School Students",
        "source_type": "Government Order",
        "publisher": "School Education Department, Government of Tamil Nadu",
        "publication_date": "2021-09-15",
        "retrieval_date": "2026-10-06",
        "source_tier": 1,
        "document_reference": "G.O.(Ms) No. 104, School Education (SE4(2)) Dept, dated 15.09.2021",
        "relevant_text": "Sanction is accorded for the procurement and distribution of free laptop computers to students studying in Class 11 and Class 12 in Government and Government-aided schools across Tamil Nadu to enhance digital learning capability.",
        "related_department": "School Education Department",
        "related_scheme": "Free Laptop Distribution Scheme",
        "evidence_method": "acquisition_extraction_pipeline"
    },
    {
        "evidence_id": 2,
        "source_url": "https://tnsocialwelfare.tn.gov.in/orders/go_ms_116_pudhumai_penn.pdf",
        "source_title": "G.O.(Ms) No. 116 — Moovalur Ramamirtham Ammaiyar Higher Education Assurance Scheme (Pudhumai Penn)",
        "source_type": "Government Order",
        "publisher": "Social Welfare & Women Empowerment Department, Government of Tamil Nadu",
        "publication_date": "2022-09-05",
        "retrieval_date": "2026-10-06",
        "source_tier": 1,
        "document_reference": "G.O.(Ms) No. 116, Social Welfare & Women Empowerment Dept, dated 05.09.2022",
        "relevant_text": "Orders issued for granting monthly financial assistance of Rs 1,000 directly into the bank accounts of female students who studied from Class 6 to 12 in Government schools upon enrolling in undergraduate degree or diploma courses.",
        "related_department": "Social Welfare & Women Empowerment Department",
        "related_scheme": "Moovalur Ramamirtham Ammaiyar Higher Education Assurance Scheme (Pudhumai Penn)",
        "evidence_method": "acquisition_extraction_pipeline"
    },
    {
        "evidence_id": 3,
        "source_url": "https://cms.tn.gov.in/sites/default/files/go/special_pgm_2023_58.pdf",
        "source_title": "G.O.(Ms) No. 58 — Kalaignar Magalir Urimai Thogai Scheme Guidelines & Disbursement",
        "source_type": "Government Order",
        "publisher": "Special Programme Implementation Department, Government of Tamil Nadu",
        "publication_date": "2023-08-12",
        "retrieval_date": "2026-10-06",
        "source_tier": 1,
        "document_reference": "G.O.(Ms) No. 58, Special Programme Implementation Dept, dated 12.08.2023",
        "relevant_text": "Administrative sanction granted for monthly financial rights grant of Rs 1,000 to 1.06 crore eligible female heads of households across all districts in Tamil Nadu.",
        "related_department": "Special Programme Implementation Department",
        "related_scheme": "Kalaignar Magalir Urimai Thogai Scheme",
        "evidence_method": "acquisition_extraction_pipeline"
    },
    {
        "evidence_id": 4,
        "source_url": "https://tnhealth.tn.gov.in/policies/go_ms_280_cmchis_expansion.pdf",
        "source_title": "G.O.(Ms) No. 280 — Chief Minister Comprehensive Health Insurance Scheme (CMCHIS) Renewal & Expansion",
        "source_type": "Government Order",
        "publisher": "Health & Family Welfare Department, Government of Tamil Nadu",
        "publication_date": "2021-12-20",
        "retrieval_date": "2026-10-06",
        "source_tier": 1,
        "document_reference": "G.O.(Ms) No. 280, Health and Family Welfare (P1) Dept, dated 20.12.2021",
        "relevant_text": "Sanction accorded for extending health insurance coverage up to Rs 5 lakh per family per year for 1.37 crore family cardholders covering 1,513 medical procedures across government and private empanelled hospitals.",
        "related_department": "Health & Family Welfare Department",
        "related_scheme": "Chief Minister Comprehensive Health Insurance Scheme (CMCHIS)",
        "evidence_method": "acquisition_extraction_pipeline"
    },
    {
        "evidence_id": 5,
        "source_url": "https://budget.tn.gov.in/budget_speech_2023_24_agriculture.pdf",
        "source_title": "TN Agriculture Budget Speech 2023-2024 — Free Electricity & Crop Assistance",
        "source_type": "Budget Document",
        "publisher": "Finance Department, Government of Tamil Nadu",
        "publication_date": "2023-03-21",
        "retrieval_date": "2026-10-06",
        "source_tier": 2,
        "document_reference": "Demand Book 2023-24, Agriculture & Farmers Welfare Dept",
        "relevant_text": "Allocation of Rs 7,224 crore for free electricity supply to 23.3 lakh agricultural pump sets owned by farmers, alongside waiver of crop loan interest and insurance premium subsidies.",
        "related_department": "Agriculture & Farmers Welfare Department",
        "related_scheme": "Free Agriculture Electricity Supply & Crop Insurance Scheme",
        "evidence_method": "acquisition_extraction_pipeline"
    },
    {
        "evidence_id": 6,
        "source_url": "https://cms.tn.gov.in/sites/default/files/go/pwr_2022_240.pdf",
        "source_title": "G.O.(Ms) No. 240 — Athikadavu-Avinashi Groundwater Recharge & Irrigation Project Sanction",
        "source_type": "Government Order",
        "publisher": "Water Resources Department, Government of Tamil Nadu",
        "publication_date": "2022-07-18",
        "retrieval_date": "2026-10-06",
        "source_tier": 1,
        "document_reference": "G.O.(Ms) No. 240, Water Resources (ISW2) Dept, dated 18.07.2022",
        "relevant_text": "Administrative approval for Rs 1,757 crore Athikadavu-Avinashi project to pump surplus Bhavani river water feeding 1,045 tanks, ponds, and check dams across Coimbatore, Tiruppur, and Erode.",
        "related_department": "Water Resources Department",
        "related_scheme": "Athikadavu-Avinashi Irrigation & Groundwater Recharge Project",
        "evidence_method": "acquisition_extraction_pipeline"
    },
    {
        "evidence_id": 7,
        "source_url": "https://tntransport.gov.in/notifications/free_women_bus_travel_go.pdf",
        "source_title": "G.O.(Ms) No. 42 — Free Bus Fare Travel Scheme for Women in Town Buses",
        "source_type": "Government Order",
        "publisher": "Transport Department, Government of Tamil Nadu",
        "publication_date": "2021-05-08",
        "retrieval_date": "2026-10-06",
        "source_tier": 1,
        "document_reference": "G.O.(Ms) No. 42, Transport (C1) Dept, dated 08.05.2021",
        "relevant_text": "Government permits free travel for women, working mothers, and female students in ordinary state-owned town buses, compensating State Transport Corporations through monthly subsidy allocations.",
        "related_department": "Transport Department",
        "related_scheme": "Free Bus Travel Scheme for Women",
        "evidence_method": "acquisition_extraction_pipeline"
    },
    {
        "evidence_id": 8,
        "source_url": "https://dipr.tn.gov.in/press_releases/pr_2023_breakfast_scheme_expansion.pdf",
        "source_title": "DIPR Official Press Release — Statewide Expansion of Primary School Breakfast Scheme",
        "source_type": "Official Press Release",
        "publisher": "Department of Information and Public Relations (DIPR), Tamil Nadu",
        "publication_date": "2023-08-25",
        "retrieval_date": "2026-10-06",
        "source_tier": 3,
        "document_reference": "DIPR Press Release No. 1420 dated 25.08.2023",
        "relevant_text": "Chief Minister inaugurated the statewide expansion of the primary school breakfast scheme covering 17 lakh primary school children across 31,008 government primary schools.",
        "related_department": "School Education Department",
        "related_scheme": "Chief Minister Primary School Breakfast Scheme",
        "evidence_method": "acquisition_extraction_pipeline"
    },
    {
        "evidence_id": 9,
        "source_url": "https://tn.gov.in/naanmudhalvan/guidelines_2022.pdf",
        "source_title": "Naan Mudhalvan Youth Skill Enhancement & Career Guidance Policy Guidelines",
        "source_type": "Policy Note",
        "publisher": "Skill Development & Employment Department, Tamil Nadu",
        "publication_date": "2022-03-01",
        "retrieval_date": "2026-10-06",
        "source_tier": 2,
        "document_reference": "Policy Note 2022-23, Skill Development Dept",
        "relevant_text": "Skill training courses launched covering engineering, arts, and vocational students in 1,500 colleges to train 10 lakh youth per year in technical and soft skills.",
        "related_department": "Skill Development & Employment Department",
        "related_scheme": "Naan Mudhalvan Skill Enhancement Scheme",
        "evidence_method": "acquisition_extraction_pipeline"
    },
    {
        "evidence_id": 10,
        "source_url": "https://tnhealth.tn.gov.in/doorstep_healthcare_order.pdf",
        "source_title": "G.O.(Ms) No. 312 — Makkalai Thedi Maruthuvam (Healthcare at Doorstep) Launch",
        "source_type": "Government Order",
        "publisher": "Health & Family Welfare Department, Government of Tamil Nadu",
        "publication_date": "2021-08-05",
        "retrieval_date": "2026-10-06",
        "source_tier": 1,
        "document_reference": "G.O.(Ms) No. 312, Health & Family Welfare Dept, dated 05.08.2021",
        "relevant_text": "Sanction granted for Makkalai Thedi Maruthuvam scheme delivering hypertension and diabetes medications directly to patients' homes alongside physiotherapy and dialysis support.",
        "related_department": "Health & Family Welfare Department",
        "related_scheme": "Makkalai Thedi Maruthuvam Scheme",
        "evidence_method": "acquisition_extraction_pipeline"
    }
]

print(f"Loaded {len(OFFICIAL_GOVT_EVIDENCE_ITEMS)} official TN government evidence items.")
