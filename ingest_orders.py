"""Aggregate order exports into sku_daily_stats Elasticsearch index.

Assumes the CSV export contains at least the columns:
- order_date (ISO or parseable date)
- sku
- quantity (number of units for that SKU within the order line)
- line_total (monetary total for that line, in the same currency as ES reporting)

Adjust column names by editing this script if your platform uses different labels.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd
from elasticsearch import Elasticsearch, helpers

from settings import configure_logging, get_settings

logger = logging.getLogger(__name__)
REQUIRED_COLUMNS = {"order_date", "sku", "quantity", "line_total"}


def load_orders(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce", utc=True)
    df = df.dropna(subset=["order_date", "sku"])
    df["order_date"] = df["order_date"].dt.date
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    df["line_total"] = pd.to_numeric(df["line_total"], errors="coerce").fillna(0.0)
    return df


def aggregate_orders(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    grouped = (
        df.groupby(["sku", "order_date"], as_index=False)
        .agg(purchases=("quantity", "sum"), revenue=("line_total", "sum"))
        .sort_values(["order_date", "sku"])
    )
    grouped["purchases"] = grouped["purchases"].astype(int)
    grouped["revenue"] = grouped["revenue"].astype(float)
    return grouped


def _build_actions(df: pd.DataFrame, index: str) -> Iterable[Dict[str, object]]:
    for record in df.to_dict("records"):
        sku = record["sku"]
        date_value = record["order_date"].isoformat() if hasattr(record["order_date"], "isoformat") else str(record["order_date"])
        doc = {
            "sku": sku,
            "date": date_value,
            "purchases": int(record["purchases"]),
            "revenue": float(record["revenue"]),
        }
        yield {
            "_op_type": "update",
            "_index": index,
            "_id": f"{sku}_{date_value}",
            "doc": doc,
            "doc_as_upsert": True,
        }


def ingest_orders(file_path: Path, index_name: Optional[str] = None) -> Dict[str, int]:
    settings = get_settings()
    index = index_name or settings.indices.sku_daily_stats

    if not file_path.exists():
        raise FileNotFoundError(f"Orders file not found: {file_path}")

    df = aggregate_orders(load_orders(file_path))
    if df.empty:
        logger.warning("Orders CSV produced no rows after aggregation")
        return {"created": 0, "updated": 0, "noop": 0}

    client = Elasticsearch(settings.es_url, basic_auth=settings.es_basic_auth)
    stats = {"created": 0, "updated": 0, "noop": 0}
    errors = []
    for ok, info in helpers.streaming_bulk(
        client,
        _build_actions(df, index),
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
        raise RuntimeError(f"Encountered {len(errors)} errors while ingesting orders")

    logger.info(
        "Orders aggregated into %s (created=%s updated=%s noop=%s)",
        index,
        stats["created"],
        stats["updated"],
        stats["noop"],
    )
    return stats


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Aggregate orders CSV into sku_daily_stats index")
    parser.add_argument("--file", type=Path, help="Calea spre exportul CSV de comenzi")
    parser.add_argument(
        "--index",
        type=str,
        help="Numele indexului (implicit valoarea din local_settings.json)",
    )
    args = parser.parse_args()

    settings = get_settings()
    file_path: Optional[Path] = args.file
    if file_path is None:
        default_orders = settings.data_paths.orders_export
        if not default_orders:
            parser.error("Setează --file sau data_paths.orders_export în local_settings.json")
        file_path = Path(default_orders)

    try:
        ingest_orders(file_path=file_path, index_name=args.index)
    except Exception as exc:  # pragma: no cover - CLI safety
        logger.exception("Orders ingestion failed")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
