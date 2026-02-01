"""API client for sending scraped data to the Real Estate Tracker API."""

import os
import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal

import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class APIClient:
    """Client for interacting with the Real Estate Tracker API."""
    
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize API client.
        
        Args:
            base_url: API base URL (defaults to env var API_URL)
            api_key: API key (defaults to env var API_KEY)
        """
        self.base_url = base_url or os.getenv("API_URL", "http://localhost:8000/api/v1")
        self.api_key = api_key or os.getenv("API_KEY", "")
        
        if not self.api_key:
            logger.warning("No API key provided. Authentication will fail.")
        
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make an API request."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.request(method, url, json=json_data) as response:
                if response.status == 401:
                    logger.error("Authentication failed. Check API key.")
                    raise PermissionError("Invalid API key")
                
                if response.status == 404:
                    return {"success": False, "error": "Not found"}
                
                response.raise_for_status()
                return await response.json()
        
        except aiohttp.ClientError as e:
            logger.error(f"API request failed: {e}")
            raise
    
    async def create_or_update_listing(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a listing.
        
        Args:
            listing_data: Listing data dictionary
            
        Returns:
            API response with success status and listing_id
        """
        # Clean up data
        cleaned = self._clean_listing_data(listing_data)
        
        logger.info(f"Sending listing {cleaned.get('mls_number')} to API")
        
        result = await self._request("POST", "/listings", cleaned)
        
        if result.get("success"):
            if result.get("is_new"):
                logger.info(f"✓ Created new listing: {cleaned.get('mls_number')}")
            else:
                logger.info(f"✓ Updated listing: {cleaned.get('mls_number')}")
        
        return result
    
    async def get_listing(self, mls_number: str) -> Optional[Dict[str, Any]]:
        """Get a listing by MLS number."""
        result = await self._request("GET", f"/listings/{mls_number}")
        return result if "mls_number" in result else None
    
    async def add_price(self, mls_number: str, price: Decimal, notes: Optional[str] = None) -> Dict[str, Any]:
        """Add a price history entry."""
        data = {
            "price": float(price),
            "event_type": "Price Change"
        }
        if notes:
            data["notes"] = notes
        
        return await self._request("POST", f"/listings/{mls_number}/prices", data)
    
    async def list_buildings(self) -> List[Dict[str, Any]]:
        """Get list of buildings."""
        result = await self._request("GET", "/buildings")
        return result if isinstance(result, list) else []
    
    def _clean_listing_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize listing data for API."""
        cleaned = {}
        
        # String fields
        for field in ["mls_number", "building_name", "address", "neighborhood",
                      "unit_number", "status", "property_type", "description",
                      "listing_agent", "listing_brokerage", "source_url", "source_platform"]:
            if field in data and data[field] is not None:
                cleaned[field] = str(data[field]).strip()
        
        # Numeric fields
        if "price" in data and data["price"] is not None:
            try:
                cleaned["price"] = float(Decimal(str(data["price"])))
            except (ValueError, TypeError):
                pass
        
        if "bedrooms" in data and data["bedrooms"] is not None:
            try:
                cleaned["bedrooms"] = int(float(data["bedrooms"]))
            except (ValueError, TypeError):
                pass
        
        if "bathrooms" in data and data["bathrooms"] is not None:
            try:
                cleaned["bathrooms"] = float(data["bathrooms"])
            except (ValueError, TypeError):
                pass
        
        if "square_feet" in data and data["square_feet"] is not None:
            try:
                cleaned["square_feet"] = int(float(data["square_feet"]))
            except (ValueError, TypeError):
                pass
        
        if "days_on_market" in data and data["days_on_market"] is not None:
            try:
                cleaned["days_on_market"] = int(data["days_on_market"])
            except (ValueError, TypeError):
                pass
        
        # Date fields
        if "listing_date" in data and data["listing_date"]:
            cleaned["listing_date"] = data["listing_date"]
        
        # Photo URLs
        if "photos" in data and isinstance(data["photos"], list):
            cleaned["photos"] = [url for url in data["photos"] if url]
        
        return cleaned
