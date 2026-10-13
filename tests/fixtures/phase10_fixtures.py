"""
Phase 10.1 — Policy Outcome & Impact Evaluation Test Fixtures.
==============================================================

Provides strictly labelled, synthetic yet empirically realistic test fixtures
modeling Tamil Nadu welfare policy interventions:
1. Pudhumai Penn Scheme (Higher Education Assurance Scheme for Girls)
2. Kalaignar Magalir Urimai Thittam (Basic Income for Women)
3. Makkalai Thedi Maruthuvam (Doorstep Healthcare Scheme)

All fixtures carry `is_test_fixture=True` and deterministic IDs.
"""

from typing import List, Dict, Any


def get_phase10_sample_objectives() -> List[Dict[str, Any]]:
    return [
        {
            "objective_id": "OBJ-TEST-PUDHUMAI-PENN-01",
            "scheme_id": "SCH-TEST-PUDHUMAI-PENN",
            "promise_id": "PROM-TEST-DMK-2021-EDU-01",
            "title": "Moovalur Ramamirtham Ammaiyar Higher Education Assurance Scheme (Pudhumai Penn)",
            "title_ta": "புதுமைப் பெண் திட்டம் - மூவலூர் ராமாமிர்தம் அம்மையார் உயர்கல்வி உறுதித் திட்டம்",
            "description": "Provide monthly financial assistance of ₹1,000 to girl students who studied in Classes 6 to 12 in Tamil Nadu government schools until they complete their undergraduate degree, diploma, or ITI course.",
            "sector": "Higher Education & Social Welfare",
            "is_statutory": True,
            "target_metrics": {
                "target_beneficiaries_year_1": 500000,
                "target_ger_increase_points": 5.0,
            },
            "is_test_fixture": True,
        },
        {
            "objective_id": "OBJ-TEST-MAGALIR-URIMAI-01",
            "scheme_id": "SCH-TEST-KMUT",
            "promise_id": "PROM-TEST-DMK-2021-WEL-01",
            "title": "Kalaignar Magalir Urimai Thittam (Basic Income for Women)",
            "title_ta": "கலைஞர் மகளிர் உரிமைத் திட்டம்",
            "description": "Provide unconditional monthly basic income grant of ₹1,000 to eligible adult women heads of households to recognize unpaid household labor and alleviate female financial vulnerability.",
            "sector": "Social Welfare & Poverty Alleviation",
            "is_statutory": True,
            "target_metrics": {
                "target_women_heads": 10000000,
                "annual_outlay_cr": 12000.0,
            },
            "is_test_fixture": True,
        },
        {
            "objective_id": "OBJ-TEST-MAKKALAI-THEDI-01",
            "scheme_id": "SCH-TEST-MTM",
            "promise_id": "PROM-TEST-DMK-2021-HLT-01",
            "title": "Makkalai Thedi Maruthuvam (Healthcare at Doorsteps)",
            "title_ta": "மக்களைத் தேடி மருத்துவம்",
            "description": "Screen and deliver essential medications directly to citizens' homes for hypertension, diabetes, and palliative care, reducing out-of-pocket healthcare costs.",
            "sector": "Public Health & Preventive Medicine",
            "is_statutory": False,
            "target_metrics": {
                "screened_citizens_target": 10000000,
                "doorstep_medicine_kits": 5000000,
            },
            "is_test_fixture": True,
        },
    ]


def get_phase10_sample_beneficiary_groups() -> List[Dict[str, Any]]:
    return [
        {
            "group_id": "BEN-TEST-PUDHUMAI-GIRLS",
            "objective_id": "OBJ-TEST-PUDHUMAI-PENN-01",
            "scheme_id": "SCH-TEST-PUDHUMAI-PENN",
            "name": "Government School Female Students Entering Higher Education",
            "name_ta": "அரசுப் பள்ளி மாணவிகள் - உயர்கல்வி பயில்வோர்",
            "eligibility_criteria": "Girls who studied continuously from Classes 6 to 12 in Tamil Nadu Government schools and enrolled in recognized undergraduate degrees, diplomas, or ITI programs.",
            "exclusion_criteria": "Students who did not study in government schools or enrolled in private correspondence courses without attendance.",
            "estimated_eligible_population": 520000,
            "geographic_focus": "Statewide (All 38 Districts)",
            "is_test_fixture": True,
        },
        {
            "group_id": "BEN-TEST-KMUT-WOMEN",
            "objective_id": "OBJ-TEST-MAGALIR-URIMAI-01",
            "scheme_id": "SCH-TEST-KMUT",
            "name": "Eligible Women Family Heads (Low-Income Households)",
            "name_ta": "தகுதிவாய்ந்த மகளிர் குடும்பத் தலைவிகள்",
            "eligibility_criteria": "Women aged 21 and above whose annual family income is below ₹2.5 Lakh, possessing family ration card, owning less than 5 acres of wetland or 10 acres of dry land, and consuming less than 3,600 units of electricity annually.",
            "exclusion_criteria": "Income tax payees, government employees, pensioners receiving > ₹2,500/month, and four-wheeler owners.",
            "estimated_eligible_population": 12500000,
            "geographic_focus": "Statewide (All 38 Districts)",
            "is_test_fixture": True,
        },
    ]


