import streamlit as st
import pandas as pd
import plotly.express as px
from frontend.services.api import api_client

st.set_page_config(page_title="Budget Insights - CivicLens TN", layout="wide")
st.title(" Budget Insights & Pattern Discovery")
st.markdown("""
Explore machine learning groups (clusters) and statistical anomalies within the official budget data. 
**Notice:** Models identify *mathematical deviations* (variance, budget size, year-over-year changes). 
These outputs DO NOT imply substantive similarity, political intent, evidence of wrongdoing, or factual conclusions about political actors.
""")

# Fetch basic metadata for filters
depts_ok, depts_data = api_client.get_budget_departments()
if not depts_ok:
    st.error("Could not load departments. API might be offline.")
    st.stop()
    
# --- Sidebar Controls ---
st.sidebar.header("Data Filters")
stage_options = ["budget_estimate", "revised_estimate", "actual_expenditure"]
selected_stage = st.sidebar.selectbox("Target Budget Stage", options=stage_options)

dept_map = {d["name"]: d["id"] for d in depts_data}
dept_options = ["All"] + list(dept_map.keys())
selected_dept_name = st.sidebar.selectbox("Department Filter", options=dept_options)
selected_dept_id = dept_map.get(selected_dept_name) if selected_dept_name != "All" else None

tab1, tab2 = st.tabs([" Clustering Analysis", " Anomaly Detection"])

with tab1:
    st.subheader("Clustering Configuration")
    algorithm = st.radio("Clustering Algorithm", options=["K-Means", "DBSCAN"], horizontal=True)

    kwargs = {}
    if algorithm == "K-Means":
        k = st.slider("Number of Clusters (k)", min_value=2, max_value=8, value=3)
        kwargs["k"] = k
    elif algorithm == "DBSCAN":
        st.markdown("DBSCAN finds density-based clusters and isolated noise points.")
        col1, col2 = st.columns(2)
        eps = col1.slider("Neighborhood Size (eps)", min_value=0.1, max_value=2.0, value=0.5, step=0.1)
        min_samples = col2.slider("Minimum Samples", min_value=2, max_value=10, value=3)
        kwargs["eps"] = eps
        kwargs["min_samples"] = min_samples

    if st.button("Run Clustering"):
        with st.spinner(f"Running {algorithm} and Principal Component Analysis..."):
            algo_key = "kmeans" if algorithm == "K-Means" else "dbscan"
            success, response = api_client.get_ml_clustering(
                budget_stage=selected_stage, 
                algorithm=algo_key, 
                department_id=selected_dept_id,
                **kwargs
            )
            
        if not success:
            st.error("Failed to run clustering pipeline.")
            st.write(response.get("message", "Unknown error"))
        else:
            data = response.get("data_points", [])
            if not data:
                st.warning("Not enough valid data points found for clustering (minimum 2 required).")
            else:
                df = pd.DataFrame(data)
                summaries = response.get("summaries", {})
                variance = response.get("explained_variance", {})

                if algo_key == "dbscan":
                    df["Cluster Label"] = df["cluster"].apply(lambda x: "Noise (Isolated)" if x == -1 else f"Cluster {x}")
                else:
                    df["Cluster Label"] = df["cluster"].apply(lambda x: f"Cluster {x}")

                # PCA Scatter Plot
                st.markdown(f"**Explained Variance**: PC1 captures {variance['explained_variance_ratio'][0]*100:.1f}%, PC2 captures {variance['explained_variance_ratio'][1]*100:.1f}% of the total pattern variance.")
                
                fig = px.scatter(
                    df, x="PC1", y="PC2", color="Cluster Label",
                    hover_data=["department", "scheme", "financial_year"],
                    title=f"{algorithm} Clusters mapped on Principal Components",
                    labels={"PC1": "Principal Component 1 (Variance)", "PC2": "Principal Component 2 (Variance)"},
                    color_discrete_sequence=px.colors.qualitative.Plotly
                )
                
                if algo_key == "dbscan":
                    fig.update_traces(marker=dict(size=8, opacity=0.7))
                    for i, trace in enumerate(fig.data):
                        if trace.name == "Noise (Isolated)":
                            trace.marker.color = 'rgba(200, 200, 200, 0.8)' 
                            trace.marker.symbol = 'x'
                            
                st.plotly_chart(fig, use_container_width=True)

                # Cluster Summaries
                st.markdown("#### Cluster Summaries")
                summary_records = []
                for label, stats in summaries.items():
                    display_label = f"Cluster {label}" if isinstance(label, int) else label
                    summary_records.append({
                        "Group": display_label,
                        "Record Count": stats["count"],
                        "Avg Budget Estimate": f"{stats['mean_be_amount']:,.2f}",
                        "Median Allocation Share": f"{stats['median_allocation_share']*100:.2f}%",
                        "Avg YoY Change": f"{stats['mean_yoy_change_be']*100:.2f}%" if stats['mean_yoy_change_be'] is not None else "N/A",
                        "Avg Actual vs BE": f"{stats['mean_actual_vs_be_diff']*100:.2f}%" if stats['mean_actual_vs_be_diff'] is not None else "N/A"
                    })

                st.dataframe(pd.DataFrame(summary_records), use_container_width=True, hide_index=True)

                with st.expander("Explore Clustered Data Points & Sources"):
                    display_cols = ["department", "scheme", "financial_year", "Cluster Label", "PC1", "PC2", "source_documents"]
                    available_cols = [c for c in display_cols if c in df.columns]
                    st.dataframe(df[available_cols], use_container_width=True, hide_index=True)


