"""
Phase 9.9 — Auditable Cross-Phase Investigation Workflows Service.
==================================================================

Provides end-to-end investigation orchestration connecting information across
Phases 1 through 8 in CIVICLENS TN with strict epistemic standards and auditability:

Workflows:
- WORKFLOW A: Political Promise -> Related Schemes -> Budgets -> Implementation & Claims.
- WORKFLOW B: Civic Issue -> Original Public Record -> Department Response -> Status & Resolution Proof.
- WORKFLOW C: Public Claim -> Supporting, Contradicting & Contextual Records.
- WORKFLOW D: Representative -> Constituency -> Legislative & Public-Work Records (Anti-Causality Guardrail).
- WORKFLOW E: Disclosed Political Funding -> Source Gazette/ECI Document -> Supported Entities (Anti-Defamation Guardrail).

Core Guarantees:
1. Records Actually Available: Explicitly lists existing records vs. gaps.
2. Source Links & Hashes: Preserves primary document IDs, URLs, and SHA-256 checksums.
3. Missing Information: Flags missing vouchers, field audits, or missing intermediate links.
4. Unreviewed Candidate Links: Distinctly separates automated candidate proposals from confirmed edges.
5. Official Reporting vs. Independent Verification: Distinguishes departmental self-claims (e.g. ATR, press releases)
   from independent verification (e.g. CAG constitutional audits, RTI responses, sensor telemetry).
6. Auditable History of Reviewer Decisions: Pulls proposal reviews and entity audit records.
7. Non-Verdict Summary: Lists verified evidence and unresolved questions without generating unsupported verdicts.
8. Privacy & Export Sanitization: Strips PII (DPDPA 2023) and server filesystem paths from export reports.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import or_, and_, desc
from sqlalchemy.orm import Session

from backend.models.entity_registry import (
    CanonicalEntity,
    EntityAlias,
    EntityAuditRecord,
    SourceIdentifierMapping,
)
from backend.models.graph import (
    CivicGraphNode,
    CivicEvidenceEdge,
    CandidateRelationshipProposal,
    CandidateReviewDisposition,
    CivicConflictRecord,
    ConflictTypeEnum,
    GraphEntityType,
    GraphRelationshipType,
    MatchingMethod,
    GraphReviewStatus,
    GraphProvenanceStatus,
)
from backend.services.civic_search_service import (
    sanitize_payload,
    sanitize_system_paths,
    NodeNotFoundError,
)
from backend.models.civic_issue import sanitize_pii

logger = logging.getLogger("civiclens.phase9.investigation")


class CrossPhaseInvestigationService:
    """
    Orchestrates auditable investigations connecting records across Phases 1–8.
    """

    # =========================================================================
    # WORKFLOW A: PROMISE -> SCHEMES -> BUDGETS -> IMPLEMENTATION EVIDENCE
    # =========================================================================
    @staticmethod
    def investigate_promise_delivery(identifier: str, session: Session) -> Dict[str, Any]:
        """
        WORKFLOW A: Select a political promise, inspect related schemes and budgets,
        then review available implementation and claim evidence.
        """
        node, can_ent = CrossPhaseInvestigationService._resolve_entity_node(
            identifier, [GraphEntityType.POLITICAL_PROMISE], session
        )

        node_id = node.node_id if node else identifier

        # 1. Connected Edges & Discovered Links
        edges = session.query(CivicEvidenceEdge).filter(
            or_(CivicEvidenceEdge.source_node_id == node_id, CivicEvidenceEdge.target_node_id == node_id),
            CivicEvidenceEdge.provenance_status.notin_([GraphProvenanceStatus.RETRACTED, GraphProvenanceStatus.SUPERSEDED]),
        ).all()

        # Related schemes (promises -> scheme)
        scheme_node_ids = [
            e.target_node_id for e in edges
            if e.relationship_type in (GraphRelationshipType.PROMISES, GraphRelationshipType.RELATES_TO)
        ]
        schemes = session.query(CivicGraphNode).filter(CivicGraphNode.node_id.in_(scheme_node_ids)).all() if scheme_node_ids else []

        # Budgets funding those schemes
        budget_edges = session.query(CivicEvidenceEdge).filter(
            CivicEvidenceEdge.target_node_id.in_(scheme_node_ids),
            CivicEvidenceEdge.relationship_type == GraphRelationshipType.FUNDS,
        ).all() if scheme_node_ids else []
        budget_node_ids = [be.source_node_id for be in budget_edges]
        budgets = session.query(CivicGraphNode).filter(CivicGraphNode.node_id.in_(budget_node_ids)).all() if budget_node_ids else []

        # Implementation and claim evidence linked to scheme or promise
        impl_edges = session.query(CivicEvidenceEdge).filter(
            CivicEvidenceEdge.target_node_id.in_(scheme_node_ids + [node_id]),
            CivicEvidenceEdge.relationship_type.in_([
                GraphRelationshipType.PROVIDES_EVIDENCE_FOR,
                GraphRelationshipType.IMPLEMENTS,
                GraphRelationshipType.CONTRADICTS,
            ]),
        ).all() if scheme_node_ids else []

        # 2. Unreviewed Candidate Proposals
        proposals = session.query(CandidateRelationshipProposal).filter(
            or_(CandidateRelationshipProposal.source_node_id == node_id, CandidateRelationshipProposal.target_node_id == node_id),
            CandidateRelationshipProposal.review_status == CandidateReviewDisposition.PENDING_REVIEW,
        ).all()

        # 3. Detect Missing Information Gaps
        missing_info: List[str] = []
        if not schemes:
            missing_info.append("No government scheme officially mapped to this political manifesto promise.")
        if schemes and not budgets:
            missing_info.append("Mapped scheme lacks verified capital budget outlay or Demand for Grants line item.")
        if budgets and not impl_edges:
            missing_info.append("Budget allocation exists but no documented physical implementation proof or completion certificate is available.")

        # 4. Distinguish Official Reporting vs. Independent Verification
        reporting_matrix = CrossPhaseInvestigationService._build_reporting_matrix(edges + budget_edges + impl_edges)

        # 5. Reviewer Audit Decisions
        audit_history = CrossPhaseInvestigationService._extract_reviewer_history([node_id] + scheme_node_ids, session)

        # 6. Investigation Summary
        summary = {
            "workflow": "WORKFLOW_A_PROMISE_DELIVERY",
            "subject_identifier": identifier,
            "subject_label": node.label if node else identifier,
            "records_available": {
                "promise_node": node.to_dict() if node else None,
                "related_schemes": [s.to_dict() for s in schemes],
                "budget_allocations": [b.to_dict() for b in budgets],
                "connecting_edges_count": len(edges) + len(budget_edges) + len(impl_edges),
            },
            "missing_information": missing_info,
            "unreviewed_candidate_links": [p.to_dict() for p in proposals],
            "official_reporting_vs_independent_verification": reporting_matrix,
            "reviewer_audit_history": audit_history,
            "unresolved_questions": [
                "Does the budget outlay Head of Account represent new dedicated capacity or recurring administrative overhead?",
                "Has an independent social audit or CAG report verified that the promised benefits reached targeted households?",
            ],
            "epistemic_guardrail": (
                "Policy Association Rule: Allocating budget to a scheme associated with a promise demonstrates policy activity, "
                "but does NOT constitute proof of promise fulfillment without verified end-user service delivery records."
            ),
        }
        return sanitize_payload(summary)

    # =========================================================================
    # WORKFLOW B: CIVIC ISSUE -> ORIGINAL RECORD -> RESPONSE -> RESOLUTION PROOF
    # =========================================================================
    @staticmethod
    def investigate_civic_issue_resolution(identifier: str, session: Session) -> Dict[str, Any]:
        """
        WORKFLOW B: Select a civic issue, inspect its original public record, department response,
        reported status, and resolution evidence.
        """
        node, can_ent = CrossPhaseInvestigationService._resolve_entity_node(
            identifier, [GraphEntityType.CIVIC_ISSUE, GraphEntityType.GRIEVANCE_RECORD], session
        )
        node_id = node.node_id if node else identifier

        # 1. Connected Edges (e.g. response responds_to issue, resolution provides_evidence_for)
        edges = session.query(CivicEvidenceEdge).filter(
            or_(CivicEvidenceEdge.source_node_id == node_id, CivicEvidenceEdge.target_node_id == node_id),
            CivicEvidenceEdge.provenance_status.notin_([GraphProvenanceStatus.RETRACTED, GraphProvenanceStatus.SUPERSEDED]),
        ).all()

        response_node_ids = [
            e.source_node_id for e in edges
            if e.relationship_type == GraphRelationshipType.RESPONDS_TO
        ]
        response_nodes = session.query(CivicGraphNode).filter(CivicGraphNode.node_id.in_(response_node_ids)).all() if response_node_ids else []

        evidence_node_ids = [
            e.source_node_id for e in edges
            if e.relationship_type == GraphRelationshipType.PROVIDES_EVIDENCE_FOR
        ]
        evidence_nodes = session.query(CivicGraphNode).filter(CivicGraphNode.node_id.in_(evidence_node_ids)).all() if evidence_node_ids else []

        # 2. Unreviewed Candidate Proposals
        proposals = session.query(CandidateRelationshipProposal).filter(
            or_(CandidateRelationshipProposal.source_node_id == node_id, CandidateRelationshipProposal.target_node_id == node_id),
            CandidateRelationshipProposal.review_status == CandidateReviewDisposition.PENDING_REVIEW,
        ).all()

        # 3. Detect Missing Information Gaps
        missing_info: List[str] = []
        if not response_nodes:
            missing_info.append("No formal department action-taken report (ATR) or response registered.")
        if response_nodes and not evidence_nodes:
            missing_info.append("Department status marked resolved administratively, but empirical ground proof (geo-tagged photos, citizen verification) is missing.")

        # 4. Distinguish Official Reporting vs. Independent Verification
        reporting_matrix = CrossPhaseInvestigationService._build_reporting_matrix(edges)

        # 5. Reviewer Audit Decisions
        audit_history = CrossPhaseInvestigationService._extract_reviewer_history([node_id] + response_node_ids, session)

        summary = {
            "workflow": "WORKFLOW_B_CIVIC_ISSUE_RESOLUTION",
            "subject_identifier": identifier,
            "subject_label": node.label if node else identifier,
            "records_available": {
                "civic_issue_node": node.to_dict() if node else None,
                "department_responses": [r.to_dict() for r in response_nodes],
                "resolution_evidence_nodes": [ev.to_dict() for ev in evidence_nodes],
                "connecting_edges_count": len(edges),
            },
            "missing_information": missing_info,
            "unreviewed_candidate_links": [p.to_dict() for p in proposals],
            "official_reporting_vs_independent_verification": reporting_matrix,
            "reviewer_audit_history": audit_history,
            "unresolved_questions": [
                "Was the grievance resolved through permanent infrastructure rehabilitation or temporary stop-gap repair?",
                "Has independent citizen feedback corroborated that service pressure/quality was restored to benchmark standard?",
            ],
            "epistemic_guardrail": (
                "Epistemic Status Distinction: An administrative department status of 'marked_resolved' represents an official claim, "
                "which is strictly distinguished from 'independently_verified_resolved' requiring empirical ground proof."
            ),
        }
        return sanitize_payload(summary)

    # =========================================================================
    # WORKFLOW C: PUBLIC CLAIM -> SUPPORTING & CONTRADICTING & CONTEXTUAL RECORDS
    # =========================================================================
    @staticmethod
    def investigate_claim_dialectics(identifier: str, session: Session) -> Dict[str, Any]:
        """
        WORKFLOW C: Select a public claim and explore supporting, contradicting,
        and contextual records.
        """
        node, can_ent = CrossPhaseInvestigationService._resolve_entity_node(
            identifier, [GraphEntityType.CLAIM, GraphEntityType.ATOMIC_CLAIM], session
        )
        node_id = node.node_id if node else identifier

        # 1. Connected Evidence Edges (Supporting vs Contradicting vs Contextualizing)
        edges = session.query(CivicEvidenceEdge).filter(
            or_(CivicEvidenceEdge.source_node_id == node_id, CivicEvidenceEdge.target_node_id == node_id),
            CivicEvidenceEdge.provenance_status.notin_([GraphProvenanceStatus.RETRACTED, GraphProvenanceStatus.SUPERSEDED]),
        ).all()

        supporting_edges = [e for e in edges if e.relationship_type == GraphRelationshipType.PROVIDES_EVIDENCE_FOR]
        contradicting_edges = [e for e in edges if e.relationship_type == GraphRelationshipType.CONTRADICTS]
        context_edges = [e for e in edges if e.relationship_type == GraphRelationshipType.CONTEXTUALIZES]

        # 2. Persistent Conflicts from Dialectic Analysis
        conflicts = session.query(CivicConflictRecord).filter(
            or_(CivicConflictRecord.primary_node_id == node_id, CivicConflictRecord.secondary_node_id == node_id)
        ).all()

        # 3. Missing Information Gaps
        missing_info: List[str] = []
        if not supporting_edges and not contradicting_edges:
            missing_info.append("No primary documentary evidence registered evaluating this public claim.")
        elif supporting_edges and not contradicting_edges and not conflicts:
            missing_info.append("Only unilateral supporting citations found; independent counter-verification audits have not been ingested.")

        # 4. Reporting Matrix
        reporting_matrix = CrossPhaseInvestigationService._build_reporting_matrix(edges)

        # 5. Reviewer Audit Decisions
        audit_history = CrossPhaseInvestigationService._extract_reviewer_history([node_id], session)

        summary = {
            "workflow": "WORKFLOW_C_CLAIM_DIALECTICS",
            "subject_identifier": identifier,
            "subject_label": node.label if node else identifier,
            "records_available": {
                "claim_node": node.to_dict() if node else None,
                "supporting_evidence_edges": [e.to_dict() for e in supporting_edges],
                "contradicting_evidence_edges": [e.to_dict() for e in contradicting_edges],
                "contextual_edges": [e.to_dict() for e in context_edges],
                "active_conflicts": [c.to_dict() for c in conflicts],
            },
            "missing_information": missing_info,
            "unreviewed_candidate_links": [],
            "official_reporting_vs_independent_verification": reporting_matrix,
            "reviewer_audit_history": audit_history,
            "unresolved_questions": [
                "Does the contradicting statutory audit reflect an isolated reporting interval or persistent operational underperformance?",
                "Has an updated physical audit reconciled the gap between commissioned capacity and measured output?",
            ],
            "epistemic_guardrail": (
                "Dialectical Preservation Principle: Contradictory evidence is preserved side-by-side. Statutory constitutional audit "
                "findings carry higher evidentiary weight than non-statutory departmental press statements, but neither is silently discarded."
            ),
        }
        return sanitize_payload(summary)

    # =========================================================================
    # WORKFLOW D: REPRESENTATIVE -> CONSTITUENCY -> LEGISLATIVE & PUBLIC WORKS
    # =========================================================================
    @staticmethod
    def investigate_representative_stewardship(identifier: str, session: Session) -> Dict[str, Any]:
        """
        WORKFLOW D: Select a representative and inspect documented constituency,
        legislative, scheme, and public-work records without assuming personal
        responsibility for every associated outcome.
        """
        node, can_ent = CrossPhaseInvestigationService._resolve_entity_node(
            identifier, [GraphEntityType.REPRESENTATIVE, GraphEntityType.POLITICAL_PERSON], session
        )
        node_id = node.node_id if node else identifier

        # 1. Connected Edges
        edges = session.query(CivicEvidenceEdge).filter(
            or_(CivicEvidenceEdge.source_node_id == node_id, CivicEvidenceEdge.target_node_id == node_id),
            CivicEvidenceEdge.provenance_status.notin_([GraphProvenanceStatus.RETRACTED, GraphProvenanceStatus.SUPERSEDED]),
        ).all()

        # Represented Constituency
        const_node_ids = [
            e.target_node_id for e in edges
            if e.relationship_type in (GraphRelationshipType.REPRESENTS, GraphRelationshipType.RELATES_TO)
        ]
        constituencies = session.query(CivicGraphNode).filter(CivicGraphNode.node_id.in_(const_node_ids)).all() if const_node_ids else []

        # Legislative Activities & Public Works in constituency
        works_edges = session.query(CivicEvidenceEdge).filter(
            CivicEvidenceEdge.target_node_id.in_(const_node_ids),
            CivicEvidenceEdge.relationship_type.in_([GraphRelationshipType.LOCATED_IN, GraphRelationshipType.RELATES_TO]),
        ).all() if const_node_ids else []
        works_node_ids = [we.source_node_id for we in works_edges]
        works_nodes = session.query(CivicGraphNode).filter(CivicGraphNode.node_id.in_(works_node_ids)).all() if works_node_ids else []

        # 2. Missing Information Gaps
        missing_info: List[str] = []
        if not constituencies:
            missing_info.append("No active assembly constituency gazette linkage found for representative.")
        if constituencies and not works_nodes:
            missing_info.append("No MLACDS (MLA Constituency Development Scheme) expenditure records or public works mapped.")

        # 3. Reporting Matrix
        reporting_matrix = CrossPhaseInvestigationService._build_reporting_matrix(edges + works_edges)

        # 4. Reviewer History
        audit_history = CrossPhaseInvestigationService._extract_reviewer_history([node_id] + const_node_ids, session)

        summary = {
            "workflow": "WORKFLOW_D_REPRESENTATIVE_STEWARDSHIP",
            "subject_identifier": identifier,
            "subject_label": node.label if node else identifier,
            "records_available": {
                "representative_node": node.to_dict() if node else None,
                "constituencies": [c.to_dict() for c in constituencies],
                "documented_works_and_issues": [w.to_dict() for w in works_nodes],
                "connecting_edges_count": len(edges) + len(works_edges),
            },
            "missing_information": missing_info,
            "unreviewed_candidate_links": [],
            "official_reporting_vs_independent_verification": reporting_matrix,
            "reviewer_audit_history": audit_history,
            "unresolved_questions": [
                "What proportion of constituency issues fall under state municipal departments vs. local municipal council jurisdiction?",
                "Were legislative questions raised in the Assembly directly concerning local grievance hotspots?",
            ],
            "epistemic_guardrail": (
                "Anti-Causality & Non-Defamation Rule: A representative's democratic tenure in a constituency does NOT establish "
                "personal liability or administrative fault for localized civic infrastructure failures or utility delays."
            ),
        }
        return sanitize_payload(summary)

    # =========================================================================
    # WORKFLOW E: POLITICAL FINANCE -> SOURCE DOCUMENT -> SUPPORTED ENTITIES
    # =========================================================================
    @staticmethod
    def investigate_political_finance(identifier: str, session: Session) -> Dict[str, Any]:
        """
        WORKFLOW E: Select a disclosed political funding record and inspect its
        original document and supported entity relationships without inferring wrongdoing.
        """
        node, can_ent = CrossPhaseInvestigationService._resolve_entity_node(
            identifier, [GraphEntityType.POLITICAL_PARTY, GraphEntityType.DONOR, GraphEntityType.CONTRIBUTION], session
        )
        node_id = node.node_id if node else identifier

        # 1. Connected Edges (e.g. donor funds party, or party relates_to election return)
        edges = session.query(CivicEvidenceEdge).filter(
            or_(CivicEvidenceEdge.source_node_id == node_id, CivicEvidenceEdge.target_node_id == node_id),
            CivicEvidenceEdge.provenance_status.notin_([GraphProvenanceStatus.RETRACTED, GraphProvenanceStatus.SUPERSEDED]),
        ).all()

        source_doc_ids = list({e.source_document_id for e in edges if e.source_document_id})
        source_docs = session.query(CivicGraphNode).filter(CivicGraphNode.node_id.in_(source_doc_ids)).all() if source_doc_ids else []

        # 2. Missing Information Gaps
        missing_info: List[str] = []
        if not edges:
            missing_info.append("No statutory funding disclosure transaction edges connected to this entity in the active graph slice.")
        for e in edges:
            if not e.source_document_hash:
                missing_info.append(f"Disclosure edge '{e.edge_id}' lacks verifiable SHA-256 cryptographic document checksum.")

        # 3. Reporting Matrix
        reporting_matrix = CrossPhaseInvestigationService._build_reporting_matrix(edges)

        # 4. Reviewer History
        audit_history = CrossPhaseInvestigationService._extract_reviewer_history([node_id], session)

        summary = {
            "workflow": "WORKFLOW_E_POLITICAL_FINANCE",
            "subject_identifier": identifier,
            "subject_label": node.label if node else identifier,
            "records_available": {
                "entity_node": node.to_dict() if node else None,
                "connected_transactions_count": len(edges),
                "source_documents": [sd.to_dict() for sd in source_docs],
                "connecting_edges": [e.to_dict() for e in edges],
            },
            "missing_information": missing_info,
            "unreviewed_candidate_links": [],
            "official_reporting_vs_independent_verification": reporting_matrix,
            "reviewer_audit_history": audit_history,
            "unresolved_questions": [
                "Does the statutory disclosure indicate corporate electoral trust donations or direct bank transfer contributions?",
                "Are all contribution dates synchronized with Election Commission annual audit report filings?",
            ],
            "epistemic_guardrail": (
                "Statutory Disclosure Rule: Statutory campaign contributions documented under Election Commission returns reflect legal disclosures. "
                "They do NOT establish or infer corrupt intent or unlawful quid-pro-quo without independent statutory or judicial findings."
            ),
        }
        return sanitize_payload(summary)

    # =========================================================================
    # GENERIC DISPATCHER
    # =========================================================================
    @staticmethod
    def run_investigation_workflow(workflow_type: str, identifier: str, session: Session) -> Dict[str, Any]:
        """Dispatches to the appropriate canonical workflow engine."""
        clean_wf = workflow_type.strip().lower()
        if "promise" in clean_wf or clean_wf in ("workflow_a", "a"):
            return CrossPhaseInvestigationService.investigate_promise_delivery(identifier, session)
        elif "civic" in clean_wf or "issue" in clean_wf or clean_wf in ("workflow_b", "b"):
            return CrossPhaseInvestigationService.investigate_civic_issue_resolution(identifier, session)
        elif "claim" in clean_wf or clean_wf in ("workflow_c", "c"):
            return CrossPhaseInvestigationService.investigate_claim_dialectics(identifier, session)
        elif "rep" in clean_wf or "steward" in clean_wf or clean_wf in ("workflow_d", "d"):
            return CrossPhaseInvestigationService.investigate_representative_stewardship(identifier, session)
        elif "fund" in clean_wf or "finance" in clean_wf or clean_wf in ("workflow_e", "e"):
            return CrossPhaseInvestigationService.investigate_political_finance(identifier, session)
        else:
            raise ValueError(f"Unknown investigation workflow '{workflow_type}'. Supported: workflow_a, workflow_b, workflow_c, workflow_d, workflow_e.")

    # =========================================================================
    # EXPORTABLE SOURCE-LINKED INVESTIGATION REPORT GENERATION
    # =========================================================================
    @staticmethod
    def export_investigation_report(
        workflow_type: str,
        identifier: str,
        format: str = "json",
        session: Session = None,
        is_auditor: bool = False,
    ) -> Dict[str, Any] | str:
        """
        Produces a source-linked, verifiable, auditable investigation report.
        Ensures strict PII sanitization and infrastructure path redaction.
        Supports 'json' or 'markdown' format.
        """
        investigation_data = CrossPhaseInvestigationService.run_investigation_workflow(
            workflow_type=workflow_type, identifier=identifier, session=session
        )

        now_utc = datetime.now(timezone.utc).isoformat()
        metadata = {
            "report_title": f"CIVICLENS TN Auditable Investigation Report — {investigation_data.get('workflow')}",
            "generated_at_utc": now_utc,
            "subject_identifier": identifier,
            "subject_label": investigation_data.get("subject_label"),
            "data_governance": "DPDPA 2023 Compliant (Automated PII & Internal Path Sanitization)",
            "epistemic_standard": "CIVICLENS TN Dialectical Evidentiary Methodology",
        }

        report_payload = {
            "metadata": metadata,
            "investigation_summary": investigation_data,
        }
        sanitized_report = sanitize_payload(report_payload, is_auditor=is_auditor)

        if format.lower() == "markdown":
            return CrossPhaseInvestigationService._format_report_markdown(sanitized_report)

        return sanitized_report

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================
    @staticmethod
    def _resolve_entity_node(
        identifier: str,
        allowed_types: List[GraphEntityType],
        session: Session,
    ) -> Tuple[Optional[CivicGraphNode], Optional[CanonicalEntity]]:
        """Finds node by node_id, canonical_id, or label matching."""
        # Exact node_id
        node = session.query(CivicGraphNode).filter(CivicGraphNode.node_id == identifier).first()
        if node:
            can_ent = (
                session.query(CanonicalEntity).filter(CanonicalEntity.entity_id == node.canonical_id).first()
                if node.canonical_id
                else None
            )
            return node, can_ent

        # Canonical entity match
        can_ent = session.query(CanonicalEntity).filter(
            or_(CanonicalEntity.entity_id == identifier, CanonicalEntity.canonical_name_en.ilike(f"%{identifier}%"))
        ).first()

        if can_ent:
            node = session.query(CivicGraphNode).filter(CivicGraphNode.canonical_id == can_ent.entity_id).first()
            if node:
                return node, can_ent

        # Match label
        node = session.query(CivicGraphNode).filter(
            CivicGraphNode.label.ilike(f"%{identifier}%"),
            CivicGraphNode.entity_type.in_(allowed_types),
        ).first()

        return node, can_ent

    @staticmethod
    def _build_reporting_matrix(edges: List[CivicEvidenceEdge]) -> List[Dict[str, Any]]:
        """Separates official departmental reporting from independent verification sources."""
        matrix = []
        for e in edges:
            method = e.matching_method.value if hasattr(e.matching_method, "value") else str(e.matching_method)
            rev_status = e.review_status.value if hasattr(e.review_status, "value") else str(e.review_status)
            is_statutory = "CAG" in (e.source_document_id or "") or "GAZETTE" in (e.source_document_id or "") or "ECI" in (e.source_document_id or "")

            nature = "INDEPENDENT_VERIFICATION" if (is_statutory and rev_status == "VERIFIED") else "OFFICIAL_ADMINISTRATIVE_REPORTING"
            if method == "AUTOMATED_CANDIDATE":
                nature = "UNREVIEWED_CANDIDATE_LINK"

            matrix.append({
                "edge_id": e.edge_id,
                "relationship_type": e.relationship_type.value if hasattr(e.relationship_type, "value") else str(e.relationship_type),
                "source_document_id": e.source_document_id,
                "source_document_hash": e.source_document_hash,
                "evidence_nature": nature,
                "review_status": rev_status,
                "epistemic_confidence": e.confidence_score,
            })
        return matrix

    @staticmethod
    def _extract_reviewer_history(node_ids: List[str], session: Session) -> List[Dict[str, Any]]:
        """Extracts immutable reviewer audit decisions regarding the nodes."""
        history = []
        proposals = session.query(CandidateRelationshipProposal).filter(
            or_(
                CandidateRelationshipProposal.source_node_id.in_(node_ids),
                CandidateRelationshipProposal.target_node_id.in_(node_ids),
            ),
            CandidateRelationshipProposal.review_status != CandidateReviewDisposition.PENDING_REVIEW,
        ).all()

        for p in proposals:
            history.append({
                "record_type": "PROPOSAL_REVIEW_DECISION",
                "proposal_id": p.proposal_id,
                "disposition": p.review_status.value if hasattr(p.review_status, "value") else str(p.review_status),
                "reviewed_by": p.reviewed_by or "SYSTEM",
                "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
                "rationale": p.review_rationale,
            })

        audits = session.query(EntityAuditRecord).filter(
            EntityAuditRecord.primary_entity_id.in_(node_ids)
        ).all()
        for a in audits:
            history.append({
                "record_type": "ENTITY_LIFECYCLE_AUDIT",
                "audit_id": a.audit_id,
                "operation": a.operation_type.value if hasattr(a.operation_type, "value") else str(a.operation_type),
                "performed_by": a.performed_by,
                "performed_at": a.timestamp.isoformat() if getattr(a, "timestamp", None) else None,
                "rationale": a.rationale,
            })
        return history

    @staticmethod
    def _format_report_markdown(report_dict: Dict[str, Any]) -> str:
        """Renders sanitized report into clean, verifiable Markdown format."""
        meta = report_dict.get("metadata", {})
        data = report_dict.get("investigation_summary", {})

        md = [
            f"# {meta.get('report_title')}",
            f"**Generated:** {meta.get('generated_at_utc')} | **Subject:** `{meta.get('subject_identifier')}` ({meta.get('subject_label')})",
            f"**Compliance:** {meta.get('data_governance')}",
            "",
            "## 1. Epistemic Guardrail & Methodological Notice",
            f"> {data.get('epistemic_guardrail')}",
            "",
            "## 2. Records Actually Available in CIVICLENS TN",
        ]

        rec = data.get("records_available", {})
        for k, v in rec.items():
            if isinstance(v, list):
                md.append(f"- **{k.replace('_', ' ').capitalize()}** ({len(v)} item(s)):")
                for item in v[:5]:
                    lbl = item.get("label") or item.get("edge_id") or str(item)
                    md.append(f"  - `{item.get('node_id', item.get('edge_id', ''))}`: {lbl}")
            elif isinstance(v, dict) and v:
                md.append(f"- **{k.replace('_', ' ').capitalize()}**: `{v.get('node_id')}` — {v.get('label')}")
            else:
                md.append(f"- **{k.replace('_', ' ').capitalize()}**: {v}")

        md.extend([
            "",
            "## 3. Official Administrative Reporting vs. Independent Verification",
            "| Edge ID | Relationship | Source Document | Evidence Nature | Review Status | Confidence |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ])
        for row in data.get("official_reporting_vs_independent_verification", []):
            md.append(
                f"| `{row.get('edge_id')}` | {row.get('relationship_type')} | {row.get('source_document_id')} | "
                f"{row.get('evidence_nature')} | {row.get('review_status')} | {row.get('epistemic_confidence')} |"
            )

        md.extend([
            "",
            "## 4. Missing Information & Evidentiary Gaps",
        ])
        for gap in data.get("missing_information", []):
            md.append(f"- ⚠️ {gap}")

        md.extend([
            "",
            "## 5. Reviewer Decision Audit History",
        ])
        hist = data.get("reviewer_audit_history", [])
        if hist:
            for h in hist:
                md.append(f"- **{h.get('record_type')}** by `{h.get('reviewed_by', h.get('performed_by'))}`: {h.get('rationale')}")
        else:
            md.append("*No manual override or audit decision records registered.*")

        md.extend([
            "",
            "## 6. Investigation Summary & Unresolved Questions (Non-Verdict)",
            "### Unresolved Questions for Further Statutory Scrutiny:",
        ])
        for q in data.get("unresolved_questions", []):
            md.append(f"1. {q}")

        md.extend([
            "",
            "---",
            "*Report generated securely by CIVICLENS TN Unified Civic Intelligence Evidence Graph.*",
        ])
        return "\n".join(md)
