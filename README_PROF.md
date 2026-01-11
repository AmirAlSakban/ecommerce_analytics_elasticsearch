# E-Commerce Analytics Platform — Evaluation Document

## 1. Project Overview

This project is a complete analytics platform for a nails and cosmetics e-commerce business, built on **Elasticsearch** as the core data engine. It ingests product catalogs, tracks supplier quality incidents, and provides real-time analytics through a REST API and interactive dashboard. Elasticsearch enables fast full-text search, complex aggregations, and scalable analytics on Romanian-language product data with millions of potential attribute combinations—capabilities far beyond traditional relational databases for search-driven, unstructured catalog data.

---

## 2. Milestones Coverage

| Milestone | Implementation | Demonstration |
|-----------|----------------|---------------|
| **1. Project Description** | Complete analytics platform combining Elasticsearch indexing, attribute intelligence, supplier tracking, REST API, and Streamlit UI | [docs/PROJECT_DESCRIPTION.md](docs/PROJECT_DESCRIPTION.md) |
| **2. Use Cases** | 9 concrete use cases covering product ingestion, attribute auditing, supplier incident logging, damage rate monitoring, and daily SKU stats | [docs/USE_CASES.md](docs/USE_CASES.md) |
| **3. REST API + Swagger** | FastAPI with 8 endpoints for products, incidents, and analytics; auto-generated Swagger documentation at `/docs` | `http://localhost:8000/docs` (after running `uvicorn api.main:app`) |
| **4. Elasticsearch Mapping** | Three explicit mappings: `products` (30+ fields with keyword normalization), `sku_daily_stats`, `supplier_incidents` | [elastic_mappings.py](elastic_mappings.py) — view mappings directly |
| **5. Implementation** | Python ingestion scripts, attribute extraction logic, FastAPI services, Elasticsearch queries with aggregations and pipeline aggs | All code in repository: `ingest_*.py`, `api/`, `attribute_extraction.py`, `supplier_incidents.py` |
| **6. Postman Testing** | Complete collection with positive/negative test cases for all API endpoints | [postman/EcommerceAnalyticsAPI.postman_collection.json](postman/EcommerceAnalyticsAPI.postman_collection.json) — import to Postman |

---

## 3. Use Cases

1. **Ingest Product Catalog** — Load Excel exports into Elasticsearch with automatic attribute extraction
2. **Detect Missing Attributes** — Find SKUs lacking critical fields (color codes, volumes, finish types)
3. **Audit Attribute Coverage** — Calculate completeness % by category with revenue impact
4. **Log Supplier Incidents** — Record damage events with shipment details and root causes
5. **Monitor Supplier Damage Rates** — Aggregate KPIs showing damage % and quantity totals per supplier
6. **Analyze Damage Type Distribution** — Identify predominant failure modes (packaging, transport, etc.)
7. **Retrieve SKU Daily Performance** — Query views, purchases, and returns trends for individual products
8. **Generate Weekly Supplier Reports** — Export JSON/CSV summaries for ops and procurement teams
9. **Automated Dashboard Workflows** — CI/CD-ready ingestion and analytics workspace

---

## 4. Elasticsearch Features Demonstrated

**Core Elasticsearch Capabilities:**
- **Index Mappings** — Explicit field definitions with `keyword`, `text`, `scaled_float`, `date` types
- **Normalizers** — Custom `keyword_lowercase` normalizer for case-insensitive Romanian brand names
- **Dynamic Mappings Control** — `"dynamic": "false"` to prevent schema drift
- **Full-Text Search** — Romanian-language product names and descriptions with UTF-8 support
- **Term Aggregations** — Group by supplier, category, damage type, product type
- **Date Histogram Aggregations** — Monthly supplier incident trends
- **Stats Aggregations** — Sum, average, count of damaged quantities
- **Pipeline Aggregations** — Derived metrics like damage rates (calculated from bucket totals)
- **Boolean Filters** — Combine category, date range, and SKU filters in queries
- **Scaled Float Optimization** — Price and revenue storage with `scaling_factor` for precision
- **Multi-Field Mappings** — `name` as `text` for search and `keyword` for exact match/sorting

