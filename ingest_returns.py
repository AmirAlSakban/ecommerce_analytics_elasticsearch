"""Update sku_daily_stats with returns counts derived from a CSV export.

Assumptions about the CSV structure (adjust as needed):
- return_date: date when the return/credit note was processed.
- sku: SKU identifier matching the catalog.
- quantity: number of units returned for that SKU on the row.
- reason (optional): textual reason, ignored for aggregation but available for debugging.
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
REQUIRED_COLUMNS = {"return_date", "sku", "quantity"}


def load_returns(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

    df["return_date"] = pd.to_datetime(df["return_date"], errors="coerce", utc=True)
    df = df.dropna(subset=["return_date", "sku"])
    df["return_date"] = df["return_date"].dt.date
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    return df


def aggregate_returns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    aggregated = (
        df.groupby(["sku", "return_date"], as_index=False)
        .agg(returns=("quantity", "sum"))
        .sort_values(["return_date", "sku"])
    )
    aggregated["returns"] = aggregated["returns"].astype(int)
    return aggregated


def _actions(df: pd.DataFrame, index: str) -> Iterable[Dict[str, object]]:
    for record in df.to_dict("records"):
        sku = record["sku"]
        date_value = record["return_date"].isoformat() if hasattr(record["return_date"], "isoformat") else str(record["return_date"])
        doc = {
            "sku": sku,
            "date": date_value,
            "returns": int(record["returns"]),
        }
        yield {
            "_op_type": "update",
            "_index": index,
            "_id": f"{sku}_{date_value}",
            "doc": doc,
            "doc_as_upsert": True,
        }


def ingest_returns(file_path: Path, index_name: Optional[str] = None) -> Dict[str, int]:
    settings = get_settings()
    index = index_name or settings.indices.sku_daily_stats

    if not file_path.exists():
        raise FileNotFoundError(f"Returns file not found: {file_path}")

    df = aggregate_returns(load_returns(file_path))
    if df.empty:
        logger.warning("Returns CSV produced no aggregations")
        return {"created": 0, "updated": 0, "noop": 0}

    client = Elasticsearch(settings.es_url, basic_auth=settings.es_basic_auth)
    stats = {"created": 0, "updated": 0, "noop": 0}
    errors = []
    for ok, info in helpers.streaming_bulk(
        client,
        _actions(df, index),
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
        raise RuntimeError(f"Encountered {len(errors)} errors while ingesting returns")

    logger.info(
        "Returns aggregated into %s (created=%s updated=%s noop=%s)",
        index,
        stats["created"],
        stats["updated"],
        stats["noop"],
    )
    return stats


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Actualizează returns în sku_daily_stats")
    parser.add_argument("--file", type=Path, help="Calea spre exportul CSV cu retururi")
    parser.add_argument("--index", type=str, help="Index custom pentru upsert (implicit settings)")
    args = parser.parse_args()

    settings = get_settings()
    file_path: Optional[Path] = args.file
    if file_path is None:
        default_returns = settings.data_paths.returns_export
        if not default_returns:
            parser.error("Setează --file sau data_paths.returns_export în local_settings.json")
        file_path = Path(default_returns)

    try:
        ingest_returns(file_path=file_path, index_name=args.index)
    except Exception as exc:  # pragma: no cover - CLI safety
        logger.exception("Returns ingestion failed")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
