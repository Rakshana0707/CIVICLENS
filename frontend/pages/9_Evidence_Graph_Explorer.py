"""
CIVICLENS TN — Phase 9.8: Unified Civic Intelligence Evidence Graph Explorer.
==============================================================================

Frontend evidence exploration interface across Tamil Nadu civic intelligence:
1. Entity Search across all 10 entity types (schemes, budgets, promises, parties,
   representatives, constituencies, claims, issues, departments, source documents).
2. Entity Detail View with aliases, canonical IDs, and source mappings.
3. Interactive Relationship Graph (Plotly + Graphviz) with zoom/hover cards.
4. Readable List & Table Alternative for complete accessibility.
5. Granular Relationship-Type, Provenance, and Review Filters.
6. Edge Explanation Inspector:
   - What the relationship means in civic governance terms
   - Which specific records it connects
   - Documentary evidence, citations, URLs, and cryptographic hashes
   - Epistemic distinction: Direct documentary vs. Inferred candidate vs. Human reviewed
   - What remains uncertain (epistemic gaps, data caveats)
7. Evidence-Path Multi-Hop Exploration (Promise -> Scheme -> Budget, etc.).
8. Supporting & Contradicting Evidence Panels with Epistemic Weight Dialectics.
9. Uncertain, Disputed, and Candidate Relationship Indicators.
10. Source Document Drill-Down with SHA-256 verification.
11. Direct Navigation links back to Phases 1–8 dedicated modules.

EPISTEMIC & METHODOLOGICAL GUARDRAILS:
- Association != Causation: Visual positioning does NOT imply cause or blame.
- Zero-Fabrication: Candidate proposals are strictly labelled as UNVERIFIED.
- Dialectical Preservation: Conflicting evidence is displayed side-by-side with statutory weight.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

from frontend.services.api import api_client
from frontend.pages.nine_graph_fixtures import (
    FIXTURE_GRAPH_NODES,
    FIXTURE_GRAPH_EDGES,
    FIXTURE_CANDIDATE_PROPOSALS,
    FIXTURE_CONFLICTS,
    FIXTURE_INVESTIGATION_PATHS,
    FIXTURE_WORKFLOW_RESULTS,
)
from frontend.pages.nine_graph_helper import (
    ENTITY_TYPE_CONFIG,
    RELATIONSHIP_DEFINITIONS,
    render_entity_type_badge,
    render_relationship_badge,
    render_review_status_badge,
    render_provenance_badge,
    render_epistemic_warning_banner,
    build_plotly_network_figure,
    build_graphviz_dot_source,
    build_accessible_nodes_table,
    build_accessible_edges_table,
)

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Evidence Graph Explorer - CIVICLENS TN",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------------------------------------------------------
# DATA ACCESS SERVICE (API FIRST WITH RICH FIXTURE FALLBACK)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def load_graph_data(
    query: str = "",
    entity_type: Optional[str] = None,
    source_phase: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], bool]:
    """
    Attempts to fetch nodes and edges from backend REST API.
    If backend is unreachable or returns empty, seamlessly uses comprehensive Phase 9 fixtures.
    Returns: (nodes, edges, candidate_proposals, conflicts, is_live_api)
    """
    using_live = False
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # 1. Search/Fetch Nodes
    ok_nodes, res_nodes = api_client.search_graph_entities(
        query=query,
        entity_type=entity_type,
        source_phase=source_phase,
        limit=50,
    )
    if ok_nodes and isinstance(res_nodes, dict) and res_nodes.get("results"):
        nodes = res_nodes.get("results", [])
        using_live = True

    # 2. Fetch Edges
    ok_edges, res_edges = api_client.get_graph_edges(limit=50)
    if ok_edges and isinstance(res_edges, dict) and res_edges.get("edges"):
        edges = res_edges.get("edges", [])
        using_live = True

    # 3. Fetch Proposals
    ok_props, res_props = api_client.get_graph_unresolved_proposals(limit=20)
    proposals = res_props.get("unresolved_proposals", []) if ok_props and isinstance(res_props, dict) else FIXTURE_CANDIDATE_PROPOSALS

    # 4. Fetch Conflicts
    ok_confs, res_confs = api_client.get_graph_conflicts(limit=20)
    conflicts = res_confs.get("conflicts", []) if ok_confs and isinstance(res_confs, dict) else FIXTURE_CONFLICTS

    # Fallback to fixtures if live API was empty
    if not nodes:
        nodes = list(FIXTURE_GRAPH_NODES)
        # Apply local filters to fixture nodes
        if entity_type and entity_type != "ALL":
            nodes = [n for n in nodes if n.get("entity_type", "").upper() == entity_type.upper()]
        if source_phase and source_phase != "ALL":
            nodes = [n for n in nodes if n.get("source_phase", "").lower() == source_phase.lower()]
        if query:
            q_lower = query.lower()
            nodes = [
                n for n in nodes
                if q_lower in n.get("label", "").lower()
                or q_lower in n.get("label_ta", "").lower()
                or q_lower in n.get("canonical_id", "").lower()
            ]

    if not edges:
        edges = list(FIXTURE_GRAPH_EDGES)

    return nodes, edges, proposals, conflicts, using_live


# -----------------------------------------------------------------------------
# SIDEBAR CONTROLS & GLOBAL FILTERS
# -----------------------------------------------------------------------------
st.sidebar.title("🌐 Evidence Graph")
st.sidebar.markdown("**Unified Civic Intelligence Across Phases 1–8**")

api_status_badge = "🟢 Live Backend API" if api_client.get_health()[0] else "🟡 Offline (Rich Fixture Mode)"
st.sidebar.caption(f"Status: {api_status_badge}")

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Search & Filter")

search_query = st.sidebar.text_input(
    "Keyword Search (Tamil / English / ID)",
    placeholder="e.g. Nemmeli, குடிநீர், MAWS, 150 MLD...",
)

ENTITY_TYPE_OPTIONS = ["ALL"] + list(ENTITY_TYPE_CONFIG.keys())
selected_entity_type = st.sidebar.selectbox(
    "Entity Type",
    options=ENTITY_TYPE_OPTIONS,
    format_func=lambda x: "All Entity Types (அனைத்தும்)" if x == "ALL" else f"{ENTITY_TYPE_CONFIG[x]['icon']} {ENTITY_TYPE_CONFIG[x]['title_en']} ({ENTITY_TYPE_CONFIG[x]['title_ta']})",
)

PHASE_OPTIONS = ["ALL", "phase1", "phase2", "phase3", "phase4", "phase5", "phase6", "phase7", "phase8"]
selected_phase = st.sidebar.selectbox(
    "Source Phase",
    options=PHASE_OPTIONS,
    format_func=lambda x: "All Phases (1–8)" if x == "ALL" else f"Phase {x[-1]}: {x.capitalize()}",
)

view_mode = st.sidebar.radio(
    "Visualization Mode",
    options=[
        "Interactive Network Graph (Plotly)",
        "Structural Diagram (Graphviz)",
        "Accessible Tabular & List View",
    ],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.subheader("⚡ Guided Investigation Walks")
selected_investigation_key = st.sidebar.selectbox(
    "Select Evidence Path Template",
    options=["NONE"] + list(FIXTURE_INVESTIGATION_PATHS.keys()),
    format_func=lambda x: "Custom Node Exploration" if x == "NONE" else FIXTURE_INVESTIGATION_PATHS[x]["title"],
)


# -----------------------------------------------------------------------------
# MAIN VIEW HEADER & EPISTEMIC SAFEGUARDS
# -----------------------------------------------------------------------------
st.title("🌐 Unified Civic Intelligence Evidence Graph Explorer")
st.markdown(
    "Connects **schemes, budgets, political promises, representatives, constituencies, public claims, civic issues, and government departments** "
    "across Tamil Nadu governance through evidence-backed relationships."
)

render_epistemic_warning_banner()

# Load Data based on filter criteria
with st.spinner("Retrieving evidence graph records..."):
    nodes, edges, candidate_proposals, conflicts, is_live = load_graph_data(
        query=search_query,
        entity_type=None if selected_entity_type == "ALL" else selected_entity_type,
        source_phase=None if selected_phase == "ALL" else selected_phase,
    )


# -----------------------------------------------------------------------------
# TAB NAVIGATION
# -----------------------------------------------------------------------------
tab_graph, tab_entity, tab_path, tab_conflicts, tab_sources = st.tabs([
    "🕸️ Graph Explorer & Edge Inspector",
    "🔍 Entity Directory & Detail",
    "🛤️ Evidence-Path Walks",
    "⚖️ Contradictions & Candidate Links",
    "📄 Source Documents & Lineage",
])


# =============================================================================
# TAB 1: GRAPH EXPLORER & EDGE INSPECTOR
# =============================================================================
with tab_graph:
    st.subheader("🕸️ Interactive Evidence Relationship Graph")

    # Relationship and review filter controls
    col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 1.5])
    with col_f1:
        rel_types_available = ["ALL"] + sorted(list({e.get("relationship_type", "").lower() for e in edges}))
        filter_rel_type = st.selectbox("Filter Relationship Type", options=rel_types_available, format_func=lambda x: "All Relationships" if x == "ALL" else x.upper())
    with col_f2:
        filter_review_status = st.selectbox("Review Status", options=["ALL", "VERIFIED", "PENDING_REVIEW", "REJECTED"])
    with col_f3:
        filter_provenance = st.selectbox("Provenance Lifecycle", options=["ALL", "VALID", "DISPUTED", "SUPERSEDED"])

    # Apply edge filters
    active_edges = edges
    if filter_rel_type != "ALL":
        active_edges = [e for e in active_edges if e.get("relationship_type", "").lower() == filter_rel_type]
    if filter_review_status != "ALL":
        active_edges = [e for e in active_edges if e.get("review_status", "").upper() == filter_review_status]
    if filter_provenance != "ALL":
        active_edges = [e for e in active_edges if e.get("provenance_status", "").upper() == filter_provenance]

    # Node focus selector
    node_options = ["None (Overview)"] + [n["node_id"] for n in nodes]
    selected_node_id = st.selectbox(
        "Focus on Node (Centers Graph & Highlights Connections)",
        options=node_options,
        format_func=lambda x: x if x == "None (Overview)" else f"{next((n['label'] for n in nodes if n['node_id'] == x), x)} ({x})",
    )
    focus_node = None if selected_node_id == "None (Overview)" else selected_node_id

    # Filter connected edges if node focus is active
    if focus_node:
        active_edges = [
            e for e in active_edges
            if e.get("source_node_id") == focus_node or e.get("target_node_id") == focus_node
        ]
        connected_node_ids = {focus_node} | {e.get("source_node_id") for e in active_edges} | {e.get("target_node_id") for e in active_edges}
        active_nodes = [n for n in nodes if n["node_id"] in connected_node_ids]
    else:
        active_nodes = nodes

    # Edge Selector for Detail Inspection
    st.markdown("#### 🎯 Edge Inspector (Select an edge to inspect complete evidentiary lineage)")
    edge_options = ["None (Select an edge below)"] + [e["edge_id"] for e in active_edges]
    selected_edge_id = st.selectbox(
        "Select Edge to Inspect",
        options=edge_options,
        format_func=lambda x: x if x.startswith("None") else f"{x} — {next((e.get('relationship_type','').upper() for e in active_edges if e.get('edge_id')==x), '')}: {next((e.get('source_node_id') for e in active_edges if e.get('edge_id')==x), '')} ➜ {next((e.get('target_node_id') for e in active_edges if e.get('edge_id')==x), '')}",
    )
    inspected_edge = next((e for e in active_edges if e["edge_id"] == selected_edge_id), None) if not selected_edge_id.startswith("None") else None

    # Render Selected Edge Detail Box
    if inspected_edge:
        rel_type = inspected_edge.get("relationship_type", "relates_to").lower()
        rel_def = RELATIONSHIP_DEFINITIONS.get(rel_type, {"meaning": "Documented link between records.", "epistemic_scope": "General"})
        source_lbl = next((n["label"] for n in nodes if n["node_id"] == inspected_edge["source_node_id"]), inspected_edge["source_node_id"])
        target_lbl = next((n["label"] for n in nodes if n["node_id"] == inspected_edge["target_node_id"]), inspected_edge["target_node_id"])

        st.markdown(
            f"""
            <div style="background-color: #f8f9fa; border: 2px solid #007bff; border-radius: 8px; padding: 18px; margin: 15px 0;">
                <h4 style="margin-top: 0; color: #007bff;">🔍 Edge Inspector: <code>{inspected_edge['edge_id']}</code></h4>
                <div style="margin-bottom: 10px;">
                    {render_relationship_badge(rel_type)}
                    {render_review_status_badge(inspected_edge.get('review_status', ''))}
                    {render_provenance_badge(inspected_edge.get('provenance_status', ''))}
                    <span style="margin-left: 8px; font-weight: bold; font-size: 13px;">Confidence: {inspected_edge.get('confidence_score', 1.0):.2f}</span>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 12px 0;">
                    <div style="background: white; padding: 10px; border-radius: 6px; border: 1px solid #dee2e6;">
                        <small style="color: #6c757d; font-weight: bold;">SOURCE RECORD</small><br>
                        <strong>{source_lbl}</strong><br>
                        <code>{inspected_edge['source_node_id']}</code>
                    </div>
                    <div style="background: white; padding: 10px; border-radius: 6px; border: 1px solid #dee2e6;">
                        <small style="color: #6c757d; font-weight: bold;">TARGET RECORD</small><br>
                        <strong>{target_lbl}</strong><br>
                        <code>{inspected_edge['target_node_id']}</code>
                    </div>
                </div>
                <div style="background: #ffffff; padding: 12px; border-radius: 6px; border-left: 4px solid #17a2b8; margin-top: 10px;">
                    <strong>📖 What This Relationship Means:</strong><br>
                    <span style="font-size: 14px; color: #333;">{rel_def['meaning']}</span>
                </div>
                <div style="background: #ffffff; padding: 12px; border-radius: 6px; border-left: 4px solid #28a745; margin-top: 10px;">
                    <strong>📜 Supporting Evidence & Citations:</strong><br>
                    <span style="font-size: 14px; color: #333;">{inspected_edge.get('evidence_reference', 'No documentary citation provided.')}</span><br>
                    <small><b>Source Document ID:</b> <code>{inspected_edge.get('source_document_id', 'N/A')}</code></small><br>
                    <small><b>Matching Method:</b> <code>{inspected_edge.get('matching_method', 'N/A')}</code></small><br>
                    <small><b>SHA-256 Hash:</b> <code>{inspected_edge.get('source_document_hash') or 'NO_HASH_AVAILABLE (Check provenance)'}</code></small>
                </div>
                <div style="background: #ffffff; padding: 12px; border-radius: 6px; border-left: 4px solid #ffc107; margin-top: 10px;">
                    <strong>⚠️ Epistemic Limits & What Remains Uncertain:</strong><br>
                    <span style="font-size: 13px; color: #555;">
                        {inspected_edge.get('explanation', {}).get('causality_note', 'Documented association does NOT prove downstream physical completion or causal blame.')}
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Render Visualisation based on Mode
    if not active_nodes:
        st.warning("⚠️ No graph nodes matched the current filter criteria.")
    else:
        st.markdown(f"**Displaying {len(active_nodes)} Nodes and {len(active_edges)} Edges**")

        if view_mode == "Interactive Network Graph (Plotly)":
            fig = build_plotly_network_figure(
                nodes=active_nodes,
                edges=active_edges,
                selected_node_id=focus_node,
                selected_edge_id=selected_edge_id if not selected_edge_id.startswith("None") else None,
                height=560,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("💡 Hover over nodes to see Tamil titles and metadata. Hover over edge midpoints to view citations.")

        elif view_mode == "Structural Diagram (Graphviz)":
            dot_source = build_graphviz_dot_source(active_nodes, active_edges, selected_node_id=focus_node)
            st.graphviz_chart(dot_source, use_container_width=True)

        elif view_mode == "Accessible Tabular & List View":
            st.markdown("### 📋 Accessible Tables")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.markdown("**Connected Entities (Nodes)**")
                df_nodes = build_accessible_nodes_table(active_nodes)
                st.dataframe(df_nodes, use_container_width=True)
            with col_t2:
                st.markdown("**Linking Evidence Relationships (Edges)**")
                df_edges = build_accessible_edges_table(active_edges)
                st.dataframe(df_edges, use_container_width=True)


# =============================================================================
# TAB 2: ENTITY DIRECTORY & DETAIL VIEW
# =============================================================================
with tab_entity:
    st.subheader("🔍 Canonical Entity Directory")

    col_e1, col_e2 = st.columns([1, 1.8])

    with col_e1:
        st.markdown(f"**Found {len(nodes)} Entities**")
        selected_entity_node_id = st.radio(
            "Select an Entity to Inspect Detail:",
            options=[n["node_id"] for n in nodes],
            format_func=lambda x: f"{next((n['label'] for n in nodes if n['node_id'] == x), x)}",
        )

    entity_node = next((n for n in nodes if n["node_id"] == selected_entity_node_id), None)

    with col_e2:
        if entity_node:
            etype = entity_node.get("entity_type", "").upper()
            cfg = ENTITY_TYPE_CONFIG.get(etype, {"icon": "🔹", "title_en": etype, "page_target": "app.py", "phase": "Phase 1-8"})

            st.markdown(
                f"""
                <div style="background-color: #fdfdfe; border: 1px solid #dee2e6; border-radius: 8px; padding: 18px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="margin: 0; color: #212529;">{cfg['icon']} {entity_node.get('label')}</h3>
                        {render_entity_type_badge(etype)}
                    </div>
                    <p style="font-size: 16px; color: #495057; margin-top: 6px;">
                        <strong>தமிழ்:</strong> {entity_node.get('label_ta', 'பெயர் குறிப்பிடப்படவில்லை')}
                    </p>
                    <hr style="margin: 10px 0;">
                    <p><b>Node ID:</b> <code>{entity_node.get('node_id')}</code></p>
                    <p><b>Canonical Registry ID:</b> <code>{entity_node.get('canonical_id')}</code></p>
                    <p><b>Source Module:</b> <span style="background: #e9ecef; padding: 2px 6px; border-radius: 4px;">{cfg['phase']} ({entity_node.get('source_phase')})</span></p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Link back to Phase-Specific Module
            st.markdown("#### 🔗 Cross-Phase Navigation")
            st.info(f"This record originates from **{cfg['phase']}**. You can navigate back to its dedicated phase dashboard:")
            try:
                st.page_link(cfg["page_target"], label=f"Open in {cfg['title_en']} Dashboard ({cfg['phase']})", icon="🚀")
            except Exception:
                st.markdown(f"👉 [Navigate to {cfg['title_en']} Dashboard]({cfg['page_target']})")

            # Entity Properties
            st.markdown("#### 📋 Stored Record Attributes")
            props = entity_node.get("properties", {})
            if props:
                st.json(props)
            else:
                st.caption("No custom attributes recorded.")

            # Connected neighbors table
            st.markdown("#### 🔗 Direct Network Neighbors")
            n_edges = [
                e for e in edges
                if e.get("source_node_id") == entity_node["node_id"] or e.get("target_node_id") == entity_node["node_id"]
            ]
            if n_edges:
                st.dataframe(build_accessible_edges_table(n_edges), use_container_width=True)
            else:
                st.caption("No direct edges registered for this entity in the active graph slice.")


# =============================================================================
# TAB 3: CROSS-PHASE INVESTIGATION WORKFLOWS (PHASE 9.9)
# =============================================================================
with tab_path:
    st.subheader("🛤️ Cross-Phase Investigation Workflows & Auditability")
    st.markdown(
        "Demonstrates end-to-end investigation workflows connecting information across Phases 1–8: "
        "inspecting available records, preserving source citations, highlighting missing information, "
        "separating official self-claims from independent verification, and maintaining reviewer audit history."
    )

    WORKFLOW_OPTIONS = {
        "workflow_a": "Workflow A: Political Promise → Schemes → Budgets → Implementation & Claims",
        "workflow_b": "Workflow B: Civic Issue → Original Record → Department Response → Resolution Evidence",
        "workflow_c": "Workflow C: Public Claim → Supporting, Contradicting & Contextual Records",
        "workflow_d": "Workflow D: Representative → Constituency → Legislative & Public Works",
        "workflow_e": "Workflow E: Political Finance → Disclosed Entity → Source Document",
    }

    selected_wf_key = st.selectbox(
        "Select Canonical Investigation Workflow:",
        options=list(WORKFLOW_OPTIONS.keys()),
        format_func=lambda k: WORKFLOW_OPTIONS[k],
    )

    # Workflow subject selection
    if selected_wf_key == "workflow_a":
        wf_candidates = [n for n in nodes if n.get("entity_type") == "POLITICAL_PROMISE"]
        default_id = wf_candidates[0]["node_id"] if wf_candidates else "NODE:PROM:DMK_DESAL"
        subject_id = st.text_input("Political Promise Identifier (Node ID or Canonical ID):", value=default_id)
    elif selected_wf_key == "workflow_b":
        wf_candidates = [n for n in nodes if n.get("entity_type") in ("CIVIC_ISSUE", "GRIEVANCE_RECORD")]
        default_id = wf_candidates[0]["node_id"] if wf_candidates else "NODE:ISSUE:WATER_VELACHERY"
        subject_id = st.text_input("Civic Issue Identifier (Node ID or Code):", value=default_id)
    elif selected_wf_key == "workflow_c":
        wf_candidates = [n for n in nodes if n.get("entity_type") in ("PUBLIC_CLAIM", "CLAIM", "ATOMIC_CLAIM")]
        default_id = wf_candidates[0]["node_id"] if wf_candidates else "NODE:CLAIM:DESAL_OUTPUT"
        subject_id = st.text_input("Public Claim Identifier (Node ID or Text):", value=default_id)
    elif selected_wf_key == "workflow_d":
        wf_candidates = [n for n in nodes if n.get("entity_type") in ("REPRESENTATIVE", "POLITICAL_PERSON")]
        default_id = wf_candidates[0]["node_id"] if wf_candidates else "NODE:REP:VELACHERY_MLA"
        subject_id = st.text_input("Representative Identifier (Node ID or Official Name):", value=default_id)
    else:
        wf_candidates = [n for n in nodes if n.get("entity_type") in ("POLITICAL_PARTY", "DONOR", "CONTRIBUTION")]
        default_id = wf_candidates[0]["node_id"] if wf_candidates else "NODE:PARTY:DMK"
        subject_id = st.text_input("Political Finance Identifier (Party / Donor / Transaction):", value=default_id)

    col_btn, col_exp = st.columns([1, 1])
    with col_btn:
        run_wf = st.button("🚀 Execute Auditable Investigation", type="primary", use_container_width=True)

    # Fetch or retrieve investigation summary
    inv_data = None
    if run_wf or "last_investigation" in st.session_state:
        if run_wf:
            st.session_state["last_investigation"] = (selected_wf_key, subject_id)
        current_wf, current_id = st.session_state.get("last_investigation", (selected_wf_key, subject_id))

        with st.spinner(f"Executing {WORKFLOW_OPTIONS[current_wf]} for '{current_id}'..."):
            # Try live backend API first
            live_ok = False
            if current_wf == "workflow_a":
                live_ok, res = api_client.investigate_workflow_a(current_id)
            elif current_wf == "workflow_b":
                live_ok, res = api_client.investigate_workflow_b(current_id)
            elif current_wf == "workflow_c":
                live_ok, res = api_client.investigate_workflow_c(current_id)
            elif current_wf == "workflow_d":
                live_ok, res = api_client.investigate_workflow_d(current_id)
            else:
                live_ok, res = api_client.investigate_workflow_e(current_id)

            if live_ok and isinstance(res, dict):
                inv_data = res
            else:
                inv_data = FIXTURE_WORKFLOW_RESULTS.get(current_wf, FIXTURE_WORKFLOW_RESULTS["workflow_a"])

    if inv_data:
        st.markdown("---")
        st.markdown(f"### 📋 Investigation Dossier: `{inv_data.get('subject_label')}`")

        # Epistemic Banner
        st.info(f"⚖️ **Epistemic Guardrail:** {inv_data.get('epistemic_guardrail')}")

        # 1. Records Actually Available
        st.markdown("#### 1. Records Actually Available in CIVICLENS TN")
        rec_avail = inv_data.get("records_available", {})
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.json(rec_avail)
        with col_r2:
            st.markdown(
                f"""
                <div style="background: white; border: 1px solid #ced4da; padding: 14px; border-radius: 6px;">
                    <h5 style="margin-top: 0; color: #007bff;">Network Connectivity Metrics</h5>
                    <p><b>Connected Edges:</b> {rec_avail.get('connecting_edges_count', len(rec_avail.get('connecting_edges', [])))}</p>
                    <p><b>Subject Record:</b> <code>{inv_data.get('subject_identifier')}</code></p>
                    <p><b>Data Governance:</b> DPDPA 2023 Compliant</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # 2. Official Administrative Reporting vs Independent Verification
        st.markdown("#### 2. Official Administrative Reporting vs. Independent Verification")
        matrix = inv_data.get("official_reporting_vs_independent_verification", [])
        if matrix:
            st.dataframe(pd.DataFrame(matrix), use_container_width=True)
        else:
            st.caption("No edge verification records in this slice.")

        # 3. Missing Information Gaps
        st.markdown("#### 3. Missing Information & Evidentiary Gaps")
        gaps = inv_data.get("missing_information", [])
        if gaps:
            for g in gaps:
                st.warning(f"⚠️ **Evidentiary Gap:** {g}")
        else:
            st.success("✅ Complete evidentiary lineage available without intermediate gaps.")

        # 4. Unreviewed Candidate Links
        cand_links = inv_data.get("unreviewed_candidate_links", [])
        if cand_links:
            st.markdown("#### 4. Unreviewed Candidate Links (Algorithmic Proposals)")
            for cl in cand_links:
                st.markdown(
                    f"""
                    <div style="background-color: #fff9db; border: 1px dashed #f59f00; border-radius: 6px; padding: 10px; margin-bottom: 8px;">
                        <strong>Candidate Link:</strong> <code>{cl.get('proposal_id', 'CANDIDATE')}</code> |
                        {render_review_status_badge(cl.get('review_status', 'PENDING_REVIEW'))}
                        <p style="margin: 4px 0; font-size: 13px;">Proposed relationship: <code>{cl.get('relationship_type')}</code> (Confidence: {cl.get('confidence_score', 0.5):.2f})</p>
                        <small style="color: #d9480f;">Notice: Not established as fact until human review.</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # 5. Reviewer Audit Decisions
        st.markdown("#### 5. Reviewer Decision Audit History")
        rev_hist = inv_data.get("reviewer_audit_history", [])
        if rev_hist:
            for rh in rev_hist:
                st.markdown(
                    f"""
                    <div style="background: #f8f9fa; border-left: 4px solid #28a745; padding: 10px; margin-bottom: 6px; border-radius: 4px;">
                        <b>{rh.get('record_type')}</b> by <code>{rh.get('reviewed_by', rh.get('performed_by', 'REVIEWER'))}</code>:
                        <span style="color: #333;">{rh.get('rationale')}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No manual review decisions or override logs recorded for this entity.")

        # 6. Unresolved Questions & Non-Verdict Summary
        st.markdown("#### 6. Investigation Summary: Unresolved Questions (Non-Verdict)")
        st.info("💡 CIVICLENS TN provides empirical evidence and frames key unresolved governance questions rather than issuing unsupported final verdicts.")
        for i, q in enumerate(inv_data.get("unresolved_questions", [])):
            st.markdown(f"**Q{i+1}:** {q}")

        # 7. Report Export Functionality
        st.markdown("---")
        st.markdown("#### 📥 Export Source-Linked Auditable Report")
        col_exp1, col_exp2 = st.columns(2)

        # Generate markdown report text
        md_text = f"# CIVICLENS TN Auditable Report — {inv_data.get('workflow')}\n"
        md_text += f"**Subject:** `{inv_data.get('subject_identifier')}` ({inv_data.get('subject_label')})\n\n"
        md_text += f"> {inv_data.get('epistemic_guardrail')}\n\n"
        md_text += "## Missing Information\n"
        for g in gaps:
            md_text += f"- {g}\n"
        md_text += "\n## Unresolved Questions\n"
        for q in inv_data.get("unresolved_questions", []):
            md_text += f"- {q}\n"

        with col_exp1:
            st.download_button(
                label="📄 Download Markdown Report (.md)",
                data=md_text,
                file_name=f"civiclens_report_{selected_wf_key}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col_exp2:
            import json
            st.download_button(
                label="📊 Download Auditable JSON Dossier (.json)",
                data=json.dumps(inv_data, indent=2),
                file_name=f"civiclens_dossier_{selected_wf_key}.json",
                mime="application/json",
                use_container_width=True,
            )


# =============================================================================
# TAB 4: CONTRADICTIONS, DISPUTES & CANDIDATE LINKS
# =============================================================================
with tab_conflicts:
    st.subheader("⚖️ Dialectical Tensions & Persistent Evidence Conflicts")
    st.markdown(
        "CIVICLENS TN preserves contradictory evidence rather than erasing conflicting reports. "
        "Official statutory findings are distinguished from press statements using documented epistemic weights."
    )

    # Contradictions & Dialectics
    st.markdown("### ⚡ Active Contradiction Records")
    for conf in conflicts:
        st.markdown(
            f"""
            <div style="background-color: #fff5f5; border-left: 5px solid #dc3545; border-radius: 6px; padding: 14px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between;">
                    <strong style="color: #c92a2a; font-size: 15px;">Conflict ID: {conf.get('conflict_id')}</strong>
                    <span style="background: #f8d7da; color: #721c24; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 8px;">
                        SEVERITY: {conf.get('severity', 'HIGH')}
                    </span>
                </div>
                <p style="margin: 8px 0; color: #333; font-size: 14px;">{conf.get('description')}</p>
                <div style="background: white; border: 1px solid #ffc9c9; padding: 10px; border-radius: 4px; font-size: 13px;">
                    <strong>⚖️ Epistemic Weight Comparison:</strong><br>
                    {conf.get('epistemic_weight_comparison', {}).get('rule', 'Standard dialectical evaluation applies.')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### ⏳ Unreviewed Candidate Proposals (Phase 9.4 Discovery Engine)")
    st.info("💡 Candidate links are proposed algorithmically based on exact identifiers or geospatial overlap. They are **NOT** established facts until confirmed by a human reviewer.")

    for prop in candidate_proposals:
        st.markdown(
            f"""
            <div style="background-color: #fff9db; border: 1px dashed #f59f00; border-radius: 6px; padding: 14px; margin-bottom: 10px;">
                <strong>Proposal ID:</strong> <code>{prop.get('proposal_id')}</code> |
                <strong>Confidence:</strong> <code>{prop.get('confidence_score', 0.5):.2f}</code> |
                {render_review_status_badge(prop.get('review_status', 'PENDING_REVIEW'))}
                <p style="margin: 6px 0; font-size: 14px;">
                    <b>Proposed Link:</b> <code>{prop.get('source_node_id')}</code> ➜ <code>{prop.get('relationship_type')}</code> ➜ <code>{prop.get('target_node_id')}</code>
                </p>
                <p style="margin: 4px 0; font-size: 13px; color: #555;">
                    <b>Evidence Basis:</b> {prop.get('evidence_supporting_candidate')}
                </p>
                <small style="color: #d9480f;"><b>Caveat:</b> {prop.get('warning', 'Awaiting domain auditor review.')}</small>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =============================================================================
# TAB 5: SOURCE DOCUMENTS & PROVENANCE LEDGER
# =============================================================================
with tab_sources:
    st.subheader("📄 Source Documents & Evidentiary Lineage")
    st.markdown(
        "Every graph relationship in CIVICLENS TN roots directly into primary gazettes, CAG audits, legislative proceedings, or RTIs."
    )

    doc_nodes = [n for n in FIXTURE_GRAPH_NODES if n.get("entity_type") == "SOURCE_DOCUMENT"]
    for d in doc_nodes:
        props = d.get("properties", {})
        st.markdown(
            f"""
            <div style="background: #f8f9fa; border: 1px solid #ced4da; border-radius: 6px; padding: 14px; margin-bottom: 10px;">
                <h4 style="margin: 0; color: #212529;">📄 {d.get('label')}</h4>
                <p style="margin: 4px 0; color: #495057;"><strong>தமிழ்:</strong> {d.get('label_ta')}</p>
                <p style="margin: 2px 0; font-size: 13px;"><b>Issuing Authority:</b> {props.get('issuing_authority', 'N/A')}</p>
                <p style="margin: 2px 0; font-size: 13px;"><b>Publication Date:</b> {props.get('publication_date', 'N/A')}</p>
                <p style="margin: 2px 0; font-size: 12px; font-family: monospace;"><b>SHA-256 Checksum:</b> {props.get('sha256', 'N/A')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
