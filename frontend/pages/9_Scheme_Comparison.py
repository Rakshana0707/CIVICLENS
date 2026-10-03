import streamlit as st
import pandas as pd
from frontend.services.api import api_client

st.set_page_config(page_title="Scheme Comparison", page_icon="??", layout="wide")

st.title("?? Historical Scheme Comparison")
st.markdown("Compare historically related schemes side by side.")

st.info("?? **Similarity score represents semantic similarity between the text representations. It does not mean that the schemes are identical or legally equivalent.**")

# Sidebar for Selection
st.sidebar.header("Select Schemes to Compare")
d_ok, depts = api_client.get_budget_departments()
dept_options = [{"id": 0, "name": "All"}] + (depts if d_ok else [])
selected_dept_name = st.sidebar.selectbox("Filter Department for Selection", [d["name"] for d in dept_options])
selected_dept_id = next((d["id"] for d in dept_options if d["name"] == selected_dept_name), 0)

s_ok, p2_schemes = api_client.search_schemes(department_id=selected_dept_id, limit=200)
scheme_map = {}
if s_ok and p2_schemes.get("items"):
    for s in p2_schemes["items"]:
        label = f"{s['scheme_name']} ({s['financial_year']})"
        scheme_map[label] = s['id']
        
selected_labels = st.sidebar.multiselect("Select Schemes (at least 2)", list(scheme_map.keys()), max_selections=4)

if len(selected_labels) >= 2:
    selected_ids = [scheme_map[label] for label in selected_labels]
    success, data = api_client.compare_schemes(selected_ids)
    
    if success:
        schemes = data.get("schemes", [])
        matrix = data.get("similarity_matrix", {})
        
        # Display side-by-side columns
        cols = st.columns(len(schemes))
        
        # Helper to style missing
        def display_field(title, content, is_sourced=True):
            st.markdown(f"**{title}**")
            if content and str(content).strip():
                st.write(content)
                if is_sourced:
                    st.caption("*(Sourced from official document)*")
            else:
                st.markdown("*Not Available*")
                
        for i, (col, scheme) in enumerate(zip(cols, schemes)):
            with col:
                st.subheader(scheme.get("scheme_name"))
                
                # Compare similarity to the first scheme in the selection (Baseline)
                if i > 0:
                    base_id = str(schemes[0]["id"])
                    my_id = str(scheme["id"])
                    # Convert IDs to string for JSON dict lookup
                    score = matrix.get(base_id, {}).get(my_id, 0.0)
                    st.metric(f"Similarity to {schemes[0]['scheme_name'][:15]}...", f"{score:.2f}")
                else:
                    st.metric("Similarity", "Baseline")
                    
                st.divider()
                display_field("Financial Year", scheme.get("financial_year"), is_sourced=False)
                display_field("Department", scheme.get("department"), is_sourced=False)
                display_field("Description", scheme.get("description"))
                display_field("Objectives", scheme.get("objectives"))
                display_field("Target Beneficiaries", scheme.get("target_beneficiaries"))
                
                st.markdown("**Budget Allocation**")
                st.markdown("*Link to Phase 1 financial records pending.*")
                
                st.markdown("**Source Documents**")
                sources = scheme.get("sources", [])
                if sources:
                    for src in sources:
                        st.caption(f"?? {src.get('title')} (Pg {src.get('page')})")
                else:
                    st.markdown("*Not Available*")
    else:
        st.error("Failed to load comparison data. " + data.get("message", ""))
else:
    st.warning("Please select at least two schemes from the sidebar to compare.")

