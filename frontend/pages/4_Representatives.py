"""
CIVICLENS TN — Representatives & Constituency Performance Dashboard.

Provides interactive public accountability views:
1. Representative Explorer (Filter by Type, Party, Constituency, Term).
2. Representative Profile (Details, Terms, Aliases, Metadata).
3. Constituency Profile (Demographics, Geographic Mappings, Current MP/MLA).
4. Legislative Activity (Questions, Debates, Sittings Adjustment, Attendance).
5. Constituency Works Tracker (MPLADS / MLACDS status, expenditure, attribution).
6. Development Trends (Census & district indicator trajectory with non-causality caveats).
7. Promise & Evidence Tracker (6-tier fulfillment progression from Phase 3 & 6.7).
8. Comparative Analysis (Within-cohort percentile ranks & transparent sensitivity analysis).
9. Source & Data Quality View (Data completeness audit & document provenance).
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List

from frontend.services.api import api_client

st.set_page_config(
    page_title="Representatives & Constituencies - CIVICLENS TN",
    page_icon="🏛️",
    layout="wide"
)

# Header & Legal Caveats
st.title("🏛️ Representative Performance & Constituency Development")
st.caption(
    "Open, auditable track record analysis of Members of Legislative Assembly (MLAs) and Members of Parliament (MPs) "
    "grounded exclusively in official gazettes, Sansad records, and public data."
)

with st.expander("ℹ️ Methodological & Anti-Defamation Notice", expanded=False):
    st.markdown("""
    - **No Evaluative Ranking:** CIVICLENS does not classify representatives with subjective labels (*"good"*, *"bad"*, *"corrupt"*).
    - **Missing Data Isolation:** Absence of online gazetted registers (e.g., daily MLA attendance in TN Assembly) is recorded under a **Data Completeness Index** rather than penalizing representative scores.
    - **Cohort Isolation:** Lok Sabha MPs and TN MLAs are never compared directly using raw counts due to differing constitutional remits and sitting baselines.
    - **Multi-Causality:** Constituency development trends reflect macroeconomic and departmental policies and cannot be attributed solely to the sitting legislator.
    """)

# Navigation Tabs across views
tabs = st.tabs([
    "🔍 1. Explorer",
    "👤 2. Profile",
    "🗺️ 3. Constituency",
    "📜 4. Legislative",
    "🏗️ 5. Works Tracker",
    "📈 6. Development Trends",
    "🎯 7. Promises & Evidence",
    "⚖️ 8. Comparative Analysis",
    "🛡️ 9. Data Completeness",
    "🔎 10. Evidence & Audit Trail"
])

# -----------------------------------------------------------------------------
# TAB 1: REPRESENTATIVE EXPLORER
# -----------------------------------------------------------------------------
with tabs[0]:
    st.subheader("Representative Explorer")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        search_query = st.text_input("Search Name or ID", placeholder="e.g. Stalin, Kanimozhi...")
    with col2:
        type_filter = st.selectbox("Representative Type", ["All", "MLA", "LOK_SABHA_MP", "RAJYA_SABHA_MP"])
    with col3:
        party_filter = st.text_input("Party Code / ID", placeholder="e.g. PARTY-DMK, AIADMK")
    with col4:
        active_only = st.checkbox("Active Term Only", value=True)

    success, data = api_client.search_representatives(
        q=search_query if search_query else None,
        rep_type=type_filter,
        party_id=party_filter if party_filter else None,
        active_only=active_only
    )

    if success and data.get("representatives"):
        reps = data["representatives"]
        st.success(f"Found {len(reps)} representatives matching criteria.")
        df = pd.DataFrame(reps)
        display_cols = ["representative_id", "official_name", "representative_type", "party_name", "constituency_name", "term_start", "term_end", "is_active"]
        available_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available_cols], use_container_width=True)
    else:
        st.info("No representative records found matching current filters.")

# -----------------------------------------------------------------------------
# TAB 2: REPRESENTATIVE PROFILE
# -----------------------------------------------------------------------------
with tabs[1]:
    st.subheader("Representative Profile")
    rep_id_input = st.text_input("Enter Representative ID", value="REP-MLA-013", key="prof_rep_id")
    if rep_id_input:
        success, prof = api_client.get_representative_profile(rep_id_input.strip())
        if success:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Official Name", prof.get("official_name", "N/A"))
                st.write(f"**Type:** `{prof.get('representative_type')}`")
                st.write(f"**Aliases:** {', '.join(prof.get('aliases', [])) or 'None'}")
            with c2:
                st.metric("Party Affiliation", prof.get("party_name", prof.get("party_id", "Independent")))
                st.write(f"**Constituency:** `{prof.get('constituency_name', 'None / Rajya Sabha')}`")
                st.write(f"**Active Term:** {prof.get('term_start', 'N/A')} to {prof.get('term_end') or 'Present'}")
            with c3:
                comp = prof.get("data_completeness", {})
                st.metric("Data Completeness", f"{int(comp.get('completeness_ratio', 0) * 100)}%")
                st.caption(comp.get("statutory_rule", "Evaluated from public records"))

            st.write("---")
            st.markdown("#### Historical Terms & Tenure")
            terms = prof.get("historical_terms", [])
            if terms:
                st.dataframe(pd.DataFrame(terms), use_container_width=True)
            else:
                st.write("No prior historical terms recorded in the registry.")
        else:
            st.warning(f"Profile for '{rep_id_input}' not found. {prof.get('message', '')}")

# -----------------------------------------------------------------------------
# TAB 3: CONSTITUENCY PROFILE
# -----------------------------------------------------------------------------
with tabs[2]:
    st.subheader("Constituency Profile & Delimitation")
    const_id_input = st.text_input("Constituency ID", value="AC-013", key="const_prof_id")
    if const_id_input:
        success, cdata = api_client.get_constituency_profile(const_id_input.strip())
        if success:
            cc1, cc2 = st.columns(2)
            with cc1:
                st.metric("Constituency Name", cdata.get("official_name"))
                st.write(f"**District:** {cdata.get('district')}, {cdata.get('state')}")
                st.write(f"**Constituency Type:** `{cdata.get('constituency_type')}`")
                st.write(f"**Reservation Status:** `{cdata.get('reservation_status')}`")
            with cc2:
                curr_rep = cdata.get("current_representative")
                if curr_rep:
                    st.metric("Sitting Representative", curr_rep.get("official_name"))
                    st.write(f"**Party:** {curr_rep.get('party_name')}")
                    st.write(f"**ID:** `{curr_rep.get('representative_id')}`")
                else:
                    st.info("No sitting representative currently mapped.")

            st.write("---")
            st.markdown("#### Geographic Mappings & Taluk Distribution")
            mappings = cdata.get("geographic_mappings", [])
            if mappings:
                st.dataframe(pd.DataFrame(mappings), use_container_width=True)
            else:
                st.write("No localized taluk mappings found.")
        else:
            st.warning(f"Constituency '{const_id_input}' not found.")

# -----------------------------------------------------------------------------
# TAB 4: LEGISLATIVE ACTIVITY
# -----------------------------------------------------------------------------
with tabs[3]:
    st.subheader("Legislative Activity Analysis")
    lcol1, lcol2 = st.columns([2, 1])
    with lcol1:
        leg_rep_id = st.text_input("Representative ID", value="REP-MLA-013", key="leg_rep_id")
    with lcol2:
        leg_period = st.selectbox("Reporting Period", ["2021-2026", "2019-2024", "2016-2021"])

    if leg_rep_id:
        success, leg_data = api_client.get_representative_legislative_activity(leg_rep_id.strip(), period=leg_period)
        if success:
            summary = leg_data.get("summary_metrics", {})
            raw = summary.get("raw_metrics", {})
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Questions Asked", raw.get("total_questions", 0))
            m2.metric("Questions / Sitting", raw.get("questions_per_sitting", 0.0))
            m3.metric("Debates Participated", raw.get("total_debates", 0))
            att_val = raw.get("attendance_percentage")
            m4.metric("Attendance %", f"{att_val}%" if att_val is not None else "Not Gazetted")

            st.caption("ℹ️ *Attendance for TN Assembly members is not published online per legislative convention.*")

            records = leg_data.get("activity_records", [])
            if records:
                st.markdown("#### Granular Activity Log")
                st.dataframe(pd.DataFrame(records), use_container_width=True)
            else:
                st.info("No granular activity records logged for this representative.")
        else:
            st.warning(f"Could not load legislative records: {leg_data.get('message', '')}")

# -----------------------------------------------------------------------------
# TAB 5: CONSTITUENCY WORKS TRACKER
# -----------------------------------------------------------------------------
with tabs[4]:
    st.subheader("Constituency Works & Local Development Projects")
    wcol1, wcol2, wcol3 = st.columns(3)
    with wcol1:
        w_const_id = st.text_input("Constituency ID", value="AC-013", key="works_const_id")
    with wcol2:
        w_status = st.selectbox("Project Status", ["All", "PROPOSED", "SANCTIONED", "WORK_IN_PROGRESS", "REPORTED_COMPLETED", "INDEPENDENTLY_VERIFIED_COMPLETED"])
    with wcol3:
        w_attribution = st.selectbox("Attribution Type", ["All", "REPRESENTATIVE_SPONSORED", "EXECUTIVE_STATE_PROJECT", "EXECUTIVE_CENTRAL_PROJECT"])

    success, works_data = api_client.get_constituency_works(
        constituency_id=w_const_id if w_const_id else None,
        status=w_status if w_status != "All" else None,
        attribution=w_attribution if w_attribution != "All" else None
    )

    if success:
        fin_sum = works_data.get("financial_summary", {}).get("raw_metrics", {})
        if fin_sum:
            f1, f2, f3, f4 = st.columns(4)
            f1.metric("Sanctioned (INR)", f"₹{fin_sum.get('total_sanctioned_inr', 0):,.0f}")
            f2.metric("Released (INR)", f"₹{fin_sum.get('total_released_inr', 0):,.0f}")
            f3.metric("Reported Expenditure", f"₹{fin_sum.get('total_expended_inr', 0):,.0f}")
            f4.metric("Utilization Ratio", f"{fin_sum.get('expenditure_to_release_ratio_pct', 0)}%")

        works_list = works_data.get("works", [])
        if works_list:
            st.dataframe(pd.DataFrame(works_list), use_container_width=True)
        else:
            st.info("No works recorded for this constituency matching filters.")
    else:
        st.warning(f"Failed to fetch works: {works_data.get('message', '')}")

# -----------------------------------------------------------------------------
# TAB 6: DEVELOPMENT TRENDS
# -----------------------------------------------------------------------------
with tabs[5]:
    st.subheader("Socioeconomic & Demographic Development Indicators")
    dcol1, dcol2 = st.columns(2)
    with dcol1:
        dev_unit_id = st.text_input("Geographic Unit (e.g. AC-013)", value="AC-013", key="dev_unit_id")
    with dcol2:
        dev_ind_name = st.selectbox("Indicator Code", ["All", "LITERACY_RATE", "INFANT_MORTALITY_RATE", "DIGITAL_CLASSROOM_COVERAGE_PCT"])

    success, dev_data = api_client.get_development_indicators(
        unit_id=dev_unit_id if dev_unit_id else None,
        indicator_name=dev_ind_name if dev_ind_name != "All" else None
    )

    if success:
        trend = dev_data.get("trend_analysis")
        if trend and trend.get("status") != "INSUFFICIENT_OBSERVATIONS":
            t1, t2, t3 = st.columns(3)
            t1.metric("Baseline Value", f"{trend.get('baseline_value')} {trend.get('unit')}", f"Period: {trend.get('baseline_period')}")
            t2.metric("Current Value", f"{trend.get('current_value')} {trend.get('unit')}", f"Period: {trend.get('current_period')}")
            t3.metric("Change (Delta)", f"{trend.get('absolute_delta')} ({trend.get('percentage_change')}%)")

            with st.expander("⚠️ Non-Causality & Data Caveats", expanded=True):
                for cav in trend.get("caveats", []):
                    st.write(f"- {cav}")

        inds = dev_data.get("indicators", [])
        if inds:
            st.dataframe(pd.DataFrame(inds), use_container_width=True)
        else:
            st.info("No indicators found for this unit.")
    else:
        st.warning("Could not load indicators.")

# -----------------------------------------------------------------------------
# TAB 7: PROMISES & EVIDENCE TRACKER
# -----------------------------------------------------------------------------
with tabs[6]:
    st.subheader("Manifesto Promises & Public Performance Linkage")
    p_rep_id = st.text_input("Representative ID", value="REP-MLA-013", key="prom_rep_id")
    if p_rep_id:
        success, pdata = api_client.get_representative_promises(p_rep_id.strip())
        if success:
            scorecard = pdata.get("scorecard", {})
            st.metric("Total Mapped Promises", scorecard.get("total_linked_promises", 0))

            stages = scorecard.get("stage_breakdown", {})
            if stages:
                st.write("**Evidence Stage Breakdown:**")
                st.bar_chart(pd.DataFrame.from_dict(stages, orient="index", columns=["Count"]))

            links = pdata.get("linked_promises", [])
            if links:
                st.markdown("#### Linked Commitments & Empirical Proof")
                st.dataframe(pd.DataFrame(links), use_container_width=True)
            else:
                st.info("No manifesto promise links mapped for this representative.")
        else:
            st.warning(f"Could not load promise linkages: {pdata.get('message', '')}")

# -----------------------------------------------------------------------------
# TAB 8: COMPARATIVE ANALYSIS
# -----------------------------------------------------------------------------
with tabs[7]:
    st.subheader("Within-Cohort Comparative Analysis & Transparent Composite Index")
    st.markdown("Compare representatives **strictly within the same institutional cohort**.")

    comp_reps = st.text_input("Representative IDs (comma separated)", value="REP-MLA-013, REP-MLA-014", key="comp_reps_input")
    cohort_type = st.selectbox("Cohort Type", ["TN_ASSEMBLY_MLA", "LOK_SABHA_MP"])

    if st.button("Run Cohort Comparison"):
        rep_list = [r.strip() for r in comp_reps.split(",") if r.strip()]
        if len(rep_list) >= 2:
            success, cmp_data = api_client.compare_representatives(rep_list, cohort_type=cohort_type)
            if success:
                st.success("Cohort comparison calculated successfully.")
                res_df = pd.DataFrame(cmp_data.get("comparisons", []))
                st.dataframe(res_df, use_container_width=True)
            else:
                st.error(f"Comparison Error: {cmp_data.get('message', '')}")
        else:
            st.warning("Please specify at least 2 representative IDs.")

    st.write("---")
    st.markdown("#### Transparent Composite Score & Sensitivity Analysis")
    comp_single_rep = st.text_input("Representative ID for Composite Audit", value="REP-MLA-013", key="composite_single_rep")
    if comp_single_rep:
        success, comp_res = api_client.get_transparent_composite(comp_single_rep.strip())
        if success and comp_res.get("composite_score") is not None:
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Composite Score (0-100)", f"{comp_res.get('composite_score')}")
                st.write("**Component Scores:**", comp_res.get("component_scores", {}))
                st.write("**Applied Weights:**", comp_res.get("applied_weights", {}))
            with c2:
                st.write("**Sensitivity Analysis (±20% Weight Perturbation):**")
                st.json(comp_res.get("sensitivity_analysis", {}))

            st.caption(f"🛡️ **Fairness Rule:** {comp_res.get('anti_pejorative_disclaimer')}")
        else:
            st.info("Composite score could not be calculated (no observed records).")

# -----------------------------------------------------------------------------
# TAB 9: DATA COMPLETENESS & PROVENANCE
# -----------------------------------------------------------------------------
with tabs[8]:
    st.subheader("Data Completeness Index & Statutory Provenance")
    st.markdown("""
    CIVICLENS tracks **public administration transparency**.
    Representatives from regions with fewer gazetted records are never penalized algorithmically.
    """)
    audit_rep = st.text_input("Representative ID", value="REP-MLA-013", key="audit_rep_id")
    if audit_rep:
        success, audit_res = api_client.get_data_completeness(audit_rep.strip())
        if success:
            st.metric("Overall Completeness Ratio", f"{int(audit_res.get('completeness_ratio', 0) * 100)}%")
            st.write("**Domain Public Record Availability:**")
            st.json(audit_res.get("dimension_availability", {}))
            st.info(f"📜 **Statutory Mandate:** {audit_res.get('statutory_rule')}")
        else:
            st.warning("Could not retrieve completeness index.")

# -----------------------------------------------------------------------------
# TAB 10: EVIDENCE TRACEABILITY & AUDIT TRAIL (PHASE 6.11)
# -----------------------------------------------------------------------------
with tabs[9]:
    st.subheader("🔎 End-to-End Evidence Traceability & Audit Trail")
    st.markdown("""
    Every fact, metric, project status, and indicator is traceable to its verified source document,
    specific page/table, or mathematical calculation formula.
    """)

    sub_t1, sub_t2, sub_t3, sub_t4 = st.tabs([
        "📄 Source Documents",
        "🔗 Fact Evidence Citations",
        "🧮 Metric Lineage Drill-down",
        "⚖️ Conflicting Evidence & Audit"
    ])

    with sub_t1:
        st.markdown("#### Canonical Source Document Registry")
        pub_filter = st.selectbox("Filter by Publisher", ["All", "ECI", "Sansad", "PRS India", "Census India", "DES TN", "CAG"])
        success, docs_data = api_client.get_source_documents(publisher=pub_filter if pub_filter != "All" else None)
        if success and docs_data.get("documents"):
            df_docs = pd.DataFrame(docs_data["documents"])
            st.dataframe(df_docs, use_container_width=True)
        else:
            st.info("No source documents found.")

    with sub_t2:
        st.markdown("#### Granular Fact-to-Evidence Citations")
        ec1, ec2 = st.columns(2)
        with ec1:
            e_type = st.selectbox("Entity Type", ["REPRESENTATIVE", "LEGISLATIVE_ACTIVITY", "CONSTITUENCY_WORK", "DEVELOPMENT_INDICATOR"])
        with ec2:
            e_id = st.text_input("Entity / Record ID", value="REP-MP-17-PERAMBALUR", key="trace_e_id")

        if e_id:
            success, ev_data = api_client.get_entity_evidence(entity_type=e_type, entity_id=e_id.strip())
            if success and ev_data.get("evidence_links"):
                st.success(f"Found {len(ev_data['evidence_links'])} verified source citations.")
                for ev in ev_data["evidence_links"]:
                    with st.expander(f"📌 Citation: {ev.get('fact_description')} (Doc: {ev.get('document_id')})", expanded=True):
                        st.write(f"**Document Title:** {ev.get('document_title')}")
                        st.write(f"**Publisher:** {ev.get('publisher')}")
                        if ev.get("source_url"):
                            st.write(f"**Official Source URL:** [{ev.get('source_url')}]({ev.get('source_url')})")
                        else:
                            st.caption("Official URL: Local gazette or offline physical archive")
                        st.write(f"**Page / Section / Table:** Page {ev.get('page_number', 'N/A')} | {ev.get('section_or_table', 'N/A')}")
                        st.info(f"**Supporting Excerpt / Citation:** \"{ev.get('supporting_excerpt', 'No excerpt provided')}\"")
                        st.caption(f"Verification: {ev.get('verification_status')} | Extraction: {ev.get('extraction_method')}")
            else:
                st.info("No explicit source links found for this entity.")

    with sub_t3:
        st.markdown("#### Mathematical Metric Lineage & Voucher Drill-Down")
        metric_input = st.text_input("Performance Metric ID", value="MET-EXPENDITURE-PC-TN-04", key="trace_metric_id")
        if metric_input:
            success, lin_data = api_client.get_metric_lineage(metric_input.strip())
            if success:
                st.success(f"Lineage loaded for metric: {lin_data.get('metric_name')}")
                st.metric("Reported / Calculated Value", f"{lin_data.get('metric_value')}")
                st.write(f"**Calculation Method:** `{lin_data.get('calculation_method')}`")
                st.code(f"Formula: {lin_data.get('formula_expression')}", language="text")
                st.write(f"**Reporting Period:** {lin_data.get('reporting_period')} | **Geographic Level:** {lin_data.get('geographic_level')}")

                constituents = lin_data.get("constituent_input_records", [])
                if constituents:
                    st.write("---")
                    st.markdown("##### Underlying Input Records (Vouchers)")
                    st.dataframe(pd.DataFrame(constituents), use_container_width=True)
                else:
                    st.caption("No individual vouchers linked.")
            else:
                st.info(f"No metric lineage persisted for '{metric_input}'.")

    with sub_t4:
        st.markdown("#### Conflicting Evidence & Audit Trail Ledger")
        st.write("**Preserved Discrepant Reports (No Silent Overwrites):**")
        success, conf_data = api_client.get_conflicting_evidence()
        if success and conf_data.get("conflicts"):
            for cf in conf_data["conflicts"]:
                with st.expander(f"⚠️ Discrepancy: {cf.get('conflict_topic')} ({cf.get('entity_id')})", expanded=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**Source A:**")
                        st.json(cf.get("source_a", {}))
                    with c2:
                        st.markdown("**Source B:**")
                        st.json(cf.get("source_b", {}))
                    st.warning(f"**Discrepancy:** {cf.get('discrepancy_magnitude')}")
                    st.info(f"**Resolution Basis:** {cf.get('resolution_basis')}")
        else:
            st.info("No conflicting evidence currently logged.")

        st.write("---")
        st.markdown("##### Immutable Audit Trail Ledger")
        success, aud_data = api_client.get_audit_trail(limit=10)
        if success and aud_data.get("audit_events"):
            st.dataframe(pd.DataFrame(aud_data["audit_events"]), use_container_width=True)
        else:
            st.caption("Audit trail log empty.")

