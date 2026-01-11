# Use Cases

## Product & Catalog Operations
1. **Ingest New Catalog Export**
   - Input: Excel export (`products_latest.xlsx`).
   - Action: `run_all_ingest.py` or `POST /api/products`.
   - Outcome: Products indexed with derived attributes and ready for analytics.
2. **Detect Missing Attributes**
   - Input: Attribute name + categorie (ex: `attr_shade_code`, `Gel Polish`).
   - Action: `GET /api/products/missing-attributes` or Streamlit Attribute Analysis tab.
   - Outcome: Prioritized SKU list for content teams.
3. **Audit Attribute Coverage by Category**
   - Input: Target attribute.
   - Action: CLI `audit_attributes.py` or dashboard visualization.
   - Outcome: Coverage percentage + revenue impact per categorie.

## Supplier Quality & Logistics
4. **Log Supplier Incident**
   - Input: Incident form data (furnizor, shipment, qty, damage type).
   - Action: Dashboard Incident Logger or `POST /api/incidents`.
   - Outcome: Incident stored in `supplier_incidents` for KPI tracking.
5. **Monitor Damage Rate per Supplier**
   - Input: Optional `product_type` filter.
   - Action: `GET /api/incidents/kpis`, dashboard KPI cards, or CLI aggregations.
   - Outcome: Ranked list of suppliers with damage %, qty totals, and actionable insights.
6. **Analyze Damage Type Distribution**
   - Input: Supplier ID or category filter.
   - Action: Supplier analytics dashboard or API summary endpoint.
   - Outcome: Understand predominant root causes (ambalare, transport etc.).

## Performance & Planning
7. **Retrieve SKU Daily Stats**
   - Input: SKU, optional date range.
   - Action: `GET /api/stats/daily/{sku}` or bespoke scripts querying `sku_daily_stats`.
   - Outcome: Views/purchases/returns trend for conversion diagnostics.
8. **Generate Weekly Supplier Report**
   - Input: Date interval, optional product type.
   - Action: Python helpers in `supplier_incidents.py` or API KPI endpoints.
   - Outcome: CSV/JSON report for ops and procurement teams.
9. **Drive Dashboard Automation**
   - Input: Cron job or CI pipeline.
   - Action: Start Elasticsearch, run ingestion, launch Streamlit, and ping FastAPI health endpoint.
   - Outcome: Always-ready analytics workspace for QA demos or stakeholder reviews.
