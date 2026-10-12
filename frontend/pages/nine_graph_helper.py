"""
Phase 9.8 — Frontend Helper for Unified Civic Evidence Graph Explorer.
======================================================================

Taxonomy configs, badge renderers, Plotly network graph builder, Graphviz DOT generator,
and accessible tabular view builders.

Strict Epistemic Rules:
- Association != Causation: Visual layouts use neutral positioning and do not render
  causal flow arrows unless an evidence-supported causal relationship is verified.
- Candidate proposals are strictly rendered with dashed amber styling and explicit
  unverified warnings.
- Contradictory evidence and disputed edges are surfaced with prominent dialectical indicators.
"""

from __future__ import annotations

import math
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# -----------------------------------------------------------------------------
# 1. ENTITY TYPE TAXONOMY CONFIGURATION
# -----------------------------------------------------------------------------
ENTITY_TYPE_CONFIG: Dict[str, Dict[str, Any]] = {
    "GOVERNMENT_DEPARTMENT": {
        "icon": "🏛️",
        "color": "#007bff",
        "bg_color": "#e7f1ff",
        "title_en": "Government Department",
        "title_ta": "அரசுத் துறை",
        "page_target": "pages/8_Civic_Issue_Intelligence.py",
        "phase": "Phase 3",
    },
    "SCHEME": {
        "icon": "📜",
        "color": "#17a2b8",
        "bg_color": "#e0f7fa",
        "title_en": "Scheme",
        "title_ta": "அரசுத் திட்டம்",
        "page_target": "pages/1_Budget_&_Schemes.py",
        "phase": "Phase 2",
    },
    "BUDGET_LINE_ITEM": {
        "icon": "💰",
        "color": "#28a745",
        "bg_color": "#e8f5e9",
        "title_en": "Budget Line Item",
        "title_ta": "நிதிநிலை ஒதுக்கீடு",
        "page_target": "pages/1_Budget_&_Schemes.py",
        "phase": "Phase 1",
    },
    "POLITICAL_PROMISE": {
        "icon": "🤝",
        "color": "#6f42c1",
        "bg_color": "#f3e8ff",
        "title_en": "Political Promise",
        "title_ta": "தேர்தல் வாக்குறுதி",
        "page_target": "pages/2_Political_Promises.py",
        "phase": "Phase 1",
    },
    "POLITICAL_PARTY": {
        "icon": "🚩",
        "color": "#e83e8c",
        "bg_color": "#fce4ec",
        "title_en": "Political Party",
        "title_ta": "அரசியல் கட்சி",
        "page_target": "pages/5_Political_Funding.py",
        "phase": "Phase 5",
    },
    "REPRESENTATIVE": {
        "icon": "👤",
        "color": "#fd7e14",
        "bg_color": "#fff3e0",
        "title_en": "Representative",
        "title_ta": "மக்கள் பிரதிநிதி",
        "page_target": "pages/4_Representatives.py",
        "phase": "Phase 6",
    },
    "CONSTITUENCY": {
        "icon": "🗺️",
        "color": "#20c997",
        "bg_color": "#e6fffa",
        "title_en": "Constituency",
        "title_ta": "சட்டமன்றத் தொகுதி",
        "page_target": "pages/4_Representatives.py",
        "phase": "Phase 6",
    },
    "PUBLIC_CLAIM": {
        "icon": "🔍",
        "color": "#ffc107",
        "bg_color": "#fffde7",
        "title_en": "Public Claim",
        "title_ta": "பொதுக் கூற்று",
        "page_target": "pages/6_Claim_Verification.py",
        "phase": "Phase 8",
    },
    "CIVIC_ISSUE": {
        "icon": "🚨",
        "color": "#dc3545",
        "bg_color": "#ffebee",
        "title_en": "Civic Issue",
        "title_ta": "குடிமைப் பிரச்சினை",
        "page_target": "pages/8_Civic_Issue_Intelligence.py",
        "phase": "Phase 7",
    },
    "SOURCE_DOCUMENT": {
        "icon": "📄",
        "color": "#6c757d",
        "bg_color": "#f8f9fa",
        "title_en": "Source Document",
        "title_ta": "சான்று ஆவணம்",
        "page_target": "pages/8_Civic_Issue_Intelligence.py",
        "phase": "Phase 1-8",
    },
}


