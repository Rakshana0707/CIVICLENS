import streamlit as st
import pandas as pd
from frontend.services.api import api_client

st.set_page_config(page_title="Budget & Schemes - CivicLens TN", page_icon="dY"%", layout="wide")
st.title("dY"% Budget & Scheme Explorer")
st.markdown("Explore official Tamil Nadu budget allocations, historical scheme intelligence, and actual expenditures.")

# --- Sidebar Filters ---
st.sidebar.header("Filters")

# Fetch metadata
years_ok, years_data = api_client.get_budget_years()
depts_ok, depts_data = api_client.get_budget_departments()

if not years_ok or not depts_ok:
    st.error("Failed to load filter data from backend. Please ensure the API is running.")
    st.stop()

# Build filter options
year_options = ["All"] + years_data
selected_year = st.sidebar.selectbox("Financial Year", options=year_options)

# Departments
dept_map = {d["name"]: d["id"] for d in depts_data}
dept_options = ["All"] + list(dept_map.keys())
selected_dept_name = st.sidebar.selectbox("Department", options=dept_options)
selected_dept_id = dept_map.get(selected_dept_name) if selected_dept_name != "All" else None

# Schemes (depends on department)
schemes_ok, schemes_data = api_client.get_budget_schemes(department_id=selected_dept_id)
if schemes_ok:
    scheme_map = {s["name"]: s["id"] for s in schemes_data}
    scheme_options = ["All"] + list(scheme_map.keys())
    selected_scheme_name = st.sidebar.selectbox("Scheme", options=scheme_options)
    selected_scheme_id = scheme_map.get(selected_scheme_name) if selected_scheme_name != "All" else None
else:
    selected_scheme_id = None
    st.sidebar.warning("Could not load schemes.")

# Stage
stage_options = ["All", "budget_estimate", "revised_estimate", "actual_expenditure"]
selected_stage = st.sidebar.selectbox("Budget Stage", options=stage_options)

# --- Data Fetching ---
filters = {}
if selected_year != "All":
    filters["financial_year"] = selected_year
if selected_dept_id is not None:
    filters["department_id"] = selected_dept_id
if selected_scheme_id is not None:
    filters["scheme_id"] = selected_scheme_id
if selected_stage != "All":
    filters["budget_stage"] = selected_stage

# Pagination state
if 'budget_skip' not in st.session_state:
    st.session_state.budget_skip = 0

LIMIT = 50

# Reset pagination if filters change (naive approach for Streamlit)
if 'last_filters' not in st.session_state or st.session_state.last_filters != filters:
    st.session_state.budget_skip = 0
    st.session_state.last_filters = filters.copy()

with st.spinner("Fetching budget records..."):
    records_ok, response_data = api_client.get_budget_records(skip=st.session_state.budget_skip, limit=LIMIT, filters=filters)

if not records_ok:
    st.error("Failed to load budget records.")
    if "message" in response_data:
        st.error(f"Details: {response_data['message']}")
    st.stop()

records = response_data.get("records", [])
total_count = response_data.get("total_count", 0)

# --- Main Content ---
if total_count == 0:
    st.info("dY"" No budget records found for the selected filters. The database might be empty or your filters are too restrictive.")
else:
    st.write(f"**Showing {min(len(records), LIMIT)} of {total_count} records.**")
    
    # Transform for DataFrame
    df = pd.DataFrame(records)
    
    # Reorder and rename columns for display
    display_df = df[[
        "financial_year", 
        "department_name", 
        "scheme_name", 
        "budget_stage", 
        "amount", 
        "currency_unit", 
        "source_document_title"
    ]].copy()
    
    display_df.columns = [
        "Financial Year", 
        "Department", 
        "Scheme", 
        "Stage", 
        "Amount", 
        "Unit", 
        "Source Document"
    ]
    
    # Format amount
    display_df["Amount"] = display_df["Amount"].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "N/A")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # --- Pagination Controls ---
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.session_state.budget_skip > 0:
            if st.button("dY"  Previous"):
                st.session_state.budget_skip -= LIMIT
                st.rerun()
                
    with col2:
        current_page = (st.session_state.budget_skip // LIMIT) + 1
        total_pages = (total_count + LIMIT - 1) // LIMIT
        st.markdown(f"<div style='text-align: center;'>Page {current_page} of {total_pages}</div>", unsafe_allow_html=True)
        
    with col3:
        if st.session_state.budget_skip + LIMIT < total_count:
            if st.button("Next dY" "):
                st.session_state.budget_skip += LIMIT
                st.rerun()

    # --- Year-Wise Analysis ---
    st.markdown("---")
    st.subheader("dY"^ Year-Wise Analysis")
    
    if selected_stage == "All":
        st.info("dY"i Please select a specific **Budget Stage** (e.g., 'budget_estimate') from the sidebar to view year-over-year trends. Mixing different budget stages in a single trend line is invalid and unsupported.")
    else:
        with st.spinner("Calculating trends..."):
            trend_ok, trend_data = api_client.get_budget_trend(
                budget_stage=selected_stage,
                department_id=selected_dept_id,
                scheme_id=selected_scheme_id
            )
            
        if trend_ok and trend_data:
            st.markdown(f"**Stage:** `{selected_stage}` | **Coverage:** {min(trend_data.keys())} to {max(trend_data.keys())}")
            
            # Prepare data for chart
            trend_records = []
            for y, stats in trend_data.items():
                trend_records.append({
                    "Financial Year": y,
                    "Total Amount": stats["total"],
                    "Percentage Change": stats["percentage_change"]
                })
            
            trend_df = pd.DataFrame(trend_records)
            
            # Show chart
            st.bar_chart(data=trend_df, x="Financial Year", y="Total Amount", use_container_width=True)
            
            # Show descriptive data
            st.dataframe(
                trend_df.style.format({
                    "Total Amount": "{:,.2f}",
                    "Percentage Change": "{:,.2f}%"
                }, na_rep="N/A"),
                use_container_width=True,
                hide_index=True
            )
            
            # Disclaimers
            st.caption("dY"i **Note:** Missing years indicate no matching official data was found. We do not interpolate or fabricate missing years. Percentage changes reflect nominal values and are not adjusted for inflation. Descriptive comparisons do not imply causation.")
        else:
            st.warning("Not enough data to calculate year-over-year trends for this selection.")

    # --- Scheme-Level Analysis ---
    if selected_scheme_id is None:
        st.markdown("---")
        st.subheader("dY"i Scheme-Level Trend Comparison")
        if selected_stage == "All":
             st.info("dY"i Please select a specific **Budget Stage** to compare scheme allocations over time.")
        else:
            with st.spinner("Fetching scheme trends..."):
                sch_trend_ok, sch_trend_data = api_client.get_scheme_trends(
                    budget_stage=selected_stage,
                    department_id=selected_dept_id
                )
            if sch_trend_ok and sch_trend_data:
                st.markdown(f"**Stage:** `{selected_stage}`")
                
                # Transform data for line chart
                chart_data = {}
                scheme_meta = []
                for s_name, data in sch_trend_data.items():
                    scheme_meta.append({
                        "Scheme": s_name, 
                        "Available Stages in Records": ", ".join(data["available_stages"])
                    })
                    for year, stats in data["yearly_trend"].items():
                        if year not in chart_data:
                            chart_data[year] = {}
                        chart_data[year][s_name] = stats["total"]
                
                if chart_data:
                    trend_chart_df = pd.DataFrame.from_dict(chart_data, orient="index")
                    trend_chart_df.index.name = "Financial Year"
                    
                    st.line_chart(trend_chart_df, use_container_width=True)
                    
                    with st.expander("View Scheme Metadata"):
                        st.dataframe(pd.DataFrame(scheme_meta), hide_index=True, use_container_width=True)
                        st.caption("Notice: We rely on documented mappings to match scheme name aliases safely. Uncertain matches are ignored to preserve data integrity. We do not infer implementation success from allocation changes.")
                else:
                    st.warning("No scheme-level trend data available for this selection.")

st.markdown("---")
st.caption("dY"i CivicLens TN ensures transparency by providing source traceability for all data points. See 'Source Document' for exact origins.")