---

## 5. Demo Entry Points

**System is designed to run entirely locally:**

| Service | URL/Command | Purpose |
|---------|-------------|---------|
| **Elasticsearch** | `http://localhost:9200` | Data storage and query engine |
| **Kibana** | `http://localhost:5601` | Index management, Dev Tools for Elasticsearch queries |
| **Swagger UI** | `http://localhost:8000/docs` | Interactive API documentation and testing |
| **Streamlit Dashboard** | `http://localhost:8501` | Incident logging and analytics UI |
| **Postman Collection** | Import `postman/EcommerceAnalyticsAPI.postman_collection.json` | API testing with positive/negative cases |
| **Python Ingestion** | `python run_all_ingest.py` or `./run_ingest_with_picker.bat` | Load product catalog and stats |

---

## 6. Architecture

The system follows a three-layer architecture:

1. **Data Layer** — Elasticsearch 8.15+ with three indices (`products`, `sku_daily_stats`, `supplier_incidents`)
2. **Application Layer** — Python ingestion scripts + FastAPI REST service + Streamlit UI
3. **Integration Layer** — Swagger for API docs, Postman for testing, Kibana for Elasticsearch interaction

**Visual Architecture:**
- System overview: [diagrams/architecture.puml](diagrams/architecture.puml)
- Data ingestion flow: [diagrams/data_flow.puml](diagrams/data_flow.puml)
- API request sequences: [diagrams/api_flow.puml](diagrams/api_flow.puml)
- Incident tracking workflow: [diagrams/incident_flow.puml](diagrams/incident_flow.puml)

---

## 7. Why Elasticsearch vs Relational Database

**Elasticsearch advantages for this analytics use case:**

| Requirement | Elasticsearch | Relational DB |
|-------------|---------------|---------------|
| **Full-Text Search** | Native tokenization, Romanian language support, relevance scoring | Requires external search engine or limited `LIKE` queries |
| **Schema Flexibility** | Dynamic attributes (30+ product fields), no ALTER TABLE overhead | Rigid schema, migrations for new attributes |
| **Aggregation Performance** | Sub-second bucket aggregations on millions of docs | Complex GROUP BY with indexes, slower on large datasets |
| **Horizontal Scaling** | Built-in sharding and replication | Vertical scaling or complex partitioning |
| **JSON-Native Storage** | Direct mapping to Python dicts and API responses | ORM overhead or manual JSON serialization |
| **Analytics Queries** | Date histograms, pipeline aggregations (derivative, bucket selectors) | Requires window functions, subqueries, or external tools |

**Specific to this project:**
- **Attribute extraction** benefits from Elasticsearch's flexible schema (add `attr_shade_code` without migrations)
- **Supplier KPI dashboards** rely on term aggregations grouped by `supplier_id`, `product_type`, and `damage_type`
- **Catalog search** uses full-text matching on product names and descriptions with Romanian diacritics
- **Daily stats analysis** leverages date histograms to trend SKU performance over time

---

## Quick Start for Evaluation

1. **Start Elasticsearch**: `./start_elasticsearch.bat` (wait 60s for startup)
2. **Verify health**: `curl http://localhost:9200` → should return cluster info
3. **Start Kibana** (optional): Navigate to Elasticsearch folder, run `bin\kibana.bat`
4. **Create indices**: `python -c "from elastic_mappings import ensure_all_indices; ensure_all_indices()"`
5. **Ingest sample data**: `./run_ingest_with_picker.bat` (select product Excel file)
6. **Launch API**: `uvicorn api.main:app` → Swagger at `http://localhost:8000/docs`
7. **Run Postman tests**: Import collection, set `baseUrl=http://localhost:8000`, execute folder
8. **Open dashboard**: `streamlit run app/streamlit_app.py` → `http://localhost:8501`

---

**All milestones are demonstrable locally with provided URLs and commands.**
