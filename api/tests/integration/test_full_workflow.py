"""Integration tests for complete workflows."""

import pytest
from decimal import Decimal


class TestFullWorkflow:
    """Integration tests covering complete user workflows."""
    
    def test_track_listing_and_detect_price_drop(self, client, auth_headers):
        """Full workflow: Track listing, update with price drop, verify analytics."""
        # 1. Create a new listing
        listing_data = {
            "mls_number": "RWORKFLOW1",
            "building_name": "Workflow Test Building",
            "address": "123 Workflow St",
            "neighborhood": "Downtown",
            "unit_number": "1001",
            "bedrooms": 2,
            "bathrooms": 2.0,
            "square_feet": 900,
            "price": 600000,
            "source_platform": "Realtor.ca"
        }
        
        response = client.post("/api/v1/listings", json=listing_data, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["is_new"] is True
        
        # 2. Verify listing was created
        response = client.get("/api/v1/listings/RWORKFLOW1", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["current_price"] == 600000
        assert len(data["price_history"]) == 1
        
        # 3. Add a price drop
        response = client.post(
            "/api/v1/listings/RWORKFLOW1/prices",
            json={"price": 575000, "event_type": "Price Drop", "notes": "Market adjustment"},
            headers=auth_headers
        )
        assert response.status_code == 200
        price_data = response.json()
        assert price_data["price_change"] == -25000
        assert price_data["percent_change"] == pytest.approx(-4.17, 0.01)
        
        # 4. Check price drops in analytics
        response = client.get("/api/v1/analytics/price-drops", headers=auth_headers)
        assert response.status_code == 200
        drops = response.json()
        assert drops["count"] == 1
        assert drops["drops"][0]["mls_number"] == "RWORKFLOW1"
        assert drops["drops"][0]["drop_percent"] == pytest.approx(4.17, 0.01)
        
        # 5. Add historical sale to same building
        sale_data = {
            "building_name": "Workflow Test Building",
            "address": "123 Workflow St",
            "unit_number": "1002",
            "sale_price": 550000,
            "sale_date": "2024-06-01",
            "bedrooms": 2,
            "square_feet": 900,
            "property_type": "Condo"
        }
        response = client.post("/api/v1/historical-sales", json=sale_data, headers=auth_headers)
        assert response.status_code == 200
        
        # 6. Check building stats
        response = client.get("/api/v1/buildings", headers=auth_headers)
        assert response.status_code == 200
        buildings = response.json()
        workflow_building = [b for b in buildings if b["name"] == "Workflow Test Building"][0]
        
        response = client.get(f"/api/v1/buildings/{workflow_building['id']}/stats", headers=auth_headers)
        assert response.status_code == 200
        stats = response.json()
        assert stats["active_listings"] == 1
        assert stats["historical_sales_count"] == 1
    
    def test_csv_import_and_analysis(self, client, auth_headers):
        """Full workflow: Import CSV, verify data, run analytics."""
        import io
        
        # 1. Import CSV with multiple sales
        csv_content = """building_name,address,neighborhood,unit_number,sale_price,sale_date,bedrooms,bathrooms,square_feet,property_type
Import Building,123 Import St,Downtown,101,500000,2024-01-15,1,1.0,600,Condo
Import Building,123 Import St,Downtown,102,550000,2024-03-20,2,2.0,800,Condo
Import Building,123 Import St,Downtown,103,525000,2024-05-10,1,1.5,650,Condo
Another Building,456 Other St,James Bay,201,600000,2024-02-28,2,2.0,900,Condo
"""
        
        response = client.post(
            "/api/v1/historical-sales/import",
            files={"file": ("sales.csv", io.BytesIO(csv_content.encode()), "text/csv")},
            headers=auth_headers
        )
        assert response.status_code == 200
        result = response.json()
        assert result["imported"] == 4
        
        # 2. List historical sales for building
        response = client.get("/api/v1/buildings", headers=auth_headers)
        buildings = response.json()
        import_building = [b for b in buildings if b["name"] == "Import Building"][0]
        
        response = client.get(
            f"/api/v1/historical-sales?building_id={import_building['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        sales_data = response.json()
        assert sales_data["total"] == 3
        
        # 3. Verify price per sqft calculation
        for sale in sales_data["sales"]:
            if sale["square_feet"]:
                expected_ppsf = round(sale["sale_price"] / sale["square_feet"], 2)
                assert sale["price_per_sqft"] == expected_ppsf
    
    def test_market_summary_by_neighborhood(self, client, auth_headers):
        """Full workflow: Create listings in different neighborhoods, verify summary."""
        # Create listings in Downtown
        downtown_listings = [
            {"mls_number": "RDW001", "building_name": "Downtown A", "neighborhood": "Downtown", "price": 500000, "source_platform": "Test"},
            {"mls_number": "RDW002", "building_name": "Downtown B", "neighborhood": "Downtown", "price": 600000, "source_platform": "Test"},
        ]
        
        # Create listings in James Bay
        jamesbay_listings = [
            {"mls_number": "RJB001", "building_name": "James Bay A", "neighborhood": "James Bay", "price": 550000, "source_platform": "Test"},
            {"mls_number": "RJB002", "building_name": "James Bay B", "neighborhood": "James Bay", "price": 650000, "source_platform": "Test"},
        ]
        
        for listing in downtown_listings + jamesbay_listings:
            response = client.post("/api/v1/listings", json=listing, headers=auth_headers)
            assert response.status_code == 200
        
        # Get market summary
        response = client.get("/api/v1/analytics/market-summary", headers=auth_headers)
        assert response.status_code == 200
        summary = response.json()["summary"]
        
        # Should have data for both neighborhoods
        neighborhoods = [s["neighborhood"] for s in summary]
        assert "Downtown" in neighborhoods or any("Downtown" in str(n) for n in neighborhoods)
        assert "James Bay" in neighborhoods or any("James Bay" in str(n) for n in neighborhoods)
    
    def test_photo_management_workflow(self, client, auth_headers, temp_photo_dir):
        """Full workflow: Create listing, manage photos, purge."""
        # 1. Create listing
        listing_data = {
            "mls_number": "RPHOTO001",
            "building_name": "Photo Test Building",
            "price": 500000,
            "source_platform": "Test",
            "photos": []  # Would normally have URLs
        }
        
        response = client.post("/api/v1/listings", json=listing_data, headers=auth_headers)
        assert response.status_code == 200
        
        # 2. Create mock photos in database
        from app.core.database import get_db
        db = get_db()
        listing = db.execute(
            "SELECT id FROM listing WHERE mls_number = ?",
            ("RPHOTO001",),
            fetch_one=True
        )
        
        # Add photo records
        for i in range(3):
            db.execute_insert(
                "INSERT INTO listing_photo (listing_id, photo_url, display_order) VALUES (?, ?, ?)",
                (listing["id"], f"listings/RPHOTO001/0{i+1}.jpg", i)
            )
        
        # 3. Create actual photo files
        listing_dir = temp_photo_dir / "listings" / "RPHOTO001"
        listing_dir.mkdir(parents=True)
        for i in range(3):
            (listing_dir / f"0{i+1}.jpg").write_bytes(b"fake photo data")
        
        # 4. Verify photos exist
        response = client.get("/api/v1/photos/listings/RPHOTO001", headers=auth_headers)
        assert response.status_code == 200
        photos_data = response.json()
        assert len(photos_data["photos"]) == 3
        
        # 5. Purge photos
        response = client.delete("/api/v1/photos/listings/RPHOTO001", headers=auth_headers)
        assert response.status_code == 200
        purge_result = response.json()
        assert purge_result["deleted_count"] == 3
        
        # 6. Verify photos deleted
        assert not listing_dir.exists()