# -----------------------------------------------------------------------------
# 2. RELATIONSHIP TYPE MEANINGS & DEFINITIONS
# -----------------------------------------------------------------------------
RELATIONSHIP_DEFINITIONS: Dict[str, Dict[str, str]] = {
    "funds": {
        "meaning": "Authorizes statutory financial outlay or grants budget capital without guaranteeing physical completion or personal benefit.",
        "epistemic_scope": "Statutory Financial Authority",
        "color": "#28a745",
    },
    "implements": {
        "meaning": "Nodal department or executing board administratively sanctions and executes the project/scheme.",
        "epistemic_scope": "Administrative Execution",
        "color": "#007bff",
    },
    "promises": {
        "meaning": "Political party election manifesto officially pledges policy delivery or project realization.",
        "epistemic_scope": "Electoral Pledge",
        "color": "#6f42c1",
    },
    "relates_to": {
        "meaning": "Documented institutional, organizational, or statutory affiliation connects both entities.",
        "epistemic_scope": "Institutional Affiliation",
        "color": "#495057",
    },
    "reports_on": {
        "meaning": "Journalistic or administrative document provides monitored coverage regarding the subject entity.",
        "epistemic_scope": "Documentary Reporting",
        "color": "#17a2b8",
    },
    "mentions": {
        "meaning": "Primary document text directly references or cites the entity identifier.",
        "epistemic_scope": "Textual Reference",
        "color": "#6c757d",
    },
    "concerns": {
        "meaning": "Grievance, petition, or inquiry substantively concerns the domain of the target entity.",
        "epistemic_scope": "Domain Relevance",
        "color": "#6c757d",
    },
    "represents": {
        "meaning": "Representative holds constitutional democratic mandate to represent voters of the constituency.",
        "epistemic_scope": "Democratic Representation",
        "color": "#fd7e14",
    },
    "responds_to": {
        "meaning": "Official action-taken report, reply letter, or repair order responds to the grievance docket.",
        "epistemic_scope": "Administrative Response",
        "color": "#20c997",
    },
    "provides_evidence_for": {
        "meaning": "Statutory audit, gazette order, or field measurement provides documentary corroboration supporting the claim.",
        "epistemic_scope": "Evidentiary Support",
        "color": "#28a745",
    },
    "contradicts": {
        "meaning": "Verified empirical audit, field measurement, or statutory finding directly contradicts the claim.",
        "epistemic_scope": "Dialectical Contradiction",
        "color": "#dc3545",
    },
    "contextualizes": {
        "meaning": "Provides background geographic, demographic, or legal framework explaining the context.",
        "epistemic_scope": "Contextual Nuance",
        "color": "#ffc107",
    },
    "located_in": {
        "meaning": "Physical or civic event took place within the territorial boundary of the administrative unit.",
        "epistemic_scope": "Spatial Geography",
        "color": "#20c997",
    },
    "derived_from": {
        "meaning": "Data entity was computed, extracted, or synthesized from the primary source document.",
        "epistemic_scope": "Data Provenance",
        "color": "#6c757d",
    },
}


# -----------------------------------------------------------------------------
# 3. BADGE RENDERING HELPERS
# -----------------------------------------------------------------------------
def render_entity_type_badge(entity_type: str) -> str:
    """Renders HTML badge for an entity type."""
    cfg = ENTITY_TYPE_CONFIG.get(entity_type.upper(), {
        "icon": "🔹",
        "color": "#495057",
        "bg_color": "#e9ecef",
        "title_en": entity_type,
    })
    return (
        f'<span style="background-color: {cfg["bg_color"]}; color: {cfg["color"]}; '
        f'padding: 3px 8px; border-radius: 12px; font-weight: 600; font-size: 12px; '
        f'border: 1px solid {cfg["color"]};">'
        f'{cfg["icon"]} {cfg["title_en"]}</span>'
    )


def render_relationship_badge(rel_type: str) -> str:
    """Renders HTML badge for relationship type."""
    cfg = RELATIONSHIP_DEFINITIONS.get(rel_type.lower(), {
        "color": "#6c757d",
    })
    color = cfg["color"]
    return (
        f'<span style="background-color: #f8f9fa; color: {color}; padding: 2px 7px; '
        f'border-radius: 10px; font-size: 11px; font-weight: bold; border: 1px solid {color};">'
        f'{rel_type.upper()}</span>'
    )


