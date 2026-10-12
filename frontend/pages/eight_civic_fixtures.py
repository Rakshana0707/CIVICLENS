"""
CIVICLENS TN — Phase 8.9: Civic Issue Intelligence Test Fixtures.
================================================================

Comprehensive, realistic, clearly-labelled test fixtures for the
Civic Issue Intelligence dashboard.

METHODOLOGICAL & ETHICAL PRINCIPLES:
1. Clearly Labelled: Every record prefix is marked with [FIXTURE] to prevent confusion
   with empirical civic records.
2. DPDPA 2023 Compliance: Zero personal citizen data (names, phone numbers, exact residential
   door/flat numbers) is present in descriptions or summaries.
3. Anti-Causality & Non-Defamation: No political blame rankings; issues reflect municipal
   maintenance and civic reporting demand, not personal fault of elected representatives.
4. Epistemic Status Distinction: Clear separation between departmental administrative claims
   ('marked_resolved') and empirical proof ('independently_verified_resolved').
"""

from typing import Dict, List, Any

FIXTURE_CATEGORIES: List[Dict[str, Any]] = [
    {
        "id": "pot_holes_and_road_damage",
        "name": "Potholes & Road Damage",
        "tamil_name": "சாலை பள்ளங்கள் மற்றும் சேதங்கள்",
        "sla_standard_days": 7,
        "total_issues": 1420,
        "resolved_issues": 980,
        "resolution_rate": 69.0,
        "description": "Potholes, surface erosion, damaged bituminous layers, and road caving on public thoroughfares."
    },
    {
        "id": "drinking_water_contamination_or_shortage",
        "name": "Drinking Water Contamination or Shortage",
        "tamil_name": "குடிநீர் மாசுபாடு அல்லது தட்டுப்பாடு",
        "sla_standard_days": 3,
        "total_issues": 1180,
        "resolved_issues": 750,
        "resolution_rate": 63.5,
        "description": "Turbid or contaminated pipeline supply, low pressure, water head disruptions, and tanker distribution delays."
    },
    {
        "id": "sanitation_and_solid_waste",
        "name": "Sanitation & Solid Waste Management",
        "tamil_name": "சுகாதாரம் மற்றும் குப்பை மேலாண்மை",
        "sla_standard_days": 2,
        "total_issues": 2100,
        "resolved_issues": 1650,
        "resolution_rate": 78.6,
        "description": "Overflowing dumper bins, missed door-to-door garbage collection, open dumping, and littering."
    },
    {
        "id": "street_lighting_outage",
        "name": "Street Lighting Outage",
        "tamil_name": "தெரு விளக்கு பழுது",
        "sla_standard_days": 3,
        "total_issues": 890,
        "resolved_issues": 720,
        "resolution_rate": 80.9,
        "description": "Non-functional LED/sodium street lights, damaged poles, faulty automated timers, and phase line tripping."
    },
    {
        "id": "storm_water_drainage_and_flooding",
        "name": "Stormwater Drainage & Flooding",
        "tamil_name": "மழைநீர் வடிகால் மற்றும் வெள்ளப் பெருக்கு",
        "sla_standard_days": 10,
        "total_issues": 940,
        "resolved_issues": 530,
        "resolution_rate": 56.4,
        "description": "Choked culverts, missing drain slabs, monsoon waterlogging, and silt accumulation in primary macro drains."
    },
    {
        "id": "encroachment_and_building_violations",
        "name": "Encroachment & Building Violations",
        "tamil_name": "ஆக்கிரமிப்பு மற்றும் விதிமீறல்",
        "sla_standard_days": 30,
        "total_issues": 430,
        "resolved_issues": 180,
        "resolution_rate": 41.9,
        "description": "Pedestrian footway encroachments, unauthorized commercial projections, waterbody bank occupations."
    },
    {
        "id": "public_health_and_mosquito_breeding",
        "name": "Public Health & Vector Control",
        "tamil_name": "பொது சுகாதாரம் மற்றும் கொசு உற்பத்தி",
        "sla_standard_days": 5,
        "total_issues": 760,
        "resolved_issues": 510,
        "resolution_rate": 67.1,
        "description": "Stagnant pools prone to dengue larvae, vector fogging requests, and chlorination drives."
    },
    {
        "id": "parks_and_playgrounds_maintenance",
        "name": "Parks & Playgrounds Maintenance",
        "tamil_name": "பூங்காக்கள் மற்றும் விளையாட்டு மைதானங்கள்",
        "sla_standard_days": 14,
        "total_issues": 310,
        "resolved_issues": 190,
        "resolution_rate": 61.3,
        "description": "Broken play equipment, untrimmed vegetation, dry fountains, and damaged security railings in municipal parks."
    },
    {
        "id": "traffic_signals_and_signage",
        "name": "Traffic Signals & Road Signage",
        "tamil_name": "போக்குவரத்து சமிக்ஞைகள் மற்றும் பலகைகள்",
        "sla_standard_days": 4,
        "total_issues": 420,
        "resolved_issues": 340,
        "resolution_rate": 81.0,
        "description": "Blinking junction signals, obscured directional signages, missing pedestrian pelican crossings."
    },
    {
        "id": "stray_animals_control",
        "name": "Stray Animals & Animal Birth Control",
        "tamil_name": "தெரு விலங்குகள் கட்டுப்பாடு",
        "sla_standard_days": 7,
        "total_issues": 580,
        "resolved_issues": 390,
        "resolution_rate": 67.2,
        "description": "Pack dog bite hazards, cattle wandering on arterial bypasses, rabies immunization requests."
    },
    {
        "id": "public_toilets_maintenance",
        "name": "Public Toilets & Community Sanitation",
        "tamil_name": "பொதுக் கழிப்பறை பராமரிப்பு",
        "sla_standard_days": 3,
        "total_issues": 390,
        "resolved_issues": 240,
        "resolution_rate": 61.5,
        "description": "Waterless public toilets, damaged cisterns, sewage backflow, and missing lighting in community complexes."
    },
    {
        "id": "air_and_noise_pollution",
        "name": "Air & Noise Environmental Quality",
        "tamil_name": "காற்று மற்றும் ஒலி மாசுபாடு",
        "sla_standard_days": 15,
        "total_issues": 250,
        "resolved_issues": 110,
        "resolution_rate": 44.0,
        "description": "Industrial dust dispersion, commercial diesel generator noise, and open burning of biomass."
    }
]

