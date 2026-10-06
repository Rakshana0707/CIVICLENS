import streamlit as st
import pandas as pd
from datetime import datetime
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
# STATUS STYLING HELPER
# ---------------------------------------------------------------------------
STATUS_COLORS = {
    "implemented": "#28a745",
    "partially_implemented": "#17a2b8",
    "policy_action": "#007bff",
    "announced": "#ffc107",
    "no_evidence_found": "#fd7e14",
    "not_assessed": "#6c757d",
    "unclear": "#6f42c1",
    "disputed": "#dc3545"
}

def render_status_badge(status_str: str):
    color = STATUS_COLORS.get(status_str, "#6c757d")
    label = status_str.replace("_", " ").title()
    return f'<span style="background-color: {color}; color: white; padding: 4px 12px; border-radius: 14px; font-size: 13px; font-weight: bold;">{label}</span>'


# ---------------------------------------------------------------------------
# MAIN LAYOUT & HEADER
# ---------------------------------------------------------------------------
st.title("📜 Political Promise Tracker")
st.markdown("### Tamil Nadu Election Manifestos vs Evidence-Based Implementation Tracking")

# Sidebar Controls
st.sidebar.header("🛠️ Development & Filters")
dev_mode = st.sidebar.toggle("🧪 Development / Test Mode (Fixture Data)", value=False)

st.sidebar.subheader("Filter Promises")
filter_election = st.sidebar.selectbox("Election Year", ["All", 2026, 2021])
filter_party = st.sidebar.selectbox("Party", ["All", "DMK", "AIADMK", "TVK"])
filter_category = st.sidebar.selectbox("Category", [
    "All", "Education", "Healthcare", "Agriculture", "Employment", "Welfare", 
    "Women", "Youth", "Infrastructure", "Transport", "Housing", "Environment", "Industry", "Governance"
])
filter_status = st.sidebar.selectbox("Implementation Status", [
    "All", "not_assessed", "no_evidence_found", "announced", "policy_action", 
    "partially_implemented", "implemented", "unclear", "disputed"
])
search_kw = st.sidebar.text_input("🔍 Search Keyword")


# ---------------------------------------------------------------------------
# DATA FETCHING (API vs Fixture Mode)
# ---------------------------------------------------------------------------
promises_data = []
total_count = 0
using_fixtures = False

if dev_mode:
    using_fixtures = True
    promises_data = FIXTURE_PROMISES
    # Filter fixtures
    if filter_election != "All":
        promises_data = [p for p in promises_data if p["election_year"] == filter_election]
    if filter_party != "All":
        promises_data = [p for p in promises_data if p["party"] == filter_party]
    if filter_category != "All":
        promises_data = [p for p in promises_data if p["primary_category"] == filter_category]
    if filter_status != "All":
        promises_data = [p for p in promises_data if p["current_status"] == filter_status]
    if search_kw:
        promises_data = [p for p in promises_data if search_kw.lower() in p["original_text"].lower()]
    total_count = len(promises_data)
else:
    # Query Real API
    success, api_res = api_client.get_promises(
        party=filter_party,
        year=filter_election,
        category=filter_category,
        status=filter_status,
        search=search_kw
    )
    if success and isinstance(api_res, dict):
        promises_data = api_res.get("items", [])
        total_count = api_res.get("total", 0)


# ---------------------------------------------------------------------------
# EMPTY STATE HANDLING REQUIREMENT
# ---------------------------------------------------------------------------
if not promises_data and not dev_mode:
    st.warning("""
    ### ⚠️ No manifesto data has been loaded yet.

    *The Political Promise Tracker pipeline and database infrastructure are fully built and verified.*
    *No official manifesto documents have been collected into the production dataset yet.*

    ---
    **Instructions:**
    - To inspect real pipeline outputs, collect verified manifesto source files into the repository.
    - To explore the interactive UI components now, enable **"🧪 Development / Test Mode (Fixture Data)"** in the left sidebar.
    """)
    st.stop()


# ---------------------------------------------------------------------------
# MAIN MULTI-TAB INTERFACE
# ---------------------------------------------------------------------------
if using_fixtures:
    st.info("ℹ️ **Development / Test Mode Active**: Displaying temporary test fixtures for UI verification.")

tab_explorer, tab_detail, tab_timeline, tab_schemes, tab_sources = st.tabs([
    "🌐 Promise Explorer",
    "🔍 Promise Detail & Assessment",
    "⏱️ Evidence Timeline",
    "🏛️ Historical Scheme Matches",
    "📑 Source Viewer"
])

