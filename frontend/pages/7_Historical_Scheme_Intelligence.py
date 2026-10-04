import streamlit as st
import pandas as pd
from frontend.services.api import api_client

st.set_page_config(page_title="Historical Scheme Intelligence", page_icon="???", layout="wide")

st.title("??? Historical Scheme Intelligence")
st.markdown("A unified dashboard for exploring, comparing, and analyzing the semantic history of Tamil Nadu government schemes.")

tab_explore, tab_similar, tab_compare, tab_theme = st.tabs([
    "?? Scheme Explorer & Timeline", 
    "?? Similar Scheme Discovery", 
    "?? Scheme Comparison", 
    "?? Theme Analysis"
])

# --- STATE INITIALIZATION ---
if "selected_scheme_id" not in st.session_state:
    st.session_state.selected_scheme_id = None

# --- GLOBAL FILTERS DATA ---
y_ok, years = api_client.get_budget_years()
year_options = ["All"] + (years if y_ok else [])

d_ok, depts = api_client.get_budget_departments()
dept_options = [{"id": 0, "name": "All"}] + (depts if d_ok else [])
dept_names = [d["name"] for d in dept_options]

c_ok, cats = api_client.get_scheme_categories()
cat_options = [{"id": 0, "name": "All"}] + (cats if c_ok else [])
cat_names = [c["name"] for c in cat_options]

def get_dept_name(d_id):
    return next((d["name"] for d in dept_options if d["id"] == d_id), "Unknown")


# ==========================================
# TAB 1: EXPLORER, TIMELINE & TRACEABILITY
# ==========================================
with tab_explore:
    if st.session_state.selected_scheme_id:
        if st.button("? Back to Search"):
            st.session_state.selected_scheme_id = None
            st.rerun()

        scheme_id = st.session_state.selected_scheme_id
        success, scheme_data = api_client.get_scheme(scheme_id)
        
        if not success:
            st.error(scheme_data.get("message", "Failed to load scheme details."))
        else:
            h_success, history = api_client.get_scheme_history(scheme_id)
            s_success, sources = api_client.get_scheme_sources(scheme_id)
            
            st.header(scheme_data.get("scheme_name", "Unknown Scheme"))
            st.caption(f"Financial Year: {scheme_data.get('financial_year')} | Department: {get_dept_name(scheme_data.get('department_id'))}")
            
            if scheme_data.get("is_uncertain_match"):
                st.warning("?? This scheme has an uncertain match with Phase 1 quantitative data.")
                
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("Description")
                st.write(scheme_data.get("description") or "No description available.")
                st.subheader("Objectives")
                st.write(scheme_data.get("objectives") or "No objectives listed.")
                st.subheader("Target Beneficiaries")
                st.write(scheme_data.get("target_beneficiaries") or "No beneficiaries listed.")
                
                st.subheader("Budget Information")
                st.info("Detailed historical allocation graphs and Phase 1 budget link will be integrated natively in future steps.")
                
            with col2:
                st.subheader("Source Traceability")
                if s_success and sources:
                    for src in sources:
                        with st.expander(f"?? {src.get('document_title') or 'Unknown Document'}"):
                            st.markdown(f"**Page:** {src.get('source_page_number') or 'N/A'}")
                            if src.get('extracted_text_snippet'):
                                st.text_area("Snippet", src.get('extracted_text_snippet'), height=150, disabled=True)
                else:
                    st.info("No source documents linked.")
                    
                st.subheader("Historical Timeline")
                if h_success and history:
                    for entry in history:
                        year = entry.get("financial_year")
                        is_current = " (Current View)" if entry.get("id") == scheme_id else ""
                        st.markdown(f"**{year}**{is_current}")
                        if not is_current:
                            if st.button(f"View {year} version", key=f"hist_{entry.get('id')}"):
                                st.session_state.selected_scheme_id = entry.get('id')
                                st.rerun()
                else:
                    st.info("No historical variations found.")
    else:
        st.subheader("Search & Filter")
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1: search_query = st.text_input("Search term", key="exp_search")
        with col_f2: selected_year = st.selectbox("Financial Year", year_options, key="exp_year")
        with col_f3: selected_dept_name = st.selectbox("Department", dept_names, key="exp_dept")
        with col_f4: selected_cat_name = st.selectbox("Category", cat_names, key="exp_cat")
        
        selected_dept_id = next((d["id"] for d in dept_options if d["name"] == selected_dept_name), 0)
        selected_cat_id = next((c["id"] for c in cat_options if c["name"] == selected_cat_name), 0)
        
        if st.button("Search Schemes", type="primary", key="exp_btn"):
            with st.spinner("Searching..."):
                success, results = api_client.search_schemes(
                    name=search_query, year=selected_year, department_id=selected_dept_id,
                    category_id=selected_cat_id, limit=50
                )
                
                if success:
                    items = results.get("items", [])
                    st.success(f"Found {results.get('total', 0)} schemes.")
                    for item in items:
                        with st.container(border=True):
                            c_title, c_act = st.columns([4, 1])
                            with c_title:
                                st.subheader(item.get("scheme_name"))
                                st.caption(f"{item.get('financial_year')} | {get_dept_name(item.get('department_id'))}")
                                desc = item.get("description")
                                if desc: st.write(desc[:200] + "...")
                            with c_act:
                                if st.button("View Details", key=f"view_{item.get('id')}"):
                                    st.session_state.selected_scheme_id = item.get('id')
                                    st.rerun()
                else:
                    st.error("Search failed.")