def get_phase10_sample_activities() -> List[Dict[str, Any]]:
    return [
        {
            "activity_id": "ACT-TEST-PUDHUMAI-DBT-INTEG",
            "scheme_id": "SCH-TEST-PUDHUMAI-PENN",
            "activity_name": "Penkalvi Portal Development & Aadhaar-Linked Bank Seeding",
            "activity_type": "PROCUREMENT_AND_IT",
            "scheduled_start": "2022-04-01",
            "scheduled_end": "2022-08-31",
            "actual_end": "2022-09-05",
            "status": "COMPLETED",
            "budget_allocated": 15.5,
            "expenditure_incurred": 14.8,
            "implementing_agency": "TNeGA & Higher Education Department",
            "source_document_id": "DOC-TEST-GO-HE-2022-01",
            "is_test_fixture": True,
        },
        {
            "activity_id": "ACT-TEST-KMUT-CAMP-SCRUTINY",
            "scheme_id": "SCH-TEST-KMUT",
            "activity_name": "Two-Phase Statewide Application Collection & Field Verification Camps",
            "activity_type": "REGISTRATION_CAMPS",
            "scheduled_start": "2023-07-01",
            "scheduled_end": "2023-08-25",
            "actual_end": "2023-08-28",
            "status": "COMPLETED",
            "budget_allocated": 45.0,
            "expenditure_incurred": 42.6,
            "implementing_agency": "Revenue and Disaster Management Department",
            "source_document_id": "DOC-TEST-KMUT-CAMP-GUIDELINES-2023",
            "is_test_fixture": True,
        },
    ]


def get_phase10_sample_indicators() -> List[Dict[str, Any]]:
    return [
        # INPUT
        {
            "indicator_id": "IND-TEST-PUDHUMAI-BUDGET",
            "objective_id": "OBJ-TEST-PUDHUMAI-PENN-01",
            "scheme_id": "SCH-TEST-PUDHUMAI-PENN",
            "indicator_name": "Annual Scheme Budgetary Allocation",
            "indicator_name_ta": "திட்ட ஆண்டு நிதி ஒதுக்கீடு",
            "indicator_type": "INPUT",
            "unit": "RUPEES_CRORE",
            "direction_of_improvement": "INCREASE",
            "aggregation_method": "SUM",
            "description": "Total budget provision sanctioned in State Budget Demands for Grants.",
            "is_test_fixture": True,
        },
        # OUTPUT
        {
            "indicator_id": "IND-TEST-PUDHUMAI-BENEFICIARIES",
            "objective_id": "OBJ-TEST-PUDHUMAI-PENN-01",
            "scheme_id": "SCH-TEST-PUDHUMAI-PENN",
            "indicator_name": "Active Female Students Receiving Monthly Stipend",
            "indicator_name_ta": "மாத உதவித்தொகை பெறும் மாணவிகள் எண்ணிக்கை",
            "indicator_type": "OUTPUT",
            "unit": "COUNT",
            "direction_of_improvement": "INCREASE",
            "aggregation_method": "SUM",
            "description": "Verified count of girl students receiving monthly ₹1,000 credit in their bank accounts.",
            "is_test_fixture": True,
        },
        # OUTCOME
        {
            "indicator_id": "IND-TEST-PUDHUMAI-GER-FEMALE",
            "objective_id": "OBJ-TEST-PUDHUMAI-PENN-01",
            "scheme_id": "SCH-TEST-PUDHUMAI-PENN",
            "indicator_name": "Female Gross Enrollment Ratio (GER) in Higher Education",
            "indicator_name_ta": "உயர்கல்வியில் பெண்களுக்கான மொத்த சேர்க்கை விகிதம்",
            "indicator_type": "OUTCOME",
            "unit": "PERCENT",
            "direction_of_improvement": "INCREASE",
            "aggregation_method": "WEIGHTED_AVERAGE",
            "description": "Percentage of eligible female population aged 18-23 enrolled in tertiary education institutions in Tamil Nadu.",
            "is_test_fixture": True,
        },
        # OUTCOME 2 (Transition rate)
        {
            "indicator_id": "IND-TEST-PUDHUMAI-TRANSITION-RATE",
            "objective_id": "OBJ-TEST-PUDHUMAI-PENN-01",
            "scheme_id": "SCH-TEST-PUDHUMAI-PENN",
            "indicator_name": "Govt School Female Transition Rate to College",
            "indicator_name_ta": "அரசுப் பள்ளி மாணவிகளின் கல்லூரி சேர்க்கை மாற்றம்",
            "indicator_type": "OUTCOME",
            "unit": "PERCENT",
            "direction_of_improvement": "INCREASE",
            "aggregation_method": "MEAN",
            "description": "Share of Class 12 government school female graduates progressing to recognized tertiary degree/diploma programs within 1 year.",
            "is_test_fixture": True,
        },
        # IMPACT
        {
            "indicator_id": "IND-TEST-PUDHUMAI-LFPR-FEMALE",
            "objective_id": "OBJ-TEST-PUDHUMAI-PENN-01",
            "scheme_id": "SCH-TEST-PUDHUMAI-PENN",
            "indicator_name": "Female Labor Force Participation Rate (Aged 20-29)",
            "indicator_name_ta": "பெண்கள் தொழிலாளர் பங்கேற்பு விகிதம் (20-29 வயது)",
            "indicator_type": "IMPACT",
            "unit": "PERCENT",
            "direction_of_improvement": "INCREASE",
            "aggregation_method": "WEIGHTED_AVERAGE",
            "description": "Long-term share of young graduate women entering formal or organized employment in Tamil Nadu.",
            "is_test_fixture": True,
        },
    ]