# ---------------------------------------------------------------------------
# TAB 1: PROMISE EXPLORER
# ---------------------------------------------------------------------------
with tab_explorer:
    st.markdown(f"#### Displaying {len(promises_data)} Promises (Total Found: {total_count})")
    
    for p in promises_data:
        p_id = p["promise_id"]
        party = p.get("party", "Unknown")
        year = p.get("election_year", "")
        category = p.get("primary_category", "Uncategorized")
        status = p.get("current_status", "not_assessed")
        text = p.get("original_text", "")
        meta = p.get("metadata", {})
        
        with st.container():
            st.markdown(f"""
            <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin-bottom: 14px; background-color: #ffffff;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div>
                        <span style="background-color: #007bff; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-right: 6px;">{party} {year}</span>
                        <span style="background-color: #6c757d; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">{category}</span>
                    </div>
                    <div>
                        {render_status_badge(status)}
                    </div>
                </div>
                <p style="font-size: 16px; font-weight: 500; color: #1a1a1a; margin-bottom: 8px;">"{text}"</p>
                <div style="font-size: 12px; color: #666;">
                    <span><b>Target Population:</b> {meta.get('target_population', 'N/A')}</span> | 
                    <span><b>Monetary Target:</b> {meta.get('monetary_target', 'N/A')}</span> | 
                    <span><b>ID:</b> <code>{p_id}</code></span>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# TAB 2: PROMISE DETAIL & ASSESSMENT
# ---------------------------------------------------------------------------
with tab_detail:
    st.markdown("#### Detailed Promise Inspection & Assessment Rationale")
    
    promise_ids = [p["promise_id"] for p in promises_data]
    selected_id = st.selectbox("Select Promise to Inspect", promise_ids) if promise_ids else None
    
    if selected_id:
        p_obj = next((p for p in promises_data if p["promise_id"] == selected_id), None)
        
        if p_obj:
            col_a, col_b = st.columns([2, 1])
            
            with col_a:
                st.markdown("##### 📌 Original Promise Text")
                st.info(f'"{p_obj.get("original_text")}"')
                
                st.markdown("##### 🔤 Normalized Promise Text")
                st.code(p_obj.get("normalized_text"))
                
                st.markdown("##### 📊 Extracted Metadata Attributes")
                meta = p_obj.get("metadata", {})
                st.json(meta)
                
            with col_b:
                st.markdown("##### 🎯 Current Implementation Status")
                status = p_obj.get("current_status", "not_assessed")
                st.markdown(render_status_badge(status), unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("##### 🔬 Assessment Rationale")
                
                # Fetch detailed assessment
                if using_fixtures:
                    st.write("**Confidence Score:** `0.85`")
                    st.write("**Explanation:** Official Government Order (G.O.) issued sanctioning policy framework for high school digital devices.")
                    st.write("**Methodology:** `deterministic_rule_engine_v1`")
                else:
                    ok_a, res_a = api_client.get_promise_assessment(selected_id)
                    if ok_a and isinstance(res_a, dict):
                        st.write(f"**Confidence Score:** `{res_a.get('confidence', 0.0)}`")
                        st.write(f"**Explanation:** {res_a.get('explanation')}")
                        st.write(f"**Methodology:** `{res_a.get('methodology')}`")


# ---------------------------------------------------------------------------
# TAB 3: EVIDENCE TIMELINE
# ---------------------------------------------------------------------------
with tab_timeline:
    st.markdown("#### ⏱️ Chronological Implementation Evidence Timeline")
    
    ev_list = FIXTURE_EVIDENCE_MATCHES if using_fixtures else []
    if not using_fixtures and selected_id:
        ok_e, res_e = api_client.get_promise_evidence_matches(selected_id)
        if ok_e and isinstance(res_e, dict):
            ev_list = res_e.get("evidence_matches", [])
            
    if ev_list:
        for ev in ev_list:
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
        st.write("No evidence timeline entries available for the selected promise.")


# ---------------------------------------------------------------------------
# TAB 4: HISTORICAL SCHEME MATCHES
# ---------------------------------------------------------------------------
with tab_schemes:
    st.markdown("#### 🏛️ Phase 2 Historical Scheme Intelligence Matches")
    st.caption("Matches promises against pre-existing historical schemes using Sentence-BERT vector similarity.")
    
    scheme_matches = FIXTURE_SCHEME_MATCHES if using_fixtures else []
    if not using_fixtures and selected_id:
        ok_s, res_s = api_client.get_promise_scheme_matches(selected_id)
        if ok_s and isinstance(res_s, dict):
            scheme_matches = res_s.get("scheme_matches", [])
            
    if scheme_matches:
        for sm in scheme_matches:
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
        st.write("No historical scheme matches found for the selected promise.")


# ---------------------------------------------------------------------------
# TAB 5: SOURCE VIEWER
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
                st.write("No source records found in database.")
