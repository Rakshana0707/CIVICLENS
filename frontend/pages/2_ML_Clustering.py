import streamlit as st
import pandas as pd
import plotly.express as px
from frontend.services.api import api_client

st.set_page_config(page_title="ML Clustering - CivicLens TN", page_icon="dY"b", layout="wide")
st.title("dY"b Budget Clustering & Pattern Discovery")
st.markdown("""
Explore machine learning groups (clusters) within the official budget data. 
**Notice:** Clusters represent mathematical groupings of allocation patterns (variance, budget size, year-over-year changes). 
Visual proximity in the PCA scatter plot denotes mathematical variance similarity. This does NOT imply substantive similarity, political intent, or evidence of wrongdoing.
""")

# Fetch basic metadata for filters
depts_ok, depts_data = api_client.get_budget_departments()
if not depts_ok:
    st.error("Could not load departments. API might be offline.")
    st.stop()
    
# --- Sidebar Controls ---
st.sidebar.header("Configuration")
stage_options = ["budget_estimate", "revised_estimate", "actual_expenditure"]
selected_stage = st.sidebar.selectbox("Target Budget Stage", options=stage_options)

dept_map = {d["name"]: d["id"] for d in depts_data}
dept_options = ["All"] + list(dept_map.keys())
selected_dept_name = st.sidebar.selectbox("Department Filter", options=dept_options)
selected_dept_id = dept_map.get(selected_dept_name) if selected_dept_name != "All" else None

st.sidebar.markdown("---")
algorithm = st.sidebar.radio("Clustering Algorithm", options=["K-Means", "DBSCAN"])

kwargs = {}
if algorithm == "K-Means":
    k = st.sidebar.slider("Number of Clusters (k)", min_value=2, max_value=8, value=3)
    kwargs["k"] = k
elif algorithm == "DBSCAN":
    st.sidebar.markdown("DBSCAN finds density-based clusters and isolated noise points.")
    eps = st.sidebar.slider("Neighborhood Size (eps)", min_value=0.1, max_value=2.0, value=0.5, step=0.1)
    min_samples = st.sidebar.slider("Minimum Samples", min_value=2, max_value=10, value=3)
    kwargs["eps"] = eps
    kwargs["min_samples"] = min_samples

# --- Execute ML ---
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
    st.stop()

# --- Render Results ---
data = response.get("data_points", [])
if not data:
    st.warning("Not enough valid data points found for clustering (minimum 2 required).")
    st.stop()

df = pd.DataFrame(data)
summaries = response.get("summaries", {})
variance = response.get("explained_variance", {})

# Clean up cluster labels for display
if algo_key == "dbscan":
    df["Cluster Label"] = df["cluster"].apply(lambda x: "Noise (Isolated)" if x == -1 else f"Cluster {x}")
else:
    df["Cluster Label"] = df["cluster"].apply(lambda x: f"Cluster {x}")

# 1. PCA Scatter Plot
st.subheader("2D PCA Projection")
st.caption(f"**Explained Variance**: PC1 captures {variance['explained_variance_ratio'][0]*100:.1f}%, PC2 captures {variance['explained_variance_ratio'][1]*100:.1f}% of the total pattern variance.")

fig = px.scatter(
    df,
    x="PC1",
    y="PC2",
    color="Cluster Label",
    hover_data=["department", "scheme", "financial_year"],
    title=f"{algorithm} Clusters mapped on Principal Components",
    labels={
        "PC1": "Principal Component 1 (Standardized Variance)",
        "PC2": "Principal Component 2 (Standardized Variance)"
    },
    color_discrete_sequence=px.colors.qualitative.Plotly
)

# Improve visibility of noise points
if algo_key == "dbscan":
    fig.update_traces(marker=dict(size=8, opacity=0.7))
    for i, trace in enumerate(fig.data):
        if trace.name == "Noise (Isolated)":
            trace.marker.color = 'rgba(200, 200, 200, 0.8)' # Distinct grey for noise
            trace.marker.symbol = 'x'

st.plotly_chart(fig, use_container_width=True)

# 2. Cluster Summaries
st.subheader("Cluster Summaries")
st.caption("Average statistics for the raw underlying records in each cluster.")
summary_records = []
for label, stats in summaries.items():
    # label might be int for kmeans, or string for dbscan depending on backend format
    display_label = f"Cluster {label}" if isinstance(label, int) else label
    summary_records.append({
        "Group": display_label,
        "Record Count": stats["count"],
        "Avg Budget Estimate": f"{stats['mean_be_amount']:,.2f}",
        "Median Allocation Share": f"{stats['median_allocation_share']*100:.2f}%",
        "Avg YoY Change": f"{stats['mean_yoy_change_be']*100:.2f}%" if stats['mean_yoy_change_be'] is not None else "N/A",
        "Avg Actual vs BE": f"{stats['mean_actual_vs_be_diff']*100:.2f}%" if stats['mean_actual_vs_be_diff'] is not None else "N/A"
    })

summary_df = pd.DataFrame(summary_records)
st.dataframe(summary_df, use_container_width=True, hide_index=True)

# 3. Data Explorer
with st.expander("Explore Clustered Data Points"):
    st.dataframe(df[["department", "scheme", "financial_year", "Cluster Label", "PC1", "PC2"]], use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("dY"i The dimensionality reduction (PCA) assumes zero-mean and unit-variance scaling. It strictly separates identifiers from mathematical variables.")