# ==========================================
# TAB 2: SIMILAR SCHEME DISCOVERY
# ==========================================
with tab_similar:
    st.info("?? **Model Explanation:** Similarity scores represent mathematical vector overlap in semantic descriptions. High similarity does not prove schemes are legally or politically identical.")
    
    sim_mode = st.radio("Search mode:", ["Custom Text Description", "Existing Scheme"], horizontal=True)
    
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1: s_dept_name = st.selectbox("Filter Department", dept_names, key="sim_dept")
    with col_s2: s_year = st.selectbox("Filter Year", year_options, key="sim_year")
    with col_s3: s_top_k = st.slider("Max Results", 1, 20, 5, key="sim_topk")
    s_dept_id = next((d["id"] for d in dept_options if d["name"] == s_dept_name), 0)
    
    if sim_mode == "Custom Text Description":
        q_text = st.text_area("Enter scheme description:")
        if st.button("Search Semantically", type="primary") and q_text:
            with st.spinner("Analyzing semantic overlap..."):
                ok, res = api_client.semantic_search_schemes(q_text, top_k=s_top_k, department_id=s_dept_id, year=s_year)
                if ok:
                    items = res.get("items", [])
                    st.success(f"Found {len(items)} similar schemes.")
                    for item in items:
                        with st.container(border=True):
                            st.subheader(f"{item.get('scheme_name')} (Score: {item.get('similarity_score'):.2f})")
                            st.caption(f"{item.get('financial_year')} | {item.get('department')}")
                            st.write(item.get("description", ""))
                else:
                    st.error("Search failed.")
    else:
        # Phase 2 schemes loader
        ok_s, s_list = api_client.search_schemes(department_id=s_dept_id, limit=200)
        if ok_s and s_list.get("items"):
            s_map = {f"{x['scheme_name']} ({x['financial_year']})": x['id'] for x in s_list["items"]}
            sel_s = st.selectbox("Select Historical Scheme", list(s_map.keys()))
            if st.button("Find Similar", type="primary"):
                with st.spinner("Finding matches..."):
                    ok, res = api_client.get_similar_schemes(s_map[sel_s], top_k=s_top_k, department_id=s_dept_id, year=s_year)
                    if ok:
                        items = res.get("items", [])
                        st.success(f"Found {len(items)} similar schemes.")
                        for item in items:
                            with st.container(border=True):
                                st.subheader(f"{item.get('scheme_name')} (Score: {item.get('similarity_score'):.2f})")
                                st.caption(f"{item.get('financial_year')} | {item.get('department')}")
                                st.write(item.get("description", ""))
                    else:
                        st.error("Search failed.")
        else:
            st.warning("No schemes found to select. Change filters.")


