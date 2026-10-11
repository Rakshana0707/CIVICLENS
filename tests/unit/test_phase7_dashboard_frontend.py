"""
Unit & Integration Tests for Phase 7.9 — Political Claim Verification Dashboard Frontend.

Tests:
1. APIClient methods for Phase 7 Claim Verification endpoints.
2. Streamlit page compilation and syntax integrity (frontend/pages/6_Claim_Verification.py).
3. Test fixture taxonomy and completeness across all 8 evidentiary outcome states.
4. Multilingual text preservation (Tamil, English, mixed-language).
5. Granular atomic claim decomposition representations.
6. Evidence relationship linkage (supporting, contradicting, contextualizing).
7. Visible conflicting/contradictory evidence guarantees.
8. Filter engine logic (category, outcome, review status, language, party, speaker, keyword).
9. Human review workflow and role-based distinction.
10. Strict enforcement of non-ranking and non-defamatory epistemic constraints.
"""

import pytest
import importlib.util
from unittest.mock import MagicMock, patch
from frontend.services.api import APIClient


class TestPhase7DashboardFrontend:
    """Test suite for Phase 7.9 frontend dashboard components, fixtures, and API client."""

    def test_1_api_client_phase7_methods(self):
        """Test APIClient wrapper methods for all Phase 7 Claim Verification endpoints."""
        client = APIClient(base_url="http://localhost:8000")

        with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "status": "success",
                "data": {
                    "claims": [{"claim_id": "CLM-TEST-001"}],
                    "total": 1
                }
            }
            mock_get.return_value = mock_resp
            mock_post.return_value = mock_resp

            # 1. Search claims
            ok, data = client.search_claims(q="GSDP", category="ECONOMIC_METRICS", outcome="supported_by_available_evidence")
            assert ok is True
            assert len(data["claims"]) == 1

            # 2. Claim detail
            ok, data = client.get_claim_detail("CLM-TEST-001")
            assert ok is True

            # 3. Atomic claim detail
            ok, data = client.get_atomic_claim_detail("CLM-TEST-001", "ATM-001")
            assert ok is True

            # 4. Search evidence
            ok, data = client.search_evidence(q="budget", doc_type="PDF")
            assert ok is True

            # 5. Evidence document detail
            ok, data = client.get_evidence_document("EVD-001")
            assert ok is True

            # 6. Claim relationships
            ok, data = client.get_claim_relationships("CLM-TEST-001")
            assert ok is True

            # 7. Verification outcome
            ok, data = client.get_claim_verification("CLM-TEST-001")
            assert ok is True

            # 8. Verification history
            ok, data = client.get_claim_history("CLM-TEST-001")
            assert ok is True

            # 9. Submit review
            ok, data = client.submit_claim_review(
                "CLM-TEST-001",
                {"action": "accept_assessment", "reviewed_by": "Senior Reviewer"},
                reviewer_role="SENIOR_FACT_CHECKER"
            )
            assert ok is True

            # 10. Source registry
            ok, data = client.get_claim_source("SRC-001")
            assert ok is True

            # 11. Claim provenance
            ok, data = client.get_claim_provenance("CLM-TEST-001")
            assert ok is True

            # 12. Cross-phase links
            ok, data = client.get_claim_cross_phase("CLM-TEST-001")
            assert ok is True

    def test_2_streamlit_page_syntax_and_module_spec(self):
        """Verify that frontend/pages/6_Claim_Verification.py compiles without syntax errors."""
        spec = importlib.util.spec_from_file_location(
            "claim_verification_page",
            "frontend/pages/6_Claim_Verification.py"
        )
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        assert module is not None

        # Verify module imports and definitions can be loaded
        with open("frontend/pages/6_Claim_Verification.py", "r", encoding="utf-8") as f:
            code = f.read()
        compiled = compile(code, "frontend/pages/6_Claim_Verification.py", "exec")
        assert compiled is not None

    def test_3_fixture_taxonomies_and_outcome_coverage(self):
        """Verify that verified fixtures cover all 8 required epistemic outcome states."""
        from frontend.pages.six_claim_verification_test_helper import (
            FIXTURE_CLAIMS, OUTCOME_LABELS, OUTCOME_COLORS
        )

        assert len(FIXTURE_CLAIMS) >= 8

        outcomes_in_fixtures = {
            c["verification"]["outcome"] for c in FIXTURE_CLAIMS if "verification" in c
        }

        # Check all 8 required outcome labels
        required_outcomes = {
            "supported_by_available_evidence",
            "contradicted_by_available_evidence",
            "partially_supported",
            "missing_important_context",
            "insufficient_evidence",
            "disputed_evidence",
            "unverifiable",
            "pending_review"
        }
        for ro in required_outcomes:
            assert ro in outcomes_in_fixtures, f"Missing outcome state in fixtures: {ro}"
            assert ro in OUTCOME_LABELS
            assert ro in OUTCOME_COLORS

    def test_4_multilingual_tamil_and_english_preservation(self):
        """Verify that Tamil Unicode text is preserved without mangling."""
        from frontend.pages.six_claim_verification_test_helper import FIXTURE_CLAIMS

        tamil_claims = [c for c in FIXTURE_CLAIMS if c.get("language") == "ta"]
        assert len(tamil_claims) >= 2

        # Check exact Tamil substrings
        clm1 = next(c for c in tamil_claims if c["claim_id"] == "TEST_FIXTURE_CLM_01")
        assert "பொருளாதார வளர்ச்சி" in clm1["original_text"]
        assert "8.2 சதவீதமாக" in clm1["original_text"]

        clm3 = next(c for c in tamil_claims if c["claim_id"] == "TEST_FIXTURE_CLM_03")
        assert "மகளிருக்கு" in clm3["original_text"]
        assert "1.15 கோடி" in clm3["original_text"]

    def test_5_atomic_claims_decomposition_integrity(self):
        """Verify granular atomic claims contain subject, predicate, object, and values."""
        from frontend.pages.six_claim_verification_test_helper import FIXTURE_CLAIMS

        clm4 = next(c for c in FIXTURE_CLAIMS if c["claim_id"] == "TEST_FIXTURE_CLM_04")
        assert len(clm4["atomic_claims"]) == 2

        atm1 = clm4["atomic_claims"][0]
        assert atm1["subject"] == "Rural Road Infrastructure"
        assert atm1["numeric_value"] == 12000
        assert atm1["unit"] == "km"

        atm2 = clm4["atomic_claims"][1]
        assert atm2["subject"] == "Road Maintenance Expenditure"
        assert atm2["numeric_value"] == 0

    def test_6_supporting_and_contradicting_evidence_separation(self):
        """Verify supporting vs contradicting evidence items are distinguished and visible."""
        from frontend.pages.six_claim_verification_test_helper import FIXTURE_CLAIMS

        # Contradicted claim has explicit contradicting evidence
        clm2 = next(c for c in FIXTURE_CLAIMS if c["claim_id"] == "TEST_FIXTURE_CLM_02")
        contradicting = [r for r in clm2["relationships"] if r["relationship_type"] == "contradicts"]
        assert len(contradicting) >= 1
        assert "UDISE+" in contradicting[0]["evidence_title"]
        assert "1,28,450" in contradicting[0]["relevant_passage"]

        # Supported claim has explicit supporting evidence
        clm1 = next(c for c in FIXTURE_CLAIMS if c["claim_id"] == "TEST_FIXTURE_CLM_01")
        supporting = [r for r in clm1["relationships"] if r["relationship_type"] == "supports"]
        assert len(supporting) >= 2
        assert any("DES" in s["evidence_title"] for s in supporting)

    def test_7_contextual_omission_and_disputed_evidence(self):
        """Verify context and limitations highlighting differing baselines."""
        from frontend.pages.six_claim_verification_test_helper import FIXTURE_CLAIMS

        # Missing context fixture
        clm5 = next(c for c in FIXTURE_CLAIMS if c["claim_id"] == "TEST_FIXTURE_CLM_05")
        assert clm5["verification"]["outcome"] == "missing_important_context"
        assert "MoUs" in clm5["verification"]["explanation"]

        # Disputed evidence fixture
        clm6 = next(c for c in FIXTURE_CLAIMS if c["claim_id"] == "TEST_FIXTURE_CLM_06")
        assert clm6["verification"]["outcome"] == "disputed_evidence"
        rel_types = {r["relationship_type"] for r in clm6["relationships"]}
        assert "supports" in rel_types
        assert "contradicts" in rel_types

    def test_8_filter_engine_logic(self):
        """Test filtering logic for category, outcome, language, speaker, party, review status."""
        from frontend.pages.six_claim_verification_test_helper import (
            FIXTURE_CLAIMS, _filter_fixture_claims
        )

        # 1. Filter by category
        res = _filter_fixture_claims(FIXTURE_CLAIMS, {"category": "ECONOMIC_METRICS"})
        assert all(c["claim_category"] == "ECONOMIC_METRICS" for c in res)
        assert len(res) >= 2

        # 2. Filter by outcome
        res = _filter_fixture_claims(FIXTURE_CLAIMS, {"outcome": "contradicted_by_available_evidence"})
        assert len(res) == 1
        assert res[0]["claim_id"] == "TEST_FIXTURE_CLM_02"

        # 3. Filter by language
        res = _filter_fixture_claims(FIXTURE_CLAIMS, {"language": "ta"})
        assert all(c["language"] == "ta" for c in res)
        assert len(res) >= 2

        # 4. Filter by party
        res = _filter_fixture_claims(FIXTURE_CLAIMS, {"party": "AIADMK"})
        assert all(c["party"] == "AIADMK" for c in res)
        assert len(res) == 1

        # 5. Filter by speaker
        res = _filter_fixture_claims(FIXTURE_CLAIMS, {"speaker": "Stalin"})
        assert len(res) == 1
        assert res[0]["claim_id"] == "TEST_FIXTURE_CLM_03"

        # 6. Keyword search
        res = _filter_fixture_claims(FIXTURE_CLAIMS, {"q": "solar"})
        assert len(res) == 1
        assert res[0]["claim_id"] == "TEST_FIXTURE_CLM_08"

    def test_9_cross_phase_links_and_human_review_status(self):
        """Verify cross-phase entities linkage and distinction between human-reviewed and automated."""
        from frontend.pages.six_claim_verification_test_helper import FIXTURE_CLAIMS

        clm3 = next(c for c in FIXTURE_CLAIMS if c["claim_id"] == "TEST_FIXTURE_CLM_03")
        cp = clm3["cross_phase"]
        assert cp["historical_scheme"]["id"] == 101
        assert cp["promise"]["promise_id"] == "PRM-2021-DMK-042"
        assert cp["representative"]["official_name"] == "M.K. Stalin"
        assert clm3["is_human_reviewed"] is True
        assert clm3["review_status"] == "CONFIRMED"

        clm4 = next(c for c in FIXTURE_CLAIMS if c["claim_id"] == "TEST_FIXTURE_CLM_04")
        assert clm4["is_human_reviewed"] is False
        assert clm4["review_status"] == "AUTOMATED_INITIAL"

    def test_10_anti_defamation_and_non_ranking_policy_enforcement(self):
        """Verify that no politician truthfulness score, party rank, or leaderboard exists."""
        from frontend.pages.six_claim_verification_test_helper import FIXTURE_CLAIMS

        for c in FIXTURE_CLAIMS:
            assert "truthfulness_score" not in c
            assert "honesty_score" not in c
            assert "ranking" not in c
            assert "party_rank" not in c
            v = c.get("verification", {})
            assert "politician_score" not in v
            assert "epistemic_disclaimer" in v
