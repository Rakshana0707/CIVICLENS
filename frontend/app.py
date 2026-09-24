import streamlit as st

from frontend.services.api import api_client

st.set_page_config(
    page_title="CivicLens TN",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🔍 CivicLens TN")
st.subheader("AI-Powered Public Accountability & Policy Intelligence for Tamil Nadu")

# Check backend status with a loading state
with st.spinner("Connecting to CivicLens Backend..."):
    is_healthy, health_data = api_client.get_health()

if is_healthy:
    st.success("✅ Connected to Backend API securely.")
else:
    error_msg = health_data.get("message", "Unknown error")
    st.error(f"❌ Backend API is currently unreachable. Some features may not work. (Error: {error_msg})")

st.markdown("""
Welcome to **CivicLens TN**. This platform aims to enhance transparency and understanding of political processes, policy implementations, and civic issues in Tamil Nadu through AI-driven insights.

### Available Modules
The platform is currently under active development. Below is the status of our core analytical modules.
""")

col1, col2, col3 = st.columns(3)

def create_module_card(col, title, description, is_implemented=False):
    status_color = "#28a745" if is_implemented else "#6c757d"
    status_text = "Active" if is_implemented else "Coming Soon"
    
    col.markdown(f"""
    <div style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin-bottom: 20px; background-color: #f8f9fa; color: #333;">
        <h4 style="margin-top: 0;">{title}</h4>
        <p style="font-size: 14px; color: #555;">{description}</p>
        <span style="background-color: {status_color}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: bold;">
            {status_text}
        </span>
    </div>
    """, unsafe_allow_html=True)

with col1:
    create_module_card(col1, "Budget & Schemes", "Analyze state budget allocations and historical scheme intelligence.")
    create_module_card(col1, "Representatives", "Track and evaluate the performance of elected representatives.")

with col2:
    create_module_card(col2, "Political Promises", "Monitor election manifestos and fulfillment of political promises.")
    create_module_card(col2, "Political Funding", "Explore political funding and financial transparency data.")

with col3:
    create_module_card(col3, "Tamil News", "AI-driven framing analysis and topic modeling on Tamil news media.")
    create_module_card(col3, "Claim Verification", "Automated evidence extraction and explainable claim verification.")

st.info("👈 Use the sidebar navigation to explore the different modules as they become available.")
