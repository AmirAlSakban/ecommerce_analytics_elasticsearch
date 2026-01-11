"""Tests for settings module."""
import json
import logging
from pathlib import Path

import pytest

from settings import (
    Settings,
    configure_logging,
    get_settings,
    load_settings,
)


def test_load_settings_with_defaults(tmp_path):
    """Test loading settings when no custom file exists."""
    settings = load_settings(tmp_path / "nonexistent.json")
    
    assert settings.es_url == "http://localhost:9200"
    assert settings.indices.products == "products"
    assert settings.log_level == "INFO"


def test_load_settings_with_custom_file(tmp_path):
    """Test loading settings from a custom JSON file."""
    custom_settings = {
        "es_url": "http://custom:9200",
        "es_username": "testuser",
        "es_password": "testpass",
        "indices": {
            "products": "custom_products",
        },
        "log_level": "DEBUG",
    }
    
    settings_file = tmp_path / "custom_settings.json"
    settings_file.write_text(json.dumps(custom_settings), encoding="utf-8")
    
    settings = load_settings(settings_file)
    
    assert settings.es_url == "http://custom:9200"
    assert settings.es_username == "testuser"
    assert settings.indices.products == "custom_products"
    assert settings.log_level == "DEBUG"


def test_es_basic_auth_property():
    """Test basic auth tuple generation."""
    settings = Settings(
        es_url="http://test:9200",
        es_username="user",
        es_password="pass",
        indices=None,
        data_paths=None,
        ui=None,
    )
    
    assert settings.es_basic_auth == ("user", "pass")


def test_es_basic_auth_none_when_no_credentials():
    """Test basic auth returns None when credentials missing."""
    settings = Settings(
        es_url="http://test:9200",
        es_username=None,
        es_password=None,
        indices=None,
        data_paths=None,
        ui=None,
    )
    
    assert settings.es_basic_auth is None


def test_product_url_for_with_template():
    """Test product URL generation with template."""
    from settings import UISettings
    
    settings = Settings(
        es_url="http://test:9200",
        es_username=None,
        es_password=None,
        indices=None,
        data_paths=None,
        ui=UISettings(product_url_template="https://shop.com/product/{sku}"),
    )
    
    url = settings.product_url_for("SKU-123")
    assert url == "https://shop.com/product/SKU-123"


def test_product_url_for_without_template():
    """Test product URL returns None when no template configured."""
    from settings import UISettings
    
    settings = Settings(
        es_url="http://test:9200",
        es_username=None,
        es_password=None,
        indices=None,
        data_paths=None,
        ui=UISettings(product_url_template=None),
    )
    
    url = settings.product_url_for("SKU-123")
    assert url is None


def test_configure_logging_sets_level(caplog):
    """Test logging configuration sets the correct level."""
    configure_logging(level="DEBUG")
    
    with caplog.at_level(logging.DEBUG):
        logger = logging.getLogger("test_logger")
        logger.debug("Debug message")
    
    # Check that logging was configured and message was logged
    assert logging.getLogger().level <= logging.DEBUG


def test_configure_logging_with_file(tmp_path):
    """Test logging configuration writes to file."""
    log_file = tmp_path / "test.log"
    
    configure_logging(level="INFO", log_file=str(log_file))
    
    logger = logging.getLogger("test_file_logger")
    logger.info("Test message to file")
    
    assert log_file.exists()
    assert "Test message to file" in log_file.read_text()


def test_settings_merge_nested_dicts(tmp_path):
    """Test that nested dictionaries merge correctly."""
    custom_settings = {
        "indices": {
            "products": "my_products",
            # supplier_incidents should remain default
        },
    }
    
    settings_file = tmp_path / "partial.json"
    settings_file.write_text(json.dumps(custom_settings), encoding="utf-8")
    
    settings = load_settings(settings_file)
    
    assert settings.indices.products == "my_products"
    assert settings.indices.supplier_incidents == "supplier_incidents"  # Default


def test_get_settings_cached():
    """Test that get_settings returns cached instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    
    assert settings1 is settings2  # Same object instance
