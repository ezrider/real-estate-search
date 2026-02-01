"""Tests for PhotoService."""

import pytest
from pathlib import Path
import shutil

from app.services.photo_service import PhotoService


class TestPhotoService:
    """Tests for PhotoService."""
    
    @pytest.fixture
    def photo_service(self, temp_photo_dir, monkeypatch):
        """Create photo service with temp directory."""
        from unittest.mock import MagicMock
        
        settings = MagicMock()
        settings.PHOTO_STORAGE_PATH = str(temp_photo_dir)
        settings.max_photo_size_bytes = 10 * 1024 * 1024
        
        import app.services.photo_service as photo_module
        original = photo_module.get_settings
        photo_module.get_settings = lambda: settings
        
        service = PhotoService()
        
        yield service
        
        photo_module.get_settings = original
    
    def test_purge_listing_photos(self, photo_service, temp_photo_dir):
        """Test purging listing photos."""
        # Create test photos
        mls = "R1234567"
        listing_dir = temp_photo_dir / "listings" / mls
        listing_dir.mkdir(parents=True)
        (listing_dir / "01.jpg").write_text("photo1")
        (listing_dir / "02.jpg").write_text("photo2")
        
        deleted = photo_service.purge_listing_photos(mls)
        
        assert deleted == 2
        assert not listing_dir.exists()
    
    def test_purge_orphaned_photos(self, photo_service, temp_photo_dir, test_db):
        """Test purging orphaned photos."""
        # Create orphaned directory
        orphan_dir = temp_photo_dir / "listings" / "R9999999"
        orphan_dir.mkdir(parents=True)
        (orphan_dir / "01.jpg").write_text("orphan")
        
        # Create valid directory
        valid_dir = temp_photo_dir / "listings" / "R0000001"
        valid_dir.mkdir(parents=True)
        (valid_dir / "01.jpg").write_text("valid")
        
        # Add valid listing to database
        test_db.execute_insert(
            """INSERT INTO listing (mls_number, status, is_active, first_seen_at, last_seen_at, created_at, updated_at)
               VALUES (?, ?, 1, datetime('now'), datetime('now'), datetime('now'), datetime('now'))""",
            ("R0000001", "Active")
        )
        
        stats = photo_service.purge_orphaned_photos(test_db)
        
        assert stats["listings_deleted"] == 1  # R9999999 deleted
        assert not orphan_dir.exists()
        assert valid_dir.exists()  # R0000001 kept
    
    def test_get_photo_url(self, photo_service):
        """Test getting photo URL."""
        url = photo_service.get_photo_url("listings/R123/01.jpg")
        
        assert "/photos/" in url
        assert "listings/R123/01.jpg" in url
