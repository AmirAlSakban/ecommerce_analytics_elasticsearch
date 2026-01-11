"""Ingest product catalog exports into Elasticsearch.

Reads the Excel export with Romanian headers, maps them to internal field
names, applies attribute extraction, and bulk *upserts* the result so reruns
do not create duplicates.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from elasticsearch import Elasticsearch, helpers

from attribute_extraction import extract_attributes
from settings import configure_logging, get_settings

logger = logging.getLogger(__name__)


RO_COLUMN_MAP: Dict[str, str] = {
    "Cod Produs (SKU)": "sku",
    "Denumire Produs": "name",
    "Cod Grupa": "group_code",
    "Activ in Magazin": "active",
    "Stare Stoc": "stock_status",
    "Marca (Brand)": "brand",
    "Descriere Produs": "description_html",
    "Descriere Scurta a Produsului": "description_short",
    "Descriere pt feed-uri": "description_feed",
    "Pret": "price",
    "Pret intreg (Calculat)": "price_list",
    "Pret final (Calculat)": "price_final",
    "Pretul Include TVA": "vat_included",
    "Cota TVA": "vat_rate",
    "URL Poza de Produs": "image_url",
    "Imagine principala": "image_main",
    "Imagine secundara 1": "image_secondary_1",
    "Imagine secundara 2": "image_secondary_2",
    "Categorie / Categorii": "category_path",
    "Categorie principala": "category_main",
    "Subcategorie de nivel 1": "subcategory_level1",
    "Subcategorie de nivel 2": "subcategory_level2",
    "Titlu Meta": "meta_title",
    "Descriere Meta": "meta_description",
    "Cuvinte Cheie": "keywords",
    "Produse Cross-Sell": "cross_sell_skus",
    "Produse Up-Sell": "up_sell_skus",
    "Atribute: Ingrediente (editor text)": "ingredients_html",
}


NUMERIC_FIELDS = {"price", "price_list", "price_final", "vat_rate"}
LIST_FIELDS = {"cross_sell_skus", "up_sell_skus"}


def _safe_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def _safe_bool(value: Any) -> bool | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    value_str = str(value).strip().lower()
    if value_str in {"da", "yes", "true", "1"}:
        return True
    if value_str in {"nu", "no", "false", "0"}:
        return False
    return None


def _split_list(value: Any) -> list[str] | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    parts = [item.strip() for item in str(value).split(",") if item.strip()]
    return parts or None


def row_to_document(row: pd.Series) -> Dict[str, Any]:
    document: Dict[str, Any] = {}
    for ro_name, internal_name in RO_COLUMN_MAP.items():
        raw_value = row.get(ro_name)
        if pd.isna(raw_value) or (isinstance(raw_value, str) and not raw_value.strip()):
            raw_value = None
        if internal_name in NUMERIC_FIELDS:
            value = _safe_float(raw_value)
        elif internal_name == "vat_included":
            value = _safe_bool(raw_value)
        elif internal_name in LIST_FIELDS:
            value = _split_list(raw_value)
        else:
            value = raw_value
        if value is not None:
            document[internal_name] = value

    attributes = extract_attributes(
        name=document.get("name", ""),
        description=document.get("description_html"),
    )
    document.update(attributes)
    return document


def load_excel(path: Path) -> pd.DataFrame:
    return pd.read_excel(path, dtype=str, keep_default_na=False)


def bulk_index_products(
    file_path: Path,
    index_name: Optional[str] = None,
    client: Optional[Elasticsearch] = None,
) -> Dict[str, int]:
    settings = get_settings()
    index = index_name or settings.indices.products
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    df = load_excel(file_path)
    client = client or Elasticsearch(settings.es_url, basic_auth=settings.es_basic_auth)

    actions = []
    skipped = 0
    for _, row in df.iterrows():
        doc = row_to_document(row)
        sku = doc.get("sku")
        if not sku:
            skipped += 1
            continue
        actions.append(
            {
                "_op_type": "update",
                "_index": index,
                "_id": sku,
                "doc": doc,
                "doc_as_upsert": True,
            }
        )

    if not actions:
        raise RuntimeError("No valid product documents were found in the Excel file")

    stats = {"created": 0, "updated": 0, "noop": 0}
    errors = []
    for ok, info in helpers.streaming_bulk(
        client,
        actions,
        raise_on_error=False,
        max_retries=3,
        request_timeout=60,
    ):
        if not ok:
            errors.append(info)
            continue
        result = info.get("update", {}).get("result")
        if result in stats:
            stats[result] += 1
        else:
            stats["updated"] += 1

    if errors:
        logger.error("Bulk ingestion encountered %d errors", len(errors))
        raise RuntimeError(f"Bulk ingestion failed for {len(errors)} documents")

    logger.info(
        "Products indexed into %s (created=%s updated=%s noop=%s skipped=%s)",
        index,
        stats["created"],
        stats["updated"],
        stats["noop"],
        skipped,
    )
    stats["skipped"] = skipped
    return stats


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Ingest product catalog into Elasticsearch")
    parser.add_argument(
        "--file",
        type=Path,
        help="Path către fișierul Excel cu exportul de produse",
    )
    parser.add_argument(
        "--index",
        type=str,
        help="Numele indexului Elasticsearch (implicit din settings)",
    )
    args = parser.parse_args()

    settings = get_settings()
    file_path: Optional[Path] = args.file
    if file_path is None:
        default_products_path = settings.data_paths.products_export
        if not default_products_path:
            parser.error("Setează --file sau data_paths.products_export în local_settings.json")
        file_path = Path(default_products_path)

    try:
        stats = bulk_index_products(file_path=file_path, index_name=args.index)
    except Exception as exc:  # pragma: no cover - CLI safety
        logger.exception("Product ingestion failed")
        raise SystemExit(1) from exc

    logger.info(
        "Ingestion finished: created=%s updated=%s noop=%s skipped=%s",
        stats["created"],
        stats["updated"],
        stats["noop"],
        stats["skipped"],
    )


if __name__ == "__main__":
    main()
