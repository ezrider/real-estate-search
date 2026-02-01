"""API routes for buildings."""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Query

from app.models.building import BuildingResponse, BuildingStats, BuildingListItem
from app.core.database import get_db

router = APIRouter()


@router.get("", response_model=List[BuildingListItem])
def list_buildings(
    neighborhood_id: Optional[int] = Query(None, description="Filter by neighborhood"),
    has_active_listings: bool = Query(False, description="Only buildings with active listings")
):
    """List buildings."""
    db = get_db()
    
    query = """
        SELECT 
            b.id,
            b.name,
            b.address,
            n.name as neighborhood,
            b.building_type,
            COUNT(DISTINCT l.id) as active_listings
        FROM building b
        LEFT JOIN neighborhood n ON b.neighborhood_id = n.id
        LEFT JOIN listing l ON b.id = l.building_id AND l.is_active = 1
        WHERE 1=1
    """
    params = []
    
    if neighborhood_id:
        query += " AND b.neighborhood_id = ?"
        params.append(neighborhood_id)
    
    query += " GROUP BY b.id, b.name, b.address, n.name, b.building_type"
    
    if has_active_listings:
        query += " HAVING active_listings > 0"
    
    query += " ORDER BY b.name"
    
    buildings = db.execute(query, tuple(params))
    return buildings


@router.get("/{building_id}", response_model=BuildingResponse)
def get_building(building_id: int):
    """Get building details."""
    db = get_db()
    
    building = db.execute(
        """SELECT 
            b.*,
            n.name as neighborhood_name
           FROM building b
           LEFT JOIN neighborhood n ON b.neighborhood_id = n.id
           WHERE b.id = ?""",
        (building_id,),
        fetch_one=True
    )
    
    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building with ID {building_id} not found"
        )
    
    return building


@router.get("/{building_id}/stats", response_model=BuildingStats)
def get_building_stats(building_id: int):
    """Get statistics for a building."""
    db = get_db()
    
    stats = db.execute(
        """SELECT 
            b.id as building_id,
            b.name as building_name,
            n.name as neighborhood,
            COUNT(DISTINCT l.id) as active_listings,
            AVG(vlcp.current_price) as avg_price,
            AVG(vlcp.price_per_sqft) as avg_price_per_sqft,
            COUNT(DISTINCT hs.id) as historical_sales_count,
            AVG(hs.sale_price) as avg_historical_sale_price
        FROM building b
        LEFT JOIN neighborhood n ON b.neighborhood_id = n.id
        LEFT JOIN listing l ON b.id = l.building_id AND l.is_active = 1
        LEFT JOIN v_listing_current_price vlcp ON l.id = vlcp.listing_id
        LEFT JOIN historical_sale hs ON b.id = hs.building_id
        WHERE b.id = ?
        GROUP BY b.id, b.name, n.name""",
        (building_id,),
        fetch_one=True
    )
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building with ID {building_id} not found"
        )
    
    return stats


@router.get("/{building_id}/listings")
def get_building_listings(
    building_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Get listings for a specific building."""
    db = get_db()
    
    # Check building exists
    building = db.execute(
        "SELECT name FROM building WHERE id = ?",
        (building_id,),
        fetch_one=True
    )
    
    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building with ID {building_id} not found"
        )
    
    from app.services.listing_service import get_listing_service
    service = get_listing_service()
    
    result = service.list_listings(
        building_id=building_id,
        limit=limit,
        offset=offset
    )
    
    return {
        "building_id": building_id,
        "building_name": building["name"],
        **result
    }


@router.get("/{building_id}/sales")
def get_building_sales(
    building_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Get historical sales for a specific building."""
    db = get_db()
    
    # Check building exists
    building = db.execute(
        "SELECT name FROM building WHERE id = ?",
        (building_id,),
        fetch_one=True
    )
    
    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building with ID {building_id} not found"
        )
    
    from app.services.historical_sale_service import get_historical_sale_service
    service = get_historical_sale_service()
    
    result = service.list_sales(
        building_id=building_id,
        limit=limit,
        offset=offset
    )
    
    return {
        "building_id": building_id,
        "building_name": building["name"],
        **result
    }


@router.get("/neighborhoods/all")
def list_neighborhoods():
    """List all neighborhoods."""
    db = get_db()
    
    neighborhoods = db.execute(
        "SELECT * FROM neighborhood ORDER BY name"
    )
    
    return {"neighborhoods": neighborhoods}