def get_phase10_sample_observations() -> List[Dict[str, Any]]:
    return [
        # Baseline GER observation (2018-19, prior to scheme)
        {
            "observation_id": "OBS-TEST-GER-BASE-2018",
            "indicator_id": "IND-TEST-PUDHUMAI-GER-FEMALE",
            "value": 48.2,
            "reference_period": "2018-19",
            "geographic_level": "STATE",
            "geographic_unit_id": "STATE-TN",
            "stage": "BASELINE",
            "source_document_id": "DOC-TEST-AISHE-2018-19",
            "source_reference": "All India Survey on Higher Education (AISHE) 2018-19 Table 4",
            "document_hash": "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
            "data_quality_status": "VERIFIED",
            "is_test_fixture": True,
        },
        # Intermediate GER observation (2021-22, transition year)
        {
            "observation_id": "OBS-TEST-GER-MID-2021",
            "indicator_id": "IND-TEST-PUDHUMAI-GER-FEMALE",
            "value": 49.5,
            "reference_period": "2021-22",
            "geographic_level": "STATE",
            "geographic_unit_id": "STATE-TN",
            "stage": "INTERMEDIATE",
            "source_document_id": "DOC-TEST-AISHE-2021-22",
            "source_reference": "AISHE 2021-22 Report",
            "document_hash": "b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef01",
            "data_quality_status": "VERIFIED",
            "is_test_fixture": True,
        },
        # Follow-up GER observation (2023-24, post-rollout)
        {
            "observation_id": "OBS-TEST-GER-FOL-2023",
            "indicator_id": "IND-TEST-PUDHUMAI-GER-FEMALE",
            "value": 54.1,
            "reference_period": "2023-24",
            "geographic_level": "STATE",
            "geographic_unit_id": "STATE-TN",
            "stage": "FOLLOW_UP",
            "source_document_id": "DOC-TEST-AISHE-2023-24",
            "source_reference": "AISHE 2023-24 Provisional State Report",
            "document_hash": "c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef012",
            "data_quality_status": "VERIFIED",
            "is_test_fixture": True,
        },
        # Formal Target GER observation
        {
            "observation_id": "OBS-TEST-GER-TGT-2026",
            "indicator_id": "IND-TEST-PUDHUMAI-GER-FEMALE",
            "value": 60.0,
            "reference_period": "2026-27",
            "geographic_level": "STATE",
            "geographic_unit_id": "STATE-TN",
            "stage": "TARGET",
            "source_document_id": "DOC-TEST-TN-POLICY-NOTE-2022",
            "source_reference": "Higher Education Department Policy Note 2022-23, p. 12",
            "document_hash": "d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0123",
            "data_quality_status": "VERIFIED",
            "is_test_fixture": True,
        },
        # Baseline Transition Rate observation
        {
            "observation_id": "OBS-TEST-TRANS-BASE-2021",
            "indicator_id": "IND-TEST-PUDHUMAI-TRANSITION-RATE",
            "value": 69.8,
            "reference_period": "2021-22",
            "geographic_level": "STATE",
            "geographic_unit_id": "STATE-TN",
            "stage": "BASELINE",
            "source_document_id": "DOC-TEST-SCHOOL-EDU-STAT-2021",
            "source_reference": "TN School Education Department Administrative Report 2021-22",
            "document_hash": "e5f67890123456789abcdef0123456789abcdef0123456789abcdef01234",
            "data_quality_status": "VERIFIED",
            "is_test_fixture": True,
        },
        # Follow-up Transition Rate observation
        {
            "observation_id": "OBS-TEST-TRANS-FOL-2023",
            "indicator_id": "IND-TEST-PUDHUMAI-TRANSITION-RATE",
            "value": 84.6,
            "reference_period": "2023-24",
            "geographic_level": "STATE",
            "geographic_unit_id": "STATE-TN",
            "stage": "FOLLOW_UP",
            "source_document_id": "DOC-TEST-SCHOOL-EDU-STAT-2023",
            "source_reference": "TN School Education Department Administrative Report 2023-24",
            "document_hash": "f67890123456789abcdef0123456789abcdef0123456789abcdef012345",
            "data_quality_status": "VERIFIED",
            "is_test_fixture": True,
        },
        # Output count observation (2023-24)
        {
            "observation_id": "OBS-TEST-BEN-FOL-2023",
            "indicator_id": "IND-TEST-PUDHUMAI-BENEFICIARIES",
            "value": 482000.0,
            "reference_period": "2023-24",
            "geographic_level": "STATE",
            "geographic_unit_id": "STATE-TN",
            "stage": "FOLLOW_UP",
            "source_document_id": "DOC-TEST-TN-POLICY-NOTE-2024",
            "source_reference": "Higher Education Department Policy Note 2024-25, Table 3",
            "document_hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "data_quality_status": "VERIFIED",
            "is_test_fixture": True,
        },
    ]


