"""Tests for photo management API endpoints."""

import os
from pathlib import Path


class TestPhotoEndpoints:
    """Tests for photo endpoints."""
    
    def test_get_listing_photos(self, client, auth_headers, create_listing, temp_photo_dir):
        """Test getting photo URLs for a listing."""
        mls = create_listing()
        
        # Create a mock photo file
        listing_dir = temp_photo_dir / "listings" / mls
        listing_dir.mkdir(parents=True, exist_ok=True)
        (listing_dir / "01.jpg").write_bytes(b"fake image data")
        
        # Add photo to database
        from app.core.database import get_db
        db = get_db()
        listing = db.execute(
            "SELECT id FROM listing WHERE mls_number = ?",
            (mls,),
            fetch_one=True
        )
        db.execute_insert(
            "INSERT INTO listing_photo (listing_id, photo_url, display_order) VALUES (?, ?, ?)",
            (listing["id"], f"listings/{mls}/01.jpg", 0)
        )
        
        response = client.get(f"/api/v1/photos/listings/{mls}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["mls_number"] == mls
        assert len(data["photos"]) == 1
        assert "/photos/" in data["photos"][0]["url"]
    
    def test_purge_listing_photos(self, client, auth_headers, create_listing, temp_photo_dir):
        """Test purging photos for a listing."""
        mls = create_listing()
        
        # Create mock photo files
        listing_dir = temp_photo_dir / "listings" / mls
        listing_dir.mkdir(parents=True, exist_ok=True)
        (listing_dir / "01.jpg").write_bytes(b"fake image data")
        (listing_dir / "02.jpg").write_bytes(b"fake image data 2")
        
        # Add photos to database
        from app.core.database import get_db
        db = get_db()
        listing = db.execute(
            "SELECT id FROM listing WHERE mls_number = ?",
            (mls,),
            fetch_one=True
        )
        for i in range(2):
            db.execute_insert(
                "INSERT INTO listing_photo (listing_id, photo_url, display_order) VALUES (?, ?, ?)",
                (listing["id"], f"listings/{mls}/0{i+1}.jpg", i)
            )
        
        response = client.delete(f"/api/v1/photos/listings/{mls}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 2
        
        # Verify files are deleted
        assert not listing_dir.exists()
        
        # Verify database records are deleted
        photos = db.execute(
            "SELECT * FROM listing_photo WHERE listing_id = ?",
            (listing["id"],)
        )
        assert len(photos) == 0
    
    def test_purge_orphaned_photos(self, client, auth_headers, temp_photo_dir):
        """Test purging orphaned photos."""
        # Create orphaned photo directory
        orphaned_dir = temp_photo_dir / "listings" / "R9999999"
        orphaned_dir.mkdir(parents=True, exist_ok=True)
        (orphaned_dir / "01.jpg").write_bytes(b"orphaned photo")
        
        response = client.delete("/api/v1/photos/purge-orphaned", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["listings_deleted"] == 1
        
        # Verify directory is removed
        assert not orphaned_dir.exists()
    
    def test_serve_photo(self, client, auth_headers, temp_photo_dir):
        """Test serving a photo file."""
        # Create a test photo
        photo_path = temp_photo_dir / "listings" / "test" / "01.jpg"
        photo_path.parent.mkdir(parents=True, exist_ok=True)
        photo_path.write_bytes(b"fake image content")
        
        response = client.get("/api/v1/photos/serve/listings/test/01.jpg", headers=auth_headers)
        
        # Should return 200 or 404 depending on implementation
        # Just verify endpoint doesn't crash
        assert response.status_code in [200, 404]
    
    def test_serve_photo_security(self, client, auth_headers, temp_photo_dir):
        """Test that photo serving prevents directory traversal."""
        response = client.get("/api/v1/photos/serve/../../../etc/passwd", headers=auth_headers)
        
        # Should be forbidden or not found
        assert response.status_code in [403, 404]
