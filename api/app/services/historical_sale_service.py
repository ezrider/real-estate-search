"""Historical sale service with CSV import."""

import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Tuple, Optional

from app.core.database import get_db
from app.services.photo_service import get_photo_service


class HistoricalSaleService:
    """Service for historical sale operations."""
    
    def __init__(self):
        self.db = get_db()
        self.photo_service = get_photo_service()
    
    def _get_or_create_building(
        self,
        name: str,
        address: Optional[str] = None,
        neighborhood: Optional[str] = None
    ) -> int:
        """Get existing building or create new one."""
        # Try to find by name
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
        
        # Create new building
        # Use name as address if address not provided
        building_address = address or name or "Unknown"
        
        return self.db.execute_insert(
            """INSERT INTO building (name, address, neighborhood_id, city)
               VALUES (?, ?, ?, ?)""",
            (name, building_address, neighborhood_id, "Victoria")
        )
    
    def create_sale(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a historical sale record."""
        building_id = self._get_or_create_building(
            data.get("building_name"),
            data.get("address"),
            data.get("neighborhood")
        )
        
        sale_id = self.db.execute_insert(
            """INSERT INTO historical_sale (
                building_id, unit_number, sale_price, sale_date,
                bedrooms, bathrooms, square_feet, property_type,
                days_on_market, notes, data_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                building_id,
                data.get("unit_number"),
                data.get("sale_price"),
                data.get("sale_date"),
                data.get("bedrooms"),
                data.get("bathrooms"),
                data.get("square_feet"),
                data.get("property_type"),
                data.get("days_on_market"),
                data.get("notes"),
                data.get("data_source", "Manual Entry")
            )
        )
        
        # Download photos if provided
        photo_count = 0
        if data.get("photos"):
            import asyncio
            downloaded = asyncio.run(
                self.photo_service.download_historical_sale_photos(
                    sale_id, data["photos"]
                )
            )
            photo_count = len(downloaded)
        
        return {
            "success": True,
            "sale_id": sale_id,
            "message": "Historical sale recorded"
        }
    
    def import_csv(self, csv_content: str) -> Dict[str, Any]:
        """Import historical sales from CSV content."""
        results = {
            "success": True,
            "total_rows": 0,
            "imported": 0,
            "skipped": 0,
            "errors": []
        }
        
        expected_columns = [
            "building_name", "address", "neighborhood", "unit_number",
            "sale_price", "sale_date", "bedrooms", "bathrooms",
            "square_feet", "property_type", "days_on_market", "notes"
        ]
        
        try:
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            
            # Validate headers
            if not reader.fieldnames:
                results["success"] = False
                results["errors"].append("CSV has no headers")
                return results
            
            # Check for required columns
            required = {"building_name", "sale_price", "sale_date"}
            missing = required - set(reader.fieldnames)
            if missing:
                results["success"] = False
                results["errors"].append(f"Missing required columns: {', '.join(missing)}")
                return results
            
            for row_num, row in enumerate(reader, start=2):
                results["total_rows"] += 1
                
                try:
                    # Parse sale_price
                    try:
                        price_str = row["sale_price"].replace(",", "").replace("$", "")
                        sale_price = Decimal(price_str)
                    except (InvalidOperation, ValueError) as e:
                        results["errors"].append(f"Row {row_num}: Invalid sale_price '{row['sale_price']}'")
                        results["skipped"] += 1
                        continue
                    
                    # Parse sale_date
                    sale_date = row["sale_date"]
                    # Try different date formats
                    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y"):
                        try:
                            from datetime import datetime as dt
                            parsed = dt.strptime(sale_date, fmt)
                            sale_date = parsed.strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
                    else:
                        results["errors"].append(f"Row {row_num}: Invalid date format '{sale_date}'")
                        results["skipped"] += 1
                        continue
                    
                    # Parse numbers
                    bedrooms = self._parse_int(row.get("bedrooms"))
                    bathrooms = self._parse_float(row.get("bathrooms"))
                    square_feet = self._parse_int(row.get("square_feet"))
                    days_on_market = self._parse_int(row.get("days_on_market"))
                    
                    # Create sale record
                    sale_data = {
                        "building_name": row["building_name"].strip(),
                        "address": row.get("address", "").strip() or None,
                        "neighborhood": row.get("neighborhood", "").strip() or None,
                        "unit_number": row.get("unit_number", "").strip() or None,
                        "sale_price": sale_price,
                        "sale_date": sale_date,
                        "bedrooms": bedrooms,
                        "bathrooms": bathrooms,
                        "square_feet": square_feet,
                        "property_type": row.get("property_type", "").strip() or None,
                        "days_on_market": days_on_market,
                        "notes": row.get("notes", "").strip() or None,
                        "data_source": "CSV Import"
                    }
                    
                    self.create_sale(sale_data)
                    results["imported"] += 1
                    
                except Exception as e:
                    results["errors"].append(f"Row {row_num}: {str(e)}")
                    results["skipped"] += 1
        
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"CSV parsing error: {str(e)}")
        
        return results
    
    def _parse_int(self, value: Any) -> Optional[int]:
        """Safely parse integer."""
        if not value or value.strip() == "":
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _parse_float(self, value: Any) -> Optional[float]:
        """Safely parse float."""
        if not value or value.strip() == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def list_sales(
        self,
        building_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List historical sales with filters."""
        
        where_clauses = ["1=1"]
        params = []
        
        if building_id:
            where_clauses.append("hs.building_id = ?")
            params.append(building_id)
        
        if start_date:
            where_clauses.append("hs.sale_date >= ?")
            params.append(start_date)
        
        if end_date:
            where_clauses.append("hs.sale_date <= ?")
            params.append(end_date)
        
        # Count total
        count_query = f"""
            SELECT COUNT(*) as count 
            FROM historical_sale hs
            WHERE {' AND '.join(where_clauses)}
        """
        total_result = self.db.execute(count_query, tuple(params), fetch_one=True)
        total = total_result["count"] if total_result else 0
        
        # Get sales with price_per_sqft calculation
        query = f"""
            SELECT 
                hs.id,
                b.name as building_name,
                hs.unit_number,
                hs.sale_price,
                hs.sale_date,
                hs.bedrooms,
                hs.bathrooms,
                hs.square_feet,
                CASE 
                    WHEN hs.square_feet > 0 
                    THEN ROUND(CAST(hs.sale_price AS FLOAT) / hs.square_feet, 2)
                    ELSE NULL 
                END as price_per_sqft,
                hs.days_on_market
            FROM historical_sale hs
            LEFT JOIN building b ON hs.building_id = b.id
            WHERE {' AND '.join(where_clauses)}
            ORDER BY hs.sale_date DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        sales = self.db.execute(query, tuple(params))
        
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "sales": sales
        }


# Global instance
_historical_service: Optional[HistoricalSaleService] = None


def get_historical_sale_service() -> HistoricalSaleService:
    """Get or create historical sale service instance."""
    global _historical_service
    if _historical_service is None:
        _historical_service = HistoricalSaleService()
    return _historical_service
