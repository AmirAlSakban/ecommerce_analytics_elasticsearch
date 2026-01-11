"""Streamlit UI for the local e-commerce analytics toolkit."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from elasticsearch import Elasticsearch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import attribute_analysis as aa
from settings import configure_logging, get_settings
from supplier_incidents import SupplierIncident, insert_incident

configure_logging()
st.set_page_config(page_title="Analytics Nails/Cosmetics", layout="wide")
SETTINGS = get_settings()

ATTRIBUTE_FIELDS = [
    ("attr_volume_ml", "Volum (ml)"),
    ("attr_shade_code", "Cod de nuanță"),
    ("attr_finish", "Finisaj"),
    ("attr_curing_type", "Tip polimerizare"),
    ("attr_liquid_type", "Tip lichid"),
    ("attr_scent", "Aromă"),
    ("attr_strength_percent", "Concentrație (%)"),
    ("attr_grit", "Grit / Granulație"),
    ("attr_shape", "Formă"),
]
PRODUCT_TYPES = ["nail_polish", "nail_liquid", "tool", "consumable", "other"]
DAMAGE_TYPES = [
    "bottles_broken",
    "leakage",
    "scratched_packaging",
    "missing_items",
    "wrong_variant",
]
ROOT_CAUSE_OPTIONS = [
    "poor_internal_packaging",
    "weak_secondary_box",
    "courier_damage",
    "factory_defect",
]


@st.cache_resource(show_spinner=False)
def get_es_client() -> Elasticsearch:
    return Elasticsearch(SETTINGS.es_url, basic_auth=SETTINGS.es_basic_auth)


ES_CLIENT = get_es_client()


def build_filters(
    supplier_id: Optional[str], product_type: Optional[str], date_range: Optional[tuple[date, date]]
) -> List[Dict[str, object]]:
    filters: List[Dict[str, object]] = []
    if supplier_id and supplier_id != "Toți":
        filters.append({"term": {"supplier_id": supplier_id}})
    if product_type and product_type != "Toate":
        filters.append({"term": {"product_type": product_type}})
    if date_range and all(date_range):
        start, end = date_range
        filters.append(
            {
                "range": {
                    "date_reported": {
                        "gte": start.isoformat(),
                        "lte": (end + timedelta(days=1)).isoformat(),
                    }
                }
            }
        )
    return filters


@st.cache_data(ttl=300)
def supplier_options() -> List[str]:
    body = {
        "size": 0,
        "aggs": {
            "suppliers": {
                "terms": {"field": "supplier_id", "size": 100},
                "aggs": {"names": {"top_hits": {"size": 1, "_source": ["supplier_name"]}}},
            }
        },
    }
    resp = ES_CLIENT.search(index=SETTINGS.indices.supplier_incidents, body=body)
    return [bucket["key"] for bucket in resp["aggregations"]["suppliers"]["buckets"]]


@st.cache_data(ttl=300)
def category_options() -> List[str]:
    body = {
        "size": 0,
        "aggs": {"categories": {"terms": {"field": "category_main", "size": 100}}},
    }
    resp = ES_CLIENT.search(index=SETTINGS.indices.products, body=body)
    return [bucket["key"] for bucket in resp["aggregations"]["categories"]["buckets"]]


@st.cache_data(ttl=180)
def coverage_for_attribute(attribute_field: str) -> List[Dict[str, object]]:
    return aa.attribute_coverage_by_category(attribute_field)


def render_incident_logging_page() -> None:
    st.title("Logare incident furnizor")
    existing_suppliers = ["Alege din listă"] + supplier_options()
    with st.form("incident_form"):
        selected_supplier = st.selectbox("Furnizor existent", existing_suppliers, index=0)
        supplier_id = st.text_input("Cod furnizor", "" if selected_supplier == "Alege din listă" else selected_supplier)
        supplier_name = st.text_input("Nume furnizor")
        category_main = st.text_input("Categorie principală", value="Gel Polish")
        sku = st.text_input("SKU", placeholder="SKU123")
        product_type = st.selectbox("Tip produs", PRODUCT_TYPES, index=0)
        date_reported = st.date_input("Data raportării", value=date.today())
        qty_total = st.number_input("Cantitate totală în transport", min_value=1, step=1, value=100)
        qty_damaged = st.number_input("Cantitate deteriorată", min_value=0, step=1, value=0)
        damage_type = st.multiselect("Tip daune", DAMAGE_TYPES)
        root_cause = st.selectbox("Cauză probabilă", ROOT_CAUSE_OPTIONS, index=0)
        batch_id = st.text_input("Batch / lot", placeholder="LOT-2025-05")
        packaging_primary = st.text_input("Ambalaj primar", value="glass_bottle")
        packaging_secondary = st.text_input("Ambalaj secundar", value="thin_box")
        packaging_cushioning = st.text_input("Cushioning", value="bubble_wrap")
        transport_company = st.text_input("Curier / transport")
        comment = st.text_area("Comentariu", placeholder="Observații suplimentare")
        submitted = st.form_submit_button("Salvează incident", use_container_width=True)

    if submitted:
        if not supplier_id or not sku:
            st.error("Completează cel puțin codul furnizorului și SKU-ul produsului.")
        else:
            incident = SupplierIncident(
                incident_id=f"INC-{uuid.uuid4().hex[:8].upper()}",
                supplier_id=supplier_id,
                supplier_name=supplier_name or supplier_id,
                date_reported=datetime.combine(date_reported, datetime.min.time()),
                sku=sku,
                product_type=product_type,
                category_main=category_main or "N/A",
                qty_total_in_shipment=int(qty_total),
                qty_damaged=int(qty_damaged),
                damage_type=damage_type or ["unspecified"],
                transport_company=transport_company or None,
                root_cause_guess=root_cause,
                batch_id=batch_id or None,
                packaging_primary=packaging_primary or None,
                packaging_secondary=packaging_secondary or None,
                packaging_cushioning=packaging_cushioning or None,
                comment=comment or None,
            )
            try:
                insert_incident(incident)
            except Exception as exc:  # pragma: no cover - Streamlit feedback
                st.error(f"Nu am putut salva incidentul: {exc}")
            else:
                st.success("Incident salvat cu succes ✅")

    st.subheader("Ultimele incidente")
    incidents_df = recent_incidents_df(limit=25)
    st.dataframe(incidents_df, use_container_width=True)


def recent_incidents_df(limit: int = 25) -> pd.DataFrame:
    body = {
        "size": limit,
        "sort": [{"date_reported": {"order": "desc"}}],
        "_source": [
            "date_reported",
            "supplier_id",
            "supplier_name",
            "sku",
            "product_type",
            "qty_total_in_shipment",
            "qty_damaged",
            "damage_type",
            "comment",
        ],
    }
    resp = ES_CLIENT.search(index=SETTINGS.indices.supplier_incidents, body=body)
    rows = [hit["_source"] for hit in resp["hits"]["hits"]]
    return pd.DataFrame(rows)


def render_supplier_dashboard() -> None:
    st.title("Supplier Quality Dashboard")
    with st.sidebar:
        st.header("Filtre incidente")
        supplier_filter = st.selectbox("Furnizor", ["Toți"] + supplier_options())
        product_filter = st.selectbox("Tip produs", ["Toate"] + PRODUCT_TYPES)
        default_range = (date.today() - timedelta(days=90), date.today())
        date_range = st.date_input("Interval dată", value=default_range)
    filters = build_filters(supplier_filter, product_filter, date_range if isinstance(date_range, tuple) else default_range)
    query = {"bool": {"filter": filters}} if filters else {"match_all": {}}

    body = {
        "size": 0,
        "query": query,
        "aggs": {
            "suppliers": {
                "terms": {"field": "supplier_id", "size": 30},
                "aggs": {
                    "supplier_name": {"top_hits": {"size": 1, "_source": ["supplier_name"]}},
                    "total_qty": {"sum": {"field": "qty_total_in_shipment"}},
                    "damaged_qty": {"sum": {"field": "qty_damaged"}},
                    "damage_rate": {
                        "bucket_script": {
                            "buckets_path": {"damaged": "damaged_qty", "total": "total_qty"},
                            "script": "params.total == 0 ? 0 : params.damaged / params.total",
                        }
                    },
                },
            }
        },
    }
    resp = ES_CLIENT.search(index=SETTINGS.indices.supplier_incidents, body=body)
    supplier_rows = []
    for bucket in resp["aggregations"]["suppliers"]["buckets"]:
        name_hit = bucket["supplier_name"]["hits"]["hits"]
        supplier_rows.append(
            {
                "supplier_id": bucket["key"],
                "supplier_name": name_hit[0]["_source"].get("supplier_name") if name_hit else bucket["key"],
                "damage_rate": bucket["damage_rate"]["value"],
                "qty_total": bucket["total_qty"]["value"],
            }
        )
    supplier_df = pd.DataFrame(supplier_rows)
    if not supplier_df.empty:
        supplier_df = supplier_df.sort_values("damage_rate", ascending=False)
        st.subheader("Damage rate per supplier")
        st.bar_chart(supplier_df.set_index("supplier_name")["damage_rate"])
    else:
        st.info("Nu există incidente pentru filtrele selectate.")

    if supplier_filter != "Toți" and supplier_filter:
        st.subheader(f"Trend damage rate pentru {supplier_filter}")
        trend_df = supplier_trend_df(supplier_filter, product_filter, date_range)
        if not trend_df.empty:
            st.line_chart(trend_df.set_index("month")["damage_rate"])
        else:
            st.info("Nu există date suficiente pentru trend.")

    st.subheader("Breakdown damage type")
    breakdown_df = damage_breakdown_df(query)
    if not breakdown_df.empty:
        st.bar_chart(breakdown_df.set_index("damage_type")["count"])

    st.subheader("Breakdown root cause")
    root_df = root_cause_breakdown_df(query)
    if not root_df.empty:
        st.bar_chart(root_df.set_index("root_cause_guess")["count"])

    st.subheader("Tabel incidente")
    incidents = recent_incidents_df(limit=50)
    st.dataframe(incidents, use_container_width=True)


def supplier_trend_df(
    supplier_id: str, product_type: Optional[str], date_range: Optional[tuple[date, date]]
) -> pd.DataFrame:
    filters = build_filters(supplier_id, product_type, date_range)
    query = {"bool": {"filter": filters}} if filters else {"match_all": {}}
    body = {
        "size": 0,
        "query": query,
        "aggs": {
            "monthly": {
                "date_histogram": {
                    "field": "date_reported",
                    "calendar_interval": "month",
                },
                "aggs": {
                    "total_qty": {"sum": {"field": "qty_total_in_shipment"}},
                    "damaged_qty": {"sum": {"field": "qty_damaged"}},
                    "damage_rate": {
                        "bucket_script": {
                            "buckets_path": {"damaged": "damaged_qty", "total": "total_qty"},
                            "script": "params.total == 0 ? 0 : params.damaged / params.total",
                        }
                    },
                },
            }
        },
    }
    resp = ES_CLIENT.search(index=SETTINGS.indices.supplier_incidents, body=body)
    rows = []
    for bucket in resp["aggregations"]["monthly"]["buckets"]:
        rows.append({"month": bucket["key_as_string"][:7], "damage_rate": bucket["damage_rate"]["value"]})
    return pd.DataFrame(rows)


def damage_breakdown_df(query: Dict[str, object]) -> pd.DataFrame:
    body = {
        "size": 0,
        "query": query,
        "aggs": {"damage_type": {"terms": {"field": "damage_type", "size": 20}}},
    }
    resp = ES_CLIENT.search(index=SETTINGS.indices.supplier_incidents, body=body)
    rows = [
        {"damage_type": bucket["key"], "count": bucket["doc_count"]}
        for bucket in resp["aggregations"]["damage_type"]["buckets"]
    ]
    return pd.DataFrame(rows)


def root_cause_breakdown_df(query: Dict[str, object]) -> pd.DataFrame:
    body = {
        "size": 0,
        "query": query,
        "aggs": {"root_cause": {"terms": {"field": "root_cause_guess", "size": 20}}},
    }
    resp = ES_CLIENT.search(index=SETTINGS.indices.supplier_incidents, body=body)
    rows = [
        {"root_cause_guess": bucket["key"], "count": bucket["doc_count"]}
        for bucket in resp["aggregations"]["root_cause"]["buckets"]
    ]
    return pd.DataFrame(rows)


def render_attribute_dashboard() -> None:
    st.title("Attribute Gaps Dashboard")
    categories = category_options()
    if not categories:
        st.warning("Nu există produse indexate pentru a calcula acoperirea atributelor.")
        return
    category = st.selectbox("Categorie principală", categories, index=0)
    attribute_labels = {field: label for field, label in ATTRIBUTE_FIELDS}
    selected_attribute = st.selectbox(
        "Atribut de analizat", [field for field, _ in ATTRIBUTE_FIELDS], format_func=lambda f: attribute_labels[f]
    )

    coverage_rows = []
    for field, label in ATTRIBUTE_FIELDS:
        coverage = next((row for row in coverage_for_attribute(field) if row["category_main"] == category), None)
        coverage_rows.append({"attribute": label, "coverage": coverage["coverage_ratio"] if coverage else 0})
    coverage_df = pd.DataFrame(coverage_rows)
    st.subheader("Acoperire atribute")
    st.bar_chart(coverage_df.set_index("attribute"))

    st.subheader("Fix list pentru atributul selectat")
    missing = aa.missing_attribute_fix_list(selected_attribute, category, size=200)
    df = pd.DataFrame(missing)
    if not df.empty:
        df["brand"] = df.get("brand", "-")
        if SETTINGS.ui.product_url_template:
            df["product_url"] = df["sku"].apply(lambda sku: SETTINGS.product_url_for(sku))
        st.dataframe(df[[col for col in ["sku", "name", "brand", "price_final", "product_url"] if col in df.columns]], use_container_width=True)
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button("Descarcă fix list CSV", data=csv_data, file_name="attribute_fix_list.csv", mime="text/csv")
    else:
        st.success("Toate produsele din categoria selectată au atributul ales.")


def render_action_list() -> None:
    st.title("To-Do / Action List")
    categories = category_options()
    if not categories:
        st.warning("Nu există produse indexate pentru a genera acțiuni.")
        return
    category = st.selectbox("Categorie pentru remediere", categories, index=0)
    critical_attrs = st.multiselect(
        "Atribute critice", [field for field, _ in ATTRIBUTE_FIELDS], default=["attr_shade_code", "attr_volume_ml"]
    )
    top_n = st.slider("Număr SKU-uri per atribut", min_value=5, max_value=50, value=10, step=5)

    fix_frames = []
    for attr in critical_attrs:
        rows = aa.missing_attribute_fix_list(attr, category, size=top_n)
        df = pd.DataFrame(rows)
        if df.empty:
            continue
        df["missing_attribute"] = attr
        if SETTINGS.ui.product_url_template:
            df["product_url"] = df["sku"].apply(lambda sku: SETTINGS.product_url_for(sku))
        fix_frames.append(df)
    combined_fix = pd.concat(fix_frames, ignore_index=True) if fix_frames else pd.DataFrame()
    if not combined_fix.empty:
        combined_fix = combined_fix.sort_values("price_final", ascending=False)
        st.subheader("SKU-uri prioritare fără atribute cheie")
        st.dataframe(
            combined_fix[[col for col in ["missing_attribute", "sku", "name", "price_final", "product_url"] if col in combined_fix.columns]],
            use_container_width=True,
        )
        st.download_button(
            "Exportă SKU-uri critice",
            data=combined_fix.to_csv(index=False).encode("utf-8"),
            file_name="sku_attribute_gaps.csv",
            mime="text/csv",
        )
    else:
        st.info("Nu am găsit SKU-uri lipsă pentru atributele selectate.")

    st.subheader("Furnizori cu cele mai mari damage rate (ultimele 30 zile)")
    end = date.today()
    recent = supplier_damage_rates(end - timedelta(days=30), end, label="damage_rate_recent")
    previous = supplier_damage_rates(end - timedelta(days=60), end - timedelta(days=30), label="damage_rate_prev")
    if recent.empty:
        st.info("Nu există incidente în ultimele 30 de zile.")
    else:
        if not previous.empty:
            merged = recent.merge(previous, on="supplier_id", how="left", suffixes=("_recent", "_prev"))
            merged["delta"] = merged["damage_rate_recent"] - merged["damage_rate_prev"].fillna(0)
        else:
            merged = recent.copy()
            merged["delta"] = merged["damage_rate_recent"]
        st.dataframe(merged, use_container_width=True)
        st.download_button(
            "Exportă KPI furnizori",
            data=merged.to_csv(index=False).encode("utf-8"),
            file_name="supplier_damage_watch.csv",
            mime="text/csv",
        )


def supplier_damage_rates(start: date, end: date, label: str) -> pd.DataFrame:
    filters = build_filters(None, None, (start, end))
    query = {"bool": {"filter": filters}}
    body = {
        "size": 0,
        "query": query,
        "aggs": {
            "suppliers": {
                "terms": {"field": "supplier_id", "size": 50},
                "aggs": {
                    "total_qty": {"sum": {"field": "qty_total_in_shipment"}},
                    "damaged_qty": {"sum": {"field": "qty_damaged"}},
                    "damage_rate": {
                        "bucket_script": {
                            "buckets_path": {"damaged": "damaged_qty", "total": "total_qty"},
                            "script": "params.total == 0 ? 0 : params.damaged / params.total",
                        }
                    },
                },
            }
        },
    }
    resp = ES_CLIENT.search(index=SETTINGS.indices.supplier_incidents, body=body)
    rows = [
        {
            "supplier_id": bucket["key"],
            "damage_rate": bucket["damage_rate"]["value"],
            "qty_total": bucket["total_qty"]["value"],
        }
        for bucket in resp["aggregations"]["suppliers"]["buckets"]
    ]
    # Return DataFrame with proper structure even when empty
    if not rows:
        return pd.DataFrame(columns=["supplier_id", "damage_rate", "qty_total"])
    df = pd.DataFrame(rows)
    df = df.rename(columns={"damage_rate": label})
    df = df.rename(columns={"qty_total": f"qty_total_{label}"})
    return df


def main() -> None:
    page = st.sidebar.radio(
        "Navigare",
        (
            "Logare incident",
            "Calitate furnizori",
            "Attribute gaps",
            "Action list",
        ),
    )
    if page == "Logare incident":
        render_incident_logging_page()
    elif page == "Calitate furnizori":
        render_supplier_dashboard()
    elif page == "Attribute gaps":
        render_attribute_dashboard()
    else:
        render_action_list()


if __name__ == "__main__":
    main()