FIXTURE_AREAS: List[Dict[str, Any]] = [
    {
        "id": "AREA-GCC-CHN",
        "name": "Greater Chennai Corporation",
        "district": "Chennai",
        "tier": "MUNICIPAL_CORPORATION",
        "census_population": 7139882,
        "recorded_grievances": 4120,
        "normalized_per_100k": 57.7,
        "portal_coverage_tier": "HIGH_DIGITAL_PENETRATION",
        "data_coverage_note": "GCC Namma Chennai App + 1913 Helpline data integrated. High digital literacy yields higher reported volume."
    },
    {
        "id": "AREA-CCMC-CBE",
        "name": "Coimbatore City Municipal Corporation",
        "district": "Coimbatore",
        "tier": "MUNICIPAL_CORPORATION",
        "census_population": 1601438,
        "recorded_grievances": 1450,
        "normalized_per_100k": 90.5,
        "portal_coverage_tier": "HIGH_DIGITAL_PENETRATION",
        "data_coverage_note": "Coimbatore Corporation WhatsApp Helpline + CCMC portal data."
    },
    {
        "id": "AREA-MMC-MDU",
        "name": "Madurai Municipal Corporation",
        "district": "Madurai",
        "tier": "MUNICIPAL_CORPORATION",
        "census_population": 1561129,
        "recorded_grievances": 1180,
        "normalized_per_100k": 75.6,
        "portal_coverage_tier": "MODERATE_PENETRATION",
        "data_coverage_note": "Madurai Integrated Grievance Cell records. Ward-level digitalization partially completed in 2024."
    },
    {
        "id": "AREA-TCMC-TRY",
        "name": "Tiruchirappalli City Corporation",
        "district": "Tiruchirappalli",
        "tier": "MUNICIPAL_CORPORATION",
        "census_population": 916857,
        "recorded_grievances": 720,
        "normalized_per_100k": 78.5,
        "portal_coverage_tier": "MODERATE_PENETRATION",
        "data_coverage_note": "Trichy Smart City Grievance Redressal system data."
    },
    {
        "id": "AREA-SMC-SLM",
        "name": "Salem City Municipal Corporation",
        "district": "Salem",
        "tier": "MUNICIPAL_CORPORATION",
        "census_population": 829267,
        "recorded_grievances": 580,
        "normalized_per_100k": 69.9,
        "portal_coverage_tier": "MODERATE_PENETRATION",
        "data_coverage_note": "Salem Corporation Grievance Records."
    },
    {
        "id": "AREA-TIR-TNV",
        "name": "Tirunelveli City Municipal Corporation",
        "district": "Tirunelveli",
        "tier": "MUNICIPAL_CORPORATION",
        "census_population": 473637,
        "recorded_grievances": 340,
        "normalized_per_100k": 71.8,
        "portal_coverage_tier": "EMERGING_PENETRATION",
        "data_coverage_note": "Tirunelveli Municipal Corporation records; localized paper petitions transitioning to online registry."
    }
]

FIXTURE_DEPARTMENTS: List[Dict[str, Any]] = [
    {
        "id": "DEPT-GCC-ENG",
        "name": "GCC Works & Engineering Department",
        "jurisdiction": "Greater Chennai Corporation",
        "total_dockets": 1820,
        "open_dockets": 420,
        "closed_dockets": 1400,
        "sla_compliance_rate": 76.9,
        "mean_resolution_days": 8.4,
        "escalation_count": 84,
        "mandate": "Construction and repair of municipal interior roads, bridges, culverts, and civic structures."
    },
    {
        "id": "DEPT-CMWSSB",
        "name": "Chennai Metropolitan Water Supply and Sewerage Board (CMWSSB)",
        "jurisdiction": "Chennai Metropolitan Area",
        "total_dockets": 1430,
        "open_dockets": 390,
        "closed_dockets": 1040,
        "sla_compliance_rate": 72.7,
        "mean_resolution_days": 5.2,
        "escalation_count": 92,
        "mandate": "Potable water transmission, underground sewerage network, and sewage treatment plants."
    },
    {
        "id": "DEPT-GCC-SWM",
        "name": "GCC Solid Waste Management Department",
        "jurisdiction": "Greater Chennai Corporation",
        "total_dockets": 2150,
        "open_dockets": 280,
        "closed_dockets": 1870,
        "sla_compliance_rate": 86.9,
        "mean_resolution_days": 2.1,
        "escalation_count": 45,
        "mandate": "Door-to-door waste collection, waste segregation, transfer stations, and scientific landfill operations."
    },
    {
        "id": "DEPT-TN-HIGHWAYS",
        "name": "State Highways Department (Chennai Metro Division)",
        "jurisdiction": "Tamil Nadu State",
        "total_dockets": 620,
        "open_dockets": 210,
        "closed_dockets": 410,
        "sla_compliance_rate": 66.1,
        "mean_resolution_days": 16.3,
        "escalation_count": 68,
        "mandate": "Maintenance of State Highways, Major District Roads, and arterial corridor carriageways."
    },
    {
        "id": "DEPT-TANGEDCO",
        "name": "Tamil Nadu Generation and Distribution Corporation (TANGEDCO)",
        "jurisdiction": "Tamil Nadu State",
        "total_dockets": 1280,
        "open_dockets": 190,
        "closed_dockets": 1090,
        "sla_compliance_rate": 85.1,
        "mean_resolution_days": 3.4,
        "escalation_count": 38,
        "mandate": "Substation maintenance, power distribution lines, street lighting feeder control, and transformer upkeep."
    },
    {
        "id": "DEPT-TWAD",
        "name": "Tamil Nadu Water Supply and Drainage Board (TWAD Board)",
        "jurisdiction": "Non-Chennai Urban & Rural Local Bodies",
        "total_dockets": 840,
        "open_dockets": 260,
        "closed_dockets": 580,
        "sla_compliance_rate": 69.0,
        "mean_resolution_days": 9.8,
        "escalation_count": 52,
        "mandate": "Combined Water Supply Schemes (CWSS) across municipal corporations, municipalities, and panchayats."
    }
]

