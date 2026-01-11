"""Elasticsearch mappings and helpers for the ecommerce analytics project."""
from __future__ import annotations

import logging
from typing import Dict

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import BadRequestError

from settings import get_settings

logger = logging.getLogger(__name__)


PRODUCTS_MAPPING: Dict[str, Dict] = {
    "settings": {
        "number_of_shards": 1,
        "analysis": {
            "normalizer": {
                "keyword_lowercase": {
                    "type": "custom",
                    "filter": ["lowercase"],
                }
            }
        },
    },
    "mappings": {
        "dynamic": "false",
        "properties": {
            "sku": {"type": "keyword"},
            "name": {"type": "text", "fields": {"raw": {"type": "keyword"}}},
            "group_code": {"type": "keyword"},
            "active": {"type": "keyword"},
            "stock_status": {"type": "keyword"},
            "brand": {"type": "keyword", "normalizer": "keyword_lowercase"},
            "description_html": {"type": "text"},
            "description_short": {"type": "text"},
            "description_feed": {"type": "text"},
            "price": {"type": "scaled_float", "scaling_factor": 100},
            "price_list": {"type": "scaled_float", "scaling_factor": 100},
            "price_final": {"type": "scaled_float", "scaling_factor": 100},
            "vat_included": {"type": "boolean"},
            "vat_rate": {"type": "scaled_float", "scaling_factor": 10},
            "image_url": {"type": "keyword"},
            "image_main": {"type": "keyword"},
            "image_secondary_1": {"type": "keyword"},
            "image_secondary_2": {"type": "keyword"},
            "category_path": {"type": "keyword"},
            "category_main": {"type": "keyword"},
            "subcategory_level1": {"type": "keyword"},
            "subcategory_level2": {"type": "keyword"},
            "meta_title": {"type": "text"},
            "meta_description": {"type": "text"},
            "keywords": {"type": "keyword"},
            "cross_sell_skus": {"type": "keyword"},
            "up_sell_skus": {"type": "keyword"},
            "ingredients_html": {"type": "text"},
            "total_revenue": {"type": "scaled_float", "scaling_factor": 100},
            "attr_volume_ml": {"type": "float"},
            "attr_color_name": {"type": "keyword"},
            "attr_shade_code": {"type": "keyword"},
            "attr_finish": {"type": "keyword"},
            "attr_curing_type": {"type": "keyword"},
            "attr_collection": {"type": "keyword"},
            "attr_liquid_type": {"type": "keyword"},
            "attr_scent": {"type": "keyword"},
            "attr_strength_percent": {"type": "float"},
            "attr_length_mm": {"type": "float"},
            "attr_material": {"type": "keyword"},
            "attr_grit": {"type": "keyword"},
            "attr_shape": {"type": "keyword"},
            "updated_at": {"type": "date"},
        },
    },
}


SKU_DAILY_STATS_MAPPING: Dict[str, Dict] = {
    "settings": {"number_of_shards": 1},
    "mappings": {
        "dynamic": "false",
        "properties": {
            "sku": {"type": "keyword"},
            "date": {"type": "date"},
            "views": {"type": "integer"},
            "add_to_cart": {"type": "integer"},
            "purchases": {"type": "integer"},
            "returns": {"type": "integer"},
            "revenue": {"type": "scaled_float", "scaling_factor": 100},
        },
    },
}


SUPPLIER_INCIDENTS_MAPPING: Dict[str, Dict] = {
    "settings": {"number_of_shards": 1},
    "mappings": {
        "dynamic": "false",
        "properties": {
            "incident_id": {"type": "keyword"},
            "supplier_id": {"type": "keyword"},
            "supplier_name": {"type": "keyword"},
            "date_reported": {"type": "date"},
            "shipment_id": {"type": "keyword"},
            "transport_company": {"type": "keyword"},
            "sku": {"type": "keyword"},
            "product_type": {"type": "keyword"},
            "category_main": {"type": "keyword"},
            "qty_total_in_shipment": {"type": "integer"},
            "qty_damaged": {"type": "integer"},
            "damage_type": {"type": "keyword"},
            "root_cause_guess": {"type": "keyword"},
            "batch_id": {"type": "keyword"},
            "packaging_primary": {"type": "keyword"},
            "packaging_secondary": {"type": "keyword"},
            "packaging_cushioning": {"type": "keyword"},
            "comment": {"type": "text"},
            "created_at": {"type": "date"},
        },
    },
}


def _client() -> Elasticsearch:
    settings = get_settings()
    return Elasticsearch(settings.es_url, basic_auth=settings.es_basic_auth)


def ensure_index(client: Elasticsearch, name: str, body: Dict[str, Dict]) -> None:
    """Create the index or update its mapping if it already exists."""

    if not client.indices.exists(index=name):
        logger.info("Creating index %s", name)
        try:
            client.indices.create(index=name, **body)
        except BadRequestError as exc:  # pragma: no cover - bubbled to caller
            logger.error("Failed to create index %s: %s", name, exc.info)
            raise
        return

    logger.info("Index %s already exists, updating mapping", name)
    client.indices.put_mapping(
        index=name,
        properties=body.get("mappings", {}).get("properties", {}),
    )


def ensure_products_index(client: Elasticsearch | None = None) -> None:
    settings = get_settings()
    client = client or _client()
    ensure_index(client, settings.indices.products, PRODUCTS_MAPPING)


def ensure_sku_daily_stats_index(client: Elasticsearch | None = None) -> None:
    settings = get_settings()
    client = client or _client()
    ensure_index(client, settings.indices.sku_daily_stats, SKU_DAILY_STATS_MAPPING)


def ensure_supplier_incidents_index(client: Elasticsearch | None = None) -> None:
    settings = get_settings()
    client = client or _client()
    ensure_index(client, settings.indices.supplier_incidents, SUPPLIER_INCIDENTS_MAPPING)


def ensure_all_indices(client: Elasticsearch | None = None) -> None:
    client = client or _client()
    ensure_products_index(client)
    ensure_sku_daily_stats_index(client)
    ensure_supplier_incidents_index(client)
