"""Quick product data quality checks."""
from __future__ import annotations

import logging
from typing import List

from elasticsearch import Elasticsearch

import attribute_analysis as aa
from settings import configure_logging, get_settings

logger = logging.getLogger(__name__)
REQUIRED_FIELDS = ["brand", "category_main", "price_final"]
ATTRIBUTE_FIELDS = [
    "attr_volume_ml",
    "attr_shade_code",
    "attr_finish",
    "attr_grit",
    "attr_liquid_type",
]


def get_client() -> Elasticsearch:
    settings = get_settings()
    return Elasticsearch(settings.es_url, basic_auth=settings.es_basic_auth)


def missing_percentage(client: Elasticsearch, field: str, index: str, total: int) -> float:
    if total == 0:
        return 0.0
    query = {"bool": {"must_not": {"exists": {"field": field}}}}
    count = client.count(index=index, query=query)["count"]
    return count / total


def report_missing_fields(client: Elasticsearch, index: str) -> None:
    total = client.count(index=index)["count"]
    print("=== Lipsă câmpuri critice ===")
    print(f"Total documente: {total}")
    for field in REQUIRED_FIELDS:
        pct = missing_percentage(client, field, index, total)
        print(f"- {field}: {pct:.1%} lipsă")


def report_attribute_coverage(index: str) -> None:
    print("\n=== Acoperire atribute derivate pe categorie ===")
    for attr in ATTRIBUTE_FIELDS:
        rows = aa.attribute_coverage_by_category(attr)
        top = sorted(rows, key=lambda row: row["coverage_ratio"], reverse=True)[:5]
        print(f"\nAtribut: {attr}")
        for row in top:
            print(
                f"  {row['category_main']:<25} » {row['with_attribute']}/{row['total_skus']} ({row['coverage_ratio']:.1%})"
            )


def main() -> None:
    configure_logging()
    client = get_client()
    settings = get_settings()
    report_missing_fields(client, settings.indices.products)
    report_attribute_coverage(settings.indices.products)


if __name__ == "__main__":
    main()
