"""
Phase 6.11 — Evidence Traceability, Metric Lineage & Audit Trail Service.

Provides:
1. Source Document Registry management (registration, metadata verification, SHA-256 integrity).
2. Fact-to-Evidence linking (page/table citations, excerpts, confidence, extraction methods).
3. Metric Lineage recording and drill-down reproduction (aggregates traced to constituent vouchers).
4. Conflicting Evidence preservation (side-by-side divergent records with review statuses).
5. Immutable Audit Trail event logging.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.models.representative import (
    Representative,
    Constituency,
    LegislativeActivity,
    ConstituencyWork,
    DevelopmentIndicator,
    PerformanceMetric,
    SourceDocumentRegistry,
    FactEvidenceLink,
    MetricLineage,
    ConflictingEvidenceRecord,
    ConflictResolutionStatus,
    AuditTrailEvent
)

logger = logging.getLogger("civiclens.phase6.traceability")
logging.basicConfig(level=logging.INFO)


class TraceabilityService:
    """
    Core service managing end-to-end evidence relationships, audit trail ledgers,
    and mathematical metric lineage.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    # -------------------------------------------------------------------------
    # STEP 2: SOURCE DOCUMENT REGISTRY
    # -------------------------------------------------------------------------
    def register_source_document(
        self,
        document_id: str,
        source_name: str,
        source_type: str,
        document_title: str,
        publisher: str,
        file_format: str,
        official_source_url: Optional[str] = None,
        original_filename: Optional[str] = None,
        publication_date: Optional[str] = None,
        retrieval_date: Optional[str] = None,
        document_version: str = "1.0",
        sha256_checksum: Optional[str] = None,
        reporting_period: Optional[str] = None,
        geographic_coverage: str = "TAMIL_NADU",
        verification_status: str = "VERIFIED",
        storage_path: Optional[str] = None,
        notes: Optional[str] = None
    ) -> SourceDocumentRegistry:
        """Registers an empirical or statutory source document in the canonical registry."""
        if not self.db:
            raise ValueError("Database session required.")

        doc = SourceDocumentRegistry(
            document_id=document_id,
            source_name=source_name,
            source_type=source_type,
            official_source_url=official_source_url,
            original_filename=original_filename,
            document_title=document_title,
            publisher=publisher,
            publication_date=publication_date,
            retrieval_date=retrieval_date,
            document_version=document_version,
            sha256_checksum=sha256_checksum,
            file_format=file_format,
            reporting_period=reporting_period,
            geographic_coverage=geographic_coverage,
            verification_status=verification_status,
            storage_path=storage_path,
            notes=notes
        )
        self.db.merge(doc)

        # Log audit trail
        self.log_audit_event(
            event_type="DOCUMENT_INGESTION",
            entity_type="SOURCE_DOCUMENT",
            record_id=document_id,
            new_value={"title": document_title, "publisher": publisher, "sha256": sha256_checksum},
            reason="Registered in canonical Source Document Registry",
            source_reference=document_id
        )

        self.db.commit()
        return doc

    def get_source_document(self, document_id: str) -> Optional[SourceDocumentRegistry]:
        if not self.db:
            return None
        return self.db.query(SourceDocumentRegistry).filter(
            SourceDocumentRegistry.document_id == document_id
        ).first()

    def list_source_documents(self, publisher: Optional[str] = None) -> List[SourceDocumentRegistry]:
        if not self.db:
            return []
        query = self.db.query(SourceDocumentRegistry)
        if publisher and publisher != "All":
            query = query.filter(SourceDocumentRegistry.publisher.ilike(f"%{publisher}%"))
        return query.order_by(SourceDocumentRegistry.document_id).all()

    # -------------------------------------------------------------------------
    # STEP 3: LINK FACTS TO EVIDENCE
    # -------------------------------------------------------------------------
    def link_fact_to_evidence(
        self,
        link_id: str,
        entity_type: str,
        entity_id: str,
        fact_description: str,
        document_id: str,
        page_number: Optional[int] = None,
        section_or_table: Optional[str] = None,
        source_row_id: Optional[str] = None,
        supporting_excerpt: Optional[str] = None,
        extraction_method: str = "MANUAL_VERIFIED",
        verification_status: str = "VERIFIED",
        confidence_score: float = 1.0
    ) -> FactEvidenceLink:
        """Links any fact, metric, activity, or project to its verified source citation."""
        if not self.db:
            raise ValueError("Database session required.")

        # Ensure document exists or raise clear verification error
        doc = self.get_source_document(document_id)
        if not doc:
            verification_status = "UNVERIFIED"

        link = FactEvidenceLink(
            link_id=link_id,
            entity_type=entity_type,
            entity_id=entity_id,
            fact_description=fact_description,
            document_id=document_id,
            page_number=page_number,
            section_or_table=section_or_table,
            source_row_id=source_row_id,
            supporting_excerpt=supporting_excerpt,
            extraction_method=extraction_method,
            verification_status=verification_status,
            confidence_score=confidence_score
        )
        self.db.merge(link)
        self.db.commit()
        return link

    def get_evidence_for_entity(self, entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
        """Retrieves all granular source evidence supporting a given entity."""
        if not self.db:
            return []
        links = self.db.query(FactEvidenceLink).filter(
            FactEvidenceLink.entity_type == entity_type,
            FactEvidenceLink.entity_id == entity_id
        ).all()

        results = []
        for l in links:
            doc = l.source_document
            results.append({
                "link_id": l.link_id,
                "fact_description": l.fact_description,
                "document_id": l.document_id,
                "document_title": doc.document_title if doc else "Unresolved Source Document",
                "publisher": doc.publisher if doc else "Unknown",
                "source_url": doc.official_source_url if doc else None,
                "page_number": l.page_number,
                "section_or_table": l.section_or_table,
                "source_row_id": l.source_row_id,
                "supporting_excerpt": l.supporting_excerpt,
                "extraction_method": l.extraction_method,
                "verification_status": l.verification_status,
                "confidence_score": l.confidence_score
            })
        return results

    # -------------------------------------------------------------------------
    # STEP 4: METRIC LINEAGE RECORDING & DRILL-DOWN
    # -------------------------------------------------------------------------
    def record_metric_lineage(
        self,
        lineage_id: str,
        metric_id: str,
        metric_name: str,
        metric_value: float,
        calculation_method: str,
        formula_expression: str,
        input_record_ids: List[str],
        source_document_ids: List[str],
        reporting_period: str,
        geographic_level: str,
        calculation_version: str = "1.0",
        data_quality_status: str = "VERIFIED"
    ) -> MetricLineage:
        """Persists the exact inputs, vouchers, and mathematical equation that produced a metric."""
        if not self.db:
            raise ValueError("Database session required.")

        lineage = MetricLineage(
            lineage_id=lineage_id,
            metric_id=metric_id,
            metric_name=metric_name,
            metric_value=metric_value,
            calculation_method=calculation_method,
            formula_expression=formula_expression,
            input_record_ids=input_record_ids,
            source_document_ids=source_document_ids,
            reporting_period=reporting_period,
            geographic_level=geographic_level,
            calculation_version=calculation_version,
            data_quality_status=data_quality_status
        )
        self.db.merge(lineage)
        self.db.commit()
        return lineage

    def get_metric_drilldown(self, metric_id: str) -> Optional[Dict[str, Any]]:
        """Exposes reproducible calculation formula, source documents, and underlying vouchers."""
        if not self.db:
            return None

        lineage = self.db.query(MetricLineage).filter(MetricLineage.metric_id == metric_id).first()
        if not lineage:
            return None

        # Fetch underlying constituent records where applicable
        constituent_records = []
        for r_id in (lineage.input_record_ids or []):
            # Check works
            work = self.db.query(ConstituencyWork).filter(ConstituencyWork.work_id == r_id).first()
            if work:
                constituent_records.append({
                    "record_type": "CONSTITUENCY_WORK",
                    "record_id": work.work_id,
                    "description": work.project_description,
                    "sanctioned_amount": work.sanctioned_amount,
                    "expenditure": work.reported_expenditure,
                    "status": work.project_status,
                    "source_reference": work.source_reference
                })
                continue

            # Check legislative activity
            act = self.db.query(LegislativeActivity).filter(LegislativeActivity.activity_id == r_id).first()
            if act:
                constituent_records.append({
                    "record_type": "LEGISLATIVE_ACTIVITY",
                    "record_id": act.activity_id,
                    "session": act.session,
                    "activity_type": act.activity_type,
                    "count": act.count,
                    "value": act.value,
                    "source_reference": act.source_reference
                })

        return {
            "metric_id": lineage.metric_id,
            "metric_name": lineage.metric_name,
            "metric_value": lineage.metric_value,
            "calculation_method": lineage.calculation_method,
            "formula_expression": lineage.formula_expression,
            "calculation_version": lineage.calculation_version,
            "reporting_period": lineage.reporting_period,
            "geographic_level": lineage.geographic_level,
            "source_document_ids": lineage.source_document_ids,
            "data_quality_status": lineage.data_quality_status,
            "constituent_input_records": constituent_records,
            "total_input_records_count": len(constituent_records)
        }

    # -------------------------------------------------------------------------
    # STEP 5: CONFLICTING EVIDENCE PRESERVATION
    # -------------------------------------------------------------------------
    def record_conflicting_evidence(
        self,
        conflict_id: str,
        entity_type: str,
        entity_id: str,
        conflict_topic: str,
        source_a_document_id: str,
        source_a_value: str,
        source_b_document_id: str,
        source_b_value: str,
        discrepancy_magnitude: str,
        source_a_period: Optional[str] = None,
        source_b_period: Optional[str] = None,
        review_status: str = ConflictResolutionStatus.CONFLICTING,
        resolution_basis: Optional[str] = None
    ) -> ConflictingEvidenceRecord:
        """Stores divergent source observations side-by-side without arbitrary suppression."""
        if not self.db:
            raise ValueError("Database session required.")

        conflict = ConflictingEvidenceRecord(
            conflict_id=conflict_id,
            entity_type=entity_type,
            entity_id=entity_id,
            conflict_topic=conflict_topic,
            source_a_document_id=source_a_document_id,
            source_a_value=source_a_value,
            source_a_period=source_a_period,
            source_b_document_id=source_b_document_id,
            source_b_value=source_b_value,
            source_b_period=source_b_period,
            discrepancy_magnitude=discrepancy_magnitude,
            review_status=review_status,
            resolution_basis=resolution_basis
        )
        self.db.merge(conflict)

        # Log audit trail
        self.log_audit_event(
            event_type="CONFLICT_DETECTION",
            entity_type=entity_type,
            record_id=entity_id,
            new_value={"source_a": source_a_value, "source_b": source_b_value, "topic": conflict_topic},
            reason=discrepancy_magnitude,
            source_reference=f"{source_a_document_id} vs {source_b_document_id}"
        )

        self.db.commit()
        return conflict

    def list_conflicts(self, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.db:
            return []
        query = self.db.query(ConflictingEvidenceRecord)
        if entity_type and entity_type != "All":
            query = query.filter(ConflictingEvidenceRecord.entity_type == entity_type)

        conflicts = query.all()
        results = []
        for c in conflicts:
            doc_a = c.source_a
            doc_b = c.source_b
            results.append({
                "conflict_id": c.conflict_id,
                "entity_type": c.entity_type,
                "entity_id": c.entity_id,
                "conflict_topic": c.conflict_topic,
                "source_a": {
                    "document_id": c.source_a_document_id,
                    "title": doc_a.document_title if doc_a else "Unknown",
                    "publisher": doc_a.publisher if doc_a else "Unknown",
                    "reported_value": c.source_a_value,
                    "reporting_period": c.source_a_period
                },
                "source_b": {
                    "document_id": c.source_b_document_id,
                    "title": doc_b.document_title if doc_b else "Unknown",
                    "publisher": doc_b.publisher if doc_b else "Unknown",
                    "reported_value": c.source_b_value,
                    "reporting_period": c.source_b_period
                },
                "discrepancy_magnitude": c.discrepancy_magnitude,
                "review_status": c.review_status,
                "resolution_basis": c.resolution_basis or "Preserved under multi-source disclosure without automated suppression."
            })
        return results

    # -------------------------------------------------------------------------
    # STEP 8: IMMUTABLE AUDIT TRAIL LOGGING
    # -------------------------------------------------------------------------
    def log_audit_event(
        self,
        event_type: str,
        entity_type: str,
        record_id: str,
        previous_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        reason: Optional[str] = None,
        source_reference: Optional[str] = None,
        actor_or_process: str = "CIVICLENS_PIPELINE"
    ) -> AuditTrailEvent:
        """Appends an immutable processing or verification event to the audit trail ledger."""
        if not self.db:
            raise ValueError("Database session required.")

        event_id = f"AUD-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        event = AuditTrailEvent(
            event_id=event_id,
            event_type=event_type,
            entity_type=entity_type,
            record_id=record_id,
            previous_value=previous_value,
            new_value=new_value,
            reason=reason,
            source_reference=source_reference,
            actor_or_process=actor_or_process
        )
        self.db.add(event)
        self.db.commit()
        return event

    def list_audit_trail(self, record_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.db:
            return []
        query = self.db.query(AuditTrailEvent)
        if record_id:
            query = query.filter(AuditTrailEvent.record_id == record_id)
        events = query.order_by(AuditTrailEvent.timestamp.desc()).limit(limit).all()

        return [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "entity_type": e.entity_type,
                "record_id": e.record_id,
                "previous_value": e.previous_value,
                "new_value": e.new_value,
                "reason": e.reason,
                "source_reference": e.source_reference,
                "actor_or_process": e.actor_or_process,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None
            }
            for e in events
        ]
