"""FastAPI application exposing the ecommerce analytics functionality."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from . import services
from .schemas import (
    DailyStatsResponse,
    IncidentDocument,
    IncidentPayload,
    IncidentResponse,
    MissingAttributeResponse,
    MonthlySupplierResponse,
    ProductDocument,
    ProductIngestResponse,
    ProductPayload,
    SupplierKPISummary,
)

app = FastAPI(
    title="Ecommerce Analytics API",
    version="1.0.0",
    description=(
        "REST API for product ingestion, attribute quality checks, and supplier KPIs. "
        "All endpoints preserve UTF-8 payloads for Romanian content."
    ),
    default_response_class=JSONResponse,
)


@app.get("/healthz", summary="Health probe")
def healthcheck() -> dict:
    return {"status": "ok"}


@app.post(
    "/api/products",
    response_model=ProductIngestResponse,
    summary="Ingest or update a product",
)
def ingest_product(payload: ProductPayload) -> ProductIngestResponse:
    result = services.upsert_product(payload.model_dump(mode="python", exclude_none=True))
    return ProductIngestResponse(**result)


@app.get(
    "/api/products/{sku}",
    response_model=ProductDocument,
    summary="Retrieve product document",
)
def get_product(sku: str) -> ProductDocument:
    try:
        result = services.fetch_product(sku)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ProductDocument(**result)


@app.get(
    "/api/products/missing-attributes",
    response_model=MissingAttributeResponse,
    summary="List SKUs missing a specific attribute",
)
def get_missing_attributes(
    attribute: str = Query(..., min_length=3, description="attr_* field to inspect"),
    category_main: str = Query(..., min_length=2, description="Category filter"),
    size: int = Query(50, ge=1, le=500),
) -> MissingAttributeResponse:
    payload = services.list_missing_attributes(attribute, category_main, size)
    return MissingAttributeResponse(**payload)


@app.post(
    "/api/incidents",
    response_model=IncidentResponse,
    summary="Create a supplier incident",
)
def create_incident(payload: IncidentPayload) -> IncidentResponse:
    body = payload.model_dump(mode="python")
    try:
        result = services.create_incident(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return IncidentResponse(**result)


@app.get(
    "/api/incidents",
    response_model=list[IncidentDocument],
    summary="List supplier incidents",
)
def list_incidents(
    supplier_id: Optional[str] = Query(None),
    sku: Optional[str] = Query(None),
    product_type: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    size: int = Query(50, ge=1, le=500),
) -> list[IncidentDocument]:
    items = services.list_incidents(
        supplier_id=supplier_id,
        sku=sku,
        product_type=product_type,
        date_from=date_from,
        date_to=date_to,
        size=size,
    )
    return [IncidentDocument(incident_id=item.get("incident_id", ""), document=item) for item in items]


@app.get(
    "/api/incidents/kpis",
    response_model=SupplierKPISummary,
    summary="Supplier KPI snapshot",
)
def get_supplier_kpis(
    product_type: Optional[str] = Query(None, description="Optional product_type filter"),
) -> SupplierKPISummary:
    data = services.supplier_kpis(product_type=product_type)
    return SupplierKPISummary(items=data)


@app.get(
    "/api/incidents/kpis/by-type",
    summary="Supplier KPI split by product type",
)
def get_supplier_kpis_by_type() -> list[dict]:
    return services.supplier_kpis_by_type()


@app.get(
    "/api/incidents/kpis/{supplier_id}/monthly",
    response_model=MonthlySupplierResponse,
    summary="Monthly damage rate for a supplier",
)
def get_supplier_monthly_kpis(supplier_id: str) -> MonthlySupplierResponse:
    data = services.supplier_monthly_metrics(supplier_id)
    return MonthlySupplierResponse(supplier_id=supplier_id, items=data)


@app.get(
    "/api/incidents/summary/damage-types",
    summary="Damage type distribution per supplier",
)
def get_damage_distribution() -> list[dict]:
    return services.supplier_damage_distribution()


@app.get(
    "/api/stats/daily/{sku}",
    response_model=DailyStatsResponse,
    summary="Retrieve daily stats for a SKU",
)
def get_daily_stats(
    sku: str,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    size: int = Query(90, ge=1, le=365),
) -> DailyStatsResponse:
    items = services.fetch_daily_stats(sku, date_from=date_from, date_to=date_to, size=size)
    return DailyStatsResponse(sku=sku, items=items)
