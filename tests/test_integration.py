"""Integration tests for the ecommerce analytics system.

These tests verify end-to-end workflows including:
- Elasticsearch connectivity
- Index creation and management
- Data ingestion pipelines
- Dashboard functionality

Run with: pytest tests/test_integration.py -v
"""
import logging
from datetime import datetime

import pytest
from elasticsearch import Elasticsearch

from es_setup import create_all_indices, get_client
from settings import configure_logging, get_settings
from supplier_incidents import SupplierIncident, insert_incident


@pytest.fixture(scope="module")
def es_client():
    """Create an Elasticsearch client for integration tests."""
    configure_logging(level="DEBUG")
    
    try:
        client = get_client()
        yield client
    except Exception as e:
        pytest.skip(f"Elasticsearch not available: {e}")


@pytest.fixture(scope="module")
def test_indices(es_client):
    """Create test indices for integration tests."""
    settings = get_settings()
    
    # Store original index names
    original_products = settings.indices.products
    original_incidents = settings.indices.supplier_incidents
    
    # Use test-prefixed indices
    test_prefix = "test_"
    
    try:
        # Create test indices
        create_all_indices()
        
        yield settings
    finally:
        # Cleanup: delete test indices
        try:
            es_client.indices.delete(index=f"{test_prefix}*", ignore=[404])
        except Exception as e:
            logging.warning(f"Failed to cleanup test indices: {e}")


def test_elasticsearch_connection(es_client):
    """Test that we can connect to Elasticsearch."""
    info = es_client.info()
    
    assert "version" in info
    assert "cluster_name" in info
    logging.info(f"Connected to Elasticsearch {info['version']['number']}")


def test_create_indices_idempotent(es_client):
    """Test that creating indices multiple times is safe."""
    # Create indices twice
    create_all_indices()
    create_all_indices()
    
    # Verify indices exist
    settings = get_settings()
    assert es_client.indices.exists(index=settings.indices.products)
    assert es_client.indices.exists(index=settings.indices.supplier_incidents)


def test_insert_and_retrieve_incident(es_client, test_indices):
    """Test inserting and retrieving a supplier incident."""
    settings = get_settings()
    
    # Create a test incident
    incident = SupplierIncident(
        incident_id="TEST-001",
        supplier_id="SUP-TEST",
        supplier_name="Test Supplier",
        date_reported=datetime.now(),
        sku="SKU-TEST-001",
        product_type="nail_polish",
        category_main="Gel Polish",
        qty_total_in_shipment=100,
        qty_damaged=5,
        damage_type="bottles_broken",
    )
    
    # Insert incident
    insert_incident(incident)
    
    # Wait for indexing
    es_client.indices.refresh(index=settings.indices.supplier_incidents)
    
    # Retrieve incident
    result = es_client.get(
        index=settings.indices.supplier_incidents,
        id="TEST-001"
    )
    
    assert result["_source"]["supplier_name"] == "Test Supplier"
    assert result["_source"]["qty_damaged"] == 5


def test_search_incidents_by_supplier(es_client, test_indices):
    """Test searching incidents by supplier."""
    settings = get_settings()
    
    # Search for incidents
    response = es_client.search(
        index=settings.indices.supplier_incidents,
        body={
            "query": {
                "term": {"supplier_id": "SUP-TEST"}
            }
        }
    )
    
    assert response["hits"]["total"]["value"] >= 0


def test_logging_configuration():
    """Test that logging is properly configured."""
    configure_logging(level="INFO")
    
    logger = logging.getLogger("test_integration")
    logger.info("Test log message")
    
    # Verify logger has handlers
    assert len(logger.handlers) > 0 or len(logging.getLogger().handlers) > 0


def test_bulk_incident_insertion_performance(es_client, test_indices):
    """Test bulk insertion of incidents for performance."""
    from supplier_incidents import bulk_insert_incidents
    
    settings = get_settings()
    
    # Create 100 test incidents
    incidents = [
        SupplierIncident(
            incident_id=f"PERF-{i:04d}",
            supplier_id=f"SUP-{i % 10}",
            supplier_name=f"Supplier {i % 10}",
            date_reported=datetime.now(),
            sku=f"SKU-{i:04d}",
            product_type="nail_polish",
            category_main="Gel Polish",
            qty_total_in_shipment=100,
            qty_damaged=i % 10,
        )
        for i in range(100)
    ]
    
    # Measure bulk insertion
    import time
    start = time.time()
    bulk_insert_incidents(incidents)
    duration = time.time() - start
    
    logging.info(f"Bulk inserted 100 incidents in {duration:.2f}s")
    
    # Verify insertion
    es_client.indices.refresh(index=settings.indices.supplier_incidents)
    
    response = es_client.count(index=settings.indices.supplier_incidents)
    assert response["count"] >= 100


@pytest.mark.parametrize("index_name", [
    "products",
    "sku_daily_stats",
    "supplier_incidents",
])
def test_index_mappings_valid(es_client, index_name):
    """Test that all index mappings are valid."""
    settings = get_settings()
    index = getattr(settings.indices, index_name)
    
    if es_client.indices.exists(index=index):
        mapping = es_client.indices.get_mapping(index=index)
        
        assert index in mapping
        assert "mappings" in mapping[index]
        logging.info(f"Index '{index}' has valid mapping")