FIXTURE_ISSUES: List[Dict[str, Any]] = [
    {
        "id": "CIVIC-2026-CHN-001",
        "title": "[FIXTURE] Severe Carriageway Potholes on Anna Salai Corridor (Near Nandanam)",
        "description": "Substantial cratering and surface bitumen disintegration over a 150-meter carriageway stretch causing vehicular slowdowns and two-wheeler skid hazards.",
        "category": "pot_holes_and_road_damage",
        "category_name": "Potholes & Road Damage",
        "severity": "CRITICAL",
        "status": "independently_verified_resolved",
        "verification_status": "VERIFIED_RESOLVED",
        "district": "Chennai",
        "local_body": "Greater Chennai Corporation",
        "ward": "Ward 142",
        "geographic_precision": "WARD_LEVEL",
        "department": "State Highways Department (Chennai Metro Division)",
        "department_id": "DEPT-TN-HIGHWAYS",
        "candidate_departments": ["State Highways Department (Chennai Metro Division)", "GCC Works & Engineering Department"],
        "department_uncertainty": "RESOLVED_TO_HIGHWAYS",
        "submission_date": "2026-08-10",
        "acknowledgement_date": "2026-08-11",
        "resolution_date": "2026-08-16",
        "sla_standard_days": 7,
        "resolution_days": 6,
        "sla_breached": False,
        "grievance_count": 18,
        "is_recurring": False,
        "data_limitations": [
            "Scrubbed of citizen names and vehicle registration identifiers per DPDPA 2023.",
            "Jurisdiction between State Highways and GCC resolved through statutory gazette corridor listing."
        ],
        "responses": [
            {
                "date": "2026-08-11",
                "officer_designation": "Assistant Divisional Engineer, Highways Metro",
                "response_type": "OFFICIAL_ACKNOWLEDGEMENT",
                "summary": "Docket acknowledged. Site inspection scheduled for night shift milling and hot-mix patching.",
                "source_ref": "ATR-HW-CHN-2026-0811"
            },
            {
                "date": "2026-08-15",
                "officer_designation": "Divisional Engineer, Chennai Metro Division",
                "response_type": "ACTION_TAKEN_REPORT",
                "summary": "Dense Bituminous Macadam (DBM) patching executed across 180 sqm with roller compaction.",
                "source_ref": "ATR-HW-CHN-2026-0815"
            }
        ],
        "evidence": [
            {
                "evidence_type": "GEOTAGGED_INSPECTION_PHOTO",
                "verification_status": "VERIFIED_RESOLVED",
                "inspection_date": "2026-08-16",
                "inspector": "Independent Municipal Quality Auditor (Civic Works Cell)",
                "description": "Geotagged photographic verification confirms seamless asphalt surface without depressions; riding quality restored.",
                "document_url": "https://civiclens.tn.gov.in/docs/evidence/CH-2026-001-PHOTO.pdf"
            },
            {
                "evidence_type": "COMPLETION_CERTIFICATE",
                "verification_status": "VERIFIED_RESOLVED",
                "inspection_date": "2026-08-16",
                "inspector": "Superintending Engineer, Highways",
                "description": "Measurement book entry verified and M-Book voucher signed for patch renewal.",
                "document_url": "https://civiclens.tn.gov.in/docs/evidence/CH-2026-001-MBOOK.pdf"
            }
        ],
        "public_works": [
            {
                "work_id": "PW-HW-2026-M41",
                "work_name": "Emergency Bituminous Patching of Corridor Roads - Zone 9 & 10",
                "sanctioned_amount_lakhs": 24.50,
                "contractor": "Tamil Nadu Road Infrastructure Development Corp Partner",
                "completion_status": "COMPLETED",
                "relationship_evidence": "Voucher MB-114 explicitly ties work to Anna Salai chainage 4/200."
            }
        ],
        "cross_phase_links": [
            {
                "target_phase": "PHASE_1_2_BUDGET_SCHEME",
                "entity_type": "BUDGET_SCHEME",
                "entity_id": "SCH-TN-HW-URBAN-2026",
                "entity_name": "Comprehensive Road Infrastructure Development Programme (CRIDP)",
                "matching_method": "SANCTION_HEAD_CODE_MATCH",
                "confidence": 0.94,
                "provenance": "G.O. Ms No. 42 Highways & Minor Ports Department 2026"
            },
            {
                "target_phase": "PHASE_6_REPRESENTATIVE",
                "entity_type": "CONSTITUENCY",
                "entity_id": "AC-024-T-NAGAR",
                "entity_name": "T. Nagar Assembly Constituency",
                "matching_method": "GEOGRAPHIC_BOUNDARY_INTERSECT",
                "confidence": 0.99,
                "provenance": "Delimitation Commission Gazette Notification 2008. (Note: Non-causal linkage; no personal liability inferred)."
            }
        ],
        "source_documents": [
            {
                "doc_id": "DOC-TN-HW-2026-M4",
                "title": "State Highways Metro Maintenance Log - August 2026",
                "doc_type": "GOVERNMENT_ACTION_TAKEN_REPORT",
                "checksum": "sha256:88a1b41c9b2e7d3f110a2f7c001928374a56b78e9012345678abcdef01234567",
                "retrieval_timestamp": "2026-08-20T10:00:00Z"
            }
        ]
    },
    {
        "id": "CIVIC-2026-CHN-002",
        "title": "[FIXTURE] Discolored and Turbid Pipeline Supply in Triplicane",
        "description": "Residents in multiple streets reported yellow-tinted water with distinct sewage odor from metered distribution lines during morning supply hours.",
        "category": "drinking_water_contamination_or_shortage",
        "category_name": "Drinking Water Contamination or Shortage",
        "severity": "CRITICAL",
        "status": "marked_resolved",
        "verification_status": "PENDING_INSPECTION",
        "district": "Chennai",
        "local_body": "Greater Chennai Corporation",
        "ward": "Ward 116",
        "geographic_precision": "WARD_LEVEL",
        "department": "Chennai Metropolitan Water Supply and Sewerage Board (CMWSSB)",
        "department_id": "DEPT-CMWSSB",
        "candidate_departments": ["Chennai Metropolitan Water Supply and Sewerage Board (CMWSSB)"],
        "department_uncertainty": "UNAMBIGUOUS_SINGLE_DEPARTMENT",
        "submission_date": "2026-08-14",
        "acknowledgement_date": "2026-08-14",
        "resolution_date": "2026-08-17",
        "sla_standard_days": 3,
        "resolution_days": 3,
        "sla_breached": False,
        "grievance_count": 27,
        "is_recurring": True,
        "data_limitations": [
            "Marked resolved administratively by CMWSSB Area Office 8.",
            "Independent water quality test lab certification still pending receipt.",
            "Categorized as marked_resolved; cannot be reported as verified fixed."
        ],
        "responses": [
            {
                "date": "2026-08-15",
                "officer_designation": "Area Engineer - Area 8, CMWSSB",
                "response_type": "ACTION_TAKEN_REPORT",
                "summary": "Identified cross-contamination ingress near old masonry sewer junction. Pipeline isolation valve shut; bypass replacement done.",
                "source_ref": "CMWSSB-ATR-A8-2026-77"
            },
            {
                "date": "2026-08-17",
                "officer_designation": "Superintending Engineer, Central Distribution",
                "response_type": "ADMINISTRATIVE_CLOSURE",
                "summary": "Flushing executed with 500 ppm chlorine dose; line restored. Docket closed administratively.",
                "source_ref": "CMWSSB-CLOSURE-2026-891"
            }
        ],
        "evidence": [
            {
                "evidence_type": "DEPARTMENTAL_SELF_REPORT",
                "verification_status": "PENDING_INSPECTION",
                "inspection_date": "2026-08-17",
                "inspector": "CMWSSB Quality Inspector",
                "description": "Internal test strips show residual chlorine 0.5 ppm. Awaiting third-party King Institute public lab sample verification.",
                "document_url": "https://civiclens.tn.gov.in/docs/evidence/CMWSSB-A8-TEST-002.pdf"
            }
        ],
        "public_works": [],
        "cross_phase_links": [
            {
                "target_phase": "PHASE_3_POLITICAL_PROMISE",
                "entity_type": "MANIFESTO_PROMISE",
                "entity_id": "PRM-2021-DMK-WTR-04",
                "entity_name": "Zero-Contamination 24x7 Piped Water Grid for Chennai Core",
                "matching_method": "TOPIC_AREA_POLICY_ALIGNMENT",
                "confidence": 0.82,
                "provenance": "DMK Election Manifesto 2021 Item 114"
            }
        ],
        "source_documents": [
            {
                "doc_id": "DOC-CMWSSB-DUMP-AUG26",
                "title": "CMWSSB Public Portal Redressal Statistics Extract",
                "doc_type": "PUBLIC_DATASET_DUMP",
                "checksum": "sha256:77b1c34a2e5d6f112233445566778899aabbccddeeff00112233445566778899",
                "retrieval_timestamp": "2026-08-19T14:30:00Z"
            }
        ]
    },
    {
        "id": "CIVIC-2026-CBE-003",
        "title": "[FIXTURE] Overflowing Secondary Waste Dump on Avinashi Road Service Lane",
        "description": "Uncollected commercial solid waste overflowing onto adjacent pedestrian walkway; stray cattle foraging and foul odor permeating nearby commercial establishments.",
        "category": "sanitation_and_solid_waste",
        "category_name": "Sanitation & Solid Waste Management",
        "severity": "HIGH",
        "status": "action_reported",
        "verification_status": "DEFICIENCY_OBSERVED",
        "district": "Coimbatore",
        "local_body": "Coimbatore City Municipal Corporation",
        "ward": "Ward 38",
        "geographic_precision": "WARD_LEVEL",
        "department": "GCC Solid Waste Management Department", # CCMC SWM
        "department_id": "DEPT-CCMC-SWM",
        "candidate_departments": ["Coimbatore Corporation Public Health & Sanitation"],
        "department_uncertainty": "UNAMBIGUOUS_SINGLE_DEPARTMENT",
        "submission_date": "2026-08-18",
        "acknowledgement_date": "2026-08-18",
        "resolution_date": None,
        "sla_standard_days": 2,
        "resolution_days": None,
        "sla_breached": True,
        "grievance_count": 9,
        "is_recurring": True,
        "data_limitations": [
            "Department reported waste cleared on 2026-08-19.",
            "Follow-up field check on 2026-08-20 revealed residual waste and new open dumping within 24 hours.",
            "Status maintained as action_reported rather than resolved due to chronic recurrence."
        ],
        "responses": [
            {
                "date": "2026-08-19",
                "officer_designation": "Sanitary Inspector, East Zone Coimbatore",
                "response_type": "ACTION_TAKEN_REPORT",
                "summary": "Compactor truck deployed to clear 3.2 metric tonnes of accumulated waste.",
                "source_ref": "CCMC-SWM-EZ-2026-104"
            }
        ],
        "evidence": [
            {
                "evidence_type": "CITIZEN_PHOTO_WITH_GPS",
                "verification_status": "DEFICIENCY_OBSERVED",
                "inspection_date": "2026-08-20",
                "inspector": "Independent Civic Monitor (Clean Kovai Initiative)",
                "description": "Photographic inspection showed bin cleared but surrounding pavement unbleached and illegal dumping resumed.",
                "document_url": "https://civiclens.tn.gov.in/docs/evidence/CBE-2026-003-AUDIT.pdf"
            }
        ],
        "public_works": [],
        "cross_phase_links": [
            {
                "target_phase": "PHASE_4_TAMIL_NEWS",
                "entity_type": "NEWS_ARTICLE",
                "entity_id": "NEWS-DINAMALAR-2026-CBE-98",
                "entity_name": "Dinamalar: Commercial waste clutter on Avinashi Road irks traders",
                "matching_method": "TOPIC_AND_LOCATION_KEYWORD_MATCH",
                "confidence": 0.88,
                "provenance": "Dinamalar Coimbatore Edition Page 4, 2026-08-19"
            }
        ],
        "source_documents": [
            {
                "doc_id": "DOC-CCMC-GRIEVANCE-AUG26",
                "title": "CCMC Monthly Grievance Statistics Table",
                "doc_type": "MUNICIPAL_COUNCIL_RESOLUTION",
                "checksum": "sha256:11223344556677889900aabbccddeeff00112233445566778899aabbccddeeff",
                "retrieval_timestamp": "2026-08-21T09:15:00Z"
            }
        ]
    },
    {
        "id": "CIVIC-2026-MDU-004",
        "title": "[FIXTURE] Silt Blockade and Waterlogging in Sellur Channel Drain",
        "description": "Pre-monsoon blockage in the Sellur micro-drain channel resulting in sewage backflow into residential streets after brief showers.",
        "category": "storm_water_drainage_and_flooding",
        "category_name": "Stormwater Drainage & Flooding",
        "severity": "HIGH",
        "status": "under_review",
        "verification_status": "NOT_VERIFIED",
        "district": "Madurai",
        "local_body": "Madurai Municipal Corporation",
        "ward": "Ward 22",
        "geographic_precision": "WARD_LEVEL",
        "department": "Madurai Corporation Engineering Wing",
        "department_id": "DEPT-MMC-ENG",
        "candidate_departments": ["Madurai Corporation Engineering Wing", "Water Resources Department (Vaigai Basin)"],
        "department_uncertainty": "SHARED_JURISDICTION_WRD_MMC",
        "submission_date": "2026-08-20",
        "acknowledgement_date": "2026-08-21",
        "resolution_date": None,
        "sla_standard_days": 10,
        "resolution_days": None,
        "sla_breached": False,
        "grievance_count": 14,
        "is_recurring": True,
        "data_limitations": [
            "Shared boundary responsibility between WRD channels and Corporation feeder drains.",
            "Awaiting joint survey by WRD Assistant Engineer and Corporation Executive Engineer."
        ],
        "responses": [
            {
                "date": "2026-08-21",
                "officer_designation": "Assistant Engineer, North Zone Madurai",
                "response_type": "INTERDEPARTMENTAL_REFERRAL",
                "summary": "Channel originates from WRD irrigation surplus sluice; joint desilting estimate being prepared.",
                "source_ref": "MMC-NZ-REF-2026-302"
            }
        ],
        "evidence": [],
        "public_works": [
            {
                "work_id": "PW-MMC-2026-DRN-09",
                "work_name": "Sellur Inundation Mitigation Micro-Drain Desilting Scheme",
                "sanctioned_amount_lakhs": 42.00,
                "contractor": "Tender Under Technical Evaluation",
                "completion_status": "SANCTIONED",
                "relationship_evidence": "Budget line approved in Madurai Corporation Council Meeting Resolution 104/2026."
            }
        ],
        "cross_phase_links": [
            {
                "target_phase": "PHASE_7_CLAIM_VERIFICATION",
                "entity_type": "VERIFIED_CLAIM",
                "entity_id": "CLM-2026-MDU-FLDS-01",
                "entity_name": "Claim: Sellur desilting 100% completed prior to northeast monsoon",
                "matching_method": "ENTITY_RESOLUTION_OVER_MUNICIPAL_WORK",
                "confidence": 0.91,
                "provenance": "Phase 7 Fact-Check Archive (Verdict: Partially Supported / Ongoing Work)"
            }
        ],
        "source_documents": [
            {
                "doc_id": "DOC-MMC-COUNCIL-RES-104",
                "title": "Madurai Corporation Council Resolution 104/2026",
                "doc_type": "MUNICIPAL_COUNCIL_RESOLUTION",
                "checksum": "sha256:33445566778899001122aabbccddeeff00112233445566778899aabbccddeeff",
                "retrieval_timestamp": "2026-08-22T11:45:00Z"
            }
        ]
    },
    {
        "id": "CIVIC-2026-TRY-005",
        "title": "[FIXTURE] Non-Functional High-Mast and Street Lights along Gandhi Market",
        "description": "Complete dark stretch of 12 LED streetlights and main high-mast tower around Gandhi Market resulting in safety concerns during early morning vegetable arrivals.",
        "category": "street_lighting_outage",
        "category_name": "Street Lighting Outage",
        "severity": "MEDIUM",
        "status": "independently_verified_resolved",
        "verification_status": "VERIFIED_RESOLVED",
        "district": "Tiruchirappalli",
        "local_body": "Tiruchirappalli City Corporation",
        "ward": "Ward 12",
        "geographic_precision": "WARD_LEVEL",
        "department": "Tamil Nadu Generation and Distribution Corporation (TANGEDCO)",
        "department_id": "DEPT-TANGEDCO",
        "candidate_departments": ["Tiruchirappalli Corporation Electrical Wing", "TANGEDCO"],
        "department_uncertainty": "RESOLVED_TO_CORP_ELECTRICAL",
        "submission_date": "2026-08-05",
        "acknowledgement_date": "2026-08-05",
        "resolution_date": "2026-08-07",
        "sla_standard_days": 3,
        "resolution_days": 2,
        "sla_breached": False,
        "grievance_count": 6,
        "is_recurring": False,
        "data_limitations": [
            "Energy meter failure verified by TANGEDCO Junior Engineer; replaced within SLA."
        ],
        "responses": [
            {
                "date": "2026-08-06",
                "officer_designation": "Electrical Superintendent, Trichy Corporation",
                "response_type": "ACTION_TAKEN_REPORT",
                "summary": "Damaged 63A MCB and underground feeder cable puncture rectified; timer reset.",
                "source_ref": "TRY-ELEC-ATR-2026-55"
            }
        ],
        "evidence": [
            {
                "evidence_type": "GEOTAGGED_INSPECTION_PHOTO",
                "verification_status": "VERIFIED_RESOLVED",
                "inspection_date": "2026-08-07",
                "inspector": "Tiruchirappalli Smart City Command & Control Centre",
                "description": "Automated CCTV lux meter and night patrol log confirm 100% illumination restored.",
                "document_url": "https://civiclens.tn.gov.in/docs/evidence/TRY-2026-005-LUX.pdf"
            }
        ],
        "public_works": [],
        "cross_phase_links": [],
        "source_documents": [
            {
                "doc_id": "DOC-TRY-ICCC-LOG-AUG26",
                "title": "Trichy ICCC Night Surveillance Illumination Report",
                "doc_type": "GOVERNMENT_ACTION_TAKEN_REPORT",
                "checksum": "sha256:55667788990011223344aabbccddeeff00112233445566778899aabbccddeeff",
                "retrieval_timestamp": "2026-08-08T08:00:00Z"
            }
        ]
    },
    {
        "id": "CIVIC-2026-SLM-006",
        "title": "[FIXTURE] Commercial Footpath Encroachment and Unauthorized Stalls near New Bus Stand",
        "description": "Permanent metal sheds and fruit vendors encroaching 80% of pedestrian sidewalk, forcing commuters to walk on heavy-traffic carriageway.",
        "category": "encroachment_and_building_violations",
        "category_name": "Encroachment & Building Violations",
        "severity": "MEDIUM",
        "status": "disputed",
        "verification_status": "DEFICIENCY_OBSERVED",
        "district": "Salem",
        "local_body": "Salem City Municipal Corporation",
        "ward": "Ward 28",
        "geographic_precision": "WARD_LEVEL",
        "department": "Salem Corporation Town Planning Section",
        "department_id": "DEPT-SMC-TP",
        "candidate_departments": ["Salem Corporation Town Planning Section", "Salem City Police Traffic Division"],
        "department_uncertainty": "JOINT_ENFORCEMENT_REQUIRED",
        "submission_date": "2026-07-15",
        "acknowledgement_date": "2026-07-18",
        "resolution_date": None,
        "sla_standard_days": 30,
        "resolution_days": None,
        "sla_breached": True,
        "grievance_count": 11,
        "is_recurring": True,
        "data_limitations": [
            "Eviction drive challenged in District Munsif Court; interim status quo claimed by vendor association.",
            "Administrative status disputed between municipal enforcement and court stay."
        ],
        "responses": [
            {
                "date": "2026-07-28",
                "officer_designation": "Town Planning Officer, Salem Corporation",
                "response_type": "LEGAL_NOTICE_SERVED",
                "summary": "Notices issued under Section 220 of Tamil Nadu City Municipal Corporations Act.",
                "source_ref": "SMC-TP-NOTICE-2026-112"
            }
        ],
        "evidence": [
            {
                "evidence_type": "SITE_INSPECTION_RECORD",
                "verification_status": "DEFICIENCY_OBSERVED",
                "inspection_date": "2026-08-15",
                "inspector": "Lok Adalat Legal Aid Commissioner",
                "description": "Encroachments persist; footway impassable during peak evening hours.",
                "document_url": "https://civiclens.tn.gov.in/docs/evidence/SLM-2026-006-INSP.pdf"
            }
        ],
        "public_works": [],
        "cross_phase_links": [],
        "source_documents": [
            {
                "doc_id": "DOC-SLM-COURT-AFFIDAVIT-2026",
                "title": "Salem Corporation Counter-Affidavit WP 2026/88",
                "doc_type": "STATUTORY_NOTIFICATION",
                "checksum": "sha256:99001122334455667788aabbccddeeff00112233445566778899aabbccddeeff",
                "retrieval_timestamp": "2026-08-18T16:20:00Z"
            }
        ]
    },
    {
        "id": "CIVIC-2026-TNV-007",
        "title": "[FIXTURE] Vector Breeding Hazard in Abandoned Quarry Pond near Melapalayam",
        "description": "Stagnant rainwater accumulation in disused stone quarry generating intensive mosquito breeding; multiple fever cases reported in neighboring residential layout.",
        "category": "public_health_and_mosquito_breeding",
        "category_name": "Public Health & Vector Control",
        "severity": "HIGH",
        "status": "marked_resolved",
        "verification_status": "NOT_VERIFIED",
        "district": "Tirunelveli",
        "local_body": "Tirunelveli City Municipal Corporation",
        "ward": "Ward 45",
        "geographic_precision": "WARD_LEVEL",
        "department": "Tirunelveli Corporation Health Department",
        "department_id": "DEPT-TNV-HLTH",
        "candidate_departments": ["Tirunelveli Corporation Health Department", "Department of Geology & Mining"],
        "department_uncertainty": "RESOLVED_TO_HEALTH_DEPARTMENT",
        "submission_date": "2026-08-01",
        "acknowledgement_date": "2026-08-02",
        "resolution_date": "2026-08-06",
        "sla_standard_days": 5,
        "resolution_days": 5,
        "sla_breached": False,
        "grievance_count": 8,
        "is_recurring": False,
        "data_limitations": [
            "Marked resolved by municipal health wing upon Gambusia fish release and abatement fogging.",
            "Long-term dewatering or fencing of the abandoned quarry remains unfulfilled."
        ],
        "responses": [
            {
                "date": "2026-08-05",
                "officer_designation": "City Health Officer, Tirunelveli Corporation",
                "response_type": "ACTION_TAKEN_REPORT",
                "summary": "Introduced biological vector control agents (Gambusia affinis larvae-eating fish); thermal fogging completed.",
                "source_ref": "TNV-CHO-ATR-2026-44"
            }
        ],
        "evidence": [
            {
                "evidence_type": "DEPARTMENTAL_SELF_REPORT",
                "verification_status": "NOT_VERIFIED",
                "inspection_date": "2026-08-06",
                "inspector": "Tirunelveli Health Inspector Ward 45",
                "description": "Self-certified action taken report; independent public health audit not conducted.",
                "document_url": "https://civiclens.tn.gov.in/docs/evidence/TNV-2026-007-ATR.pdf"
            }
        ],
        "public_works": [],
        "cross_phase_links": [],
        "source_documents": [
            {
                "doc_id": "DOC-TNV-HLTH-REP-2026",
                "title": "Tirunelveli Corporation Vector Control Weekly Report",
                "doc_type": "GOVERNMENT_ACTION_TAKEN_REPORT",
                "checksum": "sha256:aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899",
                "retrieval_timestamp": "2026-08-10T12:00:00Z"
            }
        ]
    },
    {
        "id": "CIVIC-2026-CHN-008",
        "title": "[FIXTURE] Recurring Stray Cattle Hazards along Velachery Main Road Arterial Section",
        "description": "Uncontrolled cattle wandering and resting on medians causing recurrent accidents, brake-locks, and severe traffic congestion during peak hours.",
        "category": "stray_animals_control",
        "category_name": "Stray Animals & Animal Birth Control",
        "severity": "MEDIUM",
        "status": "reopened",
        "verification_status": "DEFICIENCY_OBSERVED",
        "district": "Chennai",
        "local_body": "Greater Chennai Corporation",
        "ward": "Ward 177",
        "geographic_precision": "WARD_LEVEL",
        "department": "GCC Veterinary and Public Health Department",
        "department_id": "DEPT-GCC-VET",
        "candidate_departments": ["GCC Veterinary and Public Health Department"],
        "department_uncertainty": "UNAMBIGUOUS_SINGLE_DEPARTMENT",
        "submission_date": "2026-07-20",
        "acknowledgement_date": "2026-07-21",
        "resolution_date": None,
        "sla_standard_days": 7,
        "resolution_days": None,
        "sla_breached": True,
        "grievance_count": 22,
        "is_recurring": True,
        "data_limitations": [
            "Cattle impounding drives conducted periodically, but owners reclaim animals paying standard fines and release them back.",
            "Reopened by citizens following fresh accident on 2026-08-12."
        ],
        "responses": [
            {
                "date": "2026-07-24",
                "officer_designation": "Veterinary Assistant Surgeon, GCC South",
                "response_type": "ACTION_TAKEN_REPORT",
                "summary": "14 cattle impounded and moved to Perambur Cattle Depot; compound fine of Rs. 28,000 collected.",
                "source_ref": "GCC-VET-ATR-2026-88"
            },
            {
                "date": "2026-08-13",
                "officer_designation": "Grievance Redressal Officer, GCC 1913",
                "response_type": "REOPENING_ACKNOWLEDGED",
                "summary": "Grievance reopened on complaint of recurring cattle release by repeat offenders.",
                "source_ref": "GCC-REOPEN-1913-2026-901"
            }
        ],
        "evidence": [
            {
                "evidence_type": "CITIZEN_PHOTO_WITH_GPS",
                "verification_status": "DEFICIENCY_OBSERVED",
                "inspection_date": "2026-08-14",
                "inspector": "Velachery Residents Welfare Association",
                "description": "Photographic proof of 8 cattle tethered to central road divider.",
                "document_url": "https://civiclens.tn.gov.in/docs/evidence/CHN-2026-008-CATTLE.pdf"
            }
        ],
        "public_works": [],
        "cross_phase_links": [
            {
                "target_phase": "PHASE_6_REPRESENTATIVE",
                "entity_type": "CONSTITUENCY",
                "entity_id": "AC-026-VELACHERY",
                "entity_name": "Velachery Assembly Constituency",
                "matching_method": "GEOGRAPHIC_BOUNDARY_INTERSECT",
                "confidence": 0.99,
                "provenance": "Delimitation Commission Gazette. (Constituency context only; no personal fault of representative)."
            }
        ],
        "source_documents": [
            {
                "doc_id": "DOC-GCC-COUNCIL-VET-2026",
                "title": "GCC Council Resolution on Revision of Cattle Impound Fines",
                "doc_type": "MUNICIPAL_COUNCIL_RESOLUTION",
                "checksum": "sha256:00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff",
                "retrieval_timestamp": "2026-08-15T15:00:00Z"
            }
        ]
    }
]

