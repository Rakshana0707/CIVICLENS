"""
Phase 7 — Synthetic Test Fixtures for Political Claim Verification & Evidence Intelligence.

Provides isolated mock claims, evidence documents, passages, and review records explicitly
labelled as test fixtures (`is_test_fixture = True`).

Covers bilingual statements (Tamil and English) across core claim categories:
- Government Schemes
- Budget and Expenditure
- Election Results
- Political Promises
- Representative Activity
- Public Funding
- Disputed / Contradicted assertions
- Unverifiable assertions (missing / delayed evidence)
"""

from typing import Dict, Any, List

# Explicit Test Fixture Metadata Marker
IS_TEST_FIXTURE = True
FIXTURE_VERSION = "7.0-test"

# ---------------------------------------------------------------------------
# 1. Sample Claims Fixtures
# ---------------------------------------------------------------------------
MOCK_CLAIMS: List[Dict[str, Any]] = [
    {
        "claim_id": "CLM-FIX-001-SCHEME",
        "original_text": "கலைஞர் மகளிர் உரிமைத் திட்டத்தின் கீழ் 1.15 கோடி மகளிருக்கு மாதம் ₹1,000 வழங்கப்பட்டு வருகிறது.",
        "normalized_text": "கலைஞர் மகளிர் உரிமைத் திட்டத்தின் கீழ் 1.15 கோடி மகளிருக்கு மாதம் 1000 வழங்கப்பட்டு வருகிறது",
        "context_text": "2023 தமிழ்நாடு சட்டமன்றக் கூட்டத்தொடரில் ஆற்றிய உரை.",
        "language": "ta",
        "claim_category": "GOVERNMENT_SCHEMES",
        "speaker_name": "M. K. Stalin",
        "speaker_party": "DMK",
        "temporal_scope": "2023-2024",
        "geographic_scope": "Tamil Nadu",
        "is_test_fixture": True,
        "expected_verdict": "SUPPORTED",
        "subjects": [
            {"subject_type": "POLITICIAN", "canonical_name": "M. K. Stalin", "entity_id": "REP-MLA-013-STALIN"},
            {"subject_type": "SCHEME", "canonical_name": "Kalaignar Magalir Urimai Thogai", "entity_id": "SCHEME-KMUT-2023"},
            {"subject_type": "GOVERNMENT_DEPARTMENT", "canonical_name": "Special Programme Implementation Department"}
        ]
    },
    {
        "claim_id": "CLM-FIX-002-BUDGET-CONTRADICTED",
        "original_text": "In the 2022-23 State Budget, the Tamil Nadu government allocated ₹15,000 Crore exclusively for farmer debt relief.",
        "normalized_text": "in the 2022 23 state budget the tamil nadu government allocated 15000 crore exclusively for farmer debt relief",
        "context_text": "Press conference delivered during election campaign rally in Thanjavur.",
        "language": "en",
        "claim_category": "BUDGET_EXPENDITURE",
        "speaker_name": "Edappadi K. Palaniswami",
        "speaker_party": "AIADMK",
        "temporal_scope": "2022-2023",
        "geographic_scope": "Tamil Nadu",
        "is_test_fixture": True,
        "expected_verdict": "CONTRADICTED",
        "subjects": [
            {"subject_type": "GOVERNMENT_DEPARTMENT", "canonical_name": "Agriculture and Farmers Welfare Department"},
            {"subject_type": "POLITICAL_PARTY", "canonical_name": "AIADMK", "entity_id": "PARTY-AIADMK"}
        ]
    },
    {
        "claim_id": "CLM-FIX-003-ELECTION",
        "original_text": "In the 2021 Assembly elections, the winning margin in Kolathur constituency was over 30,000 votes.",
        "normalized_text": "in the 2021 assembly elections the winning margin in kolathur constituency was over 30000 votes",
        "context_text": "Post-election analytical discussion on regional television.",
        "language": "en",
        "claim_category": "ELECTION_RESULTS",
        "speaker_name": "Media Panelist",
        "speaker_party": "IND",
        "temporal_scope": "2021",
        "geographic_scope": "Kolathur (AC-013)",
        "is_test_fixture": True,
        "expected_verdict": "SUPPORTED",
        "subjects": [
            {"subject_type": "CONSTITUENCY", "canonical_name": "Kolathur", "entity_id": "AC-013-2008"},
            {"subject_type": "POLITICIAN", "canonical_name": "M. K. Stalin", "entity_id": "REP-MLA-013-STALIN"}
        ]
    },
    {
        "claim_id": "CLM-FIX-004-REPRESENTATIVE",
        "original_text": "Our South Chennai MP raised 120 questions in the 17th Lok Sabha regarding coastal environmental clearances.",
        "normalized_text": "our south chennai mp raised 120 questions in the 17th lok sabha regarding coastal environmental clearances",
        "context_text": "Campaign speech at Besant Nagar, Chennai.",
        "language": "en",
        "claim_category": "REPRESENTATIVE_ACTIVITY",
        "speaker_name": "Thamizhachi Thangapandian",
        "speaker_party": "DMK",
        "temporal_scope": "2019-2024",
        "geographic_scope": "Chennai South (PC-03)",
        "is_test_fixture": True,
        "expected_verdict": "PARTIALLY_SUPPORTED",
        "subjects": [
            {"subject_type": "POLITICIAN", "canonical_name": "Thamizhachi Thangapandian", "entity_id": "REP-MP-003-TT"},
            {"subject_type": "CONSTITUENCY", "canonical_name": "Chennai South", "entity_id": "PC-003-2008"}
        ]
    },
    {
        "claim_id": "CLM-FIX-005-FUNDING",
        "original_text": "Over 90% of DMK's total declared corporate contributions in FY 2022-23 originated from Electoral Trusts.",
        "normalized_text": "over 90 percent of dmks total declared corporate contributions in fy 2022 23 originated from electoral trusts",
        "context_text": "Civic research seminar on political funding transparency.",
        "language": "en",
        "claim_category": "PUBLIC_FUNDING",
        "speaker_name": "ADR State Coordinator",
        "speaker_party": "NGO",
        "temporal_scope": "2022-2023",
        "geographic_scope": "Tamil Nadu",
        "is_test_fixture": True,
        "expected_verdict": "SUPPORTED",
        "subjects": [
            {"subject_type": "POLITICAL_PARTY", "canonical_name": "DMK", "entity_id": "PARTY-DMK"},
            {"subject_type": "INSTITUTION", "canonical_name": "Prudent Electoral Trust"}
        ]
    },
    {
        "claim_id": "CLM-FIX-006-UNVERIFIABLE",
        "original_text": "The secret cabinet sub-committee resolved in 2020 to construct an underground bullet train across Madurai.",
        "normalized_text": "the secret cabinet sub committee resolved in 2020 to construct an underground bullet train across madurai",
        "context_text": "Unverified assertion in local political gossip blog.",
        "language": "en",
        "claim_category": "PUBLIC_INFRASTRUCTURE",
        "speaker_name": "Anonymous Commentator",
        "speaker_party": "IND",
        "temporal_scope": "2020",
        "geographic_scope": "Madurai",
        "is_test_fixture": True,
        "expected_verdict": "UNVERIFIABLE_INSUFFICIENT_EVIDENCE",
        "subjects": [
            {"subject_type": "GOVERNMENT_DEPARTMENT", "canonical_name": "Special Initiatives Department"}
        ]
    },
    {
        "claim_id": "CLM-FIX-007-CONTEXT-OMISSION",
        "original_text": "Under our administration, Tamil Nadu state debt increased by ₹1,50,000 Crore in a single financial year.",
        "normalized_text": "under our administration tamil nadu state debt increased by 150000 crore in a single financial year",
        "context_text": "Press briefing quoting nominal gross borrowing without citing GSDP ratio or pandemic revenue shocks.",
        "language": "en",
        "claim_category": "BUDGET_EXPENDITURE",
        "speaker_name": "Opposition Spokesperson",
        "speaker_party": "AIADMK",
        "temporal_scope": "2021-2022",
        "geographic_scope": "Tamil Nadu",
        "is_test_fixture": True,
        "expected_verdict": "MISLEADING_CONTEXT",
        "subjects": [
            {"subject_type": "GOVERNMENT_DEPARTMENT", "canonical_name": "Finance Department TN"}
        ]
    }
]

