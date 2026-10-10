"""
Script to import real Phase 4 Tamil news datasets (News CivicLens Batch 1, DS, and DS 2)
into SQLite database and run the full NLP, Intelligence, Event Comparison,
and Multi-Dimensional Bias Engine pipelines.
"""

import os
import sys
import uuid
import json
import hashlib
import pandas as pd
from datetime import datetime, timezone, date

# Ensure project root is on path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.database.base import Base
from backend.database.session import engine, SessionLocal
from backend.models.news import (
    Article, NewsSource, PoliticalEntity, PoliticalEvent, Topic,
    ArticleEntity, ArticleTopic, ArticleEvent, ArticleFeature,
    CoverageMetric, BiasIndicator, SourceComparison
)
from backend.nlp.multilingual_pipeline import MultilingualNewsNLPPipeline
from backend.nlp.intelligence_layer import IntelligenceLayerService, TOPIC_TAXONOMY_14
from backend.services.event_comparison_service import EventComparisonService, CrossSourceEventComparer
from backend.services.bias_indicator_engine import BiasIndicatorEngine
from backend.core.logger import setup_logger

logger = setup_logger("civiclens.scripts.import_real_news_data")


def import_real_news_dataset():
    # 1. Ensure DB tables exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    raw_dir = os.path.join(project_root, "data", "raw", "news")
    if not os.path.exists(raw_dir):
        logger.error(f"Raw data directory not found at {raw_dir}")
        return

    # Determine priority article CSV path (Prefer Phase 2 consolidated release)
    p2_csv = os.path.join(raw_dir, "ds2", "civiclens_phase2", "dataset_A_news_articles.csv")
    b2_csv = os.path.join(raw_dir, "ds1", "data", "batch2", "dataset_A_news_articles_batch2.csv")
    b1_csv = os.path.join(raw_dir, "dataset_A_news_articles_batch1.csv")

    if os.path.exists(p2_csv):
        art_csv = p2_csv
        logger.info(f"Using Phase 2 consolidated article dataset from {p2_csv}")
    elif os.path.exists(b2_csv):
        art_csv = b2_csv
        logger.info(f"Using Batch 2 article dataset from {b2_csv}")
    else:
        art_csv = b1_csv
        logger.info(f"Using Batch 1 article dataset from {b1_csv}")

    # Determine priority source CSV path
    p2_src_csv = os.path.join(raw_dir, "ds2", "civiclens_phase2", "dataset_E_source_metadata.csv")
    b1_src_csv = os.path.join(raw_dir, "dataset_E_source_metadata_batch1.csv")
    src_csv = p2_src_csv if os.path.exists(p2_src_csv) else b1_src_csv

    # Determine priority event CSV path
    p2_evt_csv = os.path.join(raw_dir, "ds2", "civiclens_phase2", "dataset_B_political_events.csv")
    b1_evt_csv = os.path.join(raw_dir, "dataset_B_political_events_batch1.csv")
    evt_csv = p2_evt_csv if os.path.exists(p2_evt_csv) else b1_evt_csv

    # Ground-Truth Dataset C (Entities & Aliases)
    p2_ent_csv = os.path.join(raw_dir, "ds2", "civiclens_phase2", "dataset_C_political_entities.csv")
    p2_alias_csv = os.path.join(raw_dir, "ds2", "civiclens_phase2", "dataset_C_aliases.csv")

    logger.info("Initializing Topic Taxonomy...")
    for tcode, tinfo in TOPIC_TAXONOMY_14.items():
        tid = f"topic_{tcode}"
        existing_top = db.query(Topic).filter((Topic.topic_id == tid) | (Topic.topic_code == tcode)).first()
        if not existing_top:
            db.add(Topic(
                topic_id=tid,
                topic_code=tcode,
                topic_name=tinfo.get("name", tcode.title()),
                description=tinfo.get("description", ""),
                keywords=tinfo.get("keywords", [])
            ))
    db.commit()

    logger.info("Initializing NLP & Intelligence components...")
    nlp_pipeline = MultilingualNewsNLPPipeline()
    intelligence_layer = IntelligenceLayerService()
    event_comparer = CrossSourceEventComparer()
    bias_engine = BiasIndicatorEngine(db=db)

    # 2. Load Source Metadata
    if os.path.exists(src_csv):
        df_src = pd.read_csv(src_csv)
        logger.info(f"Importing {len(df_src)} news sources...")

        for _, row in df_src.iterrows():
            sid = str(row["source_id"])
            sname = str(row["source_name"])
            url = str(row["website_url"]) if pd.notna(row["website_url"]) else ""
            base_domain = url.replace("https://", "").replace("http://", "").split("/")[0] if url else sname.lower().replace(" ", "")
            lang = "ta" if str(row["language"]).lower() == "tamil" else "en"

            existing_source = db.query(NewsSource).filter(
                (NewsSource.source_id == sid) | (NewsSource.source_name == sname)
            ).first()

            if not existing_source:
                domain = base_domain
                existing_dom = db.query(NewsSource).filter(NewsSource.domain == domain).first()
                if existing_dom:
                    domain = f"{base_domain}_{sid.lower().replace('-', '_')}"

                new_src = NewsSource(
                    source_id=sid,
                    source_name=sname,
                    domain=domain,
                    language=lang,
                    official_url=url if url else None,
                    robots_policy_checked=True,
                    collection_method="html_scraper",
                    priority="P1"
                )
                db.add(new_src)
                db.flush()
        db.commit()

    # 3. Load Ground-Truth Political Entities & Aliases (Dataset C)
    if os.path.exists(p2_ent_csv):
        df_c_ent = pd.read_csv(p2_ent_csv)
        df_c_alias = pd.read_csv(p2_alias_csv) if os.path.exists(p2_alias_csv) else pd.DataFrame()
        logger.info(f"Importing {len(df_c_ent)} ground-truth Dataset C political entities...")

        aliases_by_ent = {}
        if not df_c_alias.empty:
            for _, arow in df_c_alias.iterrows():
                eid = str(arow["entity_id"])
                alias_str = str(arow["alias"])
                if eid not in aliases_by_ent:
                    aliases_by_ent[eid] = []
                aliases_by_ent[eid].append(alias_str)

        for _, erow in df_c_ent.iterrows():
            eid = str(erow["entity_id"])
            orig_name = str(erow["entity_name_original"])
            eng_name = str(erow["entity_name_english"]) if pd.notna(erow["entity_name_english"]) else orig_name
            etype = str(erow["entity_type"]) if pd.notna(erow["entity_type"]) else "party"
            party_org = str(erow["party_or_organization"]) if pd.notna(erow["party_or_organization"]) else ""

            existing_ent = db.query(PoliticalEntity).filter(
                (PoliticalEntity.entity_id == eid) | (PoliticalEntity.name == orig_name)
            ).first()

            meta = {
                "english_name": eng_name,
                "party_or_organization": party_org,
                "aliases": aliases_by_ent.get(eid, [])
            }

            if not existing_ent:
                new_ent = PoliticalEntity(
                    entity_id=eid,
                    name=orig_name,
                    normalized_name=eng_name.lower(),
                    entity_type=etype,
                    metadata_json=meta
                )
                db.add(new_ent)
            else:
                existing_ent.entity_id = eid
                existing_ent.name = orig_name
                existing_ent.normalized_name = eng_name.lower()
                existing_ent.entity_type = etype
                existing_ent.metadata_json = meta
        db.commit()

    # 4. Load Political Events
    event_map = {}
    if os.path.exists(evt_csv):
        df_evt = pd.read_csv(evt_csv)
        logger.info(f"Importing {len(df_evt)} political events...")

        for _, row in df_evt.iterrows():
            eid = str(row["event_id"])
            etitle = str(row["event_title"])
            edate_str = str(row["event_date"]) if pd.notna(row["event_date"]) else "2026-01-01"

            try:
                edate = datetime.strptime(edate_str, "%Y-%m-%d").date()
            except Exception:
                edate = date.today()

            existing_evt = db.query(PoliticalEvent).filter(PoliticalEvent.event_id == eid).first()
            if not existing_evt:
                new_evt = PoliticalEvent(
                    event_id=eid,
                    event_name=etitle,
                    event_date=edate,
                    description=str(row.get("event_description", "")) if pd.notna(row.get("event_description")) else "",
                    location=str(row.get("location", "Tamil Nadu")) if pd.notna(row.get("location")) else "Tamil Nadu",
                    official_reference=str(row.get("official_reference_url", "")) if pd.notna(row.get("official_reference_url")) else None
                )
                db.add(new_evt)
                db.flush()
                event_map[eid] = new_evt
            else:
                event_map[eid] = existing_evt
        db.commit()

    # 5. Load & Ingest Articles
    df_art = pd.read_csv(art_csv)
    logger.info(f"Processing and ingesting {len(df_art)} real articles from {os.path.basename(art_csv)}...")

    imported_count = 0
    updated_count = 0

    for idx, row in df_art.iterrows():
        art_id = str(row["article_id"])
        url = str(row["article_url"]) if pd.notna(row["article_url"]) else f"https://civiclens.tn.gov.in/news/{art_id}"
        canon_url = url
        headline = str(row["headline_original"]) if pd.notna(row["headline_original"]) else ""
        text_content = str(row["article_summary"]) if pd.notna(row["article_summary"]) else headline
        lang_str = str(row["language"]).lower()
        lang = "ta" if "tamil" in lang_str else "en"
        ver_status = str(row.get("verification_status", "verified"))

        pdate_str = str(row["published_date"]) if pd.notna(row["published_date"]) else "2026-08-01"
        try:
            pub_date = datetime.strptime(pdate_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            pub_date = datetime.now(timezone.utc)

        text_hash = hashlib.sha256((headline + text_content).encode("utf-8")).hexdigest()

        source_id = str(row["source_id"])
        src_obj = db.query(NewsSource).filter(NewsSource.source_id == source_id).first()
        if not src_obj:
            src_name = str(row["source_name"])
            src_obj = db.query(NewsSource).filter(NewsSource.source_name == src_name).first()
            if not src_obj:
                src_obj = db.query(NewsSource).first()

        # NLP Processing
        nlp_doc = nlp_pipeline.process(
            original_text=text_content,
            override_language=lang
        )

        existing_art = db.query(Article).filter(
            (Article.article_id == art_id) | (Article.url == url)
        ).first()

        if existing_art:
            existing_art.title = headline
            existing_art.author = str(row["author"]) if pd.notna(row["author"]) else existing_art.author
            existing_art.section = str(row["category"]) if pd.notna(row["category"]) else existing_art.section
            existing_art.article_text = text_content
            existing_art.word_count = len(text_content.split())
            existing_art.is_test_fixture = False
            updated_count += 1
            db.flush()
            target_article = existing_art
        else:
            new_article = Article(
                article_id=art_id,
                source_id=src_obj.source_id if src_obj else "SRC-001",
                url=url,
                canonical_url=canon_url,
                retrieval_date=datetime.now(timezone.utc),
                publication_date=pub_date,
                title=headline,
                author=str(row["author"]) if pd.notna(row["author"]) else "Editorial Desk",
                section=str(row["category"]) if pd.notna(row["category"]) else "General",
                language=lang,
                article_text=text_content,
                word_count=len(text_content.split()),
                text_hash=text_hash,
                is_test_fixture=False
            )
            db.add(new_article)
            db.flush()
            target_article = new_article
            imported_count += 1

        # Extract Intelligence Entities & Topics
        intel_res = intelligence_layer.analyze_article(
            headline=headline,
            body_text=text_content
        )

        # Explicit Parties and Leaders from CSV
        parties_str = str(row["political_parties_mentioned"]) if pd.notna(row["political_parties_mentioned"]) else ""
        leaders_str = str(row["political_leaders_mentioned"]) if pd.notna(row["political_leaders_mentioned"]) else ""

        extracted_entities = intel_res.get("entities", [])
        for p in parties_str.split(";"):
            p_clean = p.strip()
            if p_clean and not any(e.get("name") == p_clean for e in extracted_entities):
                extracted_entities.append({"name": p_clean, "entity_type": "POLITICAL_PARTY", "prominence_score": 0.8})

        for l in leaders_str.split(";"):
            l_clean = l.strip()
            if l_clean and not any(e.get("name") == l_clean for e in extracted_entities):
                extracted_entities.append({"name": l_clean, "entity_type": "PERSON", "prominence_score": 0.85})

        for ent in extracted_entities:
            ename = ent.get("name")
            ecat = ent.get("entity_type", "POLITICAL_PARTY")
            p_score = ent.get("prominence_score", 0.5)

            p_entity = db.query(PoliticalEntity).filter(PoliticalEntity.name == ename).first()
            if not p_entity:
                p_entity = PoliticalEntity(
                    entity_id=f"ENT-{uuid.uuid4().hex[:8]}",
                    name=ename,
                    normalized_name=ename.lower(),
                    entity_type=ecat
                )
                db.add(p_entity)
                db.flush()

            existing_art_ent = db.query(ArticleEntity).filter(
                ArticleEntity.article_id == target_article.article_id,
                ArticleEntity.entity_id == p_entity.entity_id
            ).first()

            if not existing_art_ent:
                art_ent = ArticleEntity(
                    article_id=target_article.article_id,
                    entity_id=p_entity.entity_id,
                    mention_count=ent.get("mention_count", 1),
                    prominence_score=p_score
                )
                db.add(art_ent)

        # Topics
        topics = intel_res.get("topics", [])
        if not topics:
            top_code = str(row["category"]) if pd.notna(row["category"]) else "other"
            topics = [{"topic_id": top_code, "relevance_score": 0.85}]

        for t in topics:
            tcode = t.get("topic_id", "other")
            tid = f"topic_{tcode}"
            top_obj = db.query(Topic).filter(Topic.topic_id == tid).first()
            if not top_obj:
                top_obj = db.query(Topic).filter(Topic.topic_code == tcode).first()
            if top_obj:
                existing_art_top = db.query(ArticleTopic).filter(
                    ArticleTopic.article_id == target_article.article_id,
                    ArticleTopic.topic_id == top_obj.topic_id
                ).first()
                if not existing_art_top:
                    art_top = ArticleTopic(
                        article_id=target_article.article_id,
                        topic_id=top_obj.topic_id,
                        relevance_score=t.get("relevance_score", 0.85)
                    )
                    db.add(art_top)

        # Framing / Sentiment Features
        framing_val = str(row["framing_label"]) if pd.notna(row["framing_label"]) else "neutral"
        sentiment_val = str(row["sentiment_label"]) if pd.notna(row["sentiment_label"]) else "neutral"

        sent_score = 0.0
        if sentiment_val in ["positive", "supportive"]:
            sent_score = 0.5
        elif sentiment_val in ["negative", "critical"]:
            sent_score = -0.5

        existing_feat = db.query(ArticleFeature).filter(ArticleFeature.article_id == target_article.article_id).first()
        if not existing_feat:
            art_feat = ArticleFeature(
                article_id=target_article.article_id,
                headline_sentiment=sent_score,
                body_sentiment=sent_score,
                quote_count=1 if pd.notna(row.get("evidence_quote")) else 0,
                official_source_citation_count=1 if pd.notna(row.get("fact_check_status")) else 0,
                word_count=len(text_content.split()),
                framing_indicators={"label": framing_val, "verification_status": ver_status}
            )
            db.add(art_feat)
        else:
            existing_feat.framing_indicators = {"label": framing_val, "verification_status": ver_status}

        # Event Linkage
        evt_id = str(row["event_id"]) if pd.notna(row["event_id"]) else None
        if evt_id and evt_id in event_map:
            existing_art_evt = db.query(ArticleEvent).filter(
                ArticleEvent.article_id == target_article.article_id,
                ArticleEvent.event_id == evt_id
            ).first()
            if not existing_art_evt:
                art_evt = ArticleEvent(
                    article_id=target_article.article_id,
                    event_id=evt_id,
                    relevance_score=0.9
                )
                db.add(art_evt)

    db.commit()
    logger.info(f"Article processing complete: {imported_count} new imported, {updated_count} existing updated.")

    # 6. Execute Event Candidate Detection & Cross-Source Comparison
    logger.info("Executing Cross-Source Political Event Comparison...")
    events = db.query(PoliticalEvent).all()
    for evt in events:
        try:
            evt_comp = event_comparer.compare_event_coverage(db=db, event_id=evt.event_id)
            logger.info(f"Compared event {evt.event_id}: {evt_comp.get('total_articles', 0)} articles across {evt_comp.get('sources_count', 0)} sources.")
        except Exception as e:
            logger.warning(f"Event comparison note for {evt.event_id}: {e}")

    # 7. Execute Multi-Dimensional Bias Indicator Engine
    logger.info("Executing Multi-Dimensional Bias Indicator Engine...")
    sources = db.query(NewsSource).all()
    for src in sources:
        try:
            bias_res = bias_engine.generate_and_persist_source_indicators(
                source_id=src.source_id,
                days_window=3650
            )
            logger.info(f"Calculated indicators for source {src.source_name} ({src.source_id}): indicators count = {len(bias_res)}")
        except Exception as e:
            logger.warning(f"Bias indicator calculation note for {src.source_id}: {e}")

    db.commit()
    db.close()
    logger.info("Real multi-dataset import and analysis pipeline execution complete!")


if __name__ == "__main__":
    import_real_news_dataset()