FIXTURE_CLUSTERS: List[Dict[str, Any]] = [
    {
        "cluster_id": "CLUSTER-CHN-SWM-01",
        "area_name": "Greater Chennai Corporation (Royapuram Zone)",
        "district": "Chennai",
        "category_id": "sanitation_and_solid_waste",
        "category_name": "Sanitation & Solid Waste Management",
        "total_grievances": 84,
        "active_dockets": 19,
        "repeat_locations_count": 6,
        "chronic_recurrence_rate": 42.8,
        "first_reported_date": "2026-01-15",
        "latest_reported_date": "2026-08-20",
        "root_cause_summary": "High commercial seafood market density exceeding standard secondary compactor bin capacity.",
        "recommended_action": "Dedicated bi-hourly night compactor clearance and institutional vendor segregation mandates."
    },
    {
        "cluster_id": "CLUSTER-CBE-ROAD-02",
        "area_name": "Coimbatore City Municipal Corporation (Singanallur)",
        "district": "Coimbatore",
        "category_id": "pot_holes_and_road_damage",
        "category_name": "Potholes & Road Damage",
        "total_grievances": 62,
        "active_dockets": 24,
        "repeat_locations_count": 8,
        "chronic_recurrence_rate": 38.7,
        "first_reported_date": "2026-02-10",
        "latest_reported_date": "2026-08-18",
        "root_cause_summary": "Uncoordinated road cuts for underground gas pipeline laying followed by substandard trench restoration.",
        "recommended_action": "Strict interdepartmental right-of-way reinstatement escrow penalty on utility service providers."
    },
    {
        "cluster_id": "CLUSTER-MDU-DRAIN-03",
        "area_name": "Madurai Municipal Corporation (Sellur & Goripalayam)",
        "district": "Madurai",
        "category_id": "storm_water_drainage_and_flooding",
        "category_name": "Stormwater Drainage & Flooding",
        "total_grievances": 45,
        "active_dockets": 16,
        "repeat_locations_count": 5,
        "chronic_recurrence_rate": 53.3,
        "first_reported_date": "2026-03-01",
        "latest_reported_date": "2026-08-21",
        "root_cause_summary": "Silt accumulation at confluence of WRD supply canal with Corporation box culvert.",
        "recommended_action": "Joint mechanized silt trap installation by WRD and Madurai Corporation."
    }
]