# ---------------------------------------------------------------------------
# 2. Sample Evidence Documents Fixtures
# ---------------------------------------------------------------------------
MOCK_EVIDENCE_DOCS: List[Dict[str, Any]] = [
    {
        "document_id": "EDOC-FIX-001-GO-KMUT",
        "source_tier": "TIER_1_STATUTORY",
        "source_name": "Special Programme Implementation Department, Govt of Tamil Nadu",
        "document_type": "GOVERNMENT_ORDER",
        "title": "G.O. Ms. No. 37 - Kalaignar Magalir Urimai Thittam Guidelines and Sanctions",
        "publication_date": "2023-07-24T00:00:00Z",
        "source_url": "https://www.tn.gov.in/go_view/dept/37/2023",
        "file_hash_sha256": "3a88c0a2bf4e8db00bb8db19468e82ef451e06fa87d3a046c82d506ad65a0b12",
        "language": "ta",
        "is_official": True,
        "is_test_fixture": True,
        "passages": [
            {
                "passage_id": "EPASS-FIX-001-A",
                "passage_text": "இத்திட்டத்தின் மூலம் தகுதிவாய்ந்த குடும்பத்தலைவிகளுக்கு மாதம் ₹1,000 உரிமைத்தொகை வழங்கப்படும். முதற்கட்டமாக சுமார் 1.06 கோடி முதல் 1.15 கோடி குடும்பத்தலைவிகள் பயனடைவர்.",
                "page_number": 4,
                "section_or_table": "Section 4.1 Beneficiary Eligibility",
                "numerical_values": {"monthly_stipend_inr": 1000, "beneficiaries_crores": 1.15}
            }
        ]
    },
    {
        "document_id": "EDOC-FIX-002-TN-BUDGET-2022",
        "source_tier": "TIER_1_STATUTORY",
        "source_name": "Finance Department, Govt of Tamil Nadu",
        "document_type": "BUDGET_DDG",
        "title": "Demand No. 05 - Agriculture and Farmers Welfare Department Detailed Demands 2022-23",
        "publication_date": "2022-03-18T00:00:00Z",
        "source_url": "https://www.tnbudget.tn.gov.in/2022_2023/Demand_05.pdf",
        "file_hash_sha256": "4b99d1b3cf5e9ec11cc9ec20579f93ff562f17ab98e4b157d93e617be76b1c23",
        "language": "en",
        "is_official": True,
        "is_test_fixture": True,
        "passages": [
            {
                "passage_id": "EPASS-FIX-002-A",
                "passage_text": "Under Demand No. 05, the total budget estimate for Agriculture and Farmers Welfare is ₹6,280.45 Crore. Debt waiver provision for cooperative societies stands at ₹2,393 Crore.",
                "page_number": 12,
                "section_or_table": "Head 2401-00-103-JA",
                "numerical_values": {"total_allocation_cr": 6280.45, "debt_waiver_cr": 2393.0}
            }
        ]
    },
    {
        "document_id": "EDOC-FIX-003-ECI-FORM21E",
        "source_tier": "TIER_1_STATUTORY",
        "source_name": "Election Commission of India",
        "document_type": "ELECTION_RETURN",
        "title": "Form 21E Return of Election - 013 Kolathur Assembly Constituency 2021",
        "publication_date": "2021-05-02T00:00:00Z",
        "source_url": "https://results.eci.gov.in/Result2021/ConstituencywiseS2213.htm",
        "file_hash_sha256": "5c00e2c4df6f0fd22dd0fd31680a04aa673028bc09f5c268e04f728cf87c2d34",
        "language": "en",
        "is_official": True,
        "is_test_fixture": True,
        "passages": [
            {
                "passage_id": "EPASS-FIX-003-A",
                "passage_text": "Total valid votes polled: 1,74,233. M. K. Stalin (DMK): 1,05,522 votes. Aadi Rajaram (AIADMK): 75,138 votes. Margin of victory: 30,384 votes.",
                "page_number": 1,
                "section_or_table": "Declaration of Result",
                "numerical_values": {"winner_votes": 105522, "runner_up_votes": 75138, "margin_votes": 30384}
            }
        ]
    },
    {
        "document_id": "EDOC-FIX-004-SANSAD-QUESTIONS",
        "source_tier": "TIER_1_STATUTORY",
        "source_name": "Lok Sabha Secretariat, Parliament of India",
        "document_type": "HANSARD_DEBATE",
        "title": "17th Lok Sabha Questions and Answers Repository - Member Activity Log",
        "publication_date": "2024-02-10T00:00:00Z",
        "source_url": "https://sansad.in/ls/members/activity",
        "file_hash_sha256": "6d11f3d5ea701ae33ee1ae42791b15bb784139cd10a6d379f15a839da98d3e45",
        "language": "en",
        "is_official": True,
        "is_test_fixture": True,
        "passages": [
            {
                "passage_id": "EPASS-FIX-004-A",
                "passage_text": "Member Dr. Thamizhachi Thangapandian (Chennai South): Total questions asked: 122 across all sessions. Questions relating to Coastal Zone Management and Environment: 14.",
                "page_number": 45,
                "section_or_table": "Member Statistical Summary",
                "numerical_values": {"total_questions": 122, "coastal_questions": 14}
            }
        ]
    },
    {
        "document_id": "EDOC-FIX-005-ECI-FORM24A",
        "source_tier": "TIER_1_STATUTORY",
        "source_name": "Election Commission of India Political Finance Unit",
        "document_type": "STATUTORY_FINANCIAL_DISCLOSURE",
        "title": "Form 24A Contribution Report FY 2022-23 - Dravida Munnetra Kazhagam",
        "publication_date": "2023-09-30T00:00:00Z",
        "source_url": "https://www.eci.gov.in/political-parties/annual-audit-reports",
        "file_hash_sha256": "7e22a4e6fb812bf44ff2bf53802c26cc895240de21b7e480a26b940eb09e4f56",
        "language": "en",
        "is_official": True,
        "is_test_fixture": True,
        "passages": [
            {
                "passage_id": "EPASS-FIX-005-A",
                "passage_text": "Total contributions in excess of ₹20,000 received: ₹192.5 Crore. Contributions from Electoral Trusts (Prudent Electoral Trust): ₹180.0 Crore (93.5% of total itemized donations).",
                "page_number": 2,
                "section_or_table": "Schedule A - Contributions Exceeding Rs 20,000",
                "numerical_values": {"total_donations_cr": 192.5, "electoral_trust_cr": 180.0, "trust_pct": 93.5}
            }
        ]
    }
]

# ---------------------------------------------------------------------------
# 3. Sample Human Review Records Fixtures
# ---------------------------------------------------------------------------
MOCK_REVIEWS: List[Dict[str, Any]] = [
    {
        "review_id": "REV-FIX-001",
        "claim_id": "CLM-FIX-001-SCHEME",
        "reviewer_id": "analyst_tamil_civic_01",
        "reviewer_role": "SENIOR_FACT_CHECKER",
        "review_status": "ACCEPTED",
        "reviewed_verdict": "SUPPORTED",
        "review_notes": "Corroborated by official G.O. Ms. No. 37 and ongoing state DIPR disbursement releases.",
        "override_applied": False
    },
    {
        "review_id": "REV-FIX-002",
        "claim_id": "CLM-FIX-004-REPRESENTATIVE",
        "reviewer_id": "analyst_parliamentary_02",
        "reviewer_role": "LEGISLATIVE_AUDITOR",
        "review_status": "ACCEPTED",
        "reviewed_verdict": "PARTIALLY_SUPPORTED",
        "review_notes": "MP indeed asked 122 questions overall, but only 14 specifically pertained to coastal environmental matters.",
        "override_applied": False
    }
]
