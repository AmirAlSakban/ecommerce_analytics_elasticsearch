"""Supplier incident logging and analytics module."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List

from elasticsearch import Elasticsearch, helpers

from settings import get_settings


@dataclass
class SupplierIncident:
    incident_id: str
    supplier_id: str
    supplier_name: str
    date_reported: datetime
    sku: str
    product_type: str
    category_main: str
    qty_total_in_shipment: int
    qty_damaged: int
    damage_type: List[str] = field(default_factory=list)
    shipment_id: str | None = None
    transport_company: str | None = None
    root_cause_guess: str | None = None
    batch_id: str | None = None
    packaging_primary: str | None = None
    packaging_secondary: str | None = None
    packaging_cushioning: str | None = None
    comment: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


def _client() -> Elasticsearch:
    settings = get_settings()
    return Elasticsearch(settings.es_url, basic_auth=settings.es_basic_auth)


def insert_incident(incident: SupplierIncident) -> None:
    client = _client()
    client.index(
        index=get_settings().indices.supplier_incidents,
        id=incident.incident_id,
        document=_serialize_incident(incident),
        refresh="wait_for",
    )


def bulk_insert_incidents(incidents: Iterable[SupplierIncident]) -> None:
    client = _client()
    actions = [
        {
            "_index": get_settings().indices.supplier_incidents,
            "_id": incident.incident_id,
            "_source": _serialize_incident(incident),
        }
        for incident in incidents
    ]
    if not actions:
        return
    helpers.bulk(client, actions)


def _serialize_incident(incident: SupplierIncident) -> Dict[str, Any]:
    payload = asdict(incident)
    payload["date_reported"] = incident.date_reported.isoformat()
    payload["created_at"] = incident.created_at.isoformat()
    return payload


def damage_rate_per_supplier(product_type: str | None = None) -> List[Dict[str, Any]]:
    client = _client()
    query = {"term": {"product_type": product_type}} if product_type else {"match_all": {}}
    body = {
        "size": 0,
        "query": query,
        "aggs": {
            "suppliers": {
                "terms": {"field": "supplier_id", "size": 50},
                "aggs": {
                    "total_qty": {"sum": {"field": "qty_total_in_shipment"}},
                    "damaged_qty": {"sum": {"field": "qty_damaged"}},
                    "damage_rate": {
                        "bucket_script": {
                            "buckets_path": {
                                "damaged": "damaged_qty",
                                "total": "total_qty",
                            },
                            "script": "params.total == 0 ? 0 : params.damaged / params.total",
                        }
                    },
                },
            }
        },
    }
    response = client.search(index=get_settings().indices.supplier_incidents, body=body)
    return [
        {
            "supplier_id": bucket["key"],
            "damage_rate": bucket["damage_rate"]["value"],
            "qty_total": bucket["total_qty"]["value"],
            "qty_damaged": bucket["damaged_qty"]["value"],
        }
        for bucket in response["aggregations"]["suppliers"]["buckets"]
    ]


def damage_rate_per_supplier_and_type() -> List[Dict[str, Any]]:
    client = _client()
    body = {
        "size": 0,
        "aggs": {
            "suppliers": {
                "terms": {"field": "supplier_id", "size": 50},
                "aggs": {
                    "product_types": {
                        "terms": {"field": "product_type", "size": 10},
                        "aggs": {
                            "total_qty": {"sum": {"field": "qty_total_in_shipment"}},
                            "damaged_qty": {"sum": {"field": "qty_damaged"}},
                            "damage_rate": {
                                "bucket_script": {
                                    "buckets_path": {
                                        "damaged": "damaged_qty",
                                        "total": "total_qty",
                                    },
                                    "script": "params.total == 0 ? 0 : params.damaged / params.total",
                                }
                            },
                        },
                    }
                },
            }
        },
    }
    response = client.search(index=get_settings().indices.supplier_incidents, body=body)
    output: List[Dict[str, Any]] = []
    for supplier_bucket in response["aggregations"]["suppliers"]["buckets"]:
        for type_bucket in supplier_bucket["product_types"]["buckets"]:
            output.append(
                {
                    "supplier_id": supplier_bucket["key"],
                    "product_type": type_bucket["key"],
                    "damage_rate": type_bucket["damage_rate"]["value"],
                    "qty_total": type_bucket["total_qty"]["value"],
                    "qty_damaged": type_bucket["damaged_qty"]["value"],
                }
            )
    return output


def damage_types_distribution_per_supplier() -> List[Dict[str, Any]]:
    client = _client()
    body = {
        "size": 0,
        "aggs": {
            "suppliers": {
                "terms": {"field": "supplier_id", "size": 50},
                "aggs": {
                    "damage_types": {"terms": {"field": "damage_type", "size": 20}}
                },
            }
        },
    }
    response = client.search(index=get_settings().indices.supplier_incidents, body=body)
    return [
        {
            "supplier_id": supplier_bucket["key"],
            "damage_types": [
                {"damage_type": type_bucket["key"], "count": type_bucket["doc_count"]}
                for type_bucket in supplier_bucket["damage_types"]["buckets"]
            ],
        }
        for supplier_bucket in response["aggregations"]["suppliers"]["buckets"]
    ]


def monthly_damage_rate_for_supplier(supplier_id: str) -> List[Dict[str, Any]]:
    client = _client()
    body = {
        "size": 0,
        "query": {"term": {"supplier_id": supplier_id}},
        "aggs": {
            "monthly": {
                "date_histogram": {
                    "field": "date_reported",
                    "calendar_interval": "month",
                },
                "aggs": {
                    "total_qty": {"sum": {"field": "qty_total_in_shipment"}},
                    "damaged_qty": {"sum": {"field": "qty_damaged"}},
                    "damage_rate": {
                        "bucket_script": {
                            "buckets_path": {
                                "damaged": "damaged_qty",
                                "total": "total_qty",
                            },
                            "script": "params.total == 0 ? 0 : params.damaged / params.total",
                        }
                    },
                },
            }
        },
    }
    response = client.search(index=get_settings().indices.supplier_incidents, body=body)
    return [
        {
            "month": bucket["key_as_string"],
            "damage_rate": bucket["damage_rate"]["value"],
            "qty_total": bucket["total_qty"]["value"],
            "qty_damaged": bucket["damaged_qty"]["value"],
        }
        for bucket in response["aggregations"]["monthly"]["buckets"]
    ]
