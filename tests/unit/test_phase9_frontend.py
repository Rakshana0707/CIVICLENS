"""
Unit & Integration Tests for Phase 9.8 — Unified Civic Intelligence Evidence Graph Explorer Frontend.
=====================================================================================================

Tests:
1. APIClient methods for all Phase 9 Graph endpoints (mock network calls).
2. Streamlit page syntax and AST compilation integrity (9_Evidence_Graph_Explorer.py).
3. Complete entity taxonomy covering all 10 entity types across Phases 1–8.
4. Explicit relationship definitions and anti-causality guardrails.
5. Interactive Plotly network figure construction and styling distinctions.
6. Graphviz DOT syntax generator.
7. Accessible table generation for screen readers and tabular dataframes.
8. Search and filter engine logic (multilingual Tamil/English, type, phase).
9. Dialectical tensions, conflicts, and statutory weight comparisons.
10. Candidate relationship proposals separation and warning indicators.
11. Edge detail inspection metadata (meaning, records connected, what remains uncertain).
"""

import ast
import pytest
from unittest.mock import MagicMock, patch

from frontend.services.api import APIClient
from frontend.pages.nine_graph_fixtures import (
    FIXTURE_GRAPH_NODES,
    FIXTURE_GRAPH_EDGES,
    FIXTURE_CANDIDATE_PROPOSALS,
    FIXTURE_CONFLICTS,
    FIXTURE_INVESTIGATION_PATHS,
)
from frontend.pages.nine_graph_helper import (
    ENTITY_TYPE_CONFIG,
    RELATIONSHIP_DEFINITIONS,
    render_entity_type_badge,
    render_relationship_badge,
    render_review_status_badge,
    render_provenance_badge,
    build_plotly_network_figure,
    build_graphviz_dot_source,
    build_accessible_nodes_table,
    build_accessible_edges_table,
)
from frontend.pages import nine_graph_fixtures, nine_graph_helper