# ==========================================
# TAB 3: SCHEME COMPARISON
# ==========================================
with tab_compare:
    st.info("?? **Model Explanation:** Side-by-side comparison. Similarity scores represent semantic distance from the first selected scheme.")
    
    c_dept_name = st.selectbox("Filter Department for Selection", dept_names, key="cmp_dept")
    c_dept_id = next((d["id"] for d in dept_options if d["name"] == c_dept_name), 0)
    
    ok_c, c_schemes = api_client.search_schemes(department_id=c_dept_id, limit=200)
    if ok_c and c_schemes.get("items"):
        c_map = {f"{x['scheme_name']} ({x['financial_year']})": x['id'] for x in c_schemes["items"]}
        selections = st.multiselect("Select Schemes to Compare (2-4)", list(c_map.keys()), max_selections=4)
        
        if len(selections) >= 2:
            if st.button("Compare Schemes", type="primary"):
                ids = [c_map[x] for x in selections]
                with st.spinner("Loading comparison matrix..."):
                    ok, data = api_client.compare_schemes(ids)
                    if ok:
                        schemes = data.get("schemes", [])
                        matrix = data.get("similarity_matrix", {})
                        
                        cols = st.columns(len(schemes))
                        for i, (col, scheme) in enumerate(zip(cols, schemes)):
                            with col:
                                st.subheader(scheme.get("scheme_name"))
                                if i > 0:
                                    score = matrix.get(str(schemes[0]["id"]), {}).get(str(scheme["id"]), 0.0)
                                    st.metric("Similarity to Baseline", f"{score:.2f}")
                                else:
                                    st.metric("Similarity", "Baseline")
                                    
                                st.markdown(f"**Year:** {scheme.get('financial_year')}")
                                st.markdown(f"**Department:** {scheme.get('department')}")
                                st.markdown(f"**Description:** {scheme.get('description') or '*Not Available*'}")
                                st.markdown(f"**Objectives:** {scheme.get('objectives') or '*Not Available*'}")
                                st.markdown(f"**Beneficiaries:** {scheme.get('target_beneficiaries') or '*Not Available*'}")
                                st.caption("*(Text Sourced from official documents)*")
                    else:
                        st.error("Comparison failed.")
        else:
            st.warning("Please select at least two schemes.")


# ==========================================
# TAB 4: THEME ANALYSIS
# ==========================================
with tab_theme:
    st.info("?? **Model Explanation:** Unsupervised K-Means clustering over Sentence Embeddings. Themes indicate topical textual overlap and carry no implied political intent.")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1: t_dept_name = st.selectbox("Filter Department", dept_names, key="thm_dept")
    with col_t2: t_k = st.slider("Number of Themes (K)", 2, 15, 5, key="thm_k")
    t_dept_id = next((d["id"] for d in dept_options if d["name"] == t_dept_name), 0)
    
    if st.button("Generate Theme Clusters", type="primary"):
        with st.spinner(f"Running unsupervised clustering for {t_k} themes..."):
            ok, data = api_client.analyze_scheme_themes(n_clusters=t_k, department_id=t_dept_id)
            if ok:
                st.success(f"Analyzed {data.get('total_schemes_analyzed')} schemes.")
                for theme in data.get("themes", []):
                    with st.expander(theme.get("theme_name"), expanded=True):
                        c1, c2 = st.columns([2, 1])
                        with c1:
                            st.markdown("**Top Keywords (TF-IDF):**")
                            st.write(", ".join(theme.get("keywords", [])))
                            st.markdown("**Representative Schemes:**")
                            for rep in theme.get("representative_schemes", []):
                                st.markdown(f"- **{rep.get('scheme_name')}** ({rep.get('financial_year')})")
                        with c2:
                            st.metric("Schemes in Theme", theme.get("scheme_count"))
            else:
                st.error("Failed to generate themes. " + data.get("message", ""))
