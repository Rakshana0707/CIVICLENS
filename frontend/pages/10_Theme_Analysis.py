import streamlit as st
import pandas as pd
from frontend.services.api import api_client

st.set_page_config(page_title="Theme Analysis", page_icon="??", layout="wide")

st.title("?? Historical Scheme Theme Analysis")
st.markdown("Unsupervised Machine Learning clustering of historical schemes based on semantic similarity.")

st.info("?? **Limitations:** Themes are generated statistically via unsupervised learning (KMeans over Sentence Embeddings). They indicate topical textual overlap and carry no implied political intent. Themes may combine completely different legal mechanisms into one cluster simply because they target the same sector.")

st.sidebar.header("Clustering Parameters")

d_ok, depts = api_client.get_budget_departments()
dept_options = [{"id": 0, "name": "All"}] + (depts if d_ok else [])
selected_dept_name = st.sidebar.selectbox("Filter Department", [d["name"] for d in dept_options])
selected_dept_id = next((d["id"] for d in dept_options if d["name"] == selected_dept_name), 0)

n_clusters = st.sidebar.slider("Number of Themes (K)", min_value=2, max_value=15, value=5)

analyze_btn = st.sidebar.button("Generate Themes", type="primary")

if analyze_btn:
    with st.spinner(f"Clustering schemes into {n_clusters} themes..."):
        success, data = api_client.analyze_scheme_themes(n_clusters=n_clusters, department_id=selected_dept_id)
        
        if success:
            st.success(f"Successfully analyzed {data.get('total_schemes_analyzed', 0)} schemes.")
            
            themes = data.get("themes", [])
            for theme in themes:
                with st.expander(theme.get("theme_name"), expanded=True):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown("**Top Keywords (TF-IDF):**")
                        st.write(", ".join(theme.get("keywords", [])))
                        
                        st.markdown("**Representative Schemes:**")
                        reps = theme.get("representative_schemes", [])
                        if reps:
                            for rep in reps:
                                st.markdown(f"- **{rep.get('scheme_name')}** ({rep.get('financial_year')}) - {rep.get('department')}")
                        else:
                            st.markdown("*None*")
                            
                    with col2:
                        st.metric("Total Schemes in Theme", theme.get("scheme_count"))
                        st.markdown("**Documented Categories in Theme:**")
                        cats = theme.get("documented_categories", {})
                        if cats:
                            cat_df = pd.DataFrame(list(cats.items()), columns=["Category", "Count"]).sort_values("Count", ascending=False)
                            st.dataframe(cat_df, hide_index=True, use_container_width=True)
                        else:
                            st.markdown("*None*")
        else:
            st.error("Failed to generate themes. " + data.get("message", ""))
else:
    st.markdown("Configure parameters in the sidebar and click **Generate Themes** to start the unsupervised learning pipeline.")
