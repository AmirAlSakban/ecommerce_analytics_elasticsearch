"""Elasticsearch attribute analytics helpers."""
from __future__ import annotations

from typing import Any, Dict, List

from elasticsearch import Elasticsearch

from settings import get_settings


def _client() -> Elasticsearch:
    settings = get_settings()
    return Elasticsearch(settings.es_url, basic_auth=settings.es_basic_auth)


def attribute_coverage_by_category(attribute_field: str) -> List[Dict[str, Any]]:
    client = _client()
    body = {
        "size": 0,
        "aggs": {
            "per_category": {
                "terms": {"field": "category_main", "size": 200},
                "aggs": {
                    "total_skus": {"value_count": {"field": "sku"}},
                    "with_attr": {
                        "filter": {"exists": {"field": attribute_field}},
                        "aggs": {"count": {"value_count": {"field": "sku"}}},
                    },
                },
            }
        },
    }
    response = client.search(index=get_settings().indices.products, body=body)
    results: List[Dict[str, Any]] = []
    for bucket in response["aggregations"]["per_category"]["buckets"]:
        total = bucket["total_skus"]["value"]
        with_attr = bucket["with_attr"]["count"]["value"]
        coverage = (with_attr / total) if total else 0.0
        results.append(
            {
                "category_main": bucket["key"],
                "total_skus": total,
                "with_attribute": with_attr,
                "coverage_ratio": coverage,
            }
        )
    return results


def missing_attribute_fix_list(
    attribute_field: str, category_main_filter: str, size: int = 100
) -> List[Dict[str, Any]]:
    client = _client()
    query = {
        "bool": {
            "filter": [{"term": {"category_main": category_main_filter}}],
            "must_not": {"exists": {"field": attribute_field}},
        }
    }
    body = {
        "size": size,
        "query": query,
        "sort": [
            {"price_final": {"order": "desc", "missing": "_last"}},
            {"sku": {"order": "asc"}},
        ],
        "_source": ["sku", "name", "brand", "price_final", "category_main", "image_url"],
    }
    response = client.search(index=get_settings().indices.products, body=body)
    return [hit["_source"] for hit in response["hits"]["hits"]]


def attribute_importance_by_revenue(
    attribute_field: str, category_main_filter: str
) -> Dict[str, float]:
    client = _client()
    body = {
        "size": 0,
        "query": {"term": {"category_main": category_main_filter}},
        "aggs": {
            "with_attr": {
                "filter": {"exists": {"field": attribute_field}},
                "aggs": {
                    "revenue": {"sum": {"field": "total_revenue"}},
                },
            },
            "without_attr": {
                "filter": {"bool": {"must_not": {"exists": {"field": attribute_field}}}},
                "aggs": {
                    "revenue": {"sum": {"field": "total_revenue"}},
                },
            },
        },
    }
    response = client.search(index=get_settings().indices.products, body=body)
    return {
        "with_attribute": response["aggregations"]["with_attr"]["revenue"]["value"],
        "without_attribute": response["aggregations"]["without_attr"]["revenue"]["value"],
    }
