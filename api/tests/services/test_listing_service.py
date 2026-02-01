"""Tests for ListingService."""

import pytest
from decimal import Decimal
from datetime import date

from app.services.listing_service import ListingService


class TestListingService:
    """Tests for ListingService."""
    
    @pytest.fixture
    def service(self, test_db):
        """Create service instance with test database."""
        service = ListingService.__new__(ListingService)
        service.db = test_db
        service.photo_service = None  # Mock this if needed
        return service
    
    def test_create_new_listing(self, service):
        """Test creating a new listing."""
        data = {
            "mls_number": "R1234567",
            "building_name": "Test Building",
            "address": "123 Test St",
            "neighborhood": "Downtown",
            "unit_number": "101",
            "bedrooms": 2,
            "bathrooms": 2.0,
            "square_feet": 1000,
            "price": 500000,
            "source_platform": "Test"
        }
        
        result = service.create_or_update_listing(data)
        
        assert result["success"] is True
        assert result["is_new"] is True
        assert result["mls_number"] == "R1234567"
        assert result["price_recorded"] is True
    
    def test_update_existing_listing_price_change(self, service):
        """Test updating listing with price change."""
        # Create initial listing
        data = {
            "mls_number": "R1234567",
            "building_name": "Test Building",
            "price": 500000,
            "source_platform": "Test"
        }
        service.create_or_update_listing(data)
        
        # Update with new price
        data["price"] = 475000
        result = service.create_or_update_listing(data)
        
        assert result["is_new"] is False
        assert result["price_recorded"] is True
        
        # Verify price history
        listing = service.get_listing("R1234567")
        assert len(listing["price_history"]) == 2
    
    def test_update_existing_listing_no_price_change(self, service):
        """Test updating listing without price change."""
        # Create initial listing
        data = {
            "mls_number": "R1234567",
            "building_name": "Test Building",
            "price": 500000,
            "source_platform": "Test"
        }
        service.create_or_update_listing(data)
        
        # Update with same price
        data["description"] = "Updated description"
        result = service.create_or_update_listing(data)
        
        assert result["price_recorded"] is False
    
    def test_price_history_tracking(self, service):
        """Test that price history is properly tracked."""
        data = {
            "mls_number": "R1234567",
            "building_name": "Test Building",
            "price": 500000,
            "source_platform": "Test"
        }
        
        # Create listing
        service.create_or_update_listing(data)
        
        # Add price drops
        service._record_price(1, Decimal("475000"), event_type="Price Drop")
        service._record_price(1, Decimal("450000"), event_type="Price Drop")
        
        # Get price history
        listing = service.get_listing("R1234567")
        prices = [p["price"] for p in listing["price_history"]]
        
        assert Decimal("500000") in prices
        assert Decimal("475000") in prices
        assert Decimal("450000") in prices
    
    def test_building_auto_creation(self, service):
        """Test that buildings are auto-created."""
        data = {
            "mls_number": "R1234567",
            "building_name": "New Auto Building",
            "address": "456 New St",
            "neighborhood": "James Bay",
            "price": 500000,
            "source_platform": "Test"
        }
        
        service.create_or_update_listing(data)
        
        # Verify building was created
        building = service.db.execute(
            "SELECT * FROM building WHERE name = ?",
            ("New Auto Building",),
            fetch_one=True
        )
        assert building is not None
        assert building["address"] == "456 New St"
    
    def test_list_listings_with_filters(self, service):
        """Test listing with various filters."""
        # Create test listings
        listings = [
            {"mls_number": "R0000001", "price": 400000, "bedrooms": 1},
            {"mls_number": "R0000002", "price": 500000, "bedrooms": 2},
            {"mls_number": "R0000003", "price": 600000, "bedrooms": 2},
        ]
        
        for listing in listings:
            data = {
                "mls_number": listing["mls_number"],
                "building_name": "Test Building",
                "price": listing["price"],
                "bedrooms": listing["bedrooms"],
                "source_platform": "Test"
            }
            service.create_or_update_listing(data)
        
        # Test filter by bedrooms
        result = service.list_listings(bedrooms=2)
        assert result["total"] == 2
        
        # Test filter by price range
        result = service.list_listings(min_price=Decimal("450000"), max_price=Decimal("550000"))
        assert result["total"] == 1
    
    def test_delete_listing(self, service):
        """Test deleting a listing."""
        data = {
            "mls_number": "R1234567",
            "building_name": "Test Building",
            "price": 500000,
            "source_platform": "Test"
        }
        service.create_or_update_listing(data)
        
        success = service.delete_listing("R1234567")
        
        assert success is True
        
        listing = service.get_listing("R1234567")
        assert listing is None
    
    def test_update_status(self, service):
        """Test updating listing status."""
        data = {
            "mls_number": "R1234567",
            "building_name": "Test Building",
            "price": 500000,
            "source_platform": "Test"
        }
        service.create_or_update_listing(data)
        
        success = service.update_status("R1234567", "Sold", sale_price=Decimal("490000"))
        
        assert success is True
        
        listing = service.get_listing("R1234567")
        assert listing["status"] == "Sold"
        assert listing["is_active"] == 0 or listing["is_active"] == False