def render_review_status_badge(status: str) -> str:
    """Renders review status badge."""
    st_clean = (status or "").upper()
    if st_clean == "VERIFIED":
        return '<span style="background-color: #d4edda; color: #155724; padding: 2px 7px; border-radius: 10px; font-size: 11px; font-weight: bold;">✅ VERIFIED</span>'
    elif st_clean == "PENDING_REVIEW":
        return '<span style="background-color: #fff3cd; color: #856404; padding: 2px 7px; border-radius: 10px; font-size: 11px; font-weight: bold;">⏳ CANDIDATE (PENDING REVIEW)</span>'
    elif st_clean == "REJECTED":
        return '<span style="background-color: #f8d7da; color: #721c24; padding: 2px 7px; border-radius: 10px; font-size: 11px; font-weight: bold;">❌ REJECTED</span>'
    elif st_clean == "OVERRIDDEN":
        return '<span style="background-color: #e2e3e5; color: #383d41; padding: 2px 7px; border-radius: 10px; font-size: 11px; font-weight: bold;">⚠️ OVERRIDDEN</span>'
    return f'<span style="background-color: #e2e3e5; color: #383d41; padding: 2px 7px; border-radius: 10px; font-size: 11px;">{st_clean}</span>'


def render_provenance_badge(status: str) -> str:
    """Renders provenance lifecycle badge."""
    st_clean = (status or "").upper()
    if st_clean == "VALID":
        return '<span style="background-color: #e8f5e9; color: #2e7d32; padding: 2px 7px; border-radius: 10px; font-size: 11px; font-weight: bold;">🟢 VALID</span>'
    elif st_clean == "DISPUTED":
        return '<span style="background-color: #fbe9e7; color: #c62828; padding: 2px 7px; border-radius: 10px; font-size: 11px; font-weight: bold;">🔴 DISPUTED</span>'
    elif st_clean in ("RETRACTED", "SUPERSEDED"):
        return f'<span style="background-color: #f5f5f5; color: #757575; padding: 2px 7px; border-radius: 10px; font-size: 11px;">⚪ {st_clean}</span>'
    return f'<span style="background-color: #fff8e1; color: #f57f17; padding: 2px 7px; border-radius: 10px; font-size: 11px;">🟡 {st_clean}</span>'


