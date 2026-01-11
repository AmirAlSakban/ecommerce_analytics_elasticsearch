"""Service helpers backing the FastAPI layer."""
from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional
from uuid import uuid4

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError

from attribute_analysis import missing_attribute_fix_list
from attribute_extraction import extract_attributes
from settings import get_settings
from supplier_incidents import (
    SupplierIncident,
    damage_rate_per_supplier,
    damage_rate_per_supplier_and_type,
    damage_types_distribution_per_supplier,
    insert_incident,
    monthly_damage_rate_for_supplier,
)


@lru_cache(maxsize=1)
def _client() -> Elasticsearch:
    settings = get_settings()
    return Elasticsearch(settings.es_url, basic_auth=settings.es_basic_auth)


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def upsert_product(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update a product document with derived attributes."""

    settings = get_settings()
    client = _client()
    base_doc = {k: v for k, v in payload.items() if v is not None}
    sku = base_doc["sku"]
    name = base_doc.get("name", "")
    description = base_doc.get("description_html") or base_doc.get("description_short")
    base_doc.pop("attributes", None)

    derived = extract_attributes(name, description)
    explicit_attrs = {
        k: v for k, v in payload.get("attributes", {}).items() if v is not None
    }
    derived.update(explicit_attrs)
    base_doc.update(derived)
    base_doc["updated_at"] = _now_iso()

    client.index(
        index=settings.indices.products,
        id=sku,
        document=base_doc,
        refresh="wait_for",
    )

    product_url = settings.product_url_for(sku)
    return {
        "sku": sku,
        "indexed": True,
        "attributes": derived,
        "url": product_url,
    }


def fetch_product(sku: str) -> Dict[str, Any]:
    client = _client()
    settings = get_settings()
    try:
        response = client.get(index=settings.indices.products, id=sku)
    except NotFoundError as exc:
        raise KeyError(f"SKU {sku} was not found") from exc
    return {"sku": sku, "document": response.get("_source", {})}


def list_missing_attributes(attribute: str, category_main: str, size: int) -> Dict[str, Any]:
    items = missing_attribute_fix_list(attribute, category_main, size)
    return {
        "attribute": attribute,
        "category_main": category_main,
        "size": size,
        "items": items,
    }


def create_incident(payload: Dict[str, Any]) -> Dict[str, Any]:
    body = dict(payload)
    if not body.get("incident_id"):
        body["incident_id"] = f"INC-{uuid4().hex[:12]}"
    damage_type = body.get("damage_type")
    if isinstance(damage_type, str):
        body["damage_type"] = [damage_type]
    if body.get("qty_damaged", 0) > body.get("qty_total_in_shipment", 0):
        raise ValueError("qty_damaged cannot exceed qty_total_in_shipment")
    incident = SupplierIncident(**body)
    insert_incident(incident)
    return {"incident_id": incident.incident_id, "created": True}


def list_incidents(
    *,
    supplier_id: Optional[str] = None,
    sku: Optional[str] = None,
    product_type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    size: int = 50,
) -> List[Dict[str, Any]]:
    settings = get_settings()
    client = _client()
    filters: List[Dict[str, Any]] = []

    if supplier_id:
        filters.append({"term": {"supplier_id": supplier_id}})
    if sku:
        filters.append({"term": {"sku": sku}})
    if product_type:
        filters.append({"term": {"product_type": product_type}})
    if date_from or date_to:
        range_body: Dict[str, Any] = {}
        if date_from:
            range_body["gte"] = date_from.isoformat()
        if date_to:
            range_body["lte"] = date_to.isoformat()
        filters.append({"range": {"date_reported": range_body}})

    query: Dict[str, Any]
    if filters:
        query = {"bool": {"filter": filters}}
    else:
        query = {"match_all": {}}

    response = client.search(
        index=settings.indices.supplier_incidents,
        body={
            "size": size,
            "query": query,
            "sort": [{"date_reported": {"order": "desc"}}],
        },
    )
    return [
        {"incident_id": hit["_id"], **hit.get("_source", {})}
        for hit in response["hits"]["hits"]
    ]


def supplier_kpis(product_type: Optional[str] = None) -> List[Dict[str, Any]]:
    data = damage_rate_per_supplier(product_type=product_type)
    return data


def supplier_kpis_by_type() -> List[Dict[str, Any]]:
    return damage_rate_per_supplier_and_type()


def supplier_damage_distribution() -> List[Dict[str, Any]]:
    return damage_types_distribution_per_supplier()


def supplier_monthly_metrics(supplier_id: str) -> List[Dict[str, Any]]:
    return monthly_damage_rate_for_supplier(supplier_id)


def fetch_daily_stats(
    sku: str,
    *,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    size: int = 90,
) -> List[Dict[str, Any]]:
    settings = get_settings()
    client = _client()
    filters: List[Dict[str, Any]] = [{"term": {"sku": sku}}]

    if date_from or date_to:
        range_body: Dict[str, Any] = {}
        if date_from:
            range_body["gte"] = date_from.isoformat()
        if date_to:
            range_body["lte"] = date_to.isoformat()
        filters.append({"range": {"date": range_body}})

    response = client.search(
        index=settings.indices.sku_daily_stats,
        body={
            "size": size,
            "query": {"bool": {"filter": filters}},
            "sort": [{"date": {"order": "desc"}}],
        },
    )
    hits = response.get("hits", {}).get("hits", [])
    items: List[Dict[str, Any]] = []
    for hit in hits:
        source = hit.get("_source", {})
        items.append(
            {
                "sku": source.get("sku", sku),
                "date": source.get("date"),
                "views": source.get("views"),
                "add_to_cart": source.get("add_to_cart"),
                "purchases": source.get("purchases"),
                "returns": source.get("returns"),
                "revenue": source.get("revenue"),
            }
        )
    return items