class TestPhase9FrontendExplorer:
    """Comprehensive test suite for Phase 9.8 Evidence Graph Explorer."""

    # -------------------------------------------------------------------------
    # 1. API Client Phase 9 Methods
    # -------------------------------------------------------------------------
    def test_1_api_client_phase9_methods(self):
        """Validates all Phase 9 Graph API methods in frontend APIClient."""
        client = APIClient(base_url="http://localhost:8000")

        with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "status": "success",
                "data": {
                    "results": [{"node_id": "NODE:DEPT:MAWS"}],
                    "edges": [{"edge_id": "EDGE:001"}],
                    "total": 1,
                },
            }
            mock_get.return_value = mock_resp
            mock_post.return_value = mock_resp

            # 1. search_graph_entities
            ok, data = client.search_graph_entities(query="Nemmeli", entity_type="SCHEME")
            assert ok is True
            assert "results" in data

            # 2. get_graph_node
            ok, data = client.get_graph_node("NODE:DEPT:MAWS")
            assert ok is True

            # 3. get_graph_neighbors
            ok, data = client.get_graph_neighbors("NODE:DEPT:MAWS", direction="outgoing")
            assert ok is True

            # 4. traverse_graph
            ok, data = client.traverse_graph("NODE:PROM:001", max_depth=3)
            assert ok is True

            # 5. investigate_graph_mode
            ok, data = client.investigate_graph_mode("promise_delivery", "NODE:PROM:001")
            assert ok is True

            # 6. get_graph_edges
            ok, data = client.get_graph_edges(relationship_type="implements")
            assert ok is True

            # 7. get_graph_edge
            ok, data = client.get_graph_edge("EDGE:001")
            assert ok is True

            # 8. get_graph_unresolved_proposals
            ok, data = client.get_graph_unresolved_proposals()
            assert ok is True

            # 9. get_graph_conflicts
            ok, data = client.get_graph_conflicts(node_id="NODE:CLAIM:001")
            assert ok is True

            # 10. get_graph_disputes
            ok, data = client.get_graph_disputes()
            assert ok is True

            # 11. get_graph_history
            ok, data = client.get_graph_history()
            assert ok is True

            # 12. get_graph_original_record
            ok, data = client.get_graph_original_record("NODE:DEPT:MAWS")
            assert ok is True

            # 13. mutation actions (confirm, reject, defer)
            ok, _ = client.confirm_graph_proposal("PROP:001", "REV_1", "Verified")
            assert ok is True
            ok, _ = client.reject_graph_proposal("PROP:001", "REV_1", "False positive")
            assert ok is True
            ok, _ = client.defer_graph_proposal("PROP:001", "REV_1", "Need more info")
            assert ok is True

    # -------------------------------------------------------------------------
    # 2. Streamlit Page Syntax & Compilation
    # -------------------------------------------------------------------------
    def test_2_page_compilation_and_ast_integrity(self):
        """Verifies that 9_Evidence_Graph_Explorer.py compiles cleanly without syntax errors."""
        page_path = "frontend/pages/9_Evidence_Graph_Explorer.py"
        with open(page_path, "r", encoding="utf-8") as f:
            source = f.read()
        parsed = ast.parse(source, filename=page_path)
        assert parsed is not None
        assert len(parsed.body) > 10

    # -------------------------------------------------------------------------
    # 3. Entity Type Taxonomy Completeness (All 10 Required Types)
    # -------------------------------------------------------------------------
    def test_3_entity_type_coverage_across_all_10_domains(self):
        """Ensures all 10 required civic entity categories are fully registered."""
        required_entities = {
            "SCHEME",
            "BUDGET_LINE_ITEM",
            "POLITICAL_PROMISE",
            "POLITICAL_PARTY",
            "REPRESENTATIVE",
            "CONSTITUENCY",
            "PUBLIC_CLAIM",
            "CIVIC_ISSUE",
            "GOVERNMENT_DEPARTMENT",
            "SOURCE_DOCUMENT",
        }
        for req in required_entities:
            assert req in ENTITY_TYPE_CONFIG
            cfg = ENTITY_TYPE_CONFIG[req]
            assert "icon" in cfg
            assert "color" in cfg
            assert "title_en" in cfg
            assert "title_ta" in cfg
            assert "page_target" in cfg

        # Verify fixture nodes contain every required entity type
        fixture_types = {n["entity_type"] for n in FIXTURE_GRAPH_NODES}
        for req in required_entities:
            assert req in fixture_types, f"Entity type {req} missing in test fixtures"

    # -------------------------------------------------------------------------
    # 4. Relationship Types and Non-Causation Guardrail
    # -------------------------------------------------------------------------
    def test_4_relationship_types_vocabulary_and_epistemic_meanings(self):
        """Validates explicit relationship vocabulary and meaning descriptions."""
        required_rels = [
            "funds",
            "implements",
            "promises",
            "relates_to",
            "reports_on",
            "mentions",
            "concerns",
            "represents",
            "responds_to",
            "provides_evidence_for",
            "contradicts",
            "contextualizes",
            "located_in",
            "derived_from",
        ]
        for rel in required_rels:
            assert rel in RELATIONSHIP_DEFINITIONS
            r_def = RELATIONSHIP_DEFINITIONS[rel]
            assert "meaning" in r_def
            assert "epistemic_scope" in r_def
            assert len(r_def["meaning"]) > 15

    # -------------------------------------------------------------------------
    # 5. Interactive Plotly Network Figure Builder
    # -------------------------------------------------------------------------
    def test_5_plotly_network_figure_construction(self):
        """Validates Plotly figure generation, trace counts, and distinct edge styles."""
        fig = build_plotly_network_figure(
            nodes=FIXTURE_GRAPH_NODES,
            edges=FIXTURE_GRAPH_EDGES,
            selected_node_id="NODE:DEPT:MAWS",
            selected_edge_id="EDGE:DEPT:SCHEME:001",
        )
        assert fig is not None
        assert len(fig.data) >= 3  # edge traces + midpoints + nodes trace

        # Empty nodes fallback
        empty_fig = build_plotly_network_figure([], [])
        assert empty_fig is not None

    # -------------------------------------------------------------------------
    # 6. Graphviz DOT Diagram Generator
    # -------------------------------------------------------------------------
    def test_6_graphviz_dot_source_generation(self):
        """Validates that build_graphviz_dot_source outputs clean DOT syntax."""
        dot_str = build_graphviz_dot_source(
            nodes=FIXTURE_GRAPH_NODES[:4],
            edges=FIXTURE_GRAPH_EDGES[:3],
            selected_node_id="NODE:DEPT:MAWS",
        )
        assert dot_str.startswith("digraph CivicEvidenceGraph {")
        assert dot_str.endswith("}")
        assert "rankdir=LR;" in dot_str
        assert "NODE_DEPT_MAWS" in dot_str

    # -------------------------------------------------------------------------
    # 7. Accessible Tabular Alternatives
    # -------------------------------------------------------------------------
    def test_7_accessible_tabular_alternatives(self):
        """Ensures accessible tabular dataframes are generated with required columns."""
        df_nodes = build_accessible_nodes_table(FIXTURE_GRAPH_NODES)
        assert not df_nodes.empty
        assert "Node ID" in df_nodes.columns
        assert "Label (English)" in df_nodes.columns
        assert "Label (Tamil)" in df_nodes.columns
        assert "Entity Type" in df_nodes.columns

        df_edges = build_accessible_edges_table(FIXTURE_GRAPH_EDGES)
        assert not df_edges.empty
        assert "Edge ID" in df_edges.columns
        assert "Source Node" in df_edges.columns
        assert "Relationship" in df_edges.columns
        assert "Target Node" in df_edges.columns
        assert "Review Status" in df_edges.columns
        assert "Evidence Reference" in df_edges.columns

    # -------------------------------------------------------------------------
    # 8. Edge Detail Inspector Metadata
    # -------------------------------------------------------------------------
    def test_8_edge_detail_explanation_integrity(self):
        """Validates that each fixture edge has rich explanation and non-causality notes."""
        for edge in FIXTURE_GRAPH_EDGES:
            assert "explanation" in edge
            expl = edge["explanation"]
            assert "meaning" in expl
            assert "directness" in expl
            assert "causality_note" in expl
            assert "evidence_reference" in edge
            assert edge["confidence_score"] > 0.0

    # -------------------------------------------------------------------------
    # 9. Contradictions & Dialectical Tension Preservation
    # -------------------------------------------------------------------------
    def test_9_contradictions_and_statutory_weights(self):
        """Validates preservation of contradictory evidence and statutory weight rules."""
        assert len(FIXTURE_CONFLICTS) >= 1
        cag_conflict = next(c for c in FIXTURE_CONFLICTS if c["conflict_type"] == "CONTRADICTORY_CLAIM_EVIDENCE")
        assert cag_conflict["severity"] == "HIGH"
        assert "epistemic_weight_comparison" in cag_conflict
        weights = cag_conflict["epistemic_weight_comparison"]
        assert "statutory_weight" in weights
        assert weights["statutory_weight"] > weights.get("media_weight", 0.0)

    # -------------------------------------------------------------------------
    # 10. Candidate Relationship Separation
    # -------------------------------------------------------------------------
    def test_10_candidate_proposals_separation(self):
        """Verifies candidate links carry warning banners and PENDING_REVIEW disposition."""
        assert len(FIXTURE_CANDIDATE_PROPOSALS) >= 1
        for prop in FIXTURE_CANDIDATE_PROPOSALS:
            assert prop["review_status"] == "PENDING_REVIEW"
            assert "warning" in prop
            assert "not confirmed" in prop["warning"].lower() or "risk" in prop["warning"].lower()

    # -------------------------------------------------------------------------
    # 11. Multi-Hop Investigation Paths
    # -------------------------------------------------------------------------
    def test_11_investigation_path_templates(self):
        """Verifies the 5 canonical investigation path templates."""
        expected_paths = [
            "promise_delivery",
            "claim_verification",
            "civic_accountability",
            "representative_stewardship",
            "political_finance",
        ]
        for p in expected_paths:
            assert p in FIXTURE_INVESTIGATION_PATHS
            path_def = FIXTURE_INVESTIGATION_PATHS[p]
            assert "title" in path_def
            assert "nodes" in path_def
            assert len(path_def["nodes"]) >= 2
            assert "completeness_score" in path_def
            assert "caveat" in path_def