def get_phase10_sample_studies() -> List[Dict[str, Any]]:
    return [
        {
            "study_id": "STD-TEST-PUDHUMAI-QUASI-EXP-01",
            "scheme_id": "SCH-TEST-PUDHUMAI-PENN",
            "title": "Impact of Direct College Conditional Cash Transfer on Female Transition in Tamil Nadu: A Difference-in-Differences Study",
            "evaluation_type": "CAUSAL_EVALUATION",
            "conducting_agency": "State Planning Commission & Madras School of Economics",
            "publication_date": "2024-06-15",
            "methodology_description": "Difference-in-Differences comparing female college transition rates among government school students (treated) against private un-aided school female graduates (control group) before and after 2022 policy rollout. Pre-treatment parallel trends confirmed with p = 0.42.",
            "causal_rigor_grade": "GRADE_B_QUASI_EXPERIMENTAL",
            "is_causally_identified": True,
            "identification_strategy": "DID",
            "source_document_id": "DOC-TEST-SPC-EVAL-2024-01",
            "source_url": "https://spc.tn.gov.in/evaluation/pudhumai_penn_study_2024.pdf",
            "document_hash": "11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
            "is_test_fixture": True,
        },
        {
            "study_id": "STD-TEST-PUDHUMAI-CAG-AUDIT-01",
            "scheme_id": "SCH-TEST-PUDHUMAI-PENN",
            "title": "CAG Performance Audit on Implementation of Higher Education Welfare Schemes in Tamil Nadu",
            "evaluation_type": "AUDIT_FINDING",
            "conducting_agency": "Comptroller and Auditor General of India (Report No. 3 of 2024)",
            "publication_date": "2024-03-20",
            "methodology_description": "Field scrutiny of 45 tertiary institutions across 6 districts, auditing 12,500 beneficiary disbursements against treasury records and college biometric attendance rosters.",
            "causal_rigor_grade": "GRADE_D_DESCRIPTIVE_CORRELATIONAL",
            "is_causally_identified": False,
            "identification_strategy": "NONE",
            "source_document_id": "DOC-TEST-CAG-REPORT-3-2024",
            "source_url": "https://cag.gov.in/en/audit-report/details/119420",
            "document_hash": "22334455667788990011aabbccddeeff22334455667788990011aabbccddeeff",
            "is_test_fixture": True,
        },
        {
            "study_id": "STD-TEST-PUDHUMAI-DESCRIPTIVE-01",
            "scheme_id": "SCH-TEST-PUDHUMAI-PENN",
            "title": "Annual Implementation Progress and Budget Execution Analysis of Pudhumai Penn Scheme",
            "evaluation_type": "BEFORE_AND_AFTER_DESCRIPTIVE",
            "conducting_agency": "Directorate of Social Welfare & Nutritious Meal Programme",
            "publication_date": "2024-04-10",
            "methodology_description": "Descriptive before-and-after comparison of gross female enrollments using administrative portal figures without a comparison group.",
            "causal_rigor_grade": "GRADE_D_DESCRIPTIVE_CORRELATIONAL",
            "is_causally_identified": False,
            "identification_strategy": "NONE",
            "source_document_id": "DOC-TEST-SW-ANNUAL-2024",
            "source_url": "https://www.tn.gov.in/socialwelfare/annual_progress_2024.pdf",
            "document_hash": "33445566778899001122aabbccddeeff33445566778899001122aabbccddeeff",
            "is_test_fixture": True,
        },
        # Flawed study with missing control group designed to trigger automatic downgrading
        {
            "study_id": "STD-TEST-FLAWED-CAUSAL-CLAIM-01",
            "scheme_id": "SCH-TEST-KMUT",
            "title": "Asserted Statewide Causal Reduction in Female Poverty by Cash Transfer",
            "evaluation_type": "CAUSAL_EVALUATION",
            "conducting_agency": "Independent Think Tank Press Release",
            "publication_date": "2024-01-15",
            "methodology_description": "Observed state-level reduction in informal borrowing after cash transfer rollout. No control group, no pre-trend testing, no counterfactual.",
            "causal_rigor_grade": "GRADE_E_ANECDOTAL_UNSUBSTANTIATED",
            "is_causally_identified": False,
            "identification_strategy": "NONE",
            "source_document_id": "DOC-TEST-PRESS-RELEASE-KMUT-2024",
            "source_url": "https://civicresearch.org/reports/kmut_claim.pdf",
            "document_hash": "44556677889900112233aabbccddeeff44556677889900112233aabbccddeeff",
            "is_test_fixture": True,
        },
    ]


