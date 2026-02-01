"""Listing service with business logic."""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal

from app.core.database import get_db
from app.services.photo_service import get_photo_service


class ListingService:
    """Service for listing operations."""
    
    def __init__(self):
        self.db = get_db()
        self.photo_service = get_photo_service()
    
    def _get_or_create_building(
        self,
        name: Optional[str],
        address: Optional[str],
        neighborhood: Optional[str]
    ) -> Optional[int]:
        """Get existing building or create new one. Returns building_id."""
        if not name and not address:
            return None
        
        # Try to find existing building by name
        if name:
            result = self.db.execute(
                "SELECT id FROM building WHERE name = ?",
                (name,),
                fetch_one=True
            )
            if result:
                return result["id"]
        
        # Try to find by address
        if address:
            result = self.db.execute(
                "SELECT id FROM building WHERE address = ?",
                (address,),
                fetch_one=True
            )
            if result:
                return result["id"]
        
        # Create new building
        # Get or create neighborhood
        neighborhood_id = None
        if neighborhood:
            neigh_result = self.db.execute(
                "SELECT id FROM neighborhood WHERE name = ?",
                (neighborhood,),
                fetch_one=True
            )
            if neigh_result:
                neighborhood_id = neigh_result["id"]
        
        # Use name as address if address not provided
        building_address = address or name or "Unknown"
        building_name = name or building_address
        
        building_id = self.db.execute_insert(
            """INSERT INTO building (name, address, neighborhood_id, city)
               VALUES (?, ?, ?, ?)""",
            (building_name, building_address, neighborhood_id, "Victoria")
        )
        
        return building_id
    
    def _record_price(
        self,
        listing_id: int,
        price: Decimal,
        price_date: Optional[date] = None,
        event_type: str = "Initial"
    ) -> int:
        """Record a price point in history."""
        if price_date is None:
            price_date = date.today()
        
        # Check if price already exists for this date
        existing = self.db.execute(
            """SELECT id FROM price_history 
               WHERE listing_id = ? AND recorded_date = ? AND price = ?""",
            (listing_id, price_date, price),
            fetch_one=True
        )
        
        if existing:
            return existing["id"]
        
        # Get previous price to determine event type
        if event_type == "Price Change":
            prev = self.db.execute(
                """SELECT price FROM price_history 
                   WHERE listing_id = ? 
                   ORDER BY recorded_date DESC LIMIT 1""",
                (listing_id,),
                fetch_one=True
            )
            if prev:
                prev_price = Decimal(str(prev["price"]))
                if price < prev_price:
                    event_type = "Price Drop"
                elif price > prev_price:
                    event_type = "Price Increase"
        
        return self.db.execute_insert(
            """INSERT INTO price_history (listing_id, price, recorded_date, event_type)
               VALUES (?, ?, ?, ?)""",
            (listing_id, price, price_date, event_type)
        )
    
    def create_or_update_listing(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new listing or update existing."""
        mls_number = data.get("mls_number")
        
        if not mls_number:
            raise ValueError("mls_number is required")
        
        # Check if listing exists
        existing = self.db.execute(
            "SELECT id, is_active FROM listing WHERE mls_number = ?",
            (mls_number,),
            fetch_one=True
        )
        
        # Get or create building
        building_id = self._get_or_create_building(
            data.get("building_name"),
            data.get("address"),
            data.get("neighborhood")
        )
        
        now = datetime.now()
        price = data.get("price")
        
        if existing:
            # Update existing listing
            listing_id = existing["id"]
            
            self.db.execute_update(
                """UPDATE listing SET
                    building_id = ?,
                    unit_number = ?,
                    status = ?,
                    bedrooms = ?,
                    bathrooms = ?,
                    square_feet = ?,
                    property_type = ?,
                    listing_date = ?,
                    days_on_market = ?,
                    description = ?,
                    listing_agent = ?,
                    listing_brokerage = ?,
                    source_url = ?,
                    source_platform = ?,
                    is_active = 1,
                    last_seen_at = ?,
                    updated_at = ?
                   WHERE id = ?""",
                (
                    building_id,
                    data.get("unit_number"),
                    data.get("status", "Active"),
                    data.get("bedrooms"),
                    data.get("bathrooms"),
                    data.get("square_feet"),
                    data.get("property_type"),
                    data.get("listing_date"),
                    data.get("days_on_market"),
                    data.get("description"),
                    data.get("listing_agent"),
                    data.get("listing_brokerage"),
                    data.get("source_url"),
                    data.get("source_platform", "Manual"),
                    now,
                    now,
                    listing_id
                )
            )
            
            # Record price if provided and changed
            price_recorded = False
            if price:
                current_price = self.db.execute(
                    """SELECT price FROM price_history 
                       WHERE listing_id = ? 
                       ORDER BY recorded_date DESC LIMIT 1""",
                    (listing_id,),
                    fetch_one=True
                )
                if not current_price or Decimal(str(current_price["price"])) != price:
                    self._record_price(listing_id, price, event_type="Price Change")
                    price_recorded = True
            
            # Log event
            self.db.execute_insert(
                "INSERT INTO tracking_event (listing_id, event_type, details) VALUES (?, ?, ?)",
                (listing_id, "Updated", f"Updated from {data.get('source_platform')}")
            )
            
            return {
                "success": True,
                "listing_id": listing_id,
                "mls_number": mls_number,
                "is_new": False,
                "price_recorded": price_recorded,
                "message": "Listing updated"
            }
        
        else:
            # Create new listing
            listing_id = self.db.execute_insert(
                """INSERT INTO listing (
                    mls_number, building_id, unit_number, status,
                    bedrooms, bathrooms, square_feet, property_type,
                    listing_date, days_on_market, description,
                    listing_agent, listing_brokerage, source_url, source_platform,
                    is_active, first_seen_at, last_seen_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)""",
                (
                    mls_number,
                    building_id,
                    data.get("unit_number"),
                    data.get("status", "Active"),
                    data.get("bedrooms"),
                    data.get("bathrooms"),
                    data.get("square_feet"),
                    data.get("property_type"),
                    data.get("listing_date"),
                    data.get("days_on_market"),
                    data.get("description"),
                    data.get("listing_agent"),
                    data.get("listing_brokerage"),
                    data.get("source_url"),
                    data.get("source_platform", "Manual"),
                    now, now, now, now
                )
            )
            
            # Record initial price
            price_recorded = False
            if price:
                self._record_price(listing_id, price, data.get("listing_date"), "Initial")
                price_recorded = True
            
            # Log event
            self.db.execute_insert(
                "INSERT INTO tracking_event (listing_id, event_type, details) VALUES (?, ?, ?)",
                (listing_id, "Discovered", f"Found on {data.get('source_platform')}")
            )
            
            return {
                "success": True,
                "listing_id": listing_id,
                "mls_number": mls_number,
                "is_new": True,
                "price_recorded": price_recorded,
                "message": "New listing created"
            }
    
    def get_listing(self, mls_number: str) -> Optional[Dict[str, Any]]:
        """Get full listing details with price history and photos."""
        listing = self.db.execute(
            """SELECT 
                l.*,
                b.name as building_name,
                b.address as building_address,
                n.name as neighborhood_name
               FROM listing l
               LEFT JOIN building b ON l.building_id = b.id
               LEFT JOIN neighborhood n ON b.neighborhood_id = n.id
               WHERE l.mls_number = ?""",
            (mls_number,),
            fetch_one=True
        )
        
        if not listing:
            return None
        
        # Get price history
        price_history = self.db.execute(
            """SELECT * FROM price_history 
               WHERE listing_id = ? 
               ORDER BY recorded_date DESC""",
            (listing["id"],)
        )
        
        # Get photos
        photos = self.db.execute(
            "SELECT * FROM listing_photo WHERE listing_id = ? ORDER BY display_order",
            (listing["id"],)
        )
        
        return {
            **listing,
            "price_history": price_history,
            "photos": photos
        }
    
    def list_listings(
        self,
        status: Optional[str] = None,
        building_id: Optional[int] = None,
        neighborhood_id: Optional[int] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        bedrooms: Optional[int] = None,
        property_type: Optional[str] = None,
        sort: str = "date_desc",
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List listings with filters."""
        
        # Build query
        where_clauses = ["1=1"]
        params = []
        
        if status:
            where_clauses.append("l.status = ?")
            params.append(status)
        else:
            where_clauses.append("l.is_active = 1")
        
        if building_id:
            where_clauses.append("l.building_id = ?")
            params.append(building_id)
        
        if neighborhood_id:
            where_clauses.append("b.neighborhood_id = ?")
            params.append(neighborhood_id)
        
        if bedrooms is not None:
            where_clauses.append("l.bedrooms = ?")
            params.append(bedrooms)
        
        if property_type:
            where_clauses.append("l.property_type = ?")
            params.append(property_type)
        
        # Count total
        count_query = f"""
            SELECT COUNT(*) as count 
            FROM listing l
            LEFT JOIN building b ON l.building_id = b.id
            WHERE {' AND '.join(where_clauses)}
        """
        total_result = self.db.execute(count_query, tuple(params), fetch_one=True)
        total = total_result["count"] if total_result else 0
        
        # Sort mapping
        sort_options = {
            "price_asc": "current_price ASC",
            "price_desc": "current_price DESC",
            "date_desc": "l.listing_date DESC",
            "days_on_market": "l.days_on_market ASC"
        }
        order_by = sort_options.get(sort, "l.listing_date DESC")
        
        # Get listings with current price
        query = f"""
            SELECT 
                l.mls_number,
                b.name as building_name,
                l.unit_number,
                l.bedrooms,
                l.bathrooms,
                l.square_feet,
                l.status,
                l.days_on_market,
                l.source_url,
                (
                    SELECT ph.price 
                    FROM price_history ph 
                    WHERE ph.listing_id = l.id 
                    ORDER BY ph.recorded_date DESC 
                    LIMIT 1
                ) as current_price,
                (
                    SELECT lp.photo_url 
                    FROM listing_photo lp 
                    WHERE lp.listing_id = l.id 
                    ORDER BY lp.display_order 
                    LIMIT 1
                ) as photo_thumbnail
            FROM listing l
            LEFT JOIN building b ON l.building_id = b.id
            WHERE {' AND '.join(where_clauses)}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        listings = self.db.execute(query, tuple(params))
        
        # Calculate price_per_sqft
        for listing in listings:
            if listing.get("current_price") and listing.get("square_feet"):
                listing["price_per_sqft"] = round(
                    Decimal(str(listing["current_price"])) / listing["square_feet"], 2
                )
            else:
                listing["price_per_sqft"] = None
        
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "listings": listings
        }
    
    def update_status(
        self,
        mls_number: str,
        status: str,
        sale_price: Optional[Decimal] = None,
        sale_date: Optional[date] = None
    ) -> bool:
        """Update listing status."""
        listing = self.db.execute(
            "SELECT id FROM listing WHERE mls_number = ?",
            (mls_number,),
            fetch_one=True
        )
        
        if not listing:
            return False
        
        listing_id = listing["id"]
        now = datetime.now()
        
        self.db.execute_update(
            """UPDATE listing SET status = ?, is_active = ?, last_seen_at = ?, updated_at = ?
               WHERE id = ?""",
            (status, 0 if status in ("Sold", "Expired", "Cancelled") else 1, now, now, listing_id)
        )
        
        # Record sale price if provided
        if sale_price and status == "Sold":
            self._record_price(
                listing_id,
                sale_price,
                sale_date or date.today(),
                "Sold"
            )
        
        # Log event
        self.db.execute_insert(
            "INSERT INTO tracking_event (listing_id, event_type, details) VALUES (?, ?, ?)",
            (listing_id, "StatusChange", f"Status changed to {status}")
        )
        
        return True
    
    def delete_listing(self, mls_number: str, purge_photos: bool = False) -> bool:
        """Delete a listing and optionally its photos."""
        listing = self.db.execute(
            "SELECT id FROM listing WHERE mls_number = ?",
            (mls_number,),
            fetch_one=True
        )
        
        if not listing:
            return False
        
        if purge_photos:
            self.photo_service.purge_listing_photos(mls_number)
        
        # Delete related records (cascade will handle price_history, photos)
        self.db.execute_update("DELETE FROM listing WHERE id = ?", (listing["id"],))
        
        return True


# Global instance
_listing_service: Optional[ListingService] = None


def get_listing_service() -> ListingService:
    """Get or create listing service instance."""
    global _listing_service
    if _listing_service is None:
        _listing_service = ListingService()
    return _listing_service
