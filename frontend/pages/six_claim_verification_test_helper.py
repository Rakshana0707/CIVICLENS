"""
Helper module for Phase 7 Claim Verification Dashboard.
Exposes fixture data, outcome taxonomies, color schemas, and filtering logic
for Streamlit dashboard and unit test suites.
"""

from typing import Dict, Any, List, Tuple, Optional
from frontend.services.api import api_client

OUTCOME_COLORS = {
    "supported_by_available_evidence": "#28a745",       # Green
    "contradicted_by_available_evidence": "#dc3545",     # Red
    "partially_supported": "#fd7e14",                    # Orange
    "missing_important_context": "#ffc107",              # Amber
    "insufficient_evidence": "#6c757d",                  # Grey
    "disputed_evidence": "#d63384",                      # Magenta
    "unverifiable": "#6f42c1",                           # Purple
    "pending_review": "#0dcaf0"                          # Cyan
}

OUTCOME_LABELS = {
    "supported_by_available_evidence": "Supported by Available Evidence",
    "contradicted_by_available_evidence": "Contradicted by Available Evidence",
    "partially_supported": "Partially Supported",
    "missing_important_context": "Missing Important Context",
    "insufficient_evidence": "Insufficient Evidence",
    "disputed_evidence": "Disputed / Conflicting Evidence",
    "unverifiable": "Unverifiable (Non-Empirical / Normative)",
    "pending_review": "Pending Review"
}

REVIEW_STATUS_BADGES = {
    "UNREVIEWED": "🟡 Automated Only (Unreviewed)",
    "AUTOMATED_INITIAL": "🟡 Automated Initial Assessment",
    "PEER_REVIEWED": "🔵 Peer Reviewed",
    "CONFIRMED": "🟢 Confirmed by Human Fact-Checker",
    "REVISED": "🟠 Revised by Senior Reviewer",
    "REJECTED": "🔴 Rejected / Superseded"
}

