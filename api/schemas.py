"""Pydantic schemas for the FastAPI surface."""
from __future__ import annotations

from datetime import datetime, date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductPayload(BaseModel):
    """Minimal product payload accepted by the API."""

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    sku: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    brand: Optional[str] = None
    category_main: Optional[str] = None
    description_short: Optional[str] = None
    description_html: Optional[str] = None
    price_final: Optional[float] = None
    stock_status: Optional[str] = None
    active: Optional[str] = Field(
        default=None, description="Original active flag from catalog exports"
    )
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional explicit attr_* overrides (ex: attr_volume_ml)",
    )


class ProductIngestResponse(BaseModel):
    sku: str
    indexed: bool = True
    attributes: Dict[str, Any]
    url: Optional[str] = None


class ProductDocument(BaseModel):
    sku: str
    document: Dict[str, Any]


class MissingAttributeItem(BaseModel):
    sku: str
    name: Optional[str] = None
    brand: Optional[str] = None
    category_main: Optional[str] = None
    price_final: Optional[float] = None
    image_url: Optional[str] = None


class MissingAttributeResponse(BaseModel):
    attribute: str
    category_main: Optional[str]
    size: int
    items: List[MissingAttributeItem]


class IncidentPayload(BaseModel):
    """Supplier incident payload."""

    model_config = ConfigDict(str_strip_whitespace=True)

    incident_id: Optional[str] = Field(
        default=None, description="If omitted the API will auto-generate one"
    )
    supplier_id: str = Field(..., min_length=1)
    supplier_name: str = Field(..., min_length=1)
    date_reported: datetime = Field(default_factory=datetime.utcnow)
    sku: Optional[str] = None
    product_type: Optional[str] = None
    category_main: Optional[str] = None
    qty_total_in_shipment: int = Field(..., gt=0)
    qty_damaged: int = Field(..., ge=0)
    damage_type: List[str] = Field(default_factory=list)
    shipment_id: Optional[str] = None
    transport_company: Optional[str] = None
    root_cause_guess: Optional[str] = None
    batch_id: Optional[str] = None
    packaging_primary: Optional[str] = None
    packaging_secondary: Optional[str] = None
    packaging_cushioning: Optional[str] = None
    comment: Optional[str] = None


class IncidentResponse(BaseModel):
    incident_id: str
    created: bool = True


class IncidentDocument(BaseModel):
    incident_id: str
    document: Dict[str, Any]


class SupplierKPI(BaseModel):
    supplier_id: str
    damage_rate: float
    qty_total: float
    qty_damaged: float
    product_type: Optional[str] = None


class SupplierKPISummary(BaseModel):
    items: List[SupplierKPI]


class MonthlySupplierMetric(BaseModel):
    month: str
    damage_rate: float
    qty_total: float
    qty_damaged: float


class MonthlySupplierResponse(BaseModel):
    supplier_id: str
    items: List[MonthlySupplierMetric]


class DailyStat(BaseModel):
    sku: str
    date: date
    views: Optional[int] = None
    add_to_cart: Optional[int] = None
    purchases: Optional[int] = None
    returns: Optional[int] = None
    revenue: Optional[float] = None


class DailyStatsResponse(BaseModel):
    sku: str
    items: List[DailyStat]