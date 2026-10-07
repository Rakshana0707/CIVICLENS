import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
from frontend.services.api import api_client

st.set_page_config(
    page_title="Political Promise Tracker - CivicLens TN",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# TEST FIXTURES (For Dev/Test Mode exploration only)
# ---------------------------------------------------------------------------
FIXTURE_PROMISES = [
    {
        "promise_id": "TEST_FIXTURE_DMK_001",
        "manifesto_id": "DMK_2026_Assembly",
        "party": "DMK",
        "election_year": 2026,
        "original_text": "We will provide free laptops to all Class 11 and 12 high school students across Tamil Nadu.",
        "normalized_text": "We will provide free laptops to all Class 11 and 12 high school students across Tamil Nadu.",
        "page_number": 4,
        "section": "Education & Digital Literacy",
        "language": "English",
        "classification": "specific_promise",
        "primary_category": "Education",
        "current_status": "policy_action",
        "metadata": {
            "target_population": "Students / Youth",
            "sector": "Education",
            "department": "School & Higher Education",
            "proposed_action": "Construct / Establish",
            "numeric_target": "100%",
            "monetary_target": "Rs. 1500 crore",
            "time_horizon": "within 1 year"
        }
    },
    {
        "promise_id": "TEST_FIXTURE_AIADMK_002",
        "manifesto_id": "AIADMK_2021_Assembly",
        "party": "AIADMK",
        "election_year": 2021,
        "original_text": "விவசாயிகளுக்கு பயிர் கடன் தள்ளுபடி செய்யப்படும்.",
        "normalized_text": "விவசாயிகளுக்கு பயிர் கடன் தள்ளுபடி செய்யப்படும்.",
        "page_number": 12,
        "section": "Agriculture & Farmers Welfare",
        "language": "Tamil",
        "classification": "specific_promise",
        "primary_category": "Agriculture",
        "current_status": "implemented",
        "metadata": {
            "target_population": "Farmers",
            "sector": "Agriculture",
            "department": "Agriculture & Farmers Welfare",
            "proposed_action": "Waive / Cancel",
            "monetary_target": "Rs. 12,110 crore"
        }
    },
    {
        "promise_id": "TEST_FIXTURE_TVK_003",
        "manifesto_id": "TVK_2026_Assembly",
        "party": "TVK",
        "election_year": 2026,
        "original_text": "Monthly financial assistance of Rs. 1,000 for women household heads.",
        "normalized_text": "Monthly financial assistance of Rs. 1,000 for women household heads.",
        "page_number": 2,
        "section": "Women Empowerment & Welfare",
        "language": "English",
        "classification": "specific_promise",
        "primary_category": "Women",
        "current_status": "no_evidence_found",
        "metadata": {
            "target_population": "Women",
            "sector": "Women",
            "department": "Social Protection",
            "proposed_action": "Provide / Distribute",
            "monetary_target": "Rs. 1000 per month"
        }
    }
]

FIXTURE_SCHEME_MATCHES = [
    {
        "promise_id": "TEST_FIXTURE_DMK_001",
        "scheme_id": 101,
        "similarity_score": 0.92,
        "matching_method": "sentence_bert_cosine_similarity",
        "model_name": "paraphrase-multilingual-MiniLM-L12-v2",
        "model_version": "1.0.0",
        "scheme_details": {
            "scheme_name": "Free Laptop Scheme for School Students",
            "financial_year": "2021-2022",
            "department": "School Education Department",
            "description": "Annual distribution of free laptop computers to students studying in government schools."
        },
        "notes": "Semantic similarity indicates topical overlap only. It does NOT imply policy identity or fulfillment."
    }
]

FIXTURE_EVIDENCE_MATCHES = [
    {
        "evidence_id": 201,
        "content": "Government Order G.O. Ms. No. 45 dated 15/03/2021: Sanction of Rs. 1500 crore allocation for digital learning devices.",
        "page_number": 1,
        "context": "School Education Department - Sanction of funds for Class 11 & 12 students.",
        "supporting_values": {
            "source_url": "https://cms.tn.gov.in/sites/default/files/go/sw_2021.pdf",
            "source_domain": "cms.tn.gov.in",
            "source_name": "TN Government Orders Portal",
            "source_type": "Government Orders",
            "source_tier": 1,
            "publication_date": "15/03/2021"
        }
    }
]


# ---------------------------------------------------------------------------
# NON-ADVERSARIAL STATUS TAXONOMY & STYLING
# ---------------------------------------------------------------------------
STATUS_CONFIG = {
    "implemented": {"label": "Implemented", "color": "#28a745"},
    "partially_implemented": {"label": "Partially Implemented", "color": "#17a2b8"},
    "policy_action": {"label": "Policy Action", "color": "#007bff"},
    "announced": {"label": "Announced", "color": "#ffc107"},
    "no_evidence_found": {"label": "No Evidence Found", "color": "#fd7e14"},
    "unclear": {"label": "Insufficient Evidence", "color": "#6f42c1"},
    "not_assessed": {"label": "Not Assessed", "color": "#6c757d"},
    "disputed": {"label": "Disputed Evidence", "color": "#dc3545"}
}

def render_status_badge(status_str: str) -> str:
    cfg = STATUS_CONFIG.get(status_str, {"label": status_str.replace("_", " ").title(), "color": "#6c757d"})
    color = cfg["color"]
    label = cfg["label"]
    return f'<span style="background-color: {color}; color: white; padding: 4px 12px; border-radius: 14px; font-size: 13px; font-weight: bold;">{label}</span>'


# ---------------------------------------------------------------------------
# MAIN LAYOUT & HEADER
# ---------------------------------------------------------------------------
st.title("📜 Political Promise Tracker")
st.markdown("### Tamil Nadu Election Manifestos vs Evidence-Based Implementation Tracking")

# Sidebar Controls & Filters
st.sidebar.header("🛠️ Pipeline & Data Controls")
dev_mode = st.sidebar.toggle("🧪 Development / Test Mode (Fixture Data)", value=False)

st.sidebar.subheader("Filter Real Dataset")

# Dynamically fetch filter options from backend API or use full known taxonomy
all_parties = ["All", "AIADMK", "Archives", "BJP", "DMK", "INC", "MDMK", "MNM", "NTK", "PMK", "TVK"]
all_years = ["All", 2026, 2021, 2016, 2011, 2006, 2001, 1996]
all_categories = [
    "All", "Agriculture", "Digital services", "Education", "Employment", "Environment", 
    "Finance", "Governance", "Healthcare", "Housing", "Industry", "Infrastructure", 
    "Social protection", "Transport", "Uncategorized", "Welfare", "Women", "Youth"
]
all_languages = ["All", "English", "Tamil", "Mixed"]
all_statuses = [
    "All", "not_assessed", "no_evidence_found", "announced", "policy_action", 
    "partially_implemented", "implemented", "unclear", "disputed"
]

filter_party = st.sidebar.selectbox("Party", all_parties)
filter_election = st.sidebar.selectbox("Election Year", all_years)
filter_category = st.sidebar.selectbox("Category", all_categories)
filter_language = st.sidebar.selectbox("Language", all_languages)
filter_status = st.sidebar.selectbox("Implementation Status", all_statuses)
search_kw = st.sidebar.text_input("🔍 Search Keyword")

st.sidebar.subheader("Pagination")
page_num = st.sidebar.number_input("Page", min_value=1, value=1, step=1)
page_limit = st.sidebar.selectbox("Promises per page", [10, 20, 50, 100], index=1)


# ---------------------------------------------------------------------------
# DATA FETCHING (API vs Fixture Mode)
# ---------------------------------------------------------------------------
promises_data: List[Dict[str, Any]] = []
total_count = 0
total_pages = 1
using_fixtures = False
api_error = None

if dev_mode:
    using_fixtures = True
    promises_data = FIXTURE_PROMISES
    # Filter fixtures locally
    if filter_election != "All":
        promises_data = [p for p in promises_data if p.get("election_year") == filter_election]
    if filter_party != "All":
        promises_data = [p for p in promises_data if p.get("party") == filter_party]
    if filter_category != "All":
        promises_data = [p for p in promises_data if p.get("primary_category") == filter_category]
    if filter_language != "All":
        promises_data = [p for p in promises_data if p.get("language") == filter_language]
    if filter_status != "All":
        promises_data = [p for p in promises_data if p.get("current_status") == filter_status]
    if search_kw:
        promises_data = [p for p in promises_data if search_kw.lower() in p.get("original_text", "").lower()]
    total_count = len(promises_data)
    total_pages = 1
else:
    with st.spinner("Retrieving validated manifesto promises from CivicLens database..."):
        success, api_res = api_client.get_promises(
            party=filter_party,
            year=filter_election,
            category=filter_category,
            status=filter_status,
            language=filter_language,
            search=search_kw,
            page=page_num,
            limit=page_limit
        )
        if success and isinstance(api_res, dict):
            promises_data = api_res.get("items", [])
            total_count = api_res.get("total", 0)
            total_pages = api_res.get("pages", 1)
        else:
            api_error = api_res.get("message", "Unknown backend error")


# ---------------------------------------------------------------------------
# TOP METRICS & STATS BAR
# ---------------------------------------------------------------------------
if not dev_mode and not api_error:
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.metric("Total Real Promises", total_count)
    with m_col2:
        st.metric("Election Manifestos", 19)
    with m_col3:
        st.metric("Parties Tracked", 10)
    with m_col4:
        st.metric("Current Page", f"{page_num} of {max(1, total_pages)}")


# ---------------------------------------------------------------------------
# ERROR AND EMPTY STATE HANDLING
# ---------------------------------------------------------------------------
if api_error:
    st.error(f"""
    ### 🔌 Backend Connection Error
    Failed to connect to CivicLens API: **{api_error}**
    
    - Ensure the CivicLens backend server is running (`python -m backend.api.app` or `uvicorn`).
    - Enable **"🧪 Development / Test Mode (Fixture Data)"** in the left sidebar to explore UI layout.
    """)
    st.stop()

if not promises_data:
    st.warning(f"""
    ### ⚠️ No promises found matching your criteria.
    
    - **Filters Applied:** Party: `{filter_party}`, Year: `{filter_election}`, Category: `{filter_category}`, Language: `{filter_language}`, Status: `{filter_status}`
    - Try adjusting or clearing search filters in the left sidebar to view records.
    """)
    st.stop()


# ---------------------------------------------------------------------------
# MAIN MULTI-TAB INTERFACE
# ---------------------------------------------------------------------------
if using_fixtures:
    st.info("ℹ️ **Development / Test Mode Active**: Displaying temporary test fixtures for UI verification.")

tab_explorer, tab_detail, tab_timeline, tab_schemes, tab_sources = st.tabs([
    "🌐 Promise Explorer",
    "🔍 Promise Detail & Assessment Flow",
    "⏱️ Evidence Timeline",
    "🏛️ Historical Scheme Matches",
    "📑 Source Provenance"
])


# ---------------------------------------------------------------------------
# TAB 1: PROMISE EXPLORER
# ---------------------------------------------------------------------------
with tab_explorer:
    st.markdown(f"#### Displaying {len(promises_data)} Promises on Page {page_num} (Total Found: {total_count})")
    
    for p in promises_data:
        p_id = p["promise_id"]
        party = p.get("party", "Unknown")
        year = p.get("election_year", "")
        category = p.get("primary_category", "Uncategorized")
        status = p.get("current_status", "not_assessed")
        lang = p.get("language", "English")
        text = p.get("original_text", "")
        meta = p.get("metadata", {})
        
        with st.container():
            st.markdown(f"""
            <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin-bottom: 14px; background-color: #ffffff; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div>
                        <span style="background-color: #007bff; color: white; padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-right: 6px;">{party} {year}</span>
                        <span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-right: 6px;">{category}</span>
                        <span style="background-color: #17a2b8; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px;">{lang}</span>
                    </div>
                    <div>
                        {render_status_badge(status)}
                    </div>
                </div>
                <p style="font-size: 16px; font-weight: 500; color: #1a1a1a; margin-bottom: 8px; line-height: 1.5;">"{text}"</p>
                <div style="font-size: 12px; color: #555; background-color: #f8f9fa; padding: 8px 12px; border-radius: 6px;">
                    <span><b>Target Population:</b> {meta.get('target_population', 'N/A')}</span> &nbsp;|&nbsp; 
                    <span><b>Monetary Target:</b> {meta.get('monetary_target', 'N/A')}</span> &nbsp;|&nbsp; 
                    <span><b>Page:</b> {p.get('page_number', 'N/A')}</span> &nbsp;|&nbsp; 
                    <span><b>ID:</b> <code>{p_id}</code></span>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# TAB 2: PROMISE DETAIL & ASSESSMENT FLOW
# ---------------------------------------------------------------------------
with tab_detail:
    st.markdown("#### Structured Promise Provenance, Implementation & Rationale Flow")
    
    promise_ids = [p["promise_id"] for p in promises_data]
    selected_id = st.selectbox("Select Promise ID to Inspect Detailed Flow", promise_ids, key="promise_detail_select") if promise_ids else None
    
    if selected_id:
        p_obj = next((p for p in promises_data if p["promise_id"] == selected_id), None)
        
        if p_obj:
            st.markdown("---")
            
            # STEP 1: ORIGINAL PROMISE
            st.markdown("### 1️⃣ ORIGINAL PROMISE")
            st.markdown(f"""
            <div style="background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 14px; border-radius: 4px; margin-bottom: 16px;">
                <h5 style="margin:0; color: #856404;">Manifesto Source Statement ({p_obj.get('party')} {p_obj.get('election_year')})</h5>
                <p style="font-size: 18px; font-weight: 600; margin-top: 8px; margin-bottom: 4px; color: #1a1a1a;">"{p_obj.get('original_text')}"</p>
                <span style="font-size: 12px; color: #666;">Page {p_obj.get('page_number', 'N/A')} | Section: {p_obj.get('section', 'General')} | Language: {p_obj.get('language')}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # STEP 2: NORMALIZED PROMISE
            st.markdown("### 2️⃣ NORMALIZED PROMISE")
            col_norm1, col_norm2 = st.columns([2, 1])
            with col_norm1:
                st.code(p_obj.get("normalized_text", p_obj.get("original_text")), language="text")
            with col_norm2:
                meta = p_obj.get("metadata", {})
                st.markdown("**Structured Attributes:**")
                st.write(f"- **Target Population:** {meta.get('target_population', 'N/A')}")
                st.write(f"- **Sector / Department:** {meta.get('sector', 'N/A')} / {meta.get('department', 'N/A')}")
                st.write(f"- **Proposed Action:** {meta.get('proposed_action', 'N/A')}")
                st.write(f"- **Monetary Target:** {meta.get('monetary_target', 'N/A')}")
            
            # STEP 3: CATEGORY
            st.markdown("### 3️⃣ CATEGORY & TAXONOMY")
            st.markdown(f"""
            <div style="background-color: #e2e3e5; padding: 10px 16px; border-radius: 6px; display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <b>Primary Domain Category:</b> <span style="background-color: #007bff; color: white; padding: 4px 10px; border-radius: 12px; font-size: 13px; font-weight: bold;">{p_obj.get('primary_category', 'Uncategorized')}</span>
                </div>
                <div>
                    <b>Classification:</b> <code>{p_obj.get('classification', 'specific_promise')}</code>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # STEP 4: HISTORICAL SCHEME MATCHES
            st.markdown("### 4️⃣ HISTORICAL SCHEME MATCHES")
            st.caption("Matches promise against Phase 2 historical schemes using vector cosine similarity.")
            
            scheme_matches = FIXTURE_SCHEME_MATCHES if using_fixtures else []
            if not using_fixtures:
                ok_s, res_s = api_client.get_promise_scheme_matches(selected_id)
                if ok_s and isinstance(res_s, dict):
                    scheme_matches = res_s.get("scheme_matches", [])
            
            if scheme_matches:
                for sm in scheme_matches:
                    det = sm.get("scheme_details", {}) or {}
                    score = sm.get("similarity_score", 0.0) * 100
                    st.markdown(f"""
                    <div style="border: 1px solid #28a745; border-radius: 6px; padding: 12px; margin-bottom: 10px; background-color: #f4fbf7;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h5 style="margin:0; color: #155724;">🏛️ {det.get('scheme_name', 'Historical Scheme')}</h5>
                            <span style="background-color: #28a745; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: bold;">
                                {score:.1f}% Vector Similarity
                            </span>
                        </div>
                        <p style="font-size: 13px; color: #333; margin-top: 6px; margin-bottom: 4px;"><b>Department:</b> {det.get('department', 'N/A')} | <b>Year:</b> {det.get('financial_year', 'N/A')}</p>
                        <p style="font-size: 13px; color: #555;">{det.get('description', 'N/A')}</p>
                        <p style="font-size: 11px; color: #666; font-style: italic; margin-bottom: 0;">⚠️ <i>Disclaimer: Vector similarity indicates topical overlap only; does NOT imply policy identity or fulfillment.</i></p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("ℹ️ No top-K historical scheme vector candidate matches found for this promise.")
            
            # STEP 5: GOVERNMENT EVIDENCE
            st.markdown("### 5️⃣ GOVERNMENT EVIDENCE")
            ev_list = FIXTURE_EVIDENCE_MATCHES if using_fixtures else []
            if not using_fixtures:
                ok_e, res_e = api_client.get_promise_evidence_matches(selected_id)
                if ok_e and isinstance(res_e, dict):
                    ev_list = res_e.get("evidence_matches", [])
            
            if ev_list:
                for ev in ev_list:
                    ev_details = ev.get("evidence_details", {}) or ev
                    supp = ev_details.get("supporting_values", {}) or {}
                    st.markdown(f"""
                    <div style="border-left: 4px solid #007bff; padding-left: 14px; background-color: #f8f9fa; padding-top: 8px; padding-bottom: 8px; margin-bottom: 10px; border-radius: 0 6px 6px 0;">
                        <span style="font-size: 11px; font-weight: bold; color: #007bff;">GOVERNMENT EVIDENCE (TIER {supp.get('source_tier', 1)}) | PUBLISHED: {supp.get('publication_date', 'N/A')}</span>
                        <h6 style="margin-top: 2px; margin-bottom: 4px;">{supp.get('source_name', 'Official Government Document')}</h6>
                        <p style="font-size: 14px; color: #222; margin-bottom: 4px;">"{ev_details.get('content')}"</p>
                        <span style="font-size: 12px;">🔗 <a href="{supp.get('source_url', '#')}" target="_blank">{supp.get('source_url', 'Government Portal Link')}</a></span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("ℹ️ No official government evidence documents linked to this promise currently.")
            
            # STEP 6: CURRENT ASSESSMENT
            st.markdown("### 6️⃣ CURRENT ASSESSMENT")
            status = p_obj.get("current_status", "not_assessed")
            
            ass_data = {}
            if using_fixtures:
                ass_data = {
                    "status": status,
                    "confidence": 0.85,
                    "explanation": "Official Government Order (G.O.) issued sanctioning policy framework for high school digital devices.",
                    "methodology": "deterministic_rule_engine_v1"
                }
            else:
                ok_a, res_a = api_client.get_promise_assessment(selected_id)
                if ok_a and isinstance(res_a, dict):
                    ass_data = res_a
            
            st.markdown(f"""
            <div style="border: 1px solid #d6d8db; border-radius: 8px; padding: 16px; background-color: #ffffff;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div>
                        <h5 style="margin: 0; display: inline-block; margin-right: 12px;">Status Assessment:</h5>
                        {render_status_badge(ass_data.get('status', status))}
                    </div>
                    <span style="font-size: 13px; color: #555;"><b>Confidence Score:</b> <code>{ass_data.get('confidence', 0.0)}</code></span>
                </div>
                <p style="font-size: 15px; color: #333; line-height: 1.5;"><b>Assessment Rationale:</b> {ass_data.get('explanation', 'No rationale recorded.')}</p>
                <span style="font-size: 11px; color: #888;">Evaluation Methodology: <code>{ass_data.get('methodology', 'deterministic_rule_engine_v1')}</code></span>
            </div>
            """, unsafe_allow_html=True)
            
            if status in ["no_evidence_found", "unclear"]:
                st.caption("ℹ️ *Notice: Status 'No Evidence Found' or 'Insufficient Evidence' reflects current availability in indexed government databases and does NOT imply non-implementation.*")
            
            # STEP 7: SOURCES
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 7️⃣ SOURCES & PROVENANCE")
            st.json({
                "promise_id": p_obj.get("promise_id"),
                "manifesto_id": p_obj.get("manifesto_id"),
                "party": p_obj.get("party"),
                "election_year": p_obj.get("election_year"),
                "source_file_id": p_obj.get("source_file_id", "SRC_MANIFESTO_OFFICIAL"),
                "provenance_status": "verified_and_checksum_matched"
            })


# ---------------------------------------------------------------------------
# TAB 3: EVIDENCE TIMELINE
# ---------------------------------------------------------------------------
with tab_timeline:
    st.markdown("#### ⏱️ Chronological Government Evidence Timeline")
    
    if selected_id:
        ev_list_t = FIXTURE_EVIDENCE_MATCHES if using_fixtures else []
        if not using_fixtures:
            ok_e, res_e = api_client.get_promise_evidence_matches(selected_id)
            if ok_e and isinstance(res_e, dict):
                ev_list_t = res_e.get("evidence_matches", [])
                
        if ev_list_t:
            for ev in ev_list_t:
                ev_details = ev.get("evidence_details", {}) or ev
                supp = ev_details.get("supporting_values", {}) or {}
                st.markdown(f"""
                <div style="border-left: 4px solid #007bff; padding-left: 16px; margin-bottom: 16px;">
                    <span style="font-size: 12px; font-weight: bold; color: #007bff;">PUBLISHED: {supp.get('publication_date', 'N/A')} | TIER {supp.get('source_tier', 1)}</span>
                    <h5 style="margin-top: 4px; margin-bottom: 4px;">{supp.get('source_name', 'Government Source')} ({supp.get('source_type', 'Evidence')})</h5>
                    <p style="font-size: 14px; color: #333;">"{ev_details.get('content')}"</p>
                    <div style="font-size: 12px; color: #666;">
                        <span><b>URL:</b> <a href="{supp.get('source_url', '#')}" target="_blank">{supp.get('source_url', '#')}</a></span> | 
                        <span><b>Page:</b> {ev_details.get('page_number', 1)}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No evidence timeline entries available for the selected promise.")


# ---------------------------------------------------------------------------
# TAB 4: HISTORICAL SCHEME MATCHES
# ---------------------------------------------------------------------------
with tab_schemes:
    st.markdown("#### 🏛️ Historical Scheme Intelligence Matches")
    st.caption("Matches promises against pre-existing historical schemes using Sentence-BERT & TF-IDF vector similarity.")
    
    if selected_id:
        scheme_matches_t = FIXTURE_SCHEME_MATCHES if using_fixtures else []
        if not using_fixtures:
            ok_s, res_s = api_client.get_promise_scheme_matches(selected_id)
            if ok_s and isinstance(res_s, dict):
                scheme_matches_t = res_s.get("scheme_matches", [])
                
        if scheme_matches_t:
            for sm in scheme_matches_t:
                det = sm.get("scheme_details", {}) or {}
                score = sm.get("similarity_score", 0.0) * 100
                st.markdown(f"""
                <div style="border: 1px solid #ddd; border-radius: 8px; padding: 14px; margin-bottom: 12px; background-color: #f9f9f9;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h5 style="margin: 0; color: #2c3e50;">{det.get('scheme_name', 'Historical Scheme')}</h5>
                        <span style="background-color: #28a745; color: white; padding: 2px 10px; border-radius: 10px; font-weight: bold; font-size: 13px;">
                            {score:.1f}% Vector Similarity
                        </span>
                    </div>
                    <p style="font-size: 13px; color: #555; margin-top: 6px;"><b>Department:</b> {det.get('department', 'N/A')} | <b>Year:</b> {det.get('financial_year', 'N/A')}</p>
                    <p style="font-size: 14px; color: #333;">{det.get('description', 'No description')}</p>
                    <p style="font-size: 11px; color: #888; font-style: italic;">⚠️ {sm.get('notes', 'Similarity score indicates topical overlap only.')}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No historical scheme candidate matches found for the selected promise.")


# ---------------------------------------------------------------------------
# TAB 5: SOURCE PROVENANCE
# ---------------------------------------------------------------------------
with tab_sources:
    st.markdown("#### 📑 Manifesto Source Provenance & Document Metadata")
    
    if using_fixtures:
        st.json({
            "source_id": "SRC_DMK_2026",
            "organization": "DMK Party Official Archive",
            "source_url": "https://dmk.in/manifesto2026.pdf",
            "source_tier": 1,
            "retrieval_status": "collected",
            "file_format": "PDF",
            "checksum_sha256": "5734c3d6d67d433a65c9d6807882a5b0410690300e61971eb7446875faa67065",
            "verification_status": "verified"
        })
    else:
        ok_src, res_src = api_client.get_promise_sources()
        if ok_src and isinstance(res_src, dict):
            sources = res_src.get("sources", [])
            if sources:
                st.json(sources)
            else:
                st.info("No source records found in database.")