FIXTURE_TRENDS: Dict[str, Any] = {
    "reporting_period": "2026-01 to 2026-08",
    "total_records": 10890,
    "known_status_percentage": 94.2,
    "documented_response_rate": 88.5,
    "resolution_evidence_coverage": 41.3,
    "time_series": [
        {"month": "2026-01", "total_issues": 1120, "marked_resolved": 820, "verified_resolved": 340, "reopened": 42, "avg_resolution_days": 6.8},
        {"month": "2026-02", "total_issues": 1240, "marked_resolved": 910, "verified_resolved": 390, "reopened": 49, "avg_resolution_days": 6.5},
        {"month": "2026-03", "total_issues": 1380, "marked_resolved": 1020, "verified_resolved": 410, "reopened": 54, "avg_resolution_days": 7.1},
        {"month": "2026-04", "total_issues": 1490, "marked_resolved": 1080, "verified_resolved": 440, "reopened": 61, "avg_resolution_days": 7.4},
        {"month": "2026-05", "total_issues": 1310, "marked_resolved": 990, "verified_resolved": 420, "reopened": 48, "avg_resolution_days": 6.9},
        {"month": "2026-06", "total_issues": 1420, "marked_resolved": 1050, "verified_resolved": 460, "reopened": 58, "avg_resolution_days": 7.2},
        {"month": "2026-07", "total_issues": 1580, "marked_resolved": 1140, "verified_resolved": 480, "reopened": 72, "avg_resolution_days": 7.8},
        {"month": "2026-08", "total_issues": 1350, "marked_resolved": 960, "verified_resolved": 380, "reopened": 51, "avg_resolution_days": 6.9}
    ],
    "guarded_anomalies": [
        {
            "category": "storm_water_drainage_and_flooding",
            "metric": "MONTHLY_SPIKE",
            "sample_size": 284,
            "sample_size_valid": True, # N >= 30
            "baseline_mean": 94.2,
            "observed_value": 242.0,
            "z_score": 3.42,
            "interpretation": "Indicator requiring administrative verification: unseasonal monsoon pre-rains triggered surge in waterlogging reports across low-lying wards. Does not constitute proof of administrative failure."
        },
        {
            "category": "drinking_water_contamination_or_shortage",
            "metric": "REOPENED_DOCKETS_CLUSTER",
            "sample_size": 178,
            "sample_size_valid": True, # N >= 30
            "baseline_mean": 21.0,
            "observed_value": 58.0,
            "z_score": 2.89,
            "interpretation": "Indicator requiring administrative verification: elevated reopening rate in North Chennai pipeline zones following summer head reservoir maintenance. Flagged for engineering audit, not proof of negligence."
        }
    ]
}