def render_epistemic_warning_banner() -> None:
    """Renders epistemic integrity banner."""
    st.markdown(
        """
        <div style="background-color: #fff9db; border-left: 5px solid #f59f00; padding: 12px 16px; border-radius: 4px; margin-bottom: 16px;">
            <strong style="color: #d9480f;">⚖️ Methodological & Anti-Causal Guardrail:</strong>
            <span style="color: #495057; font-size: 13px;">
                Edges represent <strong>documented associations</strong> supported by primary evidence.
                Visual connectivity does <strong>NOT establish causal attribution</strong> (e.g., funding a department does not prove promise fulfillment; a civic complaint does not establish the individual legislator's fault).
                Unreviewed candidate links are algorithmic proposals and NOT established facts.
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# 4. PLOTLY INTERACTIVE NETWORK GRAPH BUILDER
# -----------------------------------------------------------------------------
def build_plotly_network_figure(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    selected_node_id: Optional[str] = None,
    selected_edge_id: Optional[str] = None,
    height: int = 580,
) -> go.Figure:
    """
    Constructs an interactive 2D Plotly network visualization.
    Positions nodes neutrally in a circular/spring formation without directional bias.
    """
    if not nodes:
        fig = go.Figure()
        fig.update_layout(
            title="No graph nodes available to display.",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=300,
        )
        return fig

    # Compute node coordinates (Circular layout with central focus if selected_node_id is provided)
    n_count = len(nodes)
    pos: Dict[str, Tuple[float, float]] = {}

    if selected_node_id and any(n["node_id"] == selected_node_id for n in nodes):
        pos[selected_node_id] = (0.0, 0.0)
        other_nodes = [n for n in nodes if n["node_id"] != selected_node_id]
        m = len(other_nodes)
        for i, n in enumerate(other_nodes):
            angle = 2.0 * math.pi * i / max(1, m)
            radius = 1.0 + (0.15 * (i % 2))
            pos[n["node_id"]] = (radius * math.cos(angle), radius * math.sin(angle))
    else:
        for i, n in enumerate(nodes):
            angle = 2.0 * math.pi * i / max(1, n_count)
            pos[n["node_id"]] = (math.cos(angle), math.sin(angle))

    # Build Edges Traces
    edge_traces = []
    edge_midpoint_x = []
    edge_midpoint_y = []
    edge_labels = []

    for e in edges:
        s_id = e.get("source_node_id")
        t_id = e.get("target_node_id")
        if s_id not in pos or t_id not in pos:
            continue

        x0, y0 = pos[s_id]
        x1, y1 = pos[t_id]

        rel_type = e.get("relationship_type", "relates_to").lower()
        rel_cfg = RELATIONSHIP_DEFINITIONS.get(rel_type, {"color": "#6c757d"})
        edge_color = rel_cfg["color"]

        is_candidate = e.get("review_status") == "PENDING_REVIEW"
        is_disputed = e.get("provenance_status") == "DISPUTED"
        is_contradiction = rel_type == "contradicts"

        line_dash = "dash" if is_candidate else "solid"
        line_width = 3 if e.get("edge_id") == selected_edge_id else 1.8

        if is_contradiction or is_disputed:
            edge_color = "#dc3545"

        edge_trace = go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode="lines",
            line=dict(width=line_width, color=edge_color, dash=line_dash),
            hoverinfo="none",
            showlegend=False,
        )
        edge_traces.append(edge_trace)

        # Midpoint for hover label
        mid_x = (x0 + x1) / 2.0
        mid_y = (y0 + y1) / 2.0
        edge_midpoint_x.append(mid_x)
        edge_midpoint_y.append(mid_y)
        hover_html = (
            f"<b>Relationship:</b> {rel_type.upper()}<br>"
            f"<b>ID:</b> {e.get('edge_id')}<br>"
            f"<b>Review:</b> {e.get('review_status', 'N/A')}<br>"
            f"<b>Provenance:</b> {e.get('provenance_status', 'N/A')}<br>"
            f"<b>Confidence:</b> {e.get('confidence_score', 1.0):.2f}<br>"
            f"<b>Evidence:</b> {e.get('evidence_reference', 'No reference')[:90]}..."
        )
        edge_labels.append(hover_html)

    # Edge Midpoints trace for hover tooltips
    edge_marker_trace = go.Scatter(
        x=edge_midpoint_x,
        y=edge_midpoint_y,
        mode="markers",
        marker=dict(size=8, color="#ced4da", opacity=0.7),
        hovertext=edge_labels,
        hoverinfo="text",
        showlegend=False,
    )

    # Build Node Traces
    node_x = []
    node_y = []
    node_text = []
    node_hover = []
    node_colors = []
    node_sizes = []
    node_border_widths = []
    node_border_colors = []

    for n in nodes:
        nid = n["node_id"]
        x, y = pos[nid]
        node_x.append(x)
        node_y.append(y)

        etype = (n.get("entity_type") or "").upper()
        cfg = ENTITY_TYPE_CONFIG.get(etype, {"color": "#495057", "icon": "🔹", "title_en": etype})

        # Label abbreviation for readability
        lbl = n.get("label", nid)
        short_lbl = lbl if len(lbl) <= 24 else lbl[:22] + "…"
        node_text.append(f"{cfg['icon']} {short_lbl}")

        hover_info = (
            f"<b>{n.get('label')}</b><br>"
            f"<b>Tamil:</b> {n.get('label_ta', 'N/A')}<br>"
            f"<b>Type:</b> {cfg['title_en']} ({n.get('source_phase', 'N/A')})<br>"
            f"<b>Node ID:</b> {nid}<br>"
            f"<b>Canonical ID:</b> {n.get('canonical_id', 'N/A')}"
        )
        node_hover.append(hover_info)
        node_colors.append(cfg["color"])

        if nid == selected_node_id:
            node_sizes.append(26)
            node_border_widths.append(4)
            node_border_colors.append("#212529")
        else:
            node_sizes.append(18)
            node_border_widths.append(1.5)
            node_border_colors.append("#ffffff")

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        textfont=dict(size=10, color="#212529", family="sans-serif"),
        hovertext=node_hover,
        hoverinfo="text",
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=node_border_widths, color=node_border_colors),
        ),
        showlegend=False,
    )

    fig = go.Figure(data=[*edge_traces, edge_marker_trace, node_trace])

    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        hovermode="closest",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        height=height,
    )
    return fig


# -----------------------------------------------------------------------------
# 5. GRAPHVIZ DOT BUILDER FOR STRUCTURAL DIAGRAMS
# -----------------------------------------------------------------------------
def build_graphviz_dot_source(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    selected_node_id: Optional[str] = None,
) -> str:
    """Generates clean Graphviz DOT language string for st.graphviz_chart."""
    dot_lines = [
        "digraph CivicEvidenceGraph {",
        "  rankdir=LR;",
        '  node [shape=box, style="rounded,filled", fontname="Arial", fontsize=10];',
        '  edge [fontname="Arial", fontsize=8];',
    ]

    for n in nodes:
        nid = n["node_id"].replace(":", "_").replace("-", "_")
        lbl = n.get("label", n["node_id"]).replace('"', '\\"')
        if len(lbl) > 28:
            lbl = lbl[:26] + "..."
        etype = (n.get("entity_type") or "").upper()
        cfg = ENTITY_TYPE_CONFIG.get(etype, {"color": "#6c757d", "bg_color": "#f8f9fa"})

        penwidth = "3.0" if n["node_id"] == selected_node_id else "1.0"
        dot_lines.append(
            f'  {nid} [label="{lbl}", fillcolor="{cfg["bg_color"]}", color="{cfg["color"]}", penwidth={penwidth}];'
        )

    for e in edges:
        s_id = e.get("source_node_id", "").replace(":", "_").replace("-", "_")
        t_id = e.get("target_node_id", "").replace(":", "_").replace("-", "_")
        rel = e.get("relationship_type", "relates_to").lower()
        rel_cfg = RELATIONSHIP_DEFINITIONS.get(rel, {"color": "#495057"})

        is_cand = e.get("review_status") == "PENDING_REVIEW"
        style = "dashed" if is_cand else "solid"
        color = rel_cfg["color"]

        dot_lines.append(
            f'  {s_id} -> {t_id} [label="{rel}", color="{color}", style="{style}", fontcolor="{color}"];'
        )

    dot_lines.append("}")
    return "\n".join(dot_lines)


# -----------------------------------------------------------------------------
# 6. ACCESSIBLE TABULAR ALTERNATIVES
# -----------------------------------------------------------------------------
def build_accessible_nodes_table(nodes: List[Dict[str, Any]]) -> pd.DataFrame:
    """Transforms nodes list into an accessible Pandas DataFrame."""
    rows = []
    for n in nodes:
        etype = n.get("entity_type", "")
        cfg = ENTITY_TYPE_CONFIG.get(etype.upper(), {"title_en": etype})
        rows.append({
            "Node ID": n.get("node_id"),
            "Label (English)": n.get("label"),
            "Label (Tamil)": n.get("label_ta", ""),
            "Entity Type": cfg.get("title_en", etype),
            "Canonical ID": n.get("canonical_id", ""),
            "Source Phase": n.get("source_phase", ""),
        })
    return pd.DataFrame(rows)


def build_accessible_edges_table(edges: List[Dict[str, Any]]) -> pd.DataFrame:
    """Transforms edges list into an accessible Pandas DataFrame."""
    rows = []
    for e in edges:
        rows.append({
            "Edge ID": e.get("edge_id"),
            "Source Node": e.get("source_node_id"),
            "Relationship": (e.get("relationship_type") or "").upper(),
            "Target Node": e.get("target_node_id"),
            "Review Status": e.get("review_status"),
            "Provenance": e.get("provenance_status"),
            "Confidence": e.get("confidence_score", 1.0),
            "Evidence Reference": e.get("evidence_reference", ""),
            "Source Document": e.get("source_document_id", ""),
        })
    return pd.DataFrame(rows)
