"""Index setup helpers for the ecommerce analytics project.

Provides mapping definitions and convenience helpers to create indices for
products, SKU daily stats, and supplier incidents. Designed to be idempotent
so the script can be rerun safely.
"""
from __future__ import annotations

import logging

from elasticsearch import Elasticsearch

from elastic_mappings import (
    PRODUCTS_MAPPING,
    SKU_DAILY_STATS_MAPPING,
    SUPPLIER_INCIDENTS_MAPPING,
    ensure_index,
)
from settings import get_settings

logger = logging.getLogger(__name__)


def get_client() -> Elasticsearch:
    """Initialise the Elasticsearch client using settings.json data."""

    settings = get_settings()
    logger.debug("Creating Elasticsearch client for %s", settings.es_url)
    client = Elasticsearch(settings.es_url, basic_auth=settings.es_basic_auth)
    
    # Verify connection
    try:
        info = client.info()
        logger.info("Connected to Elasticsearch %s (cluster: %s)", 
                   info["version"]["number"], info["cluster_name"])
    except Exception as e:
        logger.error("Failed to connect to Elasticsearch at %s: %s", settings.es_url, e)
        raise
    
    return client


def create_index(client: Elasticsearch, name: str, body: dict) -> None:
    """Compatibility wrapper delegating to elastic_mappings.ensure_index."""

    logger.debug("Ensuring index '%s' exists with expected mapping", name)
    if client.indices.exists(index=name):
        logger.info("Index '%s' already exists, ensuring mapping", name)
        ensure_index(client, name, body)
        return

    mapping_count = len(body.get("mappings", {}).get("properties", {}))
    logger.info("Creating index '%s' with %d mappings", name, mapping_count)
    ensure_index(client, name, body)


def create_products_index(client: Elasticsearch | None = None) -> None:
    settings = get_settings()
    client = client or get_client()
    create_index(client, settings.indices.products, PRODUCTS_MAPPING)


def create_sku_daily_stats_index(client: Elasticsearch | None = None) -> None:
    settings = get_settings()
    client = client or get_client()
    create_index(client, settings.indices.sku_daily_stats, SKU_DAILY_STATS_MAPPING)


def create_supplier_incidents_index(client: Elasticsearch | None = None) -> None:
    settings = get_settings()
    client = client or get_client()
    create_index(client, settings.indices.supplier_incidents, SUPPLIER_INCIDENTS_MAPPING)


def create_all_indices() -> None:
    """Create all required indices for the application."""
    logger.info("Ensuring all Elasticsearch indices are present")
    client = get_client()
    create_products_index(client)
    create_sku_daily_stats_index(client)
    create_supplier_incidents_index(client)
    logger.info("Successfully ensured all index mappings")
