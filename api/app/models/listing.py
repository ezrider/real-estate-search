"""Pydantic models for listings."""

from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict


class PriceHistoryEntry(BaseModel):
    """A price history record."""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[int] = None
    price: Decimal = Field(..., decimal_places=2)
    recorded_date: date
    event_type: str = "Price Change"
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    
    # Computed fields
    previous_price: Optional[Decimal] = None
    price_change: Optional[Decimal] = None
    percent_change: Optional[float] = None


class ListingPhoto(BaseModel):
    """A listing photo."""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[int] = None
    photo_url: str  # Local file path
    display_order: int = 0
    caption: Optional[str] = None
    created_at: Optional[datetime] = None


class ListingBase(BaseModel):
    """Base listing model."""
    mls_number: Optional[str] = None
    unit_number: Optional[str] = None
    status: str = "Active"
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None
    property_type: Optional[str] = None
    listing_date: Optional[date] = None
    days_on_market: Optional[int] = None
    description: Optional[str] = None
    listing_agent: Optional[str] = None
    listing_brokerage: Optional[str] = None
    source_url: Optional[str] = None
    source_platform: str = "Manual"


class ListingCreate(ListingBase):
    """Model for creating a new listing."""
    # Building info (will be auto-created if not exists)
    building_name: Optional[str] = None
    address: Optional[str] = None
    neighborhood: Optional[str] = None
    
    # Price (will create initial price_history entry)
    price: Optional[Decimal] = None
    
    # Photo URLs to download
    photos: List[str] = []


class ListingUpdate(BaseModel):
    """Model for updating a listing."""
    status: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None
    description: Optional[str] = None
    listing_agent: Optional[str] = None
    days_on_market: Optional[int] = None
    is_active: Optional[bool] = None


class ListingResponse(ListingBase):
    """Full listing response model."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    building_id: Optional[int] = None
    building_name: Optional[str] = None
    is_active: bool = True
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Computed fields
    current_price: Optional[Decimal] = None
    price_per_sqft: Optional[float] = None
    
    # Related data
    price_history: List[PriceHistoryEntry] = []
    photos: List[ListingPhoto] = []


class ListingListItem(BaseModel):
    """Simplified listing for list views."""
    model_config = ConfigDict(from_attributes=True)
    
    mls_number: Optional[str]
    building_name: Optional[str]
    unit_number: Optional[str]
    bedrooms: Optional[int]
    bathrooms: Optional[float]
    square_feet: Optional[int]
    current_price: Optional[Decimal]
    price_per_sqft: Optional[float]
    status: str
    days_on_market: Optional[int]
    photo_thumbnail: Optional[str]
    source_url: Optional[str]


class ListingListResponse(BaseModel):
    """Paginated listing response."""
    total: int
    offset: int
    limit: int
    listings: List[ListingListItem]


class PriceCreate(BaseModel):
    """Model for adding a new price point."""
    price: Decimal = Field(..., decimal_places=2)
    date: Optional[date] = None
    event_type: str = "Price Change"
    notes: Optional[str] = None


class PriceCreateResponse(BaseModel):
    """Response after creating price history."""
    success: bool
    price_history_id: int
    previous_price: Optional[Decimal]
    price_change: Optional[Decimal]
    percent_change: Optional[float]


class StatusUpdate(BaseModel):
    """Model for updating listing status."""
    status: str  # Sold, Expired, Cancelled, etc.
    sale_price: Optional[Decimal] = None
    sale_date: Optional[date] = None
