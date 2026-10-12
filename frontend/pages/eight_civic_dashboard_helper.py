"""
CIVICLENS TN — Phase 8.9: Civic Issue Intelligence Dashboard Helper.
====================================================================

Exposes shared taxonomies, color schemas, badge rendering functions,
and fixture data for the Streamlit dashboard and unit test suites.
"""

from typing import Dict, Any, List

from frontend.pages.eight_civic_fixtures import (
    FIXTURE_CATEGORIES,
    FIXTURE_AREAS,
    FIXTURE_DEPARTMENTS,
    FIXTURE_ISSUES,
    FIXTURE_CLUSTERS,
    FIXTURE_TRENDS,
    FIXTURE_SOURCE_DOCUMENTS,
)

# -----------------------------------------------------------------------------
# EPISTEMIC STATUS PALETTE & BADGE RENDERERS
# -----------------------------------------------------------------------------
STATUS_COLORS = {
    "independently_verified_resolved": "#198754",  # Forest Green
    "marked_resolved": "#ffc107",                  # Amber / Warning Yellow
    "action_reported": "#0dcaf0",                  # Cyan
    "under_review": "#0d6efd",                     # Blue
    "acknowledged": "#6f42c1",                     # Purple
    "submitted": "#6c757d",                        # Gray
    "reopened": "#fd7e14",                         # Orange
    "disputed": "#d63384",                         # Pink/Magenta
    "unknown": "#495057",                          # Dark Gray
}

STATUS_LABELS = {
    "independently_verified_resolved": "Independently Verified Resolved (Empirical Proof)",
    "marked_resolved": "Administratively Closed by Department (Awaiting Independent Verification)",
    "action_reported": "Action Reported by Department",
    "under_review": "Under Review / Site Inspection",
    "acknowledged": "Docket Acknowledged",
    "submitted": "Submitted / Pending Assignment",
    "reopened": "Reopened by Complainant / Citizen",
    "disputed": "Disputed / Legal or Boundary Conflict",
    "unknown": "Status Unknown",
}

VERIFICATION_COLORS = {
    "VERIFIED_RESOLVED": "#198754",
    "PENDING_INSPECTION": "#ffc107",
    "DEFICIENCY_OBSERVED": "#dc3545",
    "NOT_VERIFIED": "#6c757d",
    "AUDIT_REJECTED": "#b02a37",
}

SEVERITY_COLORS = {
    "CRITICAL": "#dc3545",
    "HIGH": "#fd7e14",
    "MEDIUM": "#ffc107",
    "LOW": "#198754",
}


def render_status_badge(status_code: str) -> str:
    color = STATUS_COLORS.get(status_code, "#6c757d")
    label = STATUS_LABELS.get(status_code, status_code.replace("_", " ").title())
    text_color = "#000" if status_code == "marked_resolved" else "#fff"
    return f"""<span style="background-color: {color}; color: {text_color}; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; display: inline-block;">{label}</span>"""


def render_verification_badge(verif_status: str) -> str:
    color = VERIFICATION_COLORS.get(verif_status, "#6c757d")
    label = verif_status.replace("_", " ").title()
    text_color = "#000" if verif_status == "PENDING_INSPECTION" else "#fff"
    return f"""<span style="background-color: {color}; color: {text_color}; padding: 3px 8px; border-radius: 8px; font-size: 11px; font-weight: 500;">{label}</span>"""


def render_severity_badge(severity: str) -> str:
    color = SEVERITY_COLORS.get(severity, "#6c757d")
    text_color = "#000" if severity == "MEDIUM" else "#fff"
    return f"""<span style="background-color: {color}; color: {text_color}; padding: 2px 8px; border-radius: 6px; font-size: 10px; font-weight: bold;">{severity}</span>"""
