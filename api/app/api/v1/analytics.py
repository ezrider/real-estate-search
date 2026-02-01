"""API routes for analytics."""

from datetime import date, timedelta
from typing import Optional, List

from fastapi import APIRouter, Query
from pydantic import BaseModel
from decimal import Decimal

from app.core.database import get_db

router = APIRouter()


class PriceDropItem(BaseModel):
    mls_number: str
    building_name: Optional[str]
    unit_number: Optional[str]
    old_price: Decimal
    new_price: Decimal
    price_drop: Decimal
    drop_percent: float
    drop_date: date
    days_on_market: Optional[int]


class PriceDropsResponse(BaseModel):
    count: int
    drops: List[PriceDropItem]


class MarketSummaryItem(BaseModel):
    neighborhood: Optional[str]
    active_listings: int
    avg_price: Optional[float]
    avg_price_per_sqft: Optional[float]
    avg_days_on_market: Optional[float]
    min_price: Optional[float]
    max_price: Optional[float]


@router.get("/price-drops", response_model=PriceDropsResponse)
def get_price_drops(
    days: int = Query(7, ge=1, le=90, description="Look back period in days"),
    min_drop_percent: float = Query(0, ge=0, description="Minimum drop percentage")
):
    """Get listings with price drops in the last N days."""
    db = get_db()
    
    since_date = date.today() - timedelta(days=days)
    
    # Find price drops
    query = """
        SELECT 
            l.mls_number,
            b.name as building_name,
            l.unit_number,
            ph_old.price as old_price,
            ph_new.price as new_price,
            ph_old.price - ph_new.price as price_drop,
            ROUND((ph_old.price - ph_new.price) / CAST(ph_old.price AS FLOAT) * 100, 2) as drop_percent,
            ph_new.recorded_date as drop_date,
            l.days_on_market
        FROM price_history ph_new
        JOIN price_history ph_old ON ph_new.listing_id = ph_old.listing_id
        JOIN listing l ON l.id = ph_new.listing_id
        LEFT JOIN building b ON b.id = l.building_id
        WHERE ph_new.recorded_date >= ?
          AND ph_new.event_type IN ('Price Drop', 'Price Change')
          AND ph_old.recorded_date = (
              SELECT MAX(recorded_date) 
              FROM price_history 
              WHERE listing_id = ph_new.listing_id AND recorded_date < ph_new.recorded_date
          )
          AND ph_new.price < ph_old.price
          AND (ph_old.price - ph_new.price) / CAST(ph_old.price AS FLOAT) * 100 >= ?
        ORDER BY drop_percent DESC
    """
    
    drops = db.execute(query, (since_date.isoformat(), min_drop_percent))
    
    return PriceDropsResponse(
        count=len(drops),
        drops=drops
    )


@router.get("/market-summary")
def get_market_summary(
    neighborhood_id: Optional[int] = Query(None, description="Filter by neighborhood")
):
    """Get market summary statistics."""
    db = get_db()
    
    query = """
        SELECT 
            n.name as neighborhood,
            COUNT(DISTINCT l.id) as active_listings,
            AVG(vlcp.current_price) as avg_price,
            AVG(vlcp.price_per_sqft) as avg_price_per_sqft,
            AVG(l.days_on_market) as avg_days_on_market,
            MIN(vlcp.current_price) as min_price,
            MAX(vlcp.current_price) as max_price
        FROM listing l
        LEFT JOIN building b ON l.building_id = b.id
        LEFT JOIN neighborhood n ON b.neighborhood_id = n.id
        LEFT JOIN v_listing_current_price vlcp ON l.id = vlcp.listing_id
        WHERE l.is_active = 1
    """
    params = []
    
    if neighborhood_id:
        query += " AND b.neighborhood_id = ?"
        params.append(neighborhood_id)
    
    query += " GROUP BY n.name ORDER BY active_listings DESC"
    
    summary = db.execute(query, tuple(params))
    
    return {"summary": summary}


@router.get("/building-comparison")
def compare_buildings(
    building_ids: List[int] = Query(..., description="List of building IDs to compare")
):
    """Compare statistics across multiple buildings."""
    if len(building_ids) > 10:
        return {"error": "Maximum 10 buildings can be compared"}
    
    db = get_db()
    
    placeholders = ','.join('?' * len(building_ids))
    
    # Current listings stats
    current_stats = db.execute(f"""
        SELECT 
            b.id,
            b.name,
            COUNT(l.id) as active_listings,
            AVG(vlcp.current_price) as avg_price,
            AVG(vlcp.price_per_sqft) as avg_price_per_sqft,
            MIN(vlcp.current_price) as min_price,
            MAX(vlcp.current_price) as max_price
        FROM building b
        LEFT JOIN listing l ON b.id = l.building_id AND l.is_active = 1
        LEFT JOIN v_listing_current_price vlcp ON l.id = vlcp.listing_id
        WHERE b.id IN ({placeholders})
        GROUP BY b.id, b.name
    """, tuple(building_ids))
    
    # Historical sales stats
    historical_stats = db.execute(f"""
        SELECT 
            b.id,
            COUNT(hs.id) as total_sales,
            AVG(hs.sale_price) as avg_sale_price,
            AVG(CAST(hs.sale_price AS FLOAT) / NULLIF(hs.square_feet, 0)) as avg_sale_price_per_sqft
        FROM building b
        LEFT JOIN historical_sale hs ON b.id = hs.building_id
        WHERE b.id IN ({placeholders})
        GROUP BY b.id
    """, tuple(building_ids))
    
    # Build comparison
    comparison = {}
    for stat in current_stats:
        comparison[stat["id"]] = {
            "name": stat["name"],
            "active_listings": stat["active_listings"],
            "avg_listing_price": stat["avg_price"],
            "avg_listing_price_per_sqft": stat["avg_price_per_sqft"],
            "price_range": {
                "min": stat["min_price"],
                "max": stat["max_price"]
            }
        }
    
    for stat in historical_stats:
        if stat["id"] in comparison:
            comparison[stat["id"]]["historical_sales"] = stat["total_sales"]
            comparison[stat["id"]]["avg_sale_price"] = stat["avg_sale_price"]
            comparison[stat["id"]]["avg_sale_price_per_sqft"] = stat["avg_sale_price_per_sqft"]
    
    return {"comparison": list(comparison.values())}


@router.get("/recent-activity")
def get_recent_activity(
    limit: int = Query(20, ge=1, le=100)
):
    """Get recent tracking events."""
    db = get_db()
    
    events = db.execute("""
        SELECT 
            te.event_type,
            te.details,
            te.created_at,
            l.mls_number,
            b.name as building_name
        FROM tracking_event te
        LEFT JOIN listing l ON te.listing_id = l.id
        LEFT JOIN building b ON l.building_id = b.id
        ORDER BY te.created_at DESC
        LIMIT ?
    """, (limit,))
    
    return {"events": events}