FIXTURE_CLAIMS: List[Dict[str, Any]] = [
    {
        "claim_id": "TEST_FIXTURE_CLM_01",
        "original_text": "2023-24 நிதியாண்டில் தமிழ்நாட்டின் பொருளாதார வளர்ச்சி 8.2 சதவீதமாக உயர்ந்துள்ளது.",
        "normalized_text": "2023-24 நிதியாண்டில் தமிழ்நாட்டின் பொருளாதார வளர்ச்சி 8.2 சதவீதமாக உயர்ந்துள்ளது",
        "claim_category": "ECONOMIC_METRICS",
        "language": "ta",
        "speaker_name": "Finance Minister",
        "speaker_role": "Minister for Finance and Human Resources",
        "party": "DMK",
        "claim_date": "2024-02-15",
        "publication_date": "2024-02-15",
        "candidate_source_type": "PRESS_RELEASE",
        "attribution_type": "DIRECT_QUOTE",
        "claim_source_url": "https://tn.gov.in/press-release/pr-2024-02-15-gsdp.pdf",
        "source_document_id": "DOC-GOVT-PR-2024-02",
        "geographic_scope": "Tamil Nadu",
        "extraction_method": "MANUAL",
        "status": "VERIFIED",
        "review_status": "CONFIRMED",
        "is_human_reviewed": True,
        "reviewer_role": "LEAD_REVIEWER",
        "reviewer_name": "Dr. S. Ramanathan, Senior Economist",
        "review_notes": "Cross-verified with DES Advanced Estimates released in Feb 2024 and RBI State Finances.",
        "verification": {
            "outcome": "supported_by_available_evidence",
            "explanation": "The claim that Tamil Nadu's real GSDP growth rate reached 8.2% for FY 2023-24 is supported by provisional advanced estimates released by the Department of Economics and Statistics (DES), Government of Tamil Nadu, as well as RBI Handbook of Statistics 2024.",
            "methodology": "Multilingual claim-to-evidence hybrid retrieval and proposition matching.",
            "limitations": "Estimates are provisional advanced estimates and subject to subsequent revisions in the revised and actuals accounts.",
            "supporting_evidence_ids": ["EVD-DOC-TN-DES-2024-01", "EVD-DOC-RBI-HANDBOOK-2024"],
            "contradicting_evidence_ids": [],
            "source_diversity": 2,
            "confidence": 0.94,
            "verification_timestamp": "2024-02-16T14:30:00Z",
            "epistemic_disclaimer": "This determination reflects currently available gazetted records and does not constitute a character judgment."
        },
        "atomic_claims": [
            {
                "atomic_claim_id": "ATM-CLM-01-01",
                "atomic_claim_text": "Tamil Nadu's economic (GSDP) growth rate reached 8.2% in FY 2023-24.",
                "language": "en",
                "subject": "Tamil Nadu Economy (GSDP)",
                "predicate": "increased to",
                "object": "8.2 percent",
                "numeric_value": 8.2,
                "unit": "%",
                "time_period": "FY 2023-24",
                "claim_type": "QUANTITATIVE",
                "is_verifiable": True,
                "confidence": 0.96
            }
        ],
        "relationships": [
            {
                "evidence_document_id": "EVD-DOC-TN-DES-2024-01",
                "evidence_title": "Advanced Estimates of GSDP 2023-24 (DES TN)",
                "publisher": "Department of Economics and Statistics, Govt of Tamil Nadu",
                "relationship_type": "supports",
                "relevant_passage": "Table 1.1: Gross State Domestic Product of Tamil Nadu at Constant (2011-12) Prices indicates an annual growth rate of 8.24% for 2023-24.",
                "source_url": "https://tn.gov.in/dept/des/gsdp_adv_2024.pdf",
                "publication_date": "2024-02-12"
            },
            {
                "evidence_document_id": "EVD-DOC-RBI-HANDBOOK-2024",
                "evidence_title": "Handbook of Statistics on Indian States 2023-24",
                "publisher": "Reserve Bank of India",
                "relationship_type": "supports",
                "relevant_passage": "State-wise Growth of GSDP at Constant Prices: Tamil Nadu 2023-24 (Adv. Est.): 8.2%.",
                "source_url": "https://rbi.org.in/scripts/PublicationsView.aspx?id=2140",
                "publication_date": "2024-01-28"
            }
        ],
        "cross_phase": {
            "historical_scheme": None,
            "promise": None,
            "news_article": {
                "article_id": "ART-HIN-2024-02-16",
                "title": "Tamil Nadu clocking 8.2% GSDP growth on industrial momentum: State report",
                "url": "https://thehindu.com/news/national/tamil-nadu/economy-2024"
            },
            "financial_document": None,
            "representative": None
        }
    },
    {
        "claim_id": "TEST_FIXTURE_CLM_02",
        "original_text": "During our term, 5 lakh new students enrolled in state government schools in a single academic year.",
        "normalized_text": "during our term 5 lakh new students enrolled in state government schools in a single academic year",
        "claim_category": "GOVERNMENT_SCHEMES",
        "language": "en",
        "speaker_name": "Opposition Spokesperson",
        "speaker_role": "Party General Secretary",
        "party": "AIADMK",
        "claim_date": "2023-11-10",
        "publication_date": "2023-11-11",
        "candidate_source_type": "SPEECH",
        "attribution_type": "DIRECT_QUOTE",
        "claim_source_url": "https://aiadmk.org.in/press/releases/speech-nov10-schools.html",
        "source_document_id": "DOC-SPEECH-2023-11",
        "geographic_scope": "Tamil Nadu",
        "extraction_method": "MANUAL",
        "status": "VERIFIED",
        "review_status": "PEER_REVIEWED",
        "is_human_reviewed": True,
        "reviewer_role": "SENIOR_FACT_CHECKER",
        "reviewer_name": "K. Meenakshi, Senior Education Researcher",
        "review_notes": "Official UDISE+ and School Education Department gazette confirm net enrollment increase was 1.28 lakh, not 5 lakh.",
        "verification": {
            "outcome": "contradicted_by_available_evidence",
            "explanation": "The claim that 5 lakh new students enrolled in state government schools in a single academic year is contradicted by official Unified District Information System for Education Plus (UDISE+) data. The verified net increase in state government school enrolment for the cited period was approximately 1,28,450 students.",
            "methodology": "Cross-verification against central and state gazetted statistical databases.",
            "limitations": "UDISE+ records reflect formal enrolled counts and do not track informal or short-term transitional admissions.",
            "supporting_evidence_ids": [],
            "contradicting_evidence_ids": ["EVD-DOC-UDISE-PLUS-2022-23", "EVD-DOC-TNSCH-ADMIN-2023"],
            "source_diversity": 2,
            "confidence": 0.92,
            "verification_timestamp": "2023-11-14T11:20:00Z",
            "epistemic_disclaimer": "Assessment is based strictly on officially audited registry counts. Does not infer speaker intent."
        },
        "atomic_claims": [
            {
                "atomic_claim_id": "ATM-CLM-02-01",
                "atomic_claim_text": "5 lakh new students enrolled in state government schools in a single academic year.",
                "language": "en",
                "subject": "State Government Schools Enrolment",
                "predicate": "enrolled",
                "object": "5 lakh students",
                "numeric_value": 500000,
                "unit": "students",
                "time_period": "Academic Year 2022-23",
                "claim_type": "QUANTITATIVE",
                "is_verifiable": True,
                "confidence": 0.95
            }
        ],
        "relationships": [
            {
                "evidence_document_id": "EVD-DOC-UDISE-PLUS-2022-23",
                "evidence_title": "UDISE+ Report on School Enrolment 2022-23 (Tamil Nadu Chapter)",
                "publisher": "Department of School Education and Literacy, Govt of India",
                "relationship_type": "contradicts",
                "relevant_passage": "Total Government School Enrolment in Tamil Nadu stood at 52,41,200 compared to 51,12,750 in the preceding year, showing a net addition of 1,28,450 pupils.",
                "source_url": "https://udiseplus.gov.in/report/tn_2022_23.pdf",
                "publication_date": "2023-09-15"
            },
            {
                "evidence_document_id": "EVD-DOC-TNSCH-ADMIN-2023",
                "evidence_title": "School Education Department Policy Note 2023-24",
                "publisher": "School Education Department, Govt of Tamil Nadu",
                "relationship_type": "contradicts",
                "relevant_passage": "During the intensive admission drive, 1.3 lakh students migrated from private to government schools across primary and upper primary tiers.",
                "source_url": "https://cms.tn.gov.in/sites/default/files/documents/school_edu_policy_2023.pdf",
                "publication_date": "2023-04-18"
            }
        ],
        "cross_phase": {
            "historical_scheme": None,
            "promise": None,
            "news_article": None,
            "financial_document": None,
            "representative": None
        }
    },
    {
        "claim_id": "TEST_FIXTURE_CLM_03",
        "original_text": "மாதம் ரூ.1,000 உரிமைத் தொகை திட்டத்தின் கீழ் 1.15 கோடி மகளிருக்கு வங்கிக் கணக்கில் நேரடியாக வரவு வைக்கப்பட்டுள்ளது.",
        "normalized_text": "மாதம் ரூ 1000 உரிமைத் தொகை திட்டத்தின் கீழ் 1 15 கோடி மகளிருக்கு வங்கிக் கணக்கில் நேரடியாக வரவு வைக்கப்பட்டுள்ளது",
        "claim_category": "GOVERNMENT_SCHEMES",
        "language": "ta",
        "speaker_name": "M.K. Stalin",
        "speaker_role": "Chief Minister of Tamil Nadu",
        "party": "DMK",
        "claim_date": "2024-01-20",
        "publication_date": "2024-01-20",
        "candidate_source_type": "OFFICIAL_STATEMENT",
        "attribution_type": "DIRECT_QUOTE",
        "claim_source_url": "https://tndipr.gov.in/press-release/pr-kmur-jan2024.html",
        "source_document_id": "DOC-DIPR-2024-01",
        "geographic_scope": "Tamil Nadu",
        "extraction_method": "MANUAL",
        "status": "VERIFIED",
        "review_status": "CONFIRMED",
        "is_human_reviewed": True,
        "reviewer_role": "LEAD_REVIEWER",
        "reviewer_name": "Editorial Verification Board",
        "review_notes": "Cross-verified with Public Finance Direct Benefit Transfer audit and Special Programme Implementation Department gazette.",
        "verification": {
            "outcome": "supported_by_available_evidence",
            "explanation": "The statement that 1.15 crore women receive direct benefit transfers of Rs. 1,000 per month under the Kalaignar Magalir Urimai Thittam is corroborated by Special Programme Implementation Department gazettes and DBT electronic disbursement logs for January 2024.",
            "methodology": "Direct benefit transfer verification against state treasury audit records.",
            "limitations": "Beneficiary count fluctuates across monthly reconciliation cycles due to Aadhaar de-duplication and appeals.",
            "supporting_evidence_ids": ["EVD-DOC-SPI-GO-2023", "EVD-DOC-TN-BUDGET-2024"],
            "contradicting_evidence_ids": [],
            "source_diversity": 2,
            "confidence": 0.97,
            "verification_timestamp": "2024-01-22T10:00:00Z",
            "epistemic_disclaimer": "Verifies program disbursement metrics as officially gazetted; does not evaluate scheme efficacy."
        },
        "atomic_claims": [
            {
                "atomic_claim_id": "ATM-CLM-03-01",
                "atomic_claim_text": "1.15 crore women receive direct monthly financial assistance of Rs. 1,000 under the scheme.",
                "language": "en",
                "subject": "Kalaignar Magalir Urimai Thittam",
                "predicate": "credited to",
                "object": "1.15 crore women bank accounts",
                "numeric_value": 11500000,
                "unit": "beneficiaries",
                "time_period": "January 2024",
                "claim_type": "QUANTITATIVE",
                "is_verifiable": True,
                "confidence": 0.98
            }
        ],
        "relationships": [
            {
                "evidence_document_id": "EVD-DOC-SPI-GO-2023",
                "evidence_title": "G.O. (Ms) No. 45: Kalaignar Magalir Urimai Thittam Sanction Order",
                "publisher": "Special Programme Implementation Dept, Govt of Tamil Nadu",
                "relationship_type": "supports",
                "relevant_passage": "The Government hereby approves monthly assistance of Rs. 1,000 via DBT to 1,15,16,292 verified women heads of families.",
                "source_url": "https://cms.tn.gov.in/sites/default/files/go/spid_e_45_2023.pdf",
                "publication_date": "2023-09-11"
            },
            {
                "evidence_document_id": "EVD-DOC-TN-BUDGET-2024",
                "evidence_title": "Tamil Nadu Budget Speech 2024-25 (Finance Department)",
                "publisher": "Finance Department, Govt of Tamil Nadu",
                "relationship_type": "supports",
                "relevant_passage": "Para 44: A sum of Rs. 13,720 crore has been disbursed to 1.15 crore eligible women under this revolutionary scheme.",
                "source_url": "https://budget.tn.gov.in/speeches/budget_speech_2024_25.pdf",
                "publication_date": "2024-02-19"
            }
        ],
        "cross_phase": {
            "historical_scheme": {
                "id": 101,
                "scheme_name": "Kalaignar Magalir Urimai Thittam",
                "financial_year": "2023-2024"
            },
            "promise": {
                "promise_id": "PRM-2021-DMK-042",
                "original_text": "மாதம் ரூ.1000 உரிமைத் தொகை அனைத்து மகளிருக்கும் வழங்கப்படும்."
            },
            "news_article": {
                "article_id": "ART-2024-HIN-001",
                "title": "Over 1.15 crore women receive monthly financial assistance in Tamil Nadu",
                "url": "https://thehindu.com/news/national/tamil-nadu/magalir-urimai-thittam"
            },
            "financial_document": {
                "document_id": "FIN-DMK-2023-01",
                "financial_year": "2022-2023"
            },
            "representative": {
                "representative_id": "REP-TN-MLA-001",
                "official_name": "M.K. Stalin",
                "representative_type": "MLA"
            }
        }
    },
    {
        "claim_id": "TEST_FIXTURE_CLM_04",
        "original_text": "Over 12,000 km of rural roads were paved with zero maintenance expenditure incurred by the state.",
        "normalized_text": "over 12000 km of rural roads were paved with zero maintenance expenditure incurred by the state",
        "claim_category": "INFRASTRUCTURE",
        "language": "en",
        "speaker_name": "State Infrastructure Spokesperson",
        "speaker_role": "Department Representative",
        "party": "DMK",
        "claim_date": "2023-08-14",
        "publication_date": "2023-08-14",
        "candidate_source_type": "PRESS_RELEASE",
        "attribution_type": "JOURNALIST_SUMMARY",
        "claim_source_url": "https://tn.gov.in/pr/rural-roads-aug2023.pdf",
        "source_document_id": "DOC-PR-RD-2023",
        "geographic_scope": "Tamil Nadu",
        "extraction_method": "AUTOMATED_EXTRACTION",
        "status": "VERIFIED",
        "review_status": "AUTOMATED_INITIAL",
        "is_human_reviewed": False,
        "reviewer_role": None,
        "reviewer_name": None,
        "review_notes": None,
        "verification": {
            "outcome": "partially_supported",
            "explanation": "The claim is partially supported. Evidence confirms that approximately 11,840 km of rural roads were paved under the Tamil Nadu Rural Roads Improvement Scheme. However, the secondary assertion that 'zero maintenance expenditure was incurred' is contradicted by Demand for Grants No. 42, which gazettes Rs. 320 crore in routine and periodic road maintenance expenditures.",
            "methodology": "Two-proposition atomic decomposition with separate evidence relationship matching.",
            "limitations": "Contractor defect-liability periods cover capital works; routine surface repairs remain state expenses.",
            "supporting_evidence_ids": ["EVD-DOC-RDPR-ADMIN-2023"],
            "contradicting_evidence_ids": ["EVD-DOC-TN-DEMAND-GRANTS-42"],
            "source_diversity": 2,
            "confidence": 0.88,
            "verification_timestamp": "2023-08-16T09:15:00Z",
            "epistemic_disclaimer": "Evaluates documented road length and fiscal appropriations separately."
        },
        "atomic_claims": [
            {
                "atomic_claim_id": "ATM-CLM-04-01",
                "atomic_claim_text": "12,000 km of rural roads were paved.",
                "language": "en",
                "subject": "Rural Road Infrastructure",
                "predicate": "paved",
                "object": "12,000 km",
                "numeric_value": 12000,
                "unit": "km",
                "time_period": "2022-2023",
                "claim_type": "QUANTITATIVE",
                "is_verifiable": True,
                "confidence": 0.94
            },
            {
                "atomic_claim_id": "ATM-CLM-04-02",
                "atomic_claim_text": "Zero maintenance expenditure was incurred by the state.",
                "language": "en",
                "subject": "Road Maintenance Expenditure",
                "predicate": "incurred",
                "object": "Rs. 0",
                "numeric_value": 0,
                "unit": "INR",
                "time_period": "2022-2023",
                "claim_type": "QUANTITATIVE",
                "is_verifiable": True,
                "confidence": 0.91
            }
        ],
        "relationships": [
            {
                "evidence_document_id": "EVD-DOC-RDPR-ADMIN-2023",
                "evidence_title": "Rural Development & Panchayat Raj Administrative Report 2022-23",
                "publisher": "RDPR Department, Govt of Tamil Nadu",
                "relationship_type": "supports",
                "relevant_passage": "Under TNRRIS, a cumulative length of 11,842 km of village panchayat and panchayat union roads was blacktopped and upgraded.",
                "source_url": "https://tnrd.tn.gov.in/reports/admin_report_2023.pdf",
                "publication_date": "2023-07-20"
            },
            {
                "evidence_document_id": "EVD-DOC-TN-DEMAND-GRANTS-42",
                "evidence_title": "Detailed Demand for Grants No. 42 (Panchayat Raj), Budget 2023-24",
                "publisher": "Finance Department, Govt of Tamil Nadu",
                "relationship_type": "contradicts",
                "relevant_passage": "Sub-Head 3054-04-105: Periodic Maintenance and Flood Damage Repairs for Rural Roads: Revised Estimate Rs. 320.45 crore.",
                "source_url": "https://budget.tn.gov.in/grants/demand_42_2023.pdf",
                "publication_date": "2023-03-20"
            }
        ],
        "cross_phase": {
            "historical_scheme": None,
            "promise": None,
            "news_article": None,
            "financial_document": None,
            "representative": None
        }
    },
    {
        "claim_id": "TEST_FIXTURE_CLM_05",
        "original_text": "Tamil Nadu attracted Rs 6.6 lakh crore in fresh industrial investments creating 10 lakh new jobs in 2023 alone.",
        "normalized_text": "tamil nadu attracted rs 66 lakh crore in fresh industrial investments creating 10 lakh new jobs in 2023 alone",
        "claim_category": "ECONOMIC_METRICS",
        "language": "en",
        "speaker_name": "Industries Representative",
        "speaker_role": "Government Delegate",
        "party": "DMK",
        "claim_date": "2024-01-08",
        "publication_date": "2024-01-09",
        "candidate_source_type": "PRESS_RELEASE",
        "attribution_type": "DIRECT_QUOTE",
        "claim_source_url": "https://guidancetn.com/gim2024-concluding-statement.pdf",
        "source_document_id": "DOC-GIM-2024",
        "geographic_scope": "Tamil Nadu",
        "extraction_method": "MANUAL",
        "status": "VERIFIED",
        "review_status": "PEER_REVIEWED",
        "is_human_reviewed": True,
        "reviewer_role": "SENIOR_FACT_CHECKER",
        "reviewer_name": "A. Balasubramanian, Industrial Policy Analyst",
        "review_notes": "Conflates signed Memoranda of Understanding (MoUs) over a 3-7 year pipeline with realized capital inflow and deployed employment in calendar year 2023.",
        "verification": {
            "outcome": "missing_important_context",
            "explanation": "The statement omits critical context regarding the distinction between signed commitments and realized deployment. The cited ₹6.6 lakh crore refers to Memoranda of Understanding (MoUs) committed during the Global Investors Meet (GIM 2024) with investment realization schedules spanning 3 to 7 years. It does not represent realized capital expenditure or jobs created in 2023 alone.",
            "methodology": "Investment pipeline timeline classification and capital realization tracking.",
            "limitations": "MoU-to-actual realization rates in India historically range between 40% and 65% depending on sector regulatory clearances.",
            "supporting_evidence_ids": ["EVD-DOC-GUIDANCE-GIM-2024"],
            "contradicting_evidence_ids": ["EVD-DOC-DPIIT-FDI-2023"],
            "source_diversity": 2,
            "confidence": 0.89,
            "verification_timestamp": "2024-01-12T16:45:00Z",
            "epistemic_disclaimer": "Clarifies statutory accounting terminology; does not dispute that MoUs were formally signed."
        },
        "atomic_claims": [
            {
                "atomic_claim_id": "ATM-CLM-05-01",
                "atomic_claim_text": "Tamil Nadu secured Rs 6.6 lakh crore investment commitments.",
                "language": "en",
                "subject": "Industrial Investment Commitments",
                "predicate": "signed",
                "object": "Rs 6.6 lakh crore MoUs",
                "numeric_value": 660000,
                "unit": "crore INR",
                "time_period": "2024",
                "claim_type": "QUANTITATIVE",
                "is_verifiable": True,
                "confidence": 0.95
            }
        ],
        "relationships": [
            {
                "evidence_document_id": "EVD-DOC-GUIDANCE-GIM-2024",
                "evidence_title": "Global Investors Meet 2024 Declaration Compendium",
                "publisher": "Guidance Tamil Nadu, Industries Department",
                "relationship_type": "contextualizes",
                "relevant_passage": "A total of 631 Memoranda of Understanding were signed with prospective investment commitments worth Rs. 6,64,180 crore generating potential employment of 14,54,712 over a phased horizon of 3 to 7 years.",
                "source_url": "https://guidancetn.com/gim2024/compendium.pdf",
                "publication_date": "2024-01-08"
            },
            {
                "evidence_document_id": "EVD-DOC-DPIIT-FDI-2023",
                "evidence_title": "FDI Inflow Factsheet (Jan - Dec 2023)",
                "publisher": "DPIIT, Ministry of Commerce and Industry, Govt of India",
                "relationship_type": "contextualizes",
                "relevant_passage": "Tamil Nadu actual realized Foreign Direct Investment equity inflow in calendar year 2023 stood at USD 2.65 billion (Rs. 21,780 crore).",
                "source_url": "https://dpiit.gov.in/fdi-factsheet-dec2023.pdf",
                "publication_date": "2024-02-05"
            }
        ],
        "cross_phase": {
            "historical_scheme": None,
            "promise": None,
            "news_article": None,
            "financial_document": None,
            "representative": None
        }
    },
    {
        "claim_id": "TEST_FIXTURE_CLM_06",
        "original_text": "Public healthcare expenditure in Tamil Nadu is the lowest among all major southern states.",
        "normalized_text": "public healthcare expenditure in tamil nadu is the lowest among all major southern states",
        "claim_category": "STATISTICAL_CLAIMS",
        "language": "en",
        "speaker_name": "Health Policy Critic",
        "speaker_role": "Think Tank Analyst",
        "party": "Independent",
        "claim_date": "2024-03-02",
        "publication_date": "2024-03-03",
        "candidate_source_type": "FACT_CHECK_ARTICLE",
        "attribution_type": "PARAPHRASE",
        "claim_source_url": "https://policynote.org/commentary/south-health-budget.html",
        "source_document_id": "DOC-COMMENTARY-2024",
        "geographic_scope": "Tamil Nadu",
        "extraction_method": "MANUAL",
        "status": "VERIFIED",
        "review_status": "PEER_REVIEWED",
        "is_human_reviewed": True,
        "reviewer_role": "DOMAIN_EXPERT",
        "reviewer_name": "Dr. R. Vengat, Public Health Economist",
        "review_notes": "Statistically disputed depending on whether the indicator is evaluated as % of total budget vs. per-capita health expenditure.",
        "verification": {
            "outcome": "disputed_evidence",
            "explanation": "Evidence is conflicting depending on baseline denominator choice. In terms of health spending as a percentage of total state budget (4.8%), Tamil Nadu ranks lower than Kerala (5.5%). However, in terms of per-capita public health expenditure (₹2,160), Tamil Nadu ranks higher than Andhra Pradesh (₹1,840). Consequently, opposing interpretations arise legitimately from differing metrics.",
            "methodology": "Multi-metric baseline comparison across state finance registers.",
            "limitations": "Comparing sub-national health spending across states with differing population structures can generate conflicting rankings.",
            "supporting_evidence_ids": ["EVD-DOC-PRS-STATE-HEALTH-2024"],
            "contradicting_evidence_ids": ["EVD-DOC-RBI-STATE-FINANCES-2024"],
            "source_diversity": 2,
            "confidence": 0.85,
            "verification_timestamp": "2024-03-06T12:00:00Z",
            "epistemic_disclaimer": "Highlights metric sensitivity; avoids endorsing either unilateral interpretation."
        },
        "atomic_claims": [
            {
                "atomic_claim_id": "ATM-CLM-06-01",
                "atomic_claim_text": "Healthcare expenditure in Tamil Nadu is the lowest among southern states.",
                "language": "en",
                "subject": "Healthcare Spending Comparison",
                "predicate": "ranks lowest among",
                "object": "Southern States",
                "numeric_value": None,
                "unit": "Rank / Comparison",
                "time_period": "FY 2023-24",
                "claim_type": "COMPARATIVE",
                "is_verifiable": True,
                "confidence": 0.88
            }
        ],
        "relationships": [
            {
                "evidence_document_id": "EVD-DOC-PRS-STATE-HEALTH-2024",
                "evidence_title": "State of State Finances 2023-24: Healthcare Outlays",
                "publisher": "PRS Legislative Research",
                "relationship_type": "supports",
                "relevant_passage": "Tamil Nadu allocated 4.8% of its total expenditure towards health in 2023-24, compared to the average of 6.2% across southern states (Kerala 5.5%, Karnataka 5.1%).",
                "source_url": "https://prsindia.org/budgets/states/tamil-nadu-2023-24",
                "publication_date": "2024-02-28"
            },
            {
                "evidence_document_id": "EVD-DOC-RBI-STATE-FINANCES-2024",
                "evidence_title": "State Finances: A Study of Budgets of 2023-24",
                "publisher": "Reserve Bank of India",
                "relationship_type": "contradicts",
                "relevant_passage": "Statement 38: Per Capita Expenditure on Medical and Public Health (2023-24 BE): Tamil Nadu: Rs. 2,162; Andhra Pradesh: Rs. 1,844; Telangana: Rs. 2,680.",
                "source_url": "https://rbi.org.in/scripts/PublicationsView.aspx?id=statefinances2024",
                "publication_date": "2024-01-15"
            }
        ],
        "cross_phase": {
            "historical_scheme": None,
            "promise": None,
            "news_article": None,
            "financial_document": None,
            "representative": None
        }
    },
    {
        "claim_id": "TEST_FIXTURE_CLM_07",
        "original_text": "Our party has always stood as the only genuine protector of social justice in Tamil Nadu.",
        "normalized_text": "our party has always stood as the only genuine protector of social justice in tamil nadu",
        "claim_category": "POLITICAL_PROMISES",
        "language": "en",
        "speaker_name": "Party Campaigner",
        "speaker_role": "Campaign Spokesperson",
        "party": "All",
        "claim_date": "2024-04-01",
        "publication_date": "2024-04-01",
        "candidate_source_type": "SPEECH",
        "attribution_type": "DIRECT_QUOTE",
        "claim_source_url": "https://campaign-rally.org/speech-0401.html",
        "source_document_id": "DOC-SPEECH-2024-04",
        "geographic_scope": "Tamil Nadu",
        "extraction_method": "AUTOMATED_EXTRACTION",
        "status": "VERIFIED",
        "review_status": "AUTOMATED_INITIAL",
        "is_human_reviewed": False,
        "reviewer_role": None,
        "reviewer_name": None,
        "review_notes": None,
        "verification": {
            "outcome": "unverifiable",
            "explanation": "This statement expresses a normative political philosophy, moral self-appraisal, and subjective value judgment ('only genuine protector of social justice'). It lacks an empirical proposition, testable quantitative metric, or objective falsification baseline.",
            "methodology": "Verifiability screening and speech-act classification.",
            "limitations": "Philosophical and ideological stances are not empirically verifiable through public records.",
            "supporting_evidence_ids": [],
            "contradicting_evidence_ids": [],
            "source_diversity": 0,
            "confidence": 0.99,
            "verification_timestamp": "2024-04-02T08:00:00Z",
            "epistemic_disclaimer": "Non-verifiable statements are preserved with verbatim fidelity without truth-value judgment."
        },
        "atomic_claims": [
            {
                "atomic_claim_id": "ATM-CLM-07-01",
                "atomic_claim_text": "Our party is the only genuine protector of social justice.",
                "language": "en",
                "subject": "Party Ideology",
                "predicate": "stands as",
                "object": "only genuine protector of social justice",
                "numeric_value": None,
                "unit": None,
                "time_period": "Historical / Ongoing",
                "claim_type": "OPINION",
                "is_verifiable": False,
                "confidence": 0.99
            }
        ],
        "relationships": [],
        "cross_phase": {
            "historical_scheme": None,
            "promise": None,
            "news_article": None,
            "financial_document": None,
            "representative": None
        }
    },
    {
        "claim_id": "TEST_FIXTURE_CLM_08",
        "original_text": "Tamil Nadu commissioned 3,500 MW of green solar capacity during the last calendar year.",
        "normalized_text": "tamil nadu commissioned 3500 mw of green solar capacity during the last calendar year",
        "claim_category": "INFRASTRUCTURE",
        "language": "en",
        "speaker_name": "Clean Energy Forum Speaker",
        "speaker_role": "Energy Representative",
        "party": "Independent",
        "claim_date": "2024-05-12",
        "publication_date": "2024-05-12",
        "candidate_source_type": "PRESS_RELEASE",
        "attribution_type": "DIRECT_QUOTE",
        "claim_source_url": "https://energyforum.org/tn-solar-2024.pdf",
        "source_document_id": "DOC-CLEAN-ENERGY-2024",
        "geographic_scope": "Tamil Nadu",
        "extraction_method": "AUTOMATED_EXTRACTION",
        "status": "UNVERIFIED",
        "review_status": "pending_review",
        "is_human_reviewed": False,
        "reviewer_role": None,
        "reviewer_name": None,
        "review_notes": "Awaiting final gazetted tariff order from TNERC and MNRE annual state deployment publication.",
        "verification": {
            "outcome": "insufficient_evidence",
            "explanation": "Audited official installation data for the specified calendar year has not yet been gazetted by the Ministry of New and Renewable Energy (MNRE) or Tamil Nadu Electricity Regulatory Commission (TNERC). Preliminary news reports indicate 1,200 MW, but official validation remains pending.",
            "methodology": "Public regulatory registry synchronization.",
            "limitations": "Commercial rooftop solar and captive power plants face reporting lags of 6-9 months before consolidated grid injection numbers are published.",
            "supporting_evidence_ids": [],
            "contradicting_evidence_ids": [],
            "source_diversity": 0,
            "confidence": 0.65,
            "verification_timestamp": "2024-05-14T11:00:00Z",
            "epistemic_disclaimer": "Absence of gazetted data does not imply falsehood; indicates pending data collection."
        },
        "atomic_claims": [
            {
                "atomic_claim_id": "ATM-CLM-08-01",
                "atomic_claim_text": "Tamil Nadu commissioned 3,500 MW of solar capacity in the last calendar year.",
                "language": "en",
                "subject": "Solar Generation Capacity",
                "predicate": "commissioned",
                "object": "3,500 MW",
                "numeric_value": 3500,
                "unit": "MW",
                "time_period": "2023",
                "claim_type": "QUANTITATIVE",
                "is_verifiable": True,
                "confidence": 0.92
            }
        ],
        "relationships": [],
        "cross_phase": {
            "historical_scheme": None,
            "promise": None,
            "news_article": None,
            "financial_document": None,
            "representative": None
        }
    },
    {
        "claim_id": "TEST_FIXTURE_CLM_09",
        "original_text": "Tamil Nadu has achieved 100% tap water connections in all rural school complexes.",
        "normalized_text": "tamil nadu has achieved 100 tap water connections in all rural school complexes",
        "claim_category": "PUBLIC_HEALTH",
        "language": "en",
        "speaker_name": "Rural Water Supply Representative",
        "speaker_role": "Executive Engineer",
        "party": "Independent",
        "claim_date": "2024-06-01",
        "publication_date": "2024-06-01",
        "candidate_source_type": "PRESS_RELEASE",
        "attribution_type": "DIRECT_QUOTE",
        "claim_source_url": "https://jjm.gov.in/tn/rural-schools-status.pdf",
        "source_document_id": "DOC-JJM-2024-06",
        "geographic_scope": "Tamil Nadu",
        "extraction_method": "AUTOMATED_EXTRACTION",
        "status": "UNVERIFIED",
        "review_status": "pending_review",
        "is_human_reviewed": False,
        "reviewer_role": None,
        "reviewer_name": None,
        "review_notes": None,
        "verification": {
            "outcome": "pending_review",
            "explanation": "Preliminary automated retrieval flagged conflicting field audit reports regarding functional tap connections in remote tribal hamlets. Formal peer review is pending submission by the domain expert.",
            "methodology": "Automated retrieval flag triggered for expedited peer review.",
            "limitations": "Jal Jeevan Mission MIS portal records updates weekly; ground validation by district engineers ongoing.",
            "supporting_evidence_ids": [],
            "contradicting_evidence_ids": [],
            "source_diversity": 1,
            "confidence": 0.50,
            "verification_timestamp": "2024-06-02T09:00:00Z",
            "epistemic_disclaimer": "Pending human peer review determination."
        },
        "atomic_claims": [
            {
                "atomic_claim_id": "ATM-CLM-09-01",
                "atomic_claim_text": "Tamil Nadu achieved 100% tap water connections in all rural school complexes.",
                "language": "en",
                "subject": "Rural Schools Tap Water Coverage",
                "predicate": "achieved",
                "object": "100% coverage",
                "numeric_value": 100,
                "unit": "%",
                "time_period": "2024",
                "claim_type": "QUANTITATIVE",
                "is_verifiable": True,
                "confidence": 0.88
            }
        ],
        "relationships": [],
        "cross_phase": {
            "historical_scheme": None,
            "promise": None,
            "news_article": None,
            "financial_document": None,
            "representative": None
        }
    }
]


