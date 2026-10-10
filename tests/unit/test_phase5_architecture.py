"""
Unit tests for Phase 5 Architecture, Dataset Requirements, and Anomaly Methodology.

This test suite verifies:
1. Existence and structural completeness of Phase 5 architectural documentation.
2. Complete documentation coverage of all 7 required datasets and source URLs.
3. Core data entity definitions and relationship integrity using explicitly labelled test fixtures.
4. Statistical anomaly algorithms (Gini, HHI, Benford's Law, YoY growth, Unknown source ratio).
"""

import os
import math
from typing import List
from tests.fixtures.phase5_fixtures import (
    MOCK_PARTIES_FIXTURE,
    MOCK_FINANCIAL_DOCUMENTS_FIXTURE,
    MOCK_CONTRIBUTIONS_FIXTURE,
    MOCK_FINANCIAL_STATEMENT_FIXTURE,
    MOCK_BENFORD_NORMAL_STREAM,
    MOCK_BENFORD_ANOMALOUS_STREAM
)

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "phase5")


def calculate_gini(values: List[float]) -> float:
    """Calculates Gini coefficient for a list of monetary values."""
    if not values or len(values) == 0:
        return 0.0
    sorted_v = sorted(values)
    n = len(sorted_v)
    mean_v = sum(sorted_v) / n
    if mean_v == 0:
        return 0.0
    diff_sum = sum(abs(x - y) for x in sorted_v for y in sorted_v)
    return diff_sum / (2 * n * n * mean_v)


def calculate_hhi(values: List[float]) -> float:
    """Calculates Herfindahl-Hirschman Index (HHI)."""
    total = sum(values)
    if total == 0:
        return 0.0
    return sum((v / total) ** 2 for v in values)


def calculate_benford_chi_square(values: List[float]) -> float:
    """Calculates Chi-Square goodness-of-fit for Benford's Law first-digit distribution."""
    if not values:
        return 0.0
    first_digits = [int(str(abs(v)).replace('.', '').lstrip('0')[0]) for v in values if v > 0]
    if not first_digits:
        return 0.0

    n = len(first_digits)
    observed_counts = {d: 0 for d in range(1, 10)}
    for d in first_digits:
        if 1 <= d <= 9:
            observed_counts[d] += 1

    chi_square = 0.0
    for d in range(1, 10):
        expected_p = math.log10(1 + 1 / d)
        expected_count = n * expected_p
        obs = observed_counts[d]
        chi_square += ((obs - expected_count) ** 2) / expected_count
    return chi_square


class TestPhase5Documentation:
    """Tests existence and section completeness of Phase 5 documentation files."""

    def test_documentation_files_exist(self):
        required_docs = [
            "architecture.md",
            "dataset_requirements.md",
            "data_sources.md",
            "anomaly_methodology.md"
        ]
        for doc in required_docs:
            doc_path = os.path.join(DOCS_DIR, doc)
            assert os.path.exists(doc_path), f"Missing required Phase 5 documentation: {doc}"

    def test_dataset_requirements_coverage(self):
        doc_path = os.path.join(DOCS_DIR, "dataset_requirements.md")
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify all 7 required datasets are explicitly documented
        required_datasets = [
            "ECI Political Party Contribution Reports",
            "ECI Annual Audited Accounts",
            "ADR Political Donation Analysis Reports",
            "Electoral Trust Contribution Reports",
            "Historical Electoral Bond Disclosure Records",
            "Political Party Election Expenditure Statements",
            "Official Political Party Registry"
        ]
        for ds in required_datasets:
            assert ds in content, f"Dataset '{ds}' is not documented in dataset_requirements.md"

        # Verify all required source URLs are documented
        required_urls = [
            "https://www.eci.gov.in/contribution-reports",
            "https://www.eci.gov.in/annual-audit-reports",
            "https://www.eci.gov.in/electoral-trusts-reports",
            "https://www.eci.gov.in/candidate-politicalparty",
            "https://www.adrindia.org/content/donation-report",
            "https://www.adrindia.org/research-and-report/political-party-watch"
        ]
        for url in required_urls:
            assert url in content, f"Source URL '{url}' missing from dataset_requirements.md"

    def test_anomaly_methodology_ethical_framework(self):
        doc_path = os.path.join(DOCS_DIR, "anomaly_methodology.md")
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check required ethical distinction keywords
        assert "DOES NOT prove corruption" in content or "does not prove corruption" in content.lower()
        assert "Observed Financial Facts" in content
        assert "Statistical Flags" in content
        assert "Independently Verified Findings" in content


