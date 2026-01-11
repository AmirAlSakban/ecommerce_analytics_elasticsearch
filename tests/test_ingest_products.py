import pandas as pd

from ingest_products import RO_COLUMN_MAP, row_to_document


def test_row_to_document_maps_romanian_fields_and_normalizes_values(monkeypatch):
    data = {
        "Cod Produs (SKU)": "SKU123",
        "Denumire Produs": "Gel Polish 10 ml",
        "Pret": "12,50",
        "Pret final (Calculat)": "10.00",
        "Pretul Include TVA": "Da",
        "Cuvinte Cheie": "gel, polish",
        "Produse Cross-Sell": "SKU200, SKU201",
        "Produse Up-Sell": "SKU300",
        "Descriere Produs": "Finisaj mat",
    }
    # asigurăm prezența tuturor coloanelor cerute
    for header in RO_COLUMN_MAP:
        data.setdefault(header, None)

    row = pd.Series(data)
    document = row_to_document(row)

    assert document["sku"] == "SKU123"
    assert document["price"] == 12.5
    assert document["price_final"] == 10.0
    assert document["vat_included"] is True
    assert document["cross_sell_skus"] == ["SKU200", "SKU201"]
    assert document["up_sell_skus"] == ["SKU300"]
    assert document["attr_volume_ml"] == 10.0  # din titlu
    assert document["attr_finish"] == "mat"
