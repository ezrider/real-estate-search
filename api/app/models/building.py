"""Pydantic models for buildings."""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict


class BuildingBase(BaseModel):
    """Base building model."""
    name: str
    address: str
    city: str = "Victoria"
    postal_code: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    year_built: Optional[int] = None
    total_units: Optional[int] = None
    floors: Optional[int] = None
    building_type: Optional[str] = None  # High-Rise, Mid-Rise, etc.
    amenities: Optional[str] = None  # JSON string
    description: Optional[str] = None


class BuildingCreate(BuildingBase):
    """Model for creating a building."""
    neighborhood: Optional[str] = None  # Will be matched/created


class BuildingResponse(BuildingBase):
    """Full building response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    neighborhood_id: Optional[int] = None
    neighborhood_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BuildingStats(BaseModel):
    """Building statistics."""
    model_config = ConfigDict(from_attributes=True)
    
    building_id: int
    building_name: str
    neighborhood: Optional[str]
    active_listings: int
    avg_price: Optional[Decimal]
    avg_price_per_sqft: Optional[float]
    historical_sales_count: int
    avg_historical_sale_price: Optional[Decimal]


class BuildingListItem(BaseModel):
    """Simplified building for list views."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    address: str
    neighborhood: Optional[str]
    building_type: Optional[str]
    active_listings: int = 0


class Neighborhood(BaseModel):
    """Neighborhood model."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    city: str
    description: Optional[str] = None
