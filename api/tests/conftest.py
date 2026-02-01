"""Test fixtures and configuration."""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

# Set test environment before importing app
os.environ["API_KEY"] = "test-api-key"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["PHOTO_STORAGE_PATH"] = ""
os.environ["DEBUG"] = "true"

from app.main import app
from app.core.database import Database, get_db
from app.core.config import get_settings


@pytest.fixture(scope="session")
def test_settings():
    """Get test settings."""
    return get_settings()


@pytest.fixture(scope="function")
def temp_photo_dir() -> Generator[Path, None, None]:
    """Create temporary photo directory for tests."""
    temp_dir = Path(tempfile.mkdtemp())
    (temp_dir / "listings").mkdir(exist_ok=True)
    (temp_dir / "historical_sales").mkdir(exist_ok=True)
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def test_db() -> Generator[Database, None, None]:
    """Create test database with schema."""
    # Create in-memory database
    db = Database(":memory:")
    
    # Load schema (from parent directory)
    schema_path = Path(__file__).parent.parent.parent / "schema.sql"
    with open(schema_path, "r") as f:
        schema = f.read()
    
    with db.get_connection() as conn:
        conn.executescript(schema)
        
        # Add test neighborhoods
        neighborhoods = [
            ("Downtown", "Victoria", "Test neighborhood"),
            ("James Bay", "Victoria", "Waterfront area"),
            ("Fairfield", "Victoria", "Cook Street Village"),
        ]
        conn.executemany(
            "INSERT INTO neighborhood (name, city, description) VALUES (?, ?, ?)",
            neighborhoods
        )
        conn.commit()
    
    yield db


@pytest.fixture(scope="function")
def client(test_db, temp_photo_dir, monkeypatch) -> Generator[TestClient, None, None]:
    """Create test client with mocked dependencies."""
    
    # Override database dependency
    def override_get_db():
        return test_db
    
    # Override photo storage path
    def override_get_settings():
        from unittest.mock import MagicMock
        settings = MagicMock()
        settings.API_KEY = "test-api-key"
        settings.PHOTO_STORAGE_PATH = str(temp_photo_dir)
        settings.max_photo_size_bytes = 10 * 1024 * 1024
        settings.cors_origins_list = ["*"]
        return settings
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Patch settings in services
    import app.services.photo_service as photo_module
    original_settings = photo_module.get_settings
    photo_module.get_settings = override_get_settings
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Cleanup
    app.dependency_overrides.clear()
    photo_module.get_settings = original_settings


@pytest.fixture(scope="function")
def auth_headers() -> dict:
    """Get authentication headers for API requests."""
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture(scope="function")
def sample_listing_data() -> dict:
    """Sample listing data for tests."""
    return {
        "mls_number": "R1234567",
        "building_name": "The Janion",
        "address": "123 Store Street",
        "neighborhood": "Downtown",
        "unit_number": "1206",
        "status": "Active",
        "bedrooms": 1,
        "bathrooms": 1.0,
        "square_feet": 615,
        "property_type": "Condo",
        "listing_date": "2026-01-31",
        "days_on_market": 5,
        "description": "Beautiful downtown condo",
        "listing_agent": "Jane Smith",
        "listing_brokerage": "Royal LePage",
        "source_url": "https://realtor.ca/listing/123",
        "source_platform": "Realtor.ca",
        "price": 487000,
        "photos": []
    }


@pytest.fixture(scope="function")
def sample_historical_sale_data() -> dict:
    """Sample historical sale data for tests."""
    return {
        "building_name": "The Janion",
        "address": "123 Store Street",
        "neighborhood": "Downtown",
        "unit_number": "1206",
        "sale_price": 450000,
        "sale_date": "2024-06-15",
        "bedrooms": 1,
        "bathrooms": 1.0,
        "square_feet": 615,
        "property_type": "Condo",
        "days_on_market": 12,
        "notes": "Sold above asking",
        "data_source": "Test Import",
        "photos": []
    }


@pytest.fixture(scope="function")
def create_listing(client, auth_headers, sample_listing_data):
    """Helper fixture to create a listing and return MLS number."""
    def _create_listing(overrides: dict = None):
        data = {**sample_listing_data}
        if overrides:
            data.update(overrides)
        
        response = client.post("/api/v1/listings", json=data, headers=auth_headers)
        assert response.status_code == 200
        return data["mls_number"]
    
    return _create_listing


@pytest.fixture(scope="function")
def populated_db(client, auth_headers, sample_listing_data):
    """Create multiple listings for testing list operations."""
    listings = [
        {**sample_listing_data, "mls_number": "R1000001", "price": 500000, "bedrooms": 1},
        {**sample_listing_data, "mls_number": "R1000002", "price": 600000, "bedrooms": 2},
        {**sample_listing_data, "mls_number": "R1000003", "price": 700000, "bedrooms": 2},
        {**sample_listing_data, "mls_number": "R1000004", "price": 800000, "bedrooms": 3},
    ]
    
    for listing in listings:
        response = client.post("/api/v1/listings", json=listing, headers=auth_headers)
        assert response.status_code == 200
    
    return listings