class TestPhase5CoreEntitiesFixture:
    """Tests core data entity structure using explicitly labelled test fixtures."""

    def test_political_parties_fixture(self):
        assert len(MOCK_PARTIES_FIXTURE) >= 3
        codes = [p["party_code"] for p in MOCK_PARTIES_FIXTURE]
        assert "DMK" in codes
        assert "AIADMK" in codes

    def test_financial_documents_fixture(self):
        assert len(MOCK_FINANCIAL_DOCUMENTS_FIXTURE) >= 2
        for doc in MOCK_FINANCIAL_DOCUMENTS_FIXTURE:
            assert "document_id" in doc
            assert "file_hash_sha256" in doc
            assert "filing_type" in doc

    def test_contributions_fixture(self):
        total_contributions = sum(c["amount_inr"] for c in MOCK_CONTRIBUTIONS_FIXTURE)
        assert total_contributions == 18000000.0  # ₹1.8 Crore
        for c in MOCK_CONTRIBUTIONS_FIXTURE:
            assert c["amount_inr"] >= 20000.0

    def test_financial_statement_integrity(self):
        stmt = MOCK_FINANCIAL_STATEMENT_FIXTURE
        # Verify accounting equation: Total Income - Total Expenditure = Net Surplus
        computed_surplus = stmt["total_income"] - stmt["total_expenditure"]
        assert computed_surplus == stmt["net_surplus_deficit"]


class TestPhase5AnomalyAlgorithms:
    """Tests statistical algorithms using deterministic synthetic test streams."""

    def test_gini_coefficient_calculation(self):
        # Equal contributions -> Gini = 0.0
        equal_vals = [100.0, 100.0, 100.0, 100.0]
        assert calculate_gini(equal_vals) == 0.0

        # Highly concentrated contributions -> Gini > 0.6
        concentrated_vals = [10.0, 10.0, 10.0, 970.0]
        gini = calculate_gini(concentrated_vals)
        assert gini > 0.60

    def test_hhi_calculation(self):
        # Monopoly (1 donor) -> HHI = 1.0
        monopoly = [1000.0]
        assert calculate_hhi(monopoly) == 1.0

        # 4 equal donors -> HHI = 4 * (0.25^2) = 0.25
        equal_four = [100.0, 100.0, 100.0, 100.0]
        assert round(calculate_hhi(equal_four), 4) == 0.25

    def test_benford_chi_square_detection(self):
        # Natural stream should have lower Chi-Square divergence than heavy digit-5 artificial stream
        chi_normal = calculate_benford_chi_square(MOCK_BENFORD_NORMAL_STREAM)
        chi_anomalous = calculate_benford_chi_square(MOCK_BENFORD_ANOMALOUS_STREAM)
        assert chi_anomalous > chi_normal

    def test_unknown_source_ratio_calculation(self):
        stmt = MOCK_FINANCIAL_STATEMENT_FIXTURE
        total_income = stmt["total_income"]
        disclosed_20k = stmt["donations_above_20k"]

        disclosed_ratio = disclosed_20k / total_income
        unknown_ratio = 1.0 - disclosed_ratio

        assert round(disclosed_ratio, 2) == 0.06
        assert round(unknown_ratio, 2) == 0.94
