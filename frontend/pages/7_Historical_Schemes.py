import streamlit as st
import pandas as pd
from frontend.services.api import api_client

st.set_page_config(page_title="Historical Scheme Explorer", page_icon="??", layout="wide")

st.title("?? Historical Scheme Explorer")
st.markdown("Search and explore the history of Tamil Nadu government schemes across multiple financial years.")

# State initialization
if "selected_scheme_id" not in st.session_state:
    st.session_state.selected_scheme_id = None

# Detail View
if st.session_state.selected_scheme_id:
    if st.button("? Back to Search"):
        st.session_state.selected_scheme_id = None
        st.rerun()

    scheme_id = st.session_state.selected_scheme_id
    success, scheme_data = api_client.get_scheme(scheme_id)
    
    if not success:
        st.error(scheme_data.get("message", "Failed to load scheme details."))
    else:
        # Load associated data
        h_success, history = api_client.get_scheme_history(scheme_id)
        s_success, sources = api_client.get_scheme_sources(scheme_id)
        
        # Display Scheme Header
        st.header(scheme_data.get("scheme_name", "Unknown Scheme"))
        
        # Resolve department name
        d_ok, depts = api_client.get_budget_departments()
        dept_name = "Unknown Department"
        if d_ok:
            dept_name = next((d["name"] for d in depts if d["id"] == scheme_data.get("department_id")), "Unknown Department")
        
        st.caption(f"Financial Year: {scheme_data.get('financial_year')} | Department: {dept_name}")
        
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
            
        with col2:
            st.subheader("Source Documents")
            if s_success and sources:
                for src in sources:
                    with st.expander(f"?? {src.get('document_title') or src.get('manifest_dataset_id') or 'Unknown Document'}"):
                        st.markdown(f"**Page:** {src.get('source_page_number') or 'N/A'}")
                        if src.get('extracted_text_snippet'):
                            st.text_area("Snippet", src.get('extracted_text_snippet'), height=150, disabled=True)
            else:
                st.info("No source documents linked.")
                
            st.subheader("Historical Timeline")
            if h_success and history:
                # Sort by year ascending or descending
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
                
        # Budget info placeholder to fulfill constraint
        st.subheader("Budget Information")
        st.info("Detailed historical allocation graphs and Phase 1 budget link will be integrated in future steps.")

else:
    # --- Search View ---
    with st.sidebar:
        st.header("Filters")
        
        # Fetch options
        y_ok, years = api_client.get_budget_years()
        year_options = ["All"] + (years if y_ok else [])
        
        d_ok, depts = api_client.get_budget_departments()
        dept_options = [{"id": 0, "name": "All"}] + (depts if d_ok else [])
        dept_names = [d["name"] for d in dept_options]
        
        c_ok, cats = api_client.get_scheme_categories()
        cat_options = [{"id": 0, "name": "All"}] + (cats if c_ok else [])
        cat_names = [c["name"] for c in cat_options]
        
        # Controls
        search_query = st.text_input("Search scheme name or description")
        selected_year = st.selectbox("Financial Year", year_options)
        selected_dept_name = st.selectbox("Department", dept_names)
        selected_cat_name = st.selectbox("Category", cat_names)
        
        # Map back to IDs
        selected_dept_id = next((d["id"] for d in dept_options if d["name"] == selected_dept_name), 0)
        selected_cat_id = next((c["id"] for c in cat_options if c["name"] == selected_cat_name), 0)
        
        search_btn = st.button("Search", type="primary", use_container_width=True)

    # Automatically search on load or on button press
    success, results = api_client.search_schemes(
        name=search_query,
        year=selected_year,
        department_id=selected_dept_id,
        category_id=selected_cat_id,
        limit=50
    )
    
    if success:
        total = results.get("total", 0)
        items = results.get("items", [])
        
        st.markdown(f"**Found {total} schemes**")
        
        if items:
            for item in items:
                with st.container(border=True):
                    col_title, col_action = st.columns([4, 1])
                    with col_title:
                        st.subheader(item.get("scheme_name"))
                        d_name = next((d["name"] for d in dept_options if d["id"] == item.get("department_id")), "Unknown Dept")
                        st.caption(f"{item.get('financial_year')} | {d_name}")
                        desc = item.get("description")
                        if desc:
                            st.write(desc[:200] + "..." if len(desc) > 200 else desc)
                    with col_action:
                        if st.button("View Details", key=f"view_{item.get('id')}"):
                            st.session_state.selected_scheme_id = item.get('id')
                            st.rerun()
        else:
            st.info("No schemes match your criteria.")
    else:
        st.error("Failed to load schemes from the server.")