def _filter_fixture_claims(claims: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    filtered = []
    for c in claims:
        # Keyword search
        q = filters.get("q")
        if q:
            q_lower = q.lower()
            text_match = q_lower in c.get("original_text", "").lower()
            speaker_match = q_lower in (c.get("speaker_name") or "").lower()
            claim_id_match = q_lower in c.get("claim_id", "").lower()
            if not (text_match or speaker_match or claim_id_match):
                continue

        # Category
        cat = filters.get("category")
        if cat and cat != "All" and c.get("claim_category") != cat:
            continue

        # Outcome
        outc = filters.get("outcome")
        if outc and outc != "All":
            c_outcome = c.get("verification", {}).get("outcome") if isinstance(c.get("verification"), dict) else None
            if c_outcome != outc:
                continue

        # Review Status
        rstat = filters.get("review_status")
        if rstat and rstat != "All" and c.get("review_status") != rstat:
            continue

        # Language
        lang = filters.get("language")
        if lang and lang != "All" and c.get("language") != lang:
            continue

        # Party
        pty = filters.get("party")
        if pty and pty != "All" and c.get("party") != pty:
            continue

        # Speaker
        spk = filters.get("speaker")
        if spk and spk.lower() not in (c.get("speaker_name") or "").lower():
            continue

        filtered.append(c)
    return filtered


def load_all_claims(filters: Dict[str, Any], use_fixtures_only: bool = False) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Attempts to fetch claims from the live backend API.
    If the backend is offline, returns empty, or error, falls back gracefully
    to verified test fixtures. Returns (claims_list, is_using_fixtures).
    """
    if use_fixtures_only:
        filtered = _filter_fixture_claims(FIXTURE_CLAIMS, filters)
        return filtered, True

    try:
        ok, res = api_client.search_claims(
            q=filters.get("q"),
            category=filters.get("category"),
            status=filters.get("status"),
            outcome=filters.get("outcome"),
            party=filters.get("party"),
            speaker=filters.get("speaker"),
            language=filters.get("language"),
            limit=filters.get("limit", 100)
        )
        if ok and res.get("claims"):
            return res["claims"], False
    except Exception:
        pass

    # Fallback to verified fixtures
    filtered = _filter_fixture_claims(FIXTURE_CLAIMS, filters)
    return filtered, True


def find_claim_by_id(claim_id: str, use_fixtures_only: bool = False) -> Tuple[Optional[Dict[str, Any]], bool]:
    """Finds single claim detail via API, falls back to fixtures."""
    if not use_fixtures_only:
        try:
            ok, res = api_client.get_claim_detail(claim_id)
            if ok and "claim" in res:
                return res["claim"], False
        except Exception:
            pass

    # Check fixtures
    for c in FIXTURE_CLAIMS:
        if c["claim_id"] == claim_id:
            return c, True
    return None, True
