"""API routes for photo management."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import FileResponse

from app.core.database import get_db
from app.core.config import get_settings
from app.services.photo_service import get_photo_service

router = APIRouter()


@router.get("/listings/{mls_number}")
def get_listing_photos(mls_number: str):
    """Get photo URLs for a listing."""
    db = get_db()
    
    listing = db.execute(
        "SELECT id FROM listing WHERE mls_number = ?",
        (mls_number,),
        fetch_one=True
    )
    
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing with MLS number {mls_number} not found"
        )
    
    photos = db.execute(
        """SELECT photo_url as url, display_order, caption
           FROM listing_photo 
           WHERE listing_id = ? 
           ORDER BY display_order""",
        (listing["id"],)
    )
    
    # Convert relative paths to full URLs
    settings = get_settings()
    for photo in photos:
        photo["url"] = f"/photos/{photo['url']}"
    
    return {"mls_number": mls_number, "photos": photos}


@router.delete("/listings/{mls_number}")
def purge_listing_photos(mls_number: str):
    """Remove all photos for a listing."""
    photo_service = get_photo_service()
    
    deleted_count = photo_service.purge_listing_photos(mls_number)
    
    # Also remove from database
    db = get_db()
    listing = db.execute(
        "SELECT id FROM listing WHERE mls_number = ?",
        (mls_number,),
        fetch_one=True
    )
    
    if listing:
        db.execute_update(
            "DELETE FROM listing_photo WHERE listing_id = ?",
            (listing["id"],)
        )
    
    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"Deleted {deleted_count} photos for {mls_number}"
    }


@router.delete("/purge-orphaned")
def purge_orphaned_photos():
    """Remove photos for listings/sales that no longer exist."""
    photo_service = get_photo_service()
    db = get_db()
    
    stats = photo_service.purge_orphaned_photos(db)
    
    return {
        "success": True,
        "listings_deleted": stats["listings_deleted"],
        "historical_deleted": stats["historical_deleted"],
        "errors": stats["errors"]
    }


@router.get("/serve/{path:path}")
def serve_photo(path: str):
    """Serve a photo file."""
    settings = get_settings()
    photo_path = Path(settings.PHOTO_STORAGE_PATH) / path
    
    # Security: ensure path is within photo storage
    try:
        photo_path.resolve().relative_to(Path(settings.PHOTO_STORAGE_PATH).resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid path"
        )
    
    if not photo_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    return FileResponse(photo_path)