def get_phase10_sample_findings() -> List[Dict[str, Any]]:
    return [
        {
            "finding_id": "FIND-TEST-PUDHUMAI-DID-EFFECT",
            "study_id": "STD-TEST-PUDHUMAI-QUASI-EXP-01",
            "indicator_id": "IND-TEST-PUDHUMAI-TRANSITION-RATE",
            "finding_type": "POSITIVE_IMPACT",
            "finding_text": "Pudhumai Penn Scheme caused a statistically significant 14.8 percentage point increase in female government school graduate transition into higher education relative to unaffected controls (DiD beta = 0.148, p < 0.001).",
            "quantified_effect": 14.8,
            "p_value": 0.0008,
            "confidence_level": "VERY_HIGH",
            "has_contradicting_evidence": False,
            "is_test_fixture": True,
        },
        {
            "finding_id": "FIND-TEST-PUDHUMAI-CAG-IRREGULARITY",
            "study_id": "STD-TEST-PUDHUMAI-CAG-AUDIT-01",
            "indicator_id": "IND-TEST-PUDHUMAI-BENEFICIARIES",
            "finding_type": "MIXED_RESULTS",
            "finding_text": "While 92% of eligible girls received timely disbursement, CAG audit revealed that ₹8.45 Crore remained pending due to Aadhaar-bank account mapping failures in rural branches across Ramanathapuram and Dharmapuri districts.",
            "quantified_effect": -8.45,
            "p_value": None,
            "confidence_level": "VERY_HIGH",
            "has_contradicting_evidence": True,
            "is_test_fixture": True,
        },
        {
            "finding_id": "FIND-TEST-PUDHUMAI-DESCRIPTIVE-GER",
            "study_id": "STD-TEST-PUDHUMAI-DESCRIPTIVE-01",
            "indicator_id": "IND-TEST-PUDHUMAI-GER-FEMALE",
            "finding_type": "POSITIVE_IMPACT",
            "finding_text": "Female higher education GER expanded by +5.9 percentage points between 2018-19 baseline (48.2%) and 2023-24 follow-up (54.1%). Note: Observational increase, not fully isolated from secular state growth.",
            "quantified_effect": 5.9,
            "p_value": None,
            "confidence_level": "MODERATE",
            "has_contradicting_evidence": False,
            "is_test_fixture": True,
        },
    ]


