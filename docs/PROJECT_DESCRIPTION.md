# Project Description

## Overview
This repository contains an internal analytics platform tailored for nails & cosmetics e-commerce teams. It combines Elasticsearch-backed data ingestion, attribute intelligence, supplier quality tracking, and a Streamlit dashboard into a single deployable toolkit. The system ingests Romanian product catalog exports, enriches them with derived attributes, captures supplier incidents, and surfaces KPIs through both an API and an interactive UI.

## Core Capabilities
- **Product Intelligence** – Normalize catalog exports, extract attributes (volum, finisaj, shade code) using regex/keyword heuristics, and expose SKU health metrics.
- **Supplier Quality Management** – Log incidents, analyze damage rates, and monitor trends per furnizor, categorie, and tip produs.
- **Daily Performance Tracking** – Aggregate orders/returns into SKU-level daily stats for conversion analytics.
- **Dashboards & API** – Streamlit UI for operators plus a FastAPI layer for programmatic ingestion, queries, and KPI retrieval.

## Architecture Highlights
- **Storage**: Elasticsearch indices (`products`, `sku_daily_stats`, `supplier_incidents`) with explicit mappings for UTF-8 Romanian data.
- **Processing**: Python ingestion scripts (`ingest_products.py`, `run_all_ingest.py`) and attribute extraction logic in `attribute_extraction.py`.
- **Experience Layer**: `app/streamlit_app.py` dashboard and `api/main.py` REST API with automatic Swagger docs.
- **Tooling**: Pytest suite for regression coverage, Postman collection for API verification, and structured logging for observability.

## Objectives
1. Provide a reproducible local environment for catalog analytics and supplier monitoring.
2. Enable both manual ops workflows (dashboard) and automated pipelines (API/CLI scripts).
3. Preserve Romanian linguistic nuances end-to-end, ensuring data quality for regional teams.
4. Offer extensible building blocks (mappings, services, schemas) for future product KPIs.
