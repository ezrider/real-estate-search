"""Tests for analytics API endpoints."""


class TestPriceDrops:
    """Tests for GET /api/v1/analytics/price-drops"""
    
    def test_get_price_drops(self, client, auth_headers, create_listing):
        """Test getting recent price drops."""
        # Create listing with initial price
        mls = create_listing({"price": 500000})
        
        # Add price drop
        client.post(
            f"/api/v1/listings/{mls}/prices",
            json={"price": 475000, "event_type": "Price Drop"},
            headers=auth_headers
        )
        
        response = client.get("/api/v1/analytics/price-drops", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["drops"][0]["mls_number"] == mls
        assert data["drops"][0]["old_price"] == 500000
        assert data["drops"][0]["new_price"] == 475000
        assert data["drops"][0]["drop_percent"] == 5.0
    
    def test_get_price_drops_with_min_percent(self, client, auth_headers, create_listing):
        """Test filtering price drops by minimum percentage."""
        mls = create_listing({"price": 500000})
        
        # Add small price drop (2%)
        client.post(
            f"/api/v1/listings/{mls}/prices",
            json={"price": 490000, "event_type": "Price Drop"},
            headers=auth_headers
        )
        
        response = client.get("/api/v1/analytics/price-drops?min_drop_percent=5", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0  # 2% is less than 5% threshold
    
    def test_get_price_drops_time_range(self, client, auth_headers, create_listing):
        """Test filtering by time range."""
        # This test just verifies the endpoint accepts the parameter
        response = client.get("/api/v1/analytics/price-drops?days=30", headers=auth_headers)
        
        assert response.status_code == 200


class TestMarketSummary:
    """Tests for GET /api/v1/analytics/market-summary"""
    
    def test_market_summary(self, client, auth_headers, populated_db):
        """Test getting market summary."""
        response = client.get("/api/v1/analytics/market-summary", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        # Should have data grouped by neighborhood
    
    def test_market_summary_by_neighborhood(self, client, auth_headers, populated_db):
        """Test filtering by neighborhood."""
        # Get a neighborhood ID first
        resp = client.get("/api/v1/buildings/neighborhoods/all", headers=auth_headers)
        neighborhoods = resp.json()["neighborhoods"]
        
        if neighborhoods:
            neighborhood_id = neighborhoods[0]["id"]
            response = client.get(
                f"/api/v1/analytics/market-summary?neighborhood_id={neighborhood_id}",
                headers=auth_headers
            )
            
            assert response.status_code == 200


class TestBuildingComparison:
    """Tests for GET /api/v1/analytics/building-comparison"""
    
    def test_compare_buildings(self, client, auth_headers):
        """Test comparing multiple buildings."""
        # First create some buildings with listings
        listing_data = {
            "mls_number": "R9000001",
            "building_name": "Building A",
            "address": "123 A Street",
            "neighborhood": "Downtown",
            "price": 500000,
            "source_platform": "Test"
        }
        client.post("/api/v1/listings", json=listing_data, headers=auth_headers)
        
        listing_data["mls_number"] = "R9000002"
        listing_data["building_name"] = "Building B"
        listing_data["address"] = "456 B Street"
        listing_data["price"] = 600000
        client.post("/api/v1/listings", json=listing_data, headers=auth_headers)
        
        # Get building IDs
        resp = client.get("/api/v1/buildings", headers=auth_headers)
        buildings = resp.json()
        building_ids = [b["id"] for b in buildings if b["name"] in ["Building A", "Building B"]]
        
        if len(building_ids) >= 2:
            response = client.get(
                f"/api/v1/analytics/building-comparison?building_ids={building_ids[0]}&building_ids={building_ids[1]}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["comparison"]) == 2
    
    def test_compare_too_many_buildings(self, client, auth_headers):
        """Test that comparing > 10 buildings fails gracefully."""
        building_ids = list(range(1, 12))  # 11 buildings
        query = "&".join(f"building_ids={id}" for id in building_ids)
        
        response = client.get(f"/api/v1/analytics/building-comparison?{query}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data


class TestRecentActivity:
    """Tests for GET /api/v1/analytics/recent-activity"""
    
    def test_get_recent_activity(self, client, auth_headers, create_listing):
        """Test getting recent tracking events."""
        # Create a listing to generate an event
        create_listing()
        
        response = client.get("/api/v1/analytics/recent-activity", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert len(data["events"]) > 0
    
    def test_get_recent_activity_with_limit(self, client, auth_headers):
        """Test with custom limit."""
        response = client.get("/api/v1/analytics/recent-activity?limit=5", headers=auth_headers)
        
        assert response.status_code == 200
