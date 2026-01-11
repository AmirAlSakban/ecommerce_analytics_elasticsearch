"""Local settings loader and lightweight logging helpers.

Settings are stored in JSON (see local_settings.example.json) so they can be
edited without touching code. Values fall back to documented defaults when the
JSON file is missing.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

_DEFAULT_SETTINGS_FILE = Path(__file__).with_name("local_settings.example.json")


@dataclass(frozen=True)
class IndexSettings:
    products: str
    sku_daily_stats: str
    supplier_incidents: str


@dataclass(frozen=True)
class DataPaths:
    products_export: Optional[str]
    orders_export: Optional[str]
    returns_export: Optional[str]


@dataclass(frozen=True)
class UISettings:
    product_url_template: Optional[str] = None


@dataclass(frozen=True)
class Settings:
    es_url: str
    es_username: Optional[str]
    es_password: Optional[str]
    indices: IndexSettings
    data_paths: DataPaths
    ui: UISettings
    log_level: str = "INFO"

    @property
    def es_basic_auth(self) -> Optional[tuple[str, str]]:
        if self.es_username and self.es_password:
            return self.es_username, self.es_password
        return None

    def product_url_for(self, sku: str) -> Optional[str]:
        template = self.ui.product_url_template
        if template and sku:
            return template.format(sku=sku)
        return None


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _default_payload() -> Dict[str, Any]:
    if _DEFAULT_SETTINGS_FILE.exists():
        return _read_json(_DEFAULT_SETTINGS_FILE)
    # Fallback to hardcoded defaults if the example file was removed.
    return {
        "es_url": "http://localhost:9200",
        "es_username": None,
        "es_password": None,
        "indices": {
            "products": "products",
            "sku_daily_stats": "sku_daily_stats",
            "supplier_incidents": "supplier_incidents",
        },
        "data_paths": {
            "products_export": "data/raw/products_latest.xlsx",
            "orders_export": "data/raw/orders_latest.csv",
            "returns_export": "data/raw/returns_latest.csv",
        },
        "ui": {
            "product_url_template": None,
        },
        "log_level": "INFO",
    }


def _merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_settings(path: str | Path | None = None) -> Settings:
    candidate = Path(path or os.getenv("LOCAL_SETTINGS_PATH", "local_settings.json"))
    payload = _default_payload()
    if candidate.exists():
        user_payload = _read_json(candidate)
        payload = _merge(payload, user_payload)
    else:
        logging.getLogger(__name__).info(
            "Local settings file %s not found, falling back to defaults", candidate
        )

    indices = payload.get("indices", {})
    data_paths = payload.get("data_paths", {})
    ui = payload.get("ui", {})
    return Settings(
        es_url=payload.get("es_url", "http://localhost:9200"),
        es_username=payload.get("es_username"),
        es_password=payload.get("es_password"),
        indices=IndexSettings(
            products=indices.get("products", "products"),
            sku_daily_stats=indices.get("sku_daily_stats", "sku_daily_stats"),
            supplier_incidents=indices.get("supplier_incidents", "supplier_incidents"),
        ),
        data_paths=DataPaths(
            products_export=data_paths.get("products_export"),
            orders_export=data_paths.get("orders_export"),
            returns_export=data_paths.get("returns_export"),
        ),
        ui=UISettings(product_url_template=ui.get("product_url_template")),
        log_level=payload.get("log_level", "INFO"),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


def configure_logging(level: Optional[str] = None, log_file: Optional[str] = None) -> None:
    """Configure root logging once using the desired log level.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to settings value.
        log_file: Optional file path for log output. If provided, logs to both console and file.
    """
    log_level = level or get_settings().log_level or "INFO"
    
    handlers = []
    
    # Console handler with color-friendly format
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    )
    handlers.append(console_handler)
    
    # Optional file handler with detailed format
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-8s [%(name)s:%(funcName)s:%(lineno)d] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        handlers.append(file_handler)
    
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True  # Override any existing config
    )
    
    # Log initial configuration
    logger = logging.getLogger(__name__)
    logger.info("Logging configured: level=%s, file=%s", log_level, log_file or "console-only")