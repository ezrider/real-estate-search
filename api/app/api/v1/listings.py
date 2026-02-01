"""API routes for listings."""

from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.models.listing import (
    ListingCreate, ListingResponse, ListingUpdate,
    ListingListResponse, PriceCreate, PriceCreateResponse,
    StatusUpdate
)
from app.services.listing_service import get_listing_service
from app.core.database import get_db

router = APIRouter()


class ListingCreateResponse(BaseModel):
    success: bool
    listing_id: int
    mls_number: Optional[str]
    is_new: bool
    price_recorded: bool
    photo_download_queued: int = 0
    message: str


@router.post("", response_model=ListingCreateResponse)
async def create_or_update_listing(listing: ListingCreate):
    """Create a new listing or update an existing one."""
    service = get_listing_service()
    
    # Convert Pydantic model to dict
    data = listing.model_dump(exclude_unset=True)
    
    result = service.create_or_update_listing(data)
    
    # Queue photo downloads (async)
    photo_count = 0
    if listing.photos:
        import asyncio
        from app.services.photo_service import get_photo_service
        photo_service = get_photo_service()
        try:
            downloaded = await asyncio.wait_for(
                photo_service.download_listing_photos(
                    listing.mls_number or str(result["listing_id"]),
                    listing.photos
                ),
                timeout=60
            )
            photo_count = len(downloaded)
        except asyncio.TimeoutError:
            pass  # Photos will be downloaded later
    
    return ListingCreateResponse(
        **result,
        photo_download_queued=photo_count
    )


@router.get("/{mls_number}", response_model=ListingResponse)
def get_listing(mls_number: str):
    """Get a listing by MLS number."""
    service = get_listing_service()
    listing = service.get_listing(mls_number)
    
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing with MLS number {mls_number} not found"
        )
    
    return listing


@router.get("", response_model=ListingListResponse)
def list_listings(
    status: Optional[str] = Query(None, description="Filter by status"),
    building_id: Optional[int] = Query(None, description="Filter by building ID"),
    neighborhood_id: Optional[int] = Query(None, description="Filter by neighborhood ID"),
    min_price: Optional[int] = Query(None, description="Minimum price"),
    max_price: Optional[int] = Query(None, description="Maximum price"),
    bedrooms: Optional[int] = Query(None, description="Exact bedroom count"),
    property_type: Optional[str] = Query(None, description="Property type"),
    sort: str = Query("date_desc", description="Sort order: price_asc, price_desc, date_desc, days_on_market"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """List listings with optional filters."""
    service = get_listing_service()
    
    result = service.list_listings(
        status=status,
        building_id=building_id,
        neighborhood_id=neighborhood_id,
        min_price=Decimal(min_price) if min_price else None,
        max_price=Decimal(max_price) if max_price else None,
        bedrooms=bedrooms,
        property_type=property_type,
        sort=sort,
        limit=limit,
        offset=offset
    )
    
    return result


@router.patch("/{mls_number}")
def update_listing(mls_number: str, update: ListingUpdate):
    """Update a listing."""
    service = get_listing_service()
    
    # Check if listing exists
    existing = service.get_listing(mls_number)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing with MLS number {mls_number} not found"
        )
    
    # Update fields
    update_data = update.model_dump(exclude_unset=True)
    if update_data:
        from app.core.database import get_db
        db = get_db()
        
        # Build update query
        fields = []
        values = []
        for key, value in update_data.items():
            fields.append(f"{key} = ?")
            values.append(value)
        
        values.append(mls_number)
        query = f"UPDATE listing SET {', '.join(fields)}, updated_at = datetime('now') WHERE mls_number = ?"
        
        db.execute_update(query, tuple(values))
    
    return {"success": True, "message": "Listing updated"}


@router.patch("/{mls_number}/status")
def update_listing_status(mls_number: str, update: StatusUpdate):
    """Update listing status (Sold, Expired, Cancelled, etc.)."""
    service = get_listing_service()
    
    success = service.update_status(
        mls_number,
        update.status,
        update.sale_price,
        update.sale_date
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing with MLS number {mls_number} not found"
        )
    
    return {"success": True, "message": f"Status updated to {update.status}"}


@router.delete("/{mls_number}")
def delete_listing(
    mls_number: str,
    purge_photos: bool = Query(False, description="Also delete associated photos")
):
    """Delete a listing."""
    service = get_listing_service()
    
    success = service.delete_listing(mls_number, purge_photos)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing with MLS number {mls_number} not found"
        )
    
    return {"success": True, "message": "Listing deleted"}


@router.post("/{mls_number}/prices", response_model=PriceCreateResponse)
def add_price(mls_number: str, price: PriceCreate):
    """Add a price history entry."""
    service = get_listing_service()
    
    listing = service.get_listing(mls_number)
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing with MLS number {mls_number} not found"
        )
    
    # Get previous price
    from app.core.database import get_db
    db = get_db()
    
    prev = db.execute(
        """SELECT price FROM price_history 
           WHERE listing_id = ? 
           ORDER BY recorded_date DESC LIMIT 1""",
        (listing["id"],),
        fetch_one=True
    )
    
    previous_price = Decimal(str(prev["price"])) if prev else None
    price_change = None
    percent_change = None
    
    if previous_price:
        price_change = price.price - previous_price
        if previous_price != 0:
            percent_change = float(price_change / previous_price * 100)
    
    # Record price
    price_id = service._record_price(
        listing["id"],
        price.price,
        price.date,
        price.event_type
    )
    
    return PriceCreateResponse(
        success=True,
        price_history_id=price_id,
        previous_price=previous_price,
        price_change=price_change,
        percent_change=percent_change
    )


@router.get("/{mls_number}/prices")
def get_price_history(mls_number: str):
    """Get price history for a listing."""
    from app.core.database import get_db
    db = get_db()
    
    listing = db.execute(
        "SELECT id FROM listing WHERE mls_number = ?",
        (mls_number,),
        fetch_one=True
    )
    
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing with MLS number {mls_number} not found"
        )
    
    prices = db.execute(
        """SELECT * FROM price_history 
           WHERE listing_id = ? 
           ORDER BY recorded_date DESC""",
        (listing["id"],)
    )
    
    return {"mls_number": mls_number, "prices": prices}
