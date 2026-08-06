# Phase 1 - Baseline Data Pipeline & RAG Evaluation Report

## 1. Data Source Summary
- **Source API**: Crossref REST API
- **Total Records Ingested**: 24
- **Cleaned Dataset Size**: 24 rows

## 2. Baseline RAG Evaluation Metrics
- **Evaluated Samples**: 18
- **Retrieval Hit Rate**: 1.0000
- **Mean Token F1**: 0.1110
- **Judge Accuracy**: 0.0556
- **Mean Judge Score (1-5)**: 1.11

## 3. Data Observability & Health
### Data Quality Checks
- **Status**: PASSED
- **Null Paper IDs**: 0
- **Duplicate Paper IDs**: 0
- **Empty Summaries**: 0

### Data Freshness Monitoring
- **Status**: FRESH
- **Latest Published Date**: 2026-08-05
- **Oldest Published Date**: 2026-02-12
- **Stale Rows (>180 days)**: 0 / 24
