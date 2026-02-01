"""Pydantic models for historical sales."""

from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict


class HistoricalSaleBase(BaseModel):
    """Base historical sale model."""
    unit_number: Optional[str] = None
    sale_price: Decimal = Field(..., decimal_places=2)
    sale_date: date
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None
    property_type: Optional[str] = None
    days_on_market: Optional[int] = None
    notes: Optional[str] = None
    data_source: str = "CSV Import"


class HistoricalSaleCreate(HistoricalSaleBase):
    """Model for creating a historical sale."""
    # Building info (auto-created if not exists)
    building_name: str
    address: Optional[str] = None
    neighborhood: Optional[str] = None
    
    # Photo URLs to download
    photos: List[str] = []


class HistoricalSaleResponse(HistoricalSaleBase):
    """Full historical sale response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    building_id: Optional[int] = None
    building_name: Optional[str] = None
    created_at: Optional[datetime] = None


class HistoricalSaleListItem(BaseModel):
    """Simplified historical sale for list views."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    building_name: Optional[str]
    unit_number: Optional[str]
    sale_price: Decimal
    sale_date: date
    bedrooms: Optional[int]
    bathrooms: Optional[float]
    square_feet: Optional[int]
    price_per_sqft: Optional[float]
    days_on_market: Optional[int]


class HistoricalSaleListResponse(BaseModel):
    """Paginated historical sales response."""
    total: int
    offset: int
    limit: int
    sales: List[HistoricalSaleListItem]


class CSVImportResponse(BaseModel):
    """Response from CSV import."""
    success: bool
    total_rows: int
    imported: int
    skipped: int
    errors: List[str]
