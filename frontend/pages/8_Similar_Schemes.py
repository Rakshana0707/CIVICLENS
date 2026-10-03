import streamlit as st
import pandas as pd
from frontend.services.api import api_client

st.set_page_config(page_title="Find Similar Schemes", page_icon="??", layout="wide")

st.title("?? Find Similar Historical Schemes")
st.markdown("Discover historically similar schemes using AI-powered semantic similarity.")

st.info("?? **Similarity score represents semantic similarity between the text representations. It does not mean that the schemes are identical or legally equivalent.**")

# Sidebar Filters
with st.sidebar:
    st.header("Search Parameters")
    
    # Input Mode
    search_mode = st.radio("Search by:", ["Existing Scheme", "Custom Text Description"])
    
    st.divider()
    
    st.subheader("Filters")
    y_ok, years = api_client.get_budget_years()
    year_options = ["All"] + (years if y_ok else [])
    selected_year = st.selectbox("Filter by Year", year_options)
    
    d_ok, depts = api_client.get_budget_departments()
    dept_options = [{"id": 0, "name": "All"}] + (depts if d_ok else [])
    selected_dept_name = st.selectbox("Filter by Department", [d["name"] for d in dept_options])
    selected_dept_id = next((d["id"] for d in dept_options if d["name"] == selected_dept_name), 0)
    
    st.divider()
    top_k = st.slider("Max Results", min_value=1, max_value=20, value=5)
    threshold = st.slider("Similarity Threshold", min_value=0.0, max_value=1.0, value=0.3, step=0.05)
    

# Main Content Area
if search_mode == "Custom Text Description":
    query_text = st.text_area("Enter scheme description or keywords:", height=100, placeholder="e.g., Financial assistance for rural students pursuing higher education")
    search_btn = st.button("Search Semantically", type="primary")
    
    if search_btn and query_text:
        with st.spinner("Analyzing semantic overlap..."):
            success, results = api_client.semantic_search_schemes(
                query=query_text, top_k=top_k, threshold=threshold,
                department_id=selected_dept_id, year=selected_year
            )
            
        if success:
            items = results.get("items", [])
            st.success(f"Found {len(items)} similar schemes.")
            
            for item in items:
                with st.container(border=True):
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.subheader(item.get("scheme_name"))
                        st.caption(f"{item.get('financial_year')} | {item.get('department')} | **Score:** {item.get('similarity_score')}")
                        desc = item.get("description", "")
                        st.write(desc[:300] + "..." if len(desc) > 300 else desc)
                        
                        sources = item.get("sources", [])
                        if sources:
                            src_str = ", ".join([f"{s.get('document_title')} (pg {s.get('page_number')})" for s in sources])
                            st.caption(f"?? Sources: {src_str}")
                    with col2:
                        st.metric("Similarity", f"{item.get('similarity_score'):.2f}")
        else:
            st.error("Search failed. " + results.get("message", ""))

elif search_mode == "Existing Scheme":
    st.markdown("Select a department to view available schemes.")
    
    # Needs a scheme picker. We filter by department to avoid huge lists.
    dept_for_picker = st.selectbox("Department (for Scheme Selection)", [d["name"] for d in dept_options if d["name"] != "All"])
    dept_id_picker = next((d["id"] for d in dept_options if d["name"] == dept_for_picker), None)
    
    if dept_id_picker:
        # Fetch schemes for this department (Phase 1 API supports this)
        s_ok, schemes_data = api_client.get_budget_schemes(department_id=dept_id_picker)
        
        # Note: Phase 1 budget schemes vs Phase 2 historical schemes.
        # Since similar search uses Phase 2 IDs, we should search Phase 2 schemes.
        # We can use our search_schemes endpoint from Phase 2.9 to list them.
        p2_ok, p2_schemes = api_client.search_schemes(department_id=dept_id_picker, limit=100)
        
        if p2_ok and p2_schemes.get("items"):
            items = p2_schemes.get("items")
            scheme_map = {f"{s['scheme_name']} ({s['financial_year']})": s['id'] for s in items}
            selected_scheme_label = st.selectbox("Select Historical Scheme", list(scheme_map.keys()))
            selected_scheme_id = scheme_map.get(selected_scheme_label)
            
            search_btn = st.button("Find Similar Schemes", type="primary")
            
            if search_btn and selected_scheme_id:
                with st.spinner("Finding similar schemes..."):
                    success, results = api_client.get_similar_schemes(
                        scheme_id=selected_scheme_id, top_k=top_k, threshold=threshold,
                        department_id=selected_dept_id, year=selected_year
                    )
                    
                if success:
                    sim_items = results.get("items", [])
                    st.success(f"Found {len(sim_items)} similar schemes.")
                    
                    for item in sim_items:
                        with st.container(border=True):
                            col1, col2 = st.columns([5, 1])
                            with col1:
                                st.subheader(item.get("scheme_name"))
                                st.caption(f"{item.get('financial_year')} | {item.get('department')} | **Score:** {item.get('similarity_score')}")
                                desc = item.get("description", "")
                                st.write(desc[:300] + "..." if len(desc) > 300 else desc)
                                
                                sources = item.get("sources", [])
                                if sources:
                                    src_str = ", ".join([f"{s.get('document_title')} (pg {s.get('page_number')})" for s in sources])
                                    st.caption(f"?? Sources: {src_str}")
                            with col2:
                                st.metric("Similarity", f"{item.get('similarity_score'):.2f}")
                else:
                    st.error("Search failed. " + results.get("message", ""))
        else:
            st.warning("No historical schemes found for this department.")
