"""Supplier incident sanity checks."""
from __future__ import annotations

import logging
from typing import List

from elasticsearch import Elasticsearch

from settings import configure_logging, get_settings

logger = logging.getLogger(__name__)
CRITICAL_FIELDS = ["supplier_id", "sku", "date_reported", "product_type"]


def get_client() -> Elasticsearch:
    settings = get_settings()
    return Elasticsearch(settings.es_url, basic_auth=settings.es_basic_auth)


def too_many_damages(client: Elasticsearch, index: str) -> List[dict]:
    body = {
        "size": 50,
        "query": {
            "script": {
                "script": {
                    "lang": "painless",
                    "source": (
                        "doc.containsKey('qty_damaged') && doc.containsKey('qty_total_in_shipment') "
                        "&& doc['qty_total_in_shipment'].value > 0 "
                        "&& doc['qty_damaged'].value > doc['qty_total_in_shipment'].value"
                    ),
                }
            }
        },
    }
    resp = client.search(index=index, body=body)
    return [hit["_source"] for hit in resp["hits"]["hits"]]


def missing_field_docs(client: Elasticsearch, index: str, field: str) -> int:
    query = {"bool": {"must_not": {"exists": {"field": field}}}}
    return client.count(index=index, query=query)["count"]


def main() -> None:
    configure_logging()
    client = get_client()
    settings = get_settings()
    index = settings.indices.supplier_incidents

    print("=== Validare incidente furnizori ===")
    offending = too_many_damages(client, index)
    if offending:
        print(f"\nIncidente cu qty_damaged > qty_total_in_shipment ({len(offending)} exemple):")
        for incident in offending[:10]:
            print(
                f"  {incident.get('supplier_id')} / {incident.get('sku')} "
                f"- damaged {incident.get('qty_damaged')} din {incident.get('qty_total_in_shipment')}"
            )
    else:
        print("\n✓ Niciun incident cu qty_damaged peste qty_total_in_shipment")

    total_missing = 0
    print("\nCâmpuri critice lipsă:")
    for field in CRITICAL_FIELDS:
        count = missing_field_docs(client, index, field)
        total_missing += count
        print(f"- {field}: {count} documente")
    if total_missing == 0:
        print("✓ Toate câmpurile critice sunt prezente")


if __name__ == "__main__":
    main()
