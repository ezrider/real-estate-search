"""Tests for historical sales API endpoints."""

import io


class TestCreateHistoricalSale:
    """Tests for POST /api/v1/historical-sales"""
    
    def test_create_historical_sale_success(self, client, auth_headers, sample_historical_sale_data):
        """Test creating a historical sale."""
        response = client.post(
            "/api/v1/historical-sales",
            json=sample_historical_sale_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "sale_id" in data
    
    def test_create_historical_sale_creates_building(self, client, auth_headers):
        """Test that creating a sale auto-creates the building."""
        data = {
            "building_name": "New Building",
            "address": "456 New Street",
            "neighborhood": "James Bay",
            "sale_price": 550000,
            "sale_date": "2024-01-15"
        }
        
        response = client.post("/api/v1/historical-sales", json=data, headers=auth_headers)
        assert response.status_code == 200
        
        # Verify building was created
        response = client.get("/api/v1/buildings", headers=auth_headers)
        buildings = response.json()
        building_names = [b["name"] for b in buildings]
        assert "New Building" in building_names


class TestListHistoricalSales:
    """Tests for GET /api/v1/historical-sales"""
    
    def test_list_historical_sales(self, client, auth_headers, sample_historical_sale_data):
        """Test listing historical sales."""
        # Create a few sales
        for i in range(3):
            data = {**sample_historical_sale_data, "unit_number": str(100 + i)}
            client.post("/api/v1/historical-sales", json=data, headers=auth_headers)
        
        response = client.get("/api/v1/historical-sales", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["sales"]) == 3
    
    def test_list_with_date_filter(self, client, auth_headers, sample_historical_sale_data):
        """Test filtering by date range."""
        # Create sales with different dates
        client.post("/api/v1/historical-sales", json={
            **sample_historical_sale_data, "sale_date": "2024-01-15"
        }, headers=auth_headers)
        
        client.post("/api/v1/historical-sales", json={
            **sample_historical_sale_data, "sale_date": "2024-06-15"
        }, headers=auth_headers)
        
        response = client.get(
            "/api/v1/historical-sales?start_date=2024-05-01&end_date=2024-12-31",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["sales"][0]["sale_date"] == "2024-06-15"


class TestCSVImport:
    """Tests for POST /api/v1/historical-sales/import"""
    
    def test_csv_import_success(self, client, auth_headers):
        """Test importing historical sales from CSV."""
        csv_content = """building_name,address,neighborhood,unit_number,sale_price,sale_date,bedrooms,bathrooms,square_feet,property_type,days_on_market,notes
The Janion,123 Store Street,Downtown,1206,450000,2024-06-15,1,1.0,615,Condo,12,Sold above asking
The Mondrian,456 Johnson Street,Downtown,502,520000,2024-08-20,1,1.5,700,Condo,8,
"""
        
        response = client.post(
            "/api/v1/historical-sales/import",
            files={"file": ("sales.csv", io.BytesIO(csv_content.encode()), "text/csv")},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["imported"] == 2
        assert data["skipped"] == 0
    
    def test_csv_import_with_errors(self, client, auth_headers):
        """Test CSV import with invalid data."""
        csv_content = """building_name,sale_price,sale_date
The Janion,invalid-price,2024-06-15
The Mondrian,500000,invalid-date
Valid Building,500000,2024-06-15
"""
        
        response = client.post(
            "/api/v1/historical-sales/import",
            files={"file": ("sales.csv", io.BytesIO(csv_content.encode()), "text/csv")},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["imported"] == 1
        assert data["skipped"] == 2
        assert len(data["errors"]) == 2
    
    def test_csv_import_wrong_file_type(self, client, auth_headers):
        """Test importing non-CSV file fails."""
        response = client.post(
            "/api/v1/historical-sales/import",
            files={"file": ("sales.txt", io.BytesIO(b"not a csv"), "text/plain")},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "CSV" in response.json()["detail"]
    
    def test_get_csv_template(self, client, auth_headers):
        """Test downloading CSV template."""
        response = client.get("/api/v1/historical-sales/csv-template", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        content = response.content.decode()
        assert "building_name" in content
        assert "sale_price" in content