def get_phase10_sample_evidence_links() -> List[Dict[str, Any]]:
    return [
        {
            "link_id": "EVL-TEST-AISHE-STAT",
            "finding_id": "FIND-TEST-PUDHUMAI-DID-EFFECT",
            "source_document_id": "DOC-TEST-AISHE-2023-24",
            "source_passage_id": "PASS-AISHE-TN-P14",
            "page_number": 14,
            "table_reference": "Table 2.8: State-wise Higher Education Transition by Gender",
            "stance": "SUPPORTS",
            "quotation_excerpt": "Tamil Nadu recorded the sharpest single-year surge in female undergraduate enrollment from public secondary schools (+14.2% YoY in 2023-24), driven by social welfare financial incentives.",
            "source_credibility_tier": "TIER_2_OFFICIAL_AGENCY",
            "alignment_score": 0.95,
            "document_hash": "c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef012",
            "is_test_fixture": True,
        },
        {
            "link_id": "EVL-TEST-CAG-QUALIFICATION",
            "finding_id": "FIND-TEST-PUDHUMAI-CAG-IRREGULARITY",
            "source_document_id": "DOC-TEST-CAG-REPORT-3-2024",
            "source_passage_id": "PASS-CAG-REP3-P45",
            "page_number": 45,
            "table_reference": "Paragraph 4.3.2: Pending DBT Stipend Transfers",
            "stance": "CONTRADICTS",
            "quotation_excerpt": "Audit scrutiny revealed that out of 34,200 verified applications in 6 sampled districts, 2,840 students (8.3%) did not receive monthly credits for over 4 consecutive months due to NPCI Aadhaar seeding mismatch.",
            "source_credibility_tier": "TIER_1_STATUTORY",
            "alignment_score": 1.0,
            "document_hash": "22334455667788990011aabbccddeeff22334455667788990011aabbccddeeff",
            "is_test_fixture": True,
        },
    ]


def get_phase10_sample_limitations() -> List[Dict[str, Any]]:
    return [
        {
            "limitation_id": "LIM-TEST-COVID-CONFOUNDER-01",
            "study_id": "STD-TEST-PUDHUMAI-QUASI-EXP-01",
            "category": "EXTERNAL_CONFOUNDING",
            "description": "The COVID-19 pandemic induced severe macroeconomic and household financial stress between 2020 and 2022, potentially distorting secular baseline trend lines in secondary school retention.",
            "confounding_factors": "Pandemic school closures, economic displacement, concurrent launch of Illam Thedi Kalvi.",
            "severity": "MODERATE",
            "is_test_fixture": True,
        },
        {
            "limitation_id": "LIM-TEST-ATTRITION-COLLEGE-01",
            "study_id": "STD-TEST-PUDHUMAI-QUASI-EXP-01",
            "category": "ATTRITION",
            "description": "Evaluation measures college enrollment transition at year 1; longitudinal cohort persistence through graduation (Year 3/4 completion) has not yet elapsed for the 2022 entry cohort.",
            "confounding_factors": "Early marriage pressures, post-year-1 college dropout rates.",
            "severity": "HIGH",
            "is_test_fixture": True,
        },
        {
            "limitation_id": "LIM-TEST-NO-CONTROL-GROUP-01",
            "study_id": "STD-TEST-FLAWED-CAUSAL-CLAIM-01",
            "category": "ABSENCE_OF_CONTROL_GROUP",
            "description": "Study fails to establish a contemporaneous control group or parallel pre-trends, invalidating causal attribution of borrowing reduction strictly to the cash transfer.",
            "confounding_factors": "General post-COVID state economic recovery, agricultural monsoon stability, state credit cooperative loan waivers.",
            "severity": "CRITICAL",
            "is_test_fixture": True,
        },
    ]


