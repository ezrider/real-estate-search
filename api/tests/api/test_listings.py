"""Tests for listing API endpoints."""

import pytest


class TestCreateListing:
    """Tests for POST /api/v1/listings"""
    
    def test_create_new_listing_success(self, client, auth_headers, sample_listing_data):
        """Test creating a new listing."""
        response = client.post("/api/v1/listings", json=sample_listing_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["is_new"] is True
        assert data["mls_number"] == sample_listing_data["mls_number"]
        assert data["price_recorded"] is True
        assert "listing_id" in data
    
    def test_create_listing_without_auth(self, client, sample_listing_data):
        """Test creating a listing without authentication fails."""
        response = client.post("/api/v1/listings", json=sample_listing_data)
        
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]
    
    def test_create_listing_with_invalid_auth(self, client, sample_listing_data):
        """Test creating a listing with invalid API key fails."""
        headers = {"Authorization": "Bearer invalid-key"}
        response = client.post("/api/v1/listings", json=sample_listing_data, headers=headers)
        
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
    
    def test_update_existing_listing(self, client, auth_headers, sample_listing_data, create_listing):
        """Test updating an existing listing."""
        mls = create_listing()
        
        # Update with new price
        updated_data = {**sample_listing_data, "price": 475000, "description": "Updated description"}
        response = client.post("/api/v1/listings", json=updated_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_new"] is False
        assert data["price_recorded"] is True  # Price changed
        assert data["message"] == "Listing updated"


class TestGetListing:
    """Tests for GET /api/v1/listings/{mls_number}"""
    
    def test_get_listing_success(self, client, auth_headers, create_listing):
        """Test retrieving a listing by MLS number."""
        mls = create_listing()
        
        response = client.get(f"/api/v1/listings/{mls}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["mls_number"] == mls
        assert "price_history" in data
        assert "photos" in data
    
    def test_get_listing_not_found(self, client, auth_headers):
        """Test retrieving a non-existent listing."""
        response = client.get("/api/v1/listings/R9999999", headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestListListings:
    """Tests for GET /api/v1/listings"""
    
    def test_list_listings_success(self, client, auth_headers, populated_db):
        """Test listing all active listings."""
        response = client.get("/api/v1/listings", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4
        assert len(data["listings"]) == 4
    
    def test_list_listings_with_filter(self, client, auth_headers, populated_db):
        """Test listing with bedroom filter."""
        response = client.get("/api/v1/listings?bedrooms=2", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        for listing in data["listings"]:
            assert listing["bedrooms"] == 2
    
    def test_list_listings_with_price_range(self, client, auth_headers, populated_db):
        """Test listing with price range filter."""
        response = client.get("/api/v1/listings?min_price=550000&max_price=750000", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2  # 600000 and 700000
    
    def test_list_listings_pagination(self, client, auth_headers, populated_db):
        """Test pagination."""
        response = client.get("/api/v1/listings?limit=2&offset=0", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["listings"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0
        
        # Get next page
        response = client.get("/api/v1/listings?limit=2&offset=2", headers=auth_headers)
        data = response.json()
        assert len(data["listings"]) == 2
        assert data["offset"] == 2
    
    def test_list_listings_sorting(self, client, auth_headers, populated_db):
        """Test sorting options."""
        response = client.get("/api/v1/listings?sort=price_desc", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        prices = [l["current_price"] for l in data["listings"]]
        assert prices == sorted(prices, reverse=True)


class TestUpdateListingStatus:
    """Tests for PATCH /api/v1/listings/{mls_number}/status"""
    
    def test_update_status_to_sold(self, client, auth_headers, create_listing):
        """Test marking a listing as sold."""
        mls = create_listing()
        
        response = client.patch(
            f"/api/v1/listings/{mls}/status",
            json={"status": "Sold", "sale_price": 470000, "sale_date": "2026-02-15"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Sold" in data["message"]
    
    def test_update_status_not_found(self, client, auth_headers):
        """Test updating status of non-existent listing."""
        response = client.patch(
            "/api/v1/listings/R9999999/status",
            json={"status": "Sold"},
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestDeleteListing:
    """Tests for DELETE /api/v1/listings/{mls_number}"""
    
    def test_delete_listing_success(self, client, auth_headers, create_listing):
        """Test deleting a listing."""
        mls = create_listing()
        
        response = client.delete(f"/api/v1/listings/{mls}", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Verify it's gone
        response = client.get(f"/api/v1/listings/{mls}", headers=auth_headers)
        assert response.status_code == 404
    
    def test_delete_listing_not_found(self, client, auth_headers):
        """Test deleting non-existent listing."""
        response = client.delete("/api/v1/listings/R9999999", headers=auth_headers)
        
        assert response.status_code == 404


class TestPriceHistory:
    """Tests for price history endpoints."""
    
    def test_add_price_to_listing(self, client, auth_headers, create_listing):
        """Test adding a price point."""
        mls = create_listing({"price": 500000})
        
        response = client.post(
            f"/api/v1/listings/{mls}/prices",
            json={"price": 475000, "date": "2026-02-01", "event_type": "Price Drop"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["previous_price"] == 500000
        assert data["price_change"] == -25000
        assert data["percent_change"] == -5.0
    
    def test_get_price_history(self, client, auth_headers, create_listing):
        """Test retrieving price history."""
        mls = create_listing()
        
        response = client.get(f"/api/v1/listings/{mls}/prices", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["mls_number"] == mls
        assert len(data["prices"]) == 1  # Initial price
