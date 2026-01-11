from datetime import datetime

import pytest

import supplier_incidents as si
from supplier_incidents import SupplierIncident


class DummyClient:
    def __init__(self, search_response=None):
        self.index_calls = []
        self.search_response = search_response

    def index(self, index, id, document, refresh):  # noqa: A003 - match API
        self.index_calls.append({
            "index": index,
            "id": id,
            "document": document,
            "refresh": refresh,
        })

    def search(self, index, body):
        self.last_search_body = body
        return self.search_response


def sample_incident(**overrides):
    base = SupplierIncident(
        incident_id="INC-1",
        supplier_id="SUP-1",
        supplier_name="Furnizor Test",
        date_reported=datetime(2025, 5, 10, 12, 0, 0),
        sku="SKU-1",
        product_type="nail_polish",
        category_main="Gel Polish",
        qty_total_in_shipment=100,
        qty_damaged=5,
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_insert_incident_calls_index(monkeypatch):
    dummy = DummyClient()
    monkeypatch.setattr(si, "_client", lambda: dummy)
    incident = sample_incident()

    si.insert_incident(incident)

    assert dummy.index_calls
    stored = dummy.index_calls[0]
    assert stored["id"] == "INC-1"
    assert stored["document"]["date_reported"].startswith("2025-05-10T12:00:00")


def test_bulk_insert_uses_helpers(monkeypatch):
    captured = {}

    def fake_bulk(client, actions):
        captured["actions"] = list(actions)

    monkeypatch.setattr(si, "helpers", type("Helpers", (), {"bulk": staticmethod(fake_bulk)}))
    monkeypatch.setattr(si, "_client", lambda: "client-marker")

    incidents = [sample_incident(incident_id="INC-2"), sample_incident(incident_id="INC-3")]
    si.bulk_insert_incidents(incidents)

    assert len(captured["actions"]) == 2
    assert captured["actions"][0]["_id"] == "INC-2"


def test_damage_rate_per_supplier(monkeypatch):
    response = {
        "aggregations": {
            "suppliers": {
                "buckets": [
                    {
                        "key": "SUP-1",
                        "damage_rate": {"value": 0.05},
                        "total_qty": {"value": 200},
                        "damaged_qty": {"value": 10},
                    }
                ]
            }
        }
    }
    dummy = DummyClient(search_response=response)
    monkeypatch.setattr(si, "_client", lambda: dummy)

    results = si.damage_rate_per_supplier(product_type="nail_polish")

    assert results[0]["supplier_id"] == "SUP-1"
    assert results[0]["damage_rate"] == 0.05
    assert "product_type" not in dummy.last_search_body  # filter is in query term


def test_damage_types_distribution(monkeypatch):
    response = {
        "aggregations": {
            "suppliers": {
                "buckets": [
                    {
                        "key": "SUP-2",
                        "damage_types": {
                            "buckets": [
                                {"key": "bottles_broken", "doc_count": 3},
                                {"key": "leakage", "doc_count": 2},
                            ]
                        },
                    }
                ]
            }
        }
    }
    dummy = DummyClient(search_response=response)
    monkeypatch.setattr(si, "_client", lambda: dummy)

    results = si.damage_types_distribution_per_supplier()

    assert results[0]["supplier_id"] == "SUP-2"
    assert results[0]["damage_types"][1]["damage_type"] == "leakage"


def test_monthly_damage_rate(monkeypatch):
    response = {
        "aggregations": {
            "monthly": {
                "buckets": [
                    {
                        "key_as_string": "2025-05-01T00:00:00.000Z",
                        "damage_rate": {"value": 0.1},
                        "total_qty": {"value": 100},
                        "damaged_qty": {"value": 10},
                    }
                ]
            }
        }
    }
    dummy = DummyClient(search_response=response)
    monkeypatch.setattr(si, "_client", lambda: dummy)

    series = si.monthly_damage_rate_for_supplier("SUP-3")

    assert series[0]["month"].startswith("2025-05")
    assert series[0]["damage_rate"] == 0.1