def get_phase10_sample_registry_entries() -> List[Dict[str, Any]]:
    """Phase 10.3 Policy Registry test fixtures with clear and ambiguous objectives."""
    return [
        {
            "policy_id": "POL-TEST-PUDHUMAI-PENN",
            "canonical_scheme_code": "SCH-TEST-PUDHUMAI-PENN",
            "promise_id": "PROM-TEST-DMK-2021-EDU-01",
            "policy_name": "Moovalur Ramamirtham Ammaiyar Higher Education Assurance Scheme (Pudhumai Penn)",
            "policy_name_ta": "புதுமைப் பெண் திட்டம் - மூவலூர் ராமாமிர்தம் அம்மையார் உயர்கல்வி உறுதித் திட்டம்",
            "aliases": [
                "Pudhumai Penn",
                "Pudhumai Penn Scheme",
                "Moovalur Ramamirtham Higher Education Scheme",
                "புதுமைப் பெண்",
            ],
            "responsible_department": "Social Welfare and Women Empowerment Department",
            "objectives_summary": "Increase higher education enrollment among girl students from government schools through a monthly ₹1,000 direct benefit transfer.",
            "original_objective_wording": "Provide ₹1,000 per month directly to the bank accounts of all girl students who studied from Classes 6 to 12 in Government schools to pursue higher education without financial hindrance.",
            "is_objective_ambiguous": False,
            "intended_beneficiaries": "Girl students who studied continuously in Classes 6–12 in Tamil Nadu Government schools and enrolled in undergraduate degree, diploma, or ITI courses.",
            "geographic_scope": "STATEWIDE",
            "covered_districts": ["All 38 Districts"],
            "start_date": "2022-09-05",
            "end_date": None,
            "implementation_rules": {
                "government_order": "G.O. (Ms.) No. 55, Social Welfare and Women Empowerment Dept, Dated 04.07.2022",
                "disbursement_mode": "Direct Benefit Transfer (DBT) via Aadhaar-seeded bank account",
                "monthly_amount_inr": 1000,
                "nodal_agency": "Directorate of Social Welfare & TNeGA",
            },
            "stated_targets": [
                {
                    "indicator_name": "Annual Female Student Beneficiaries",
                    "target_value": 500000.0,
                    "unit": "COUNT",
                    "target_provenance": "OFFICIALLY_STATED",
                    "source_reference": "TN Budget Speech 2022-23, Para 84 & Higher Education Policy Note 2022-23",
                },
                {
                    "indicator_name": "Female Higher Education GER Benchmark",
                    "target_value": 60.0,
                    "unit": "PERCENT",
                    "target_provenance": "ANALYST_PROPOSED_BENCHMARK",
                    "source_reference": "State Planning Commission 5-Year Analytical Benchmark (Non-Statutory)",
                },
            ],
            "source_documents": ["DOC-TEST-GO-SW-55-2022", "DOC-TEST-TN-POLICY-NOTE-2022"],
            "evaluation_status": "EVALUATED",
            "is_test_fixture": True,
        },
        {
            "policy_id": "POL-TEST-AMBIGUOUS-RURAL-VISION",
            "canonical_scheme_code": "SCH-TEST-RURAL-VISION",
            "policy_name": "Integrated Holistic Rural Paradigm Transformation Mission",
            "policy_name_ta": "ஒருங்கிணைந்த கிராமப்புற முழுமையான மாற்றத் திட்டம்",
            "aliases": ["Rural Paradigm Mission", "IHRPTM"],
            "responsible_department": "Rural Development and Panchayat Raj Department",
            "objectives_summary": "Achieve world-class holistic transformation and seamless empowerment of rural communities.",
            "original_objective_wording": "To usher in a world-class holistic transformation and overall upliftment of rural life through seamless empowerment across villages.",
            "is_objective_ambiguous": None,  # Will be automatically detected and flagged as ambiguous
            "intended_beneficiaries": "Rural residents across village panchayats in Tamil Nadu.",
            "geographic_scope": "RURAL_ONLY",
            "covered_districts": ["Dharmapuri", "Ariyalur", "Ramanathapuram"],
            "start_date": "2023-04-01",
            "end_date": None,
            "implementation_rules": {
                "government_order": "G.O. (Ms.) No. 19, RD&PR Dept, Dated 10.04.2023",
            },
            "stated_targets": [],
            "source_documents": ["DOC-TEST-GO-RD-19-2023"],
            "evaluation_status": "NOT_STARTED",
            "is_test_fixture": True,
        },
    ]


