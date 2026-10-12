"""
Phase 9.8 — Frontend Test Fixtures for Unified Civic Evidence Graph Explorer.
=============================================================================

Comprehensive mock dataset covering all 10 entity types across Phases 1–8:
1. schemes
2. budgets
3. promises
4. political parties
5. representatives
6. constituencies
7. public claims
8. civic issues
9. government departments
10. source documents

Includes explicit edges, candidate proposals, persistent conflicts, and dialectical tensions.
"""

from typing import Dict, Any, List

# -----------------------------------------------------------------------------
# 1. CANONICAL NODES ACROSS ALL 10 ENTITY TYPES
# -----------------------------------------------------------------------------
FIXTURE_GRAPH_NODES: List[Dict[str, Any]] = [
    {
        "node_id": "NODE:DEPT:MAWS",
        "canonical_id": "DEPT-MAWS-TN",
        "label": "Municipal Administration and Water Supply Department",
        "label_ta": "நகராட்சி நிர்வாகம் மற்றும் குடிநீர் வழங்கல் துறை",
        "entity_type": "GOVERNMENT_DEPARTMENT",
        "source_phase": "phase3",
        "properties": {
            "demand_number": "34",
            "nodal_secretary": "Principal Secretary, MAWS",
            "jurisdiction": "Statewide Urban Local Bodies",
        },
        "created_at": "2026-10-12T10:00:00",
    },
    {
        "node_id": "NODE:SCHEME:DESAL_NEMMELI",
        "canonical_id": "SCHEME-NEMMELI-150MLD",
        "label": "Nemmeli 150 MLD Desalination Plant Augmentation Scheme",
        "label_ta": "நெம்மேலி 150 எம்.எல்.டி கடல்நீரை குடிநீராக்கும் திட்டம்",
        "entity_type": "SCHEME",
        "source_phase": "phase2",
        "properties": {
            "head_of_account": "4215-01-102-JA",
            "target_capacity_mld": 150,
            "implementing_agency": "CMWSSB",
            "status": "OPERATIONAL",
        },
        "created_at": "2026-10-12T10:00:00",
    },
    {
        "node_id": "NODE:BUDGET:DEMAND_34_CAPITAL",
        "canonical_id": "BUDGET-2023-24-DEMAND-34",
        "label": "Demand 34 Capital Outlay for Water Infrastructure (Head 4215)",
        "label_ta": "கோரிக்கை 34 குடிநீர் உட்கட்டமைப்பு மூலதனச் செலவு",
        "entity_type": "BUDGET_LINE_ITEM",
        "source_phase": "phase1",
        "properties": {
            "budget_year": "2023-2024",
            "allocated_cr": 1250.75,
            "revised_cr": 1180.20,
            "stage": "REVISED_ESTIMATE",
        },
        "created_at": "2026-10-12T10:00:00",
    },
    {
        "node_id": "NODE:PROM:DMK_DESAL",
        "canonical_id": "PROM-DMK-2021-WATER",
        "label": "DMK Manifesto 2021 Item 114: 24x7 Treated Water Supply & Desalination",
        "label_ta": "திமுக தேர்தல் அறிக்கை 2021 உருப்படி 114: தடையில்லா குடிநீர் மற்றும் கடல்நீரை குடிநீராக்கல்",
        "entity_type": "POLITICAL_PROMISE",
        "source_phase": "phase1",
        "properties": {
            "party": "DMK",
            "manifesto_year": 2021,
            "promise_category": "Water & Sanitation",
            "monitored_status": "IN_PROGRESS",
        },
        "created_at": "2026-10-12T10:00:00",
    },
    {
        "node_id": "NODE:PARTY:DMK",
        "canonical_id": "PARTY-DMK-TN",
        "label": "Dravida Munnetra Kazhagam (DMK)",
        "label_ta": "திராவிட முன்னேற்றக் கழகம்",
        "entity_type": "POLITICAL_PARTY",
        "source_phase": "phase5",
        "properties": {
            "party_abbreviation": "DMK",
            "election_symbol": "Rising Sun",
            "ruling_period": "2021-PRESENT",
        },
        "created_at": "2026-10-12T10:00:00",
    },
    {
        "node_id": "NODE:REP:VELACHERY_MLA",
        "canonical_id": "REP-VELACHERY-MLA-2021",
        "label": "J.M.H. Aassan Maulaana (MLA, Velachery)",
        "label_ta": "ஜே.எம்.எச். அசன் மவுலானா (சட்டமன்ற உறுப்பினர், வேளச்சேரி)",
        "entity_type": "REPRESENTATIVE",
        "source_phase": "phase6",
        "properties": {
            "legislature": "Tamil Nadu Legislative Assembly",
            "term": "2021-2026",
            "party_affiliation": "INC / DMK Alliance",
        },
        "created_at": "2026-10-12T10:00:00",
    },
    {
        "node_id": "NODE:CONST:VELACHERY",
        "canonical_id": "CONST-VELACHERY-026",
        "label": "Velachery Assembly Constituency (AC-026)",
        "label_ta": "வேளச்சேரி சட்டமன்றத் தொகுதி (எண் 026)",
        "entity_type": "CONSTITUENCY",
        "source_phase": "phase6",
        "properties": {
            "district": "Chennai",
            "electorate_size": 312450,
            "zone": "Zone 13 (Adyar) / Zone 14 (Perungudi)",
        },
        "created_at": "2026-10-12T10:00:00",
    },
    {
        "node_id": "NODE:CLAIM:DESAL_OUTPUT",
        "canonical_id": "CLAIM-DESAL-OUTPUT-2024",
        "label": "Claim: Nemmeli Desalination Plant Operating at 150 MLD Daily Output",
        "label_ta": "கூற்று: நெம்மேலி ஆலை தினசரி 150 எம்.எல்.டி முழுத்திறனுடன் இயங்குகிறது",
        "entity_type": "PUBLIC_CLAIM",
        "source_phase": "phase8",
        "properties": {
            "speaker": "Minister for MAWS",
            "statement_date": "2024-02-24",
            "forum": "Press Conference / Assembly Debate",
        },
        "created_at": "2026-10-12T10:00:00",
    },
    {
        "node_id": "NODE:ISSUE:WATER_VELACHERY",
        "canonical_id": "ISSUE-WATER-VELACHERY-2024",
        "label": "Civic Issue: Acute Pipe Water Shortage in Velachery Ward 178",
        "label_ta": "குடிமைப் பிரச்சினை: வேளச்சேரி வார்டு 178 இல் கடுமையான குடிநீர் பற்றாக்குறை",
        "entity_type": "CIVIC_ISSUE",
        "source_phase": "phase7",
        "properties": {
            "category": "Water Supply & Drainage",
            "reported_date": "2024-03-01",
            "dockets_count": 48,
            "administrative_status": "INVESTIGATING",
        },
        "created_at": "2026-10-12T10:00:00",
    },
    {
        "node_id": "NODE:DOC:CAG_2023",
        "canonical_id": "DOC-CAG-REPORT-2023",
        "label": "CAG Audit Report on Urban Water Infrastructure (Report No. 4 of 2023)",
        "label_ta": "நகர்ப்புற குடிநீர் உள்கட்டமைப்பு மீதான சிஏஜி தணிக்கை அறிக்கை (2023)",
        "entity_type": "SOURCE_DOCUMENT",
        "source_phase": "phase8",
        "properties": {
            "doc_type": "STATUTORY_AUDIT",
            "issuing_authority": "Comptroller and Auditor General of India",
            "publication_date": "2023-12-18",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
        "created_at": "2026-10-12T10:00:00",
    },
    {
        "node_id": "NODE:DOC:GOMS42_2023",
        "canonical_id": "DOC-GO-MS-42-MAWS-2023",
        "label": "G.O. (Ms.) No. 42 MAWS Department: Administrative Sanction for Desalination",
        "label_ta": "அரசாணை (நிலை) எண் 42 நகராட்சி நிர்வாகத் துறை: கடல்நீராக்கல் திட்ட நிதி ஒதுக்கீடு",
        "entity_type": "SOURCE_DOCUMENT",
        "source_phase": "phase3",
        "properties": {
            "doc_type": "GOVERNMENT_ORDER",
            "gazette_number": "Part II - Section 2",
            "issuing_authority": "Government of Tamil Nadu",
            "publication_date": "2023-04-12",
            "sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
        },
        "created_at": "2026-10-12T10:00:00",
    },
]


# -----------------------------------------------------------------------------
# 2. EVIDENCE EDGES CONNECTING THE NODES
# -----------------------------------------------------------------------------
FIXTURE_GRAPH_EDGES: List[Dict[str, Any]] = [
    {
        "edge_id": "EDGE:DEPT:SCHEME:001",
        "source_node_id": "NODE:DEPT:MAWS",
        "target_node_id": "NODE:SCHEME:DESAL_NEMMELI",
        "relationship_type": "implements",
        "evidence_reference": "G.O. (Ms.) No. 42 MAWS Dept designates CMWSSB under MAWS as nodal executing body",
        "source_document_id": "DOC-GO-MS-42-MAWS-2023",
        "source_document_url": "https://cms.tn.gov.in/sites/default/files/go/maws_e_42_2023.pdf",
        "source_document_hash": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
        "matching_method": "DIRECT_DOCUMENTARY",
        "confidence_score": 0.98,
        "review_status": "VERIFIED",
        "provenance_status": "VALID",
        "valid_from": "2023-04-12",
        "valid_to": None,
        "explanation": {
            "meaning": "MAWS Department serves as the administrative authority executing and overseeing the Nemmeli plant scheme.",
            "directness": "Direct Primary Source (Government Order)",
            "causality_note": "Confirms administrative governance. Does not evaluate physical water distribution efficacy.",
        },
    },
    {
        "edge_id": "EDGE:SCHEME:BUDGET:001",
        "source_node_id": "NODE:BUDGET:DEMAND_34_CAPITAL",
        "target_node_id": "NODE:SCHEME:DESAL_NEMMELI",
        "relationship_type": "funds",
        "evidence_reference": "Demand for Grants No. 34 Budget Speech & Detailed Capital Outlay Head 4215",
        "source_document_id": "DOC-BUDGET-DEMAND-34-2023",
        "source_document_url": "https://www.tn.gov.in/budget/2023/demand34.pdf",
        "source_document_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        "matching_method": "DETERMINISTIC_ID",
        "confidence_score": 0.95,
        "review_status": "VERIFIED",
        "provenance_status": "VALID",
        "valid_from": "2023-04-01",
        "valid_to": "2024-03-31",
        "explanation": {
            "meaning": "Capital grant allocation under Demand 34 funds capital assets for the Nemmeli desalination augmentation scheme.",
            "directness": "Statutory Budget Document Match",
            "causality_note": "Budget allotment proves financial authorization, but does not prove immediate expenditure or physical completion.",
        },
    },
    {
        "edge_id": "EDGE:PROM:SCHEME:001",
        "source_node_id": "NODE:PROM:DMK_DESAL",
        "target_node_id": "NODE:SCHEME:DESAL_NEMMELI",
        "relationship_type": "promises",
        "evidence_reference": "Manifesto Item 114 commits to augmenting South Chennai water supply via Nemmeli desalination",
        "source_document_id": "DOC-DMK-MANIFESTO-2021",
        "source_document_url": "https://dmk.in/manifesto2021",
        "source_document_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "matching_method": "HUMAN_REVIEWED",
        "confidence_score": 0.88,
        "review_status": "VERIFIED",
        "provenance_status": "VALID",
        "valid_from": "2021-05-07",
        "valid_to": None,
        "explanation": {
            "meaning": "Political pledge directly references policy objective realized through the Nemmeli augmentation program.",
            "directness": "Corroborated by Verified Policy Linkage",
            "causality_note": "A pledge relating to a scheme does not establish that the scheme was initiated solely because of or fulfilled by this promise.",
        },
    },
    {
        "edge_id": "EDGE:PARTY:REP:001",
        "source_node_id": "NODE:PARTY:DMK",
        "target_node_id": "NODE:REP:VELACHERY_MLA",
        "relationship_type": "relates_to",
        "evidence_reference": "Election Commission of India Form 20 & Alliance seat agreement for Tamil Nadu General Elections 2021",
        "source_document_id": "DOC-ECI-FORM20-TN-2021",
        "source_document_url": "https://eci.gov.in/results/2021/tn",
        "source_document_hash": "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890",
        "matching_method": "DIRECT_DOCUMENTARY",
        "confidence_score": 0.99,
        "review_status": "VERIFIED",
        "provenance_status": "VALID",
        "valid_from": "2021-05-02",
        "valid_to": "2026-05-01",
        "explanation": {
            "meaning": "Representative contested and was elected under the coalition alliance led by DMK.",
            "directness": "Official Statutory Election Certificate",
            "causality_note": "Political party membership does not establish unilateral executive authority over municipal utilities.",
        },
    },
    {
        "edge_id": "EDGE:REP:CONST:001",
        "source_node_id": "NODE:REP:VELACHERY_MLA",
        "target_node_id": "NODE:CONST:VELACHERY",
        "relationship_type": "represents",
        "evidence_reference": "TN Legislative Assembly Official Gazette Member Roster 16th Assembly",
        "source_document_id": "DOC-TNLA-ROSTER-2021",
        "source_document_url": "https://assembly.tn.gov.in/members",
        "source_document_hash": "5d41402abc4b2a76b9719d911017c592",
        "matching_method": "DETERMINISTIC_ID",
        "confidence_score": 1.0,
        "review_status": "VERIFIED",
        "provenance_status": "VALID",
        "valid_from": "2021-05-02",
        "valid_to": "2026-05-01",
        "explanation": {
            "meaning": "Official democratic representation of the constituency in the State Legislative Assembly.",
            "directness": "Constitutional Gazette Certification",
            "causality_note": "Representative stewardship does not imply personal liability for individual municipal infrastructure breakages.",
        },
    },
    {
        "edge_id": "EDGE:ISSUE:CONST:001",
        "source_node_id": "NODE:ISSUE:WATER_VELACHERY",
        "target_node_id": "NODE:CONST:VELACHERY",
        "relationship_type": "located_in",
        "evidence_reference": "Greater Chennai Corporation Ward 178 geographic boundary mapping under AC-026 Velachery",
        "source_document_id": "DOC-GCC-DELIMITATION-2022",
        "source_document_url": "https://chennaicorporation.gov.in/wards",
        "source_document_hash": "7b8b965ad4bca0e41ab51de7b31363a1",
        "matching_method": "DETERMINISTIC_ID",
        "confidence_score": 0.99,
        "review_status": "VERIFIED",
        "provenance_status": "VALID",
        "valid_from": "2022-01-01",
        "valid_to": None,
        "explanation": {
            "meaning": "Civic complaints originated within the geographical boundaries of Velachery constituency.",
            "directness": "Municipal Delimitation Mapping",
            "causality_note": "Geographic association does NOT establish the representative's personal culpability for service failure.",
        },
    },
    {
        "edge_id": "EDGE:CLAIM:DOC:001",
        "source_node_id": "NODE:DOC:GOMS42_2023",
        "target_node_id": "NODE:CLAIM:DESAL_OUTPUT",
        "relationship_type": "provides_evidence_for",
        "evidence_reference": "GO Ms. No. 42 specifies plant commissioned design capacity of 150 MLD daily output",
        "source_document_id": "DOC-GO-MS-42-MAWS-2023",
        "source_document_url": "https://cms.tn.gov.in/sites/default/files/go/maws_e_42_2023.pdf",
        "source_document_hash": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
        "matching_method": "DIRECT_DOCUMENTARY",
        "confidence_score": 0.92,
        "review_status": "VERIFIED",
        "provenance_status": "VALID",
        "valid_from": "2023-04-12",
        "valid_to": None,
        "explanation": {
            "meaning": "Government Order documents the state's official commissioned design rating supporting the claim.",
            "directness": "Primary Statutory Sanction",
            "causality_note": "Documents official administrative capacity design; independent verification examines real-time dispatch.",
        },
    },
    {
        "edge_id": "EDGE:CAG:CLAIM:001",
        "source_node_id": "NODE:DOC:CAG_2023",
        "target_node_id": "NODE:CLAIM:DESAL_OUTPUT",
        "relationship_type": "contradicts",
        "evidence_reference": "CAG Report No. 4 of 2023 para 3.8 notes average actual dispatch over 9 months was 94.2 MLD due to membrane fouling",
        "source_document_id": "DOC-CAG-REPORT-2023",
        "source_document_url": "https://cag.gov.in/reports/tn/2023/report-4",
        "source_document_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "matching_method": "DIRECT_DOCUMENTARY",
        "confidence_score": 0.94,
        "review_status": "VERIFIED",
        "provenance_status": "VALID",
        "valid_from": "2023-12-18",
        "valid_to": None,
        "explanation": {
            "meaning": "Statutory constitutional audit physically measured actual continuous dispatch, contradicting claims of full 150 MLD operation.",
            "directness": "Statutory Constitutional Audit Finding",
            "causality_note": "Statutory audit findings take epistemic precedence over non-statutory departmental press remarks.",
        },
    },
    {
        "edge_id": "EDGE:DISPUTED:CONTRACTOR:001",
        "source_node_id": "NODE:CLAIM:DESAL_OUTPUT",
        "target_node_id": "NODE:SCHEME:DESAL_NEMMELI",
        "relationship_type": "provides_evidence_for",
        "evidence_reference": "Preliminary EPC consortium press note asserting 100% capacity utilization",
        "source_document_id": "DOC-EPC-NOTE-2024",
        "source_document_url": "https://contractor-epc.example.com/press",
        "source_document_hash": None,
        "matching_method": "AUTOMATED_CANDIDATE",
        "confidence_score": 0.52,
        "review_status": "PENDING_REVIEW",
        "provenance_status": "DISPUTED",
        "valid_from": "2024-01-15",
        "valid_to": None,
        "explanation": {
            "meaning": "Contractor self-assessment report disputed by independent CAG field inspection.",
            "directness": "Secondary / Self-Reported Press Release",
            "causality_note": "Marked DISPUTED due to incomplete hash provenance and contradicting statutory findings.",
        },
    },
]


# -----------------------------------------------------------------------------
# 3. UNREVIEWED CANDIDATE RELATIONSHIP PROPOSALS (PHASE 9.4 ENGINE)
# -----------------------------------------------------------------------------
FIXTURE_CANDIDATE_PROPOSALS: List[Dict[str, Any]] = [
    {
        "proposal_id": "PROP-CANDIDATE-001",
        "source_node_id": "NODE:SCHEME:DESAL_NEMMELI",
        "target_node_id": "NODE:ISSUE:WATER_VELACHERY",
        "relationship_type": "responds_to",
        "evidence_supporting_candidate": "Scheme distribution line package 3 coincides with Velachery Ward 178 grievance radius",
        "matching_method": "AUTOMATED_CANDIDATE",
        "confidence_score": 0.76,
        "source_document_id": "DOC-CMWSSB-SURVEY-2024",
        "review_status": "PENDING_REVIEW",
        "warning": "Candidate link inferred by geospatial proximity. Not confirmed until human audit review.",
    },
    {
        "proposal_id": "PROP-CANDIDATE-002",
        "source_node_id": "NODE:PARTY:DMK",
        "target_node_id": "NODE:BUDGET:DEMAND_34_CAPITAL",
        "relationship_type": "funds",
        "evidence_supporting_candidate": "Ruling party legislative majority voted budget appropriation",
        "matching_method": "AUTOMATED_CANDIDATE",
        "confidence_score": 0.45,
        "source_document_id": "DOC-TNLA-VOTE-2023",
        "review_status": "PENDING_REVIEW",
        "warning": "State treasury funds originate from public taxpayer revenue, not political party treasury. High risk of false attribution.",
    },
]


# -----------------------------------------------------------------------------
# 4. PERSISTENT CONFLICTS & DIALECTICAL TENSIONS (PHASE 9.6 ENGINE)
# -----------------------------------------------------------------------------
FIXTURE_CONFLICTS: List[Dict[str, Any]] = [
    {
        "conflict_id": "CONF-DESAL-OUTPUT-01",
        "conflict_type": "CONTRADICTORY_CLAIM_EVIDENCE",
        "severity": "HIGH",
        "primary_node_id": "NODE:CLAIM:DESAL_OUTPUT",
        "secondary_node_id": "NODE:DOC:CAG_2023",
        "description": "CAG Audit Report No. 4 of 2023 (Para 3.8) documents 94.2 MLD average dispatch, contradicting ministerial statement claiming 150 MLD full capacity.",
        "epistemic_weight_comparison": {
            "statutory_weight": 0.95,
            "statutory_source": "Comptroller and Auditor General of India (Statutory Constitutional Authority)",
            "media_weight": 0.65,
            "media_source": "Ministerial Press Conference Announcement",
            "rule": "Newer ministerial statement does not automatically invalidate earlier statutory audit findings without documented commissioning audit.",
        },
        "resolution_status": "EXPLAINED_DIALECTIC",
        "detected_at": "2026-10-12T10:15:00",
    },
    {
        "conflict_id": "CONF-DISPUTED-EDGE-02",
        "conflict_type": "INCOMPLETE_PROVENANCE",
        "severity": "MEDIUM",
        "primary_node_id": "NODE:CLAIM:DESAL_OUTPUT",
        "secondary_node_id": "NODE:SCHEME:DESAL_NEMMELI",
        "description": "Consortium press note edge lacks cryptographic SHA-256 hash and independent verification audit.",
        "epistemic_weight_comparison": {
            "status": "Provenance verification incomplete; marked as DISPUTED.",
        },
        "resolution_status": "UNRESOLVED",
        "detected_at": "2026-10-12T10:20:00",
    },
]


# -----------------------------------------------------------------------------
# 5. INVESTIGATION PATH TEMPLATES (PHASE 9.5 ENGINE)
# -----------------------------------------------------------------------------
FIXTURE_INVESTIGATION_PATHS: Dict[str, Dict[str, Any]] = {
    "promise_delivery": {
        "title": "Path 1: Political Promise → Scheme → Budget → Resolution",
        "description": "Traces an election manifesto pledge to implementing government schemes, capital budget appropriations, and documented field outcomes.",
        "sample_start_node": "NODE:PROM:DMK_DESAL",
        "nodes": [
            "NODE:PROM:DMK_DESAL",
            "NODE:SCHEME:DESAL_NEMMELI",
            "NODE:BUDGET:DEMAND_34_CAPITAL",
            "NODE:DOC:GOMS42_2023",
        ],
        "edges": [
            "EDGE:PROM:SCHEME:001",
            "EDGE:SCHEME:BUDGET:001",
            "EDGE:CLAIM:DOC:001",
        ],
        "completeness_score": 0.89,
        "is_direct": True,
        "caveat": "Financial allocation does not automatically establish full promise fulfillment without verified end-user service delivery evidence.",
    },
    "claim_verification": {
        "title": "Path 2: Public Claim → Supporting & Contradicting Evidence → Verification",
        "description": "Exposes dual-sided evidentiary lineage comparing statutory findings against ministerial statements.",
        "sample_start_node": "NODE:CLAIM:DESAL_OUTPUT",
        "nodes": [
            "NODE:CLAIM:DESAL_OUTPUT",
            "NODE:DOC:GOMS42_2023",
            "NODE:DOC:CAG_2023",
        ],
        "edges": [
            "EDGE:CLAIM:DOC:001",
            "EDGE:CAG:CLAIM:001",
        ],
        "completeness_score": 0.94,
        "is_direct": True,
        "caveat": "Dialectical tension exists between commissioned design capacity (150 MLD) and CAG actual monitored output (94.2 MLD).",
    },
    "civic_accountability": {
        "title": "Path 3: Civic Issue → Official Record → Department Response → Resolution",
        "description": "Traces localized citizen grievances to administrative department responsibilities and public works verification.",
        "sample_start_node": "NODE:ISSUE:WATER_VELACHERY",
        "nodes": [
            "NODE:ISSUE:WATER_VELACHERY",
            "NODE:CONST:VELACHERY",
            "NODE:REP:VELACHERY_MLA",
        ],
        "edges": [
            "EDGE:ISSUE:CONST:001",
            "EDGE:REP:CONST:001",
        ],
        "completeness_score": 0.75,
        "is_direct": False,
        "caveat": "Geographical proximity indicates municipal service territory; it does not indicate personal culpability of the legislator.",
    },
    "representative_stewardship": {
        "title": "Path 4: Representative → Constituency → Documented Works",
        "description": "Examines representative legislative activity and constituency works without inferring causation from association.",
        "sample_start_node": "NODE:REP:VELACHERY_MLA",
        "nodes": [
            "NODE:REP:VELACHERY_MLA",
            "NODE:CONST:VELACHERY",
            "NODE:PARTY:DMK",
        ],
        "edges": [
            "EDGE:REP:CONST:001",
            "EDGE:PARTY:REP:001",
        ],
        "completeness_score": 0.92,
        "is_direct": True,
        "caveat": "Party coalition endorsement documents political alignment, not administrative jurisdiction over civic utilities.",
    },
    "political_finance": {
        "title": "Path 5: Political Funding Disclosure → Disclosed Entity → Source Document",
        "description": "Audits corporate and individual financial contributions backed by official ECI statutory reports.",
        "sample_start_node": "NODE:PARTY:DMK",
        "nodes": [
            "NODE:PARTY:DMK",
            "NODE:REP:VELACHERY_MLA",
        ],
        "edges": [
            "EDGE:PARTY:REP:001",
        ],
        "completeness_score": 0.95,
        "is_direct": True,
        "caveat": "Disclosed campaign funding does not prove quid-pro-quo without independent judicial or statutory finding.",
    },
}