FIXTURE_SOURCE_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "doc_id": "DOC-GCC-COUNCIL-2026",
        "title": "Greater Chennai Corporation — Council Proceedings & Grievance Digest",
        "issuing_authority": "Greater Chennai Corporation",
        "doc_type": "MUNICIPAL_COUNCIL_RESOLUTION",
        "publication_date": "2026-08-01",
        "checksum": "sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
        "retrieval_timestamp": "2026-08-10T11:00:00Z",
        "access_compliance": "Statutory Public Disclosure under Section 4(1)(b) RTI Act 2005",
        "records_count": 4120
    },
    {
        "doc_id": "DOC-TN-HW-ATR-2026",
        "title": "State Highways Department Chennai Division — Monthly Action Taken Log",
        "issuing_authority": "Highways and Minor Ports Department, GoTN",
        "doc_type": "GOVERNMENT_ACTION_TAKEN_REPORT",
        "publication_date": "2026-08-15",
        "checksum": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "retrieval_timestamp": "2026-08-18T14:20:00Z",
        "access_compliance": "Permitted Open Data Digest",
        "records_count": 620
    },
    {
        "doc_id": "DOC-CMWSSB-OPS-2026",
        "title": "CMWSSB Quality & Redressal Monitoring Bulletin",
        "issuing_authority": "Chennai Metropolitan Water Supply and Sewerage Board",
        "doc_type": "PUBLIC_DATASET_DUMP",
        "publication_date": "2026-08-17",
        "checksum": "sha256:ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb",
        "retrieval_timestamp": "2026-08-19T16:00:00Z",
        "access_compliance": "Authorized Statutory Service Report",
        "records_count": 1430
    }
]
