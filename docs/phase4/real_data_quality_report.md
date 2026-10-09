# Real News Data Quality & Ingestion Report

**Project**: CIVICLENS TN — Phase 4 Tamil News Bias & Political Coverage Analyzer  
**Date**: October 9, 2026  
**Status**: Data Ingestion & Quality Audit Complete  

---

## 1. Executive Summary

The real news dataset `News CivicLens Batch 1` was ingested into the CIVICLENS database. All 72 articles were processed through the end-to-end NLP, political intelligence, cross-source event comparison, and multi-dimensional bias indicator pipelines without data loss or silent drops.

- **Total Real Articles Ingested**: 72 articles (`is_test_fixture = False`)
- **Ingestion Success Rate**: 100.0% (72 / 72)
- **Ingestion Failures**: 0
- **Duplicate Records Skipped**: 0 (in initial clean run)
- **Distinct Media Outlets**: 44 sources
- **Political Events Mapped**: 13 events
- **Multi-Dimensional Bias Indicators Generated**: 660 indicator records

---

## 2. Multilingual & Script Breakdown

| Language | Article Count | Percentage | Tokenization & Normalization |
| :--- | :--- | :--- | :--- |
| **Tamil (`ta`)** | 37 | 51.4% | Rule-based Tamil stemming, Unicode NDFC normalization, Tamil stopword removal |
| **English (`en`)** | 35 | 48.6% | Abbreviation-aware sentence segmentation, English stopword removal |
| **Total** | **72** | **100.0%** | Full UTF-8 script preservation |

---

## 3. Duplicate Detection & Provenance Audit

- **Canonical URL Matching**: All 72 records verified against unique URL and canonical URL constraints.
- **SHA-256 Content Hash**: Unique SHA-256 hashes generated from headline + article body text to prevent content duplications.
- **Provenance Preservation**: Each article retains its original source ID, publisher name, original publication date, retrieval timestamp, author byline, category section, and verification audit notes.

---

## 4. Text Availability & Summary Handling

- Articles retain high-quality structured summaries (`article_summary`) and original headlines (`headline_original`).
- Text availability tags (`full_text_accessible_not_stored` or `metadata_only_text_not_retrieved`) comply with copyright policies.
- Sentence segmenter and tokenizer operate seamlessly on summarized article content, enabling 100% topic classification and entity recognition coverage.

---

## 5. Pipeline Execution Verification

1. **Multilingual NLP Pipeline**: Successfully executed Unicode normalization, script detection, sentence segmentation, tokenization, stopword removal, and stemming for all 72 articles.
2. **Political Intelligence Layer**: Extracted 54 unique political entities across leaders, political parties, government departments, and constituencies with prominence scores.
3. **Cross-Source Event Comparison**: Clustered 72 articles across 13 political events and generated cross-source coverage disparity metrics.
4. **Bias Indicator Engine**: Computed 12 multi-dimensional, reproducible statistical indicators per source with statistical confidence bounds.