with tab2:
    st.subheader("Isolation Forest Anomaly Detection")
    st.markdown("""
    Use Isolation Forests to surface statistically unusual allocations (e.g., massive one-off distributions or unexpected YoY drops).
    *Anomalies highlight structural deviance, not policy violations.*
    """)
    
    contamination_input = st.text_input("Contamination (e.g., 'auto', '0.05', '0.1')", value="auto")
    
    if st.button("Run Anomaly Detection"):
        with st.spinner("Running Isolation Forest..."):
            success, response = api_client.get_ml_anomaly(
                budget_stage=selected_stage, 
                contamination=contamination_input, 
                department_id=selected_dept_id
            )
            
        if not success:
            st.error("Failed to run anomaly detection.")
            st.write(response.get("message", "Unknown error"))
        else:
            data = response.get("data_points", [])
            flagged = response.get("flagged_summary", [])
            meta = response.get("metadata", {})
            
            if not data:
                st.warning("Not enough valid data points found (minimum 2 required).")
            else:
                st.success(f"Analysis complete. Evaluated {meta['total_analyzed']} records. Flagged {meta['total_anomalies']} anomalies.")
                
                if flagged:
                    st.markdown("#### Flagged Anomalies")
                    flagged_df = pd.DataFrame(flagged)
                    
                    # Format numbers for better readability
                    if "be_amount" in flagged_df.columns:
                        flagged_df["be_amount"] = flagged_df["be_amount"].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "N/A")
                    if "allocation_share" in flagged_df.columns:
                        flagged_df["allocation_share"] = flagged_df["allocation_share"].apply(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "N/A")
                    if "yoy_change_be" in flagged_df.columns:
                        flagged_df["yoy_change_be"] = flagged_df["yoy_change_be"].apply(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "N/A")
                    
                    display_cols = ["department", "scheme", "financial_year", "anomaly_score", "be_amount", "allocation_share", "yoy_change_be", "source_documents"]
                    available_cols = [c for c in display_cols if c in flagged_df.columns]
                    st.dataframe(flagged_df[available_cols], use_container_width=True, hide_index=True)
                else:
                    st.info("No anomalies were flagged under the current configuration.")
                    
                with st.expander("View All Scores (Including Normal)"):
                    df = pd.DataFrame(data)
                    display_cols = ["department", "scheme", "financial_year", "is_anomaly", "anomaly_score", "source_documents"]
                    available_cols = [c for c in display_cols if c in df.columns]
                    st.dataframe(df[available_cols], use_container_width=True, hide_index=True)
