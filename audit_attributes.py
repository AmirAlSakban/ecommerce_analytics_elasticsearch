"""Sample products per category and print derived attributes for manual review."""
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from typing import Iterable, List

from elasticsearch import Elasticsearch

from settings import configure_logging, get_settings

logger = logging.getLogger(__name__)
DEFAULT_CATEGORIES = ["Manichiura", "Pedichiura", "Gel Polish"]
ATTR_FIELDS_TO_SHOW = [
    "attr_volume_ml",
    "attr_shade_code",
    "attr_finish",
    "attr_liquid_type",
    "attr_grit",
]


def get_client() -> Elasticsearch:
    settings = get_settings()
    return Elasticsearch(settings.es_url, basic_auth=settings.es_basic_auth)


def sample_category(client: Elasticsearch, index: str, category: str, size: int) -> List[dict]:
    body = {
        "size": size,
        "query": {
            "function_score": {
                "query": {"term": {"category_main": category}},
                "random_score": {"seed": int(datetime.utcnow().timestamp())},
            }
        },
        "_source": ["sku", "name", "brand", *ATTR_FIELDS_TO_SHOW],
    }
    resp = client.search(index=index, body=body)
    return [hit["_source"] for hit in resp["hits"]["hits"]]


def flag_attributes(doc: dict) -> List[str]:
    flags: List[str] = []
    volume = doc.get("attr_volume_ml")
    if volume is not None:
        if volume == 0:
            flags.append("volum 0 ml")
        elif volume > 200:
            flags.append("volum > 200 ml")
    grit = doc.get("attr_grit")
    if grit and grit not in {"80/80", "100/180", "150/180", "180/240"}:
        flags.append("grit neuzual")
    return flags


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Audit rapid al atributelor extrase")
    parser.add_argument("--categories", nargs="+", default=DEFAULT_CATEGORIES)
    parser.add_argument("--sample-size", type=int, default=5)
    args = parser.parse_args()

    client = get_client()
    settings = get_settings()
    for category in args.categories:
        docs = sample_category(client, settings.indices.products, category, args.sample_size)
        if not docs:
            print(f"\nCategorie: {category} (fără rezultate)")
            continue
        print(f"\nCategorie: {category}")
        for doc in docs:
            flags = flag_attributes(doc)
            flag_text = f" ⚠ {'; '.join(flags)}" if flags else ""
            attrs = ", ".join(
                f"{field}:{doc.get(field)}"
                for field in ATTR_FIELDS_TO_SHOW
                if doc.get(field) is not None
            )
            print(f"- {doc.get('sku')} | {doc.get('name')} ({doc.get('brand', 'N/A')}) -> {attrs}{flag_text}")


if __name__ == "__main__":
    main()