def get_phase10_sample_evaluation_plans() -> List[Dict[str, Any]]:
    """Phase 10.3 Policy Evaluation Plan test fixtures."""
    return [
        # Plan 1: Officially stated target (Output delivery)
        {
            "plan_id": "PLAN-TEST-PUDHUMAI-OUTPUT-01",
            "policy_id": "POL-TEST-PUDHUMAI-PENN",
            "objective_id": "OBJ-TEST-PUDHUMAI-PENN-01",
            "indicator_id": "IND-TEST-PUDHUMAI-BENEFICIARIES",
            "evaluation_question": "Did the Pudhumai Penn scheme reach its officially announced annual target of 500,000 girl student beneficiaries in FY 2023-24?",
            "evaluation_type": "TARGET_VERSUS_ACTUAL",
            "objective_being_assessed": "Provide monthly financial assistance of ₹1,000 to 500,000 government school girl students entering higher education.",
            "indicator_definition": "Total verified count of active female undergraduate/diploma/ITI students receiving monthly ₹1,000 DBT stipend.",
            "indicator_type": "OUTPUT",
            "unit": "COUNT",
            "baseline_period": "2021-22",
            "comparison_period": "2023-24",
            "baseline_value": 0.0,
            "target_value": 500000.0,
            "target_provenance": "OFFICIALLY_STATED",
            "target_source_reference": "TN Budget Speech 2022-23, Para 84 (Target: 5 Lakh students)",
            "actual_value": 482000.0,
            "data_source": "Higher Education Department Policy Note 2024-25 & CAG Audit Report No. 3 of 2024",
            "source_document_ids": ["DOC-TEST-TN-POLICY-NOTE-2024", "DOC-TEST-CAG-REPORT-3-2024"],
            "calculation_method": "Physical Target Realization Ratio (PTRR) = (Actual Beneficiaries / Officially Stated Target) * 100",
            "geographic_level": "STATE",
            "limitations": "Output count confirms stipend transfer but does not measure degree completion; CAG noted 8.3% NPCI seeding delays in 6 sampled districts.",
            "is_test_fixture": True,
        },
        # Plan 2: Analyst-proposed benchmark (Outcome assessment)
        {
            "plan_id": "PLAN-TEST-PUDHUMAI-OUTCOME-02",
            "policy_id": "POL-TEST-PUDHUMAI-PENN",
            "objective_id": "OBJ-TEST-PUDHUMAI-PENN-01",
            "indicator_id": "IND-TEST-PUDHUMAI-GER-FEMALE",
            "evaluation_question": "How did Tamil Nadu's female Higher Education Gross Enrollment Ratio (GER) change between baseline (2018-19) and post-rollout (2023-24) relative to the 60% analytical benchmark?",
            "evaluation_type": "BEFORE_AND_AFTER_DESCRIPTIVE",
            "objective_being_assessed": "Increase female gross enrollment ratio in higher education across Tamil Nadu.",
            "indicator_definition": "Female enrollment in tertiary education as a percentage of the female population in the 18–23 age cohort.",
            "indicator_type": "OUTCOME",
            "unit": "PERCENT",
            "baseline_period": "2018-19",
            "comparison_period": "2023-24",
            "baseline_value": 48.2,
            "target_value": 60.0,
            "target_provenance": "ANALYST_PROPOSED_BENCHMARK",
            "target_source_reference": "Analytical comparison benchmark proposed by SPC higher education working group (60% GER by 2026)",
            "actual_value": 54.1,
            "data_source": "All India Survey on Higher Education (AISHE) 2018-19 & 2023-24 Reports",
            "source_document_ids": ["DOC-TEST-AISHE-2018-19", "DOC-TEST-AISHE-2023-24"],
            "calculation_method": "Percentage Point Change = Y_2023 - Y_2018; Relative Change = ((Y_2023 - Y_2018) / Y_2018) * 100",
            "geographic_level": "STATE",
            "limitations": "Before-and-after statewide trajectory reflects both Pudhumai Penn and secular educational growth; causal attribution requires DiD control group.",
            "is_test_fixture": True,
        },
        # Plan 3: No published target (Descriptive evaluation of ambiguous policy)
        {
            "plan_id": "PLAN-TEST-RURAL-VISION-01",
            "policy_id": "POL-TEST-AMBIGUOUS-RURAL-VISION",
            "objective_id": None,
            "indicator_id": None,
            "evaluation_question": "What was the change in village panchayat own-source revenue and civic infrastructure works completed in covered rural districts between 2022-23 and 2023-24?",
            "evaluation_type": "BEFORE_AND_AFTER_DESCRIPTIVE",
            "objective_being_assessed": "To usher in a world-class holistic transformation and overall upliftment of rural life through seamless empowerment across villages.",
            "indicator_definition": "Percentage of village panchayats in covered districts with functional piped water and all-weather road connectivity.",
            "indicator_type": "OUTCOME",
            "unit": "PERCENT",
            "baseline_period": "2022-23",
            "comparison_period": "2023-24",
            "baseline_value": 74.5,
            "target_value": None,
            "target_provenance": "NO_PUBLISHED_TARGET",
            "target_source_reference": None,
            "actual_value": 78.2,
            "data_source": "Rural Development & Panchayat Raj Annual Administrative Report 2023-24",
            "source_document_ids": ["DOC-TEST-GO-RD-19-2023"],
            "calculation_method": "Before-and-After Difference (Y_2023_24 - Y_2022_23) across 3 covered districts",
            "geographic_level": "DISTRICT",
            "limitations": "Original policy objective wording is ambiguous ('world-class holistic transformation') and no numeric target was published in G.O. Ms. No. 19.",
            "is_test_fixture": True,
        },
    ]
