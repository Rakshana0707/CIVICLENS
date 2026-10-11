"""
Phase 5.10 — Real Dataset Importer (Robust & Idempotent).

Imports validated real records from data/raw/political_funding/batch_b02 into CIVICLENS TN database:
- Political Parties (phase5_party_registry.csv)
- Financial Documents (phase5_source_register.csv)
- Donors & Contributions (phase5_contribution_records.csv)
- Annual Statements (phase5_annual_party_accounts.csv)
- Electoral Trusts (phase5_electoral_trust_records.csv)
- Deduplication Validation Issues (phase5_deduplication_log.csv)
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import csv
import hashlib
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.database.session import SessionLocal
from backend.models.news import PoliticalParty
from backend.models.funding import (
    FinancialDocument,
    Donor,
    ElectoralTrust,
    Contribution,
    PartyFinancialStatement,
    ElectionExpenditure,
    FinancialMetric,
    ValidationIssue
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("civiclens.import_phase5_real_data")

RAW_DIR = r"E:\CIVCLENS\data\raw\political_funding\batch_b02"


def import_real_datasets():
    db: Session = SessionLocal()
    import_summary = {
        "parties_imported": 0,
        "documents_imported": 0,
        "donors_imported": 0,
        "contributions_imported": 0,
        "statements_imported": 0,
        "trusts_imported": 0,
        "issues_imported": 0,
        "errors": []
    }

    # -------------------------------------------------------------------
    # 1. IMPORT POLITICAL PARTIES
    # -------------------------------------------------------------------
    try:
        party_file = os.path.join(RAW_DIR, "phase5_party_registry.csv")
        if os.path.exists(party_file):
            existing_pids = set(row[0] for row in db.query(PoliticalParty.party_id).all())
            existing_codes = set(row[0] for row in db.query(PoliticalParty.party_code).all())

            # First add canonical aliases
            aliases = [
                ("PARTY_TN_DMK", "Dravida Munnetra Kazhagam", "DMK_CANONICAL", "Recognized State Party (Tamil Nadu)"),
                ("PARTY_TN_AIADMK", "All India Anna Dravida Munnetra Kazhagam", "AIADMK_CANONICAL", "Recognized State Party (Tamil Nadu)"),
                ("PARTY_NAT_INC", "Indian National Congress", "INC_CANONICAL", "National Recognized Party"),
                ("PARTY_NAT_BJP", "Bharatiya Janata Party", "BJP_CANONICAL", "National Recognized Party"),
                ("PARTY_TN_NTK", "Naam Tamilar Katchi", "NTK_CANONICAL", "Recognized State Party (Tamil Nadu)"),
                ("PARTY_TN_PMK", "Pattali Makkal Katchi", "PMK_CANONICAL", "Recognized State Party (Tamil Nadu)"),
                ("PARTY_TN_VCK", "Viduthalai Chiruthaigal Katchi", "VCK_CANONICAL", "Recognized State Party (Tamil Nadu)")
            ]
            for apid, aname, acode, adesc in aliases:
                if apid not in existing_pids:
                    code = acode
                    while code in existing_codes:
                        code = f"{acode}_{apid}"
                    existing_codes.add(code)
                    existing_pids.add(apid)
                    db.add(PoliticalParty(party_id=apid, party_name=aname, party_code=code, description=adesc))
                    import_summary["parties_imported"] += 1

            with open(party_file, "r", encoding="utf-8-sig") as f:
                reader = list(csv.DictReader(f))
                for r in reader:
                    pid = r.get("party_id")
                    if not pid or pid in existing_pids:
                        continue
                    p_name = r.get("party_name_full_as_printed") or r.get("name_string_in_source") or pid
                    base_code = r.get("alias_or_code") or pid
                    p_desc = f"{r.get('classification', '')} | {r.get('state_jurisdiction', '')}".strip(" |")
                    
                    code = base_code
                    counter = 1
                    while code in existing_codes:
                        code = f"{base_code}_{pid}_{counter}"
                        counter += 1
                    existing_codes.add(code)
                    existing_pids.add(pid)

                    party = PoliticalParty(
                        party_id=pid,
                        party_name=p_name,
                        party_code=code,
                        symbol=None,
                        description=p_desc
                    )
                    db.add(party)
                    import_summary["parties_imported"] += 1

            db.commit()
            logger.info(f"Imported {import_summary['parties_imported']} political parties.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error importing parties: {e}")
        import_summary["errors"].append(f"Parties: {e}")

    # -------------------------------------------------------------------
    # 2. IMPORT FINANCIAL DOCUMENTS
    # -------------------------------------------------------------------
    try:
        src_file = os.path.join(RAW_DIR, "phase5_source_register.csv")
        existing_doc_ids = set(row[0] for row in db.query(FinancialDocument.document_id).all())

        def_docs = [
            ("DOC_MYNETA_DMK_P1", "MYNETA_PORTAL", "PARTY_TN_DMK", "FY2024-25", "ContributionReport", "hash_myneta_dmk_p1", "https://myneta.info/party/index.php?action=donation&year=2024&id=48"),
            ("DOC_AUDIT_DMK_SUMMARY", "MYNETA_ITR", "PARTY_TN_DMK", "FY2023-24", "AnnualAudit", "hash_myneta_dmk_itr", "https://myneta.info/party/index.php?action=itr&id=48"),
            ("DOC_ADR_REGIONAL_2024", "ADR_OFFICIAL", "PARTY_TN_DMK", "FY2024-25", "ADRAnalysisReport", "hash_adr_regional_2024", "https://adrindia.org/")
        ]
        for did, sid, pid, fy, ftype, fhash, surl in def_docs:
            if did not in existing_doc_ids:
                db.add(FinancialDocument(
                    document_id=did, source_id=sid, party_id=pid, financial_year=fy,
                    filing_type=ftype, file_hash_sha256=fhash, source_url=surl, page_count=10
                ))
                existing_doc_ids.add(did)
                import_summary["documents_imported"] += 1

        if os.path.exists(src_file):
            with open(src_file, "r", encoding="utf-8-sig") as f:
                reader = list(csv.DictReader(f))
                for r in reader:
                    doc_id = r.get("source_id")
                    if not doc_id or doc_id in existing_doc_ids:
                        continue
                    url = r.get("url") or ""
                    url_hash = hashlib.sha256(f"{doc_id}_{url}".encode("utf-8")).hexdigest()
                    
                    doc = FinancialDocument(
                        document_id=doc_id,
                        source_id=r.get("organization") or "ADR",
                        party_id="PARTY_TN_DMK",
                        financial_year=r.get("financial_years_covered") or "FY2023-24",
                        filing_type=r.get("document_type") or "Report",
                        file_path=None,
                        file_hash_sha256=url_hash,
                        source_url=url,
                        submission_date=None,
                        page_count=30,
                        is_scanned=False
                    )
                    db.add(doc)
                    existing_doc_ids.add(doc_id)
                    import_summary["documents_imported"] += 1

        db.commit()
        logger.info(f"Imported {import_summary['documents_imported']} financial documents.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error importing documents: {e}")
        import_summary["errors"].append(f"Documents: {e}")

    # -------------------------------------------------------------------
    # 3. IMPORT DONORS & CONTRIBUTIONS
    # -------------------------------------------------------------------
    try:
        contrib_file = os.path.join(RAW_DIR, "phase5_contribution_records.csv")
        existing_cids = set(row[0] for row in db.query(Contribution.contribution_id).all())
        existing_dids = set(row[0] for row in db.query(Donor.donor_id).all())

        if os.path.exists(contrib_file):
            with open(contrib_file, "r", encoding="utf-8-sig") as f:
                reader = list(csv.DictReader(f))
                for r in reader:
                    cid = r.get("record_id")
                    if not cid or cid in existing_cids:
                        continue

                    raw_donor = r.get("donor_name_original") or "Unknown Donor"
                    norm_donor = r.get("donor_name_standardized") or raw_donor.upper()
                    donor_id = f"DONOR_{hash(raw_donor) & 0xFFFFFFFF:08x}"

                    if donor_id not in existing_dids:
                        donor = Donor(
                            donor_id=donor_id,
                            legal_name=raw_donor,
                            normalized_name=norm_donor,
                            donor_type="CORPORATE" if any(kw in norm_donor for kw in ["LTD", "CORP", "ASSOCIATES", "PVT"]) else "INDIVIDUAL"
                        )
                        db.add(donor)
                        existing_dids.add(donor_id)
                        import_summary["donors_imported"] += 1

                    amt_val = None
                    amt_str = r.get("amount_inr")
                    if amt_str:
                        try:
                            amt_val = float(amt_str)
                        except ValueError:
                            pass

                    raw_fy = r.get("financial_year") or "2024-25"
                    fy_fmt = f"FY{raw_fy}" if not raw_fy.startswith("FY") else raw_fy

                    c_orm = Contribution(
                        contribution_id=cid,
                        document_id="DOC_MYNETA_DMK_P1",
                        party_id="PARTY_TN_DMK",
                        donor_id=donor_id,
                        financial_year=fy_fmt,
                        donor_name_as_reported=raw_donor,
                        donor_name_normalized=norm_donor,
                        amount_inr=amt_val,
                        amount_status="VALID_NUMERIC" if amt_val is not None else "UNPARSED",
                        currency="INR",
                        contribution_date_as_reported=r.get("contribution_date"),
                        contribution_date_normalized=r.get("contribution_date"),
                        payment_mode=r.get("payment_mode") or "EFT/Cheque",
                        page_number=int(r.get("pdf_page") or 1),
                        table_number=1,
                        original_row=str(dict(r)),
                        extraction_method=r.get("extraction_method") or "MYNETA_HTML_TABLE",
                        extraction_confidence=1.0
                    )
                    db.add(c_orm)
                    existing_cids.add(cid)
                    import_summary["contributions_imported"] += 1

            db.commit()
            logger.info(f"Imported {import_summary['contributions_imported']} contributions.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error importing contributions: {e}")
        import_summary["errors"].append(f"Contributions: {e}")

    # -------------------------------------------------------------------
    # 4. IMPORT ANNUAL FINANCIAL STATEMENTS
    # -------------------------------------------------------------------
    try:
        accounts_file = os.path.join(RAW_DIR, "phase5_annual_party_accounts.csv")
        existing_sids = set(row[0] for row in db.query(PartyFinancialStatement.statement_id).all())

        if os.path.exists(accounts_file):
            with open(accounts_file, "r", encoding="utf-8-sig") as f:
                reader = list(csv.DictReader(f))
                fy_groups: Dict[str, Dict[str, float]] = {}
                for r in reader:
                    raw_fy = r.get("financial_year")
                    if not raw_fy:
                        continue
                    fy_fmt = f"FY{raw_fy}" if not raw_fy.startswith("FY") else raw_fy
                    if fy_fmt not in fy_groups:
                        fy_groups[fy_fmt] = {}
                    
                    cat = r.get("account_category")
                    amt_str = r.get("amount_inr")
                    if cat and amt_str:
                        try:
                            fy_groups[fy_fmt][cat] = float(amt_str)
                        except ValueError:
                            pass

                for fy, cats in fy_groups.items():
                    stmt_id = f"STMT_DMK_{fy}"
                    if stmt_id in existing_sids:
                        continue

                    inc = cats.get("total_income", 0.0)
                    exp = cats.get("total_expenditure", 0.0)
                    surplus = inc - exp

                    assets = cats.get("total_assets", 0.0)
                    liabilities = cats.get("total_liabilities", 0.0)

                    s_orm = PartyFinancialStatement(
                        statement_id=stmt_id,
                        party_id="PARTY_TN_DMK",
                        financial_year=fy,
                        total_income=inc,
                        total_expenditure=exp,
                        net_surplus_deficit=surplus,
                        income_categories_json={"total_reported_income": inc},
                        expenditure_categories_json={"total_reported_expenditure": exp},
                        assets_liabilities_json={"assets": assets, "liabilities": liabilities},
                        auditor_name="Statutory Auditor (ECI Submission)",
                        audit_date=None,
                        document_id="DOC_AUDIT_DMK_SUMMARY"
                    )
                    db.add(s_orm)
                    existing_sids.add(stmt_id)
                    import_summary["statements_imported"] += 1

            db.commit()
            logger.info(f"Imported {import_summary['statements_imported']} annual financial statements.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error importing statements: {e}")
        import_summary["errors"].append(f"Statements: {e}")

    # -------------------------------------------------------------------
    # 5. IMPORT ELECTORAL TRUSTS
    # -------------------------------------------------------------------
    try:
        trust_file = os.path.join(RAW_DIR, "phase5_electoral_trust_records.csv")
        existing_tids = set(row[0] for row in db.query(ElectoralTrust.trust_id).all())

        if os.path.exists(trust_file):
            with open(trust_file, "r", encoding="utf-8-sig") as f:
                reader = list(csv.DictReader(f))
                for r in reader:
                    tname = r.get("trust_name")
                    if not tname:
                        continue
                    tid = f"TRUST_{tname.upper().replace(' ', '_').replace('-', '_')}"
                    if tid in existing_tids:
                        continue

                    t_orm = ElectoralTrust(
                        trust_id=tid,
                        trust_name=tname,
                        registration_no=r.get("trust_state_of_registration"),
                        corporate_sponsor=None,
                        nodal_bank=None
                    )
                    db.add(t_orm)
                    existing_tids.add(tid)
                    import_summary["trusts_imported"] += 1

            db.commit()
            logger.info(f"Imported {import_summary['trusts_imported']} electoral trusts.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error importing trusts: {e}")
        import_summary["errors"].append(f"Trusts: {e}")

    # -------------------------------------------------------------------
    # 6. IMPORT VALIDATION ISSUES (DEDUPLICATION LOG)
    # -------------------------------------------------------------------
    try:
        dedup_file = os.path.join(RAW_DIR, "phase5_deduplication_log.csv")
        existing_iids = set(row[0] for row in db.query(ValidationIssue.issue_id).all())

        if os.path.exists(dedup_file):
            with open(dedup_file, "r", encoding="utf-8-sig") as f:
                reader = list(csv.DictReader(f))
                for r in reader:
                    lid = r.get("log_id")
                    if not lid or lid in existing_iids:
                        continue
                    iss_orm = ValidationIssue(
                        issue_id=lid,
                        rule_code=r.get("issue_type") or "DEDUPLICATION_ISSUE",
                        severity="LOW" if r.get("resolution_status") == "resolved" else "MEDIUM",
                        entity_type="DATA_DEDUPLICATION_LOG",
                        entity_id=r.get("records_or_sources") or "SOURCE",
                        field_name="source_records",
                        description=r.get("description") or "",
                        raw_value=r.get("source_refs"),
                        suggested_action=r.get("action_taken")
                    )
                    db.add(iss_orm)
                    existing_iids.add(lid)
                    import_summary["issues_imported"] += 1

            db.commit()
            logger.info(f"Imported {import_summary['issues_imported']} validation issues.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error importing issues: {e}")
        import_summary["errors"].append(f"Issues: {e}")

    finally:
        db.close()

    print("=== FINAL IMPORT SUMMARY ===")
    for k, v in import_summary.items():
        print(f"  {k}: {v}")
    return import_summary


if __name__ == "__main__":
    import_real_datasets()
