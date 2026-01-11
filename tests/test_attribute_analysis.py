import attribute_analysis as aa


class DummyClient:
    def __init__(self, search_response):
        self.search_response = search_response

    def search(self, index, body):
        self.last_request = body
        return self.search_response


def test_attribute_coverage_by_category(monkeypatch):
    response = {
        "aggregations": {
            "per_category": {
                "buckets": [
                    {
                        "key": "Gel Polish",
                        "total_skus": {"value": 10},
                        "with_attr": {"count": {"value": 7}},
                    }
                ]
            }
        }
    }
    dummy = DummyClient(response)
    monkeypatch.setattr(aa, "_client", lambda: dummy)

    result = aa.attribute_coverage_by_category("attr_shade_code")

    assert result[0]["coverage_ratio"] == 0.7


def test_missing_attribute_fix_list(monkeypatch):
    response = {
        "hits": {
            "hits": [
                {"_source": {"sku": "SKU1", "name": "Produs 1", "price_final": 10}},
                {"_source": {"sku": "SKU2", "name": "Produs 2", "price_final": 8}},
            ]
        }
    }
    dummy = DummyClient(response)
    monkeypatch.setattr(aa, "_client", lambda: dummy)

    missing = aa.missing_attribute_fix_list("attr_finish", "Gel Polish", size=2)

    assert [doc["sku"] for doc in missing] == ["SKU1", "SKU2"]
    assert dummy.last_request["size"] == 2


def test_attribute_importance_by_revenue(monkeypatch):
    response = {
        "aggregations": {
            "with_attr": {"revenue": {"value": 1200}},
            "without_attr": {"revenue": {"value": 300}},
        }
    }
    dummy = DummyClient(response)
    monkeypatch.setattr(aa, "_client", lambda: dummy)

    stats = aa.attribute_importance_by_revenue("attr_grit", "Accessories")

    assert stats["with_attribute"] == 1200
    assert stats["without_attribute"] == 300
