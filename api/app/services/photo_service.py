"""Photo download and management service."""

import hashlib
import shutil
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING
from urllib.parse import urlparse
import asyncio
import aiohttp
import aiofiles

from app.core.config import get_settings


class PhotoService:
    """Service for managing listing photos."""
    
    def __init__(self):
        settings = get_settings()
        self.storage_path = Path(settings.PHOTO_STORAGE_PATH)
        self.max_size = settings.max_photo_size_bytes
        
        # Ensure directories exist
        self.listings_path = self.storage_path / "listings"
        self.historical_path = self.storage_path / "historical_sales"
        self.listings_path.mkdir(parents=True, exist_ok=True)
        self.historical_path.mkdir(parents=True, exist_ok=True)
    
    def _get_listing_dir(self, mls_number: str) -> Path:
        """Get directory path for a listing's photos."""
        # Sanitize mls_number for filesystem
        safe_mls = "".join(c for c in mls_number if c.isalnum() or c in "-_").rstrip()
        return self.listings_path / safe_mls
    
    def _get_historical_dir(self, sale_id: int) -> Path:
        """Get directory path for historical sale photos."""
        return self.historical_path / str(sale_id)
    
    async def download_photo(
        self,
        url: str,
        destination: Path,
        session: aiohttp.ClientSession
    ) -> Optional[Path]:
        """Download a single photo."""
        try:
            async with session.get(url, timeout=30) as response:
                if response.status != 200:
                    return None
                
                # Check content length
                content_length = response.headers.get('Content-Length')
                if content_length and int(content_length) > self.max_size:
                    return None
                
                # Download
                content = await response.read()
                if len(content) > self.max_size:
                    return None
                
                # Determine extension
                content_type = response.headers.get('Content-Type', '')
                ext = self._get_extension(content_type, url)
                destination = destination.with_suffix(ext)
                
                # Save
                destination.parent.mkdir(parents=True, exist_ok=True)
                async with aiofiles.open(destination, 'wb') as f:
                    await f.write(content)
                
                return destination
        except Exception as e:
            print(f"Error downloading photo {url}: {e}")
            return None
    
    def _get_extension(self, content_type: str, url: str) -> str:
        """Determine file extension from content type or URL."""
        type_map = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/webp': '.webp',
            'image/gif': '.gif',
        }
        
        ext = type_map.get(content_type.lower())
        if ext:
            return ext
        
        # Try to get from URL
        parsed = urlparse(url)
        path_ext = Path(parsed.path).suffix
        if path_ext:
            return path_ext
        
        return '.jpg'  # Default
    
    async def download_listing_photos(
        self,
        mls_number: str,
        photo_urls: List[str]
    ) -> List[str]:
        """Download photos for a listing."""
        listing_dir = self._get_listing_dir(mls_number)
        listing_dir.mkdir(parents=True, exist_ok=True)
        
        downloaded = []
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i, url in enumerate(photo_urls[:20]):  # Max 20 photos
                dest = listing_dir / f"{i+1:02d}"
                tasks.append(self.download_photo(url, dest, session))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Path):
                    # Return relative path from storage root
                    rel_path = result.relative_to(self.storage_path)
                    downloaded.append(str(rel_path))
        
        return downloaded
    
    async def download_historical_sale_photos(
        self,
        sale_id: int,
        photo_urls: List[str]
    ) -> List[str]:
        """Download photos for a historical sale."""
        sale_dir = self._get_historical_dir(sale_id)
        sale_dir.mkdir(parents=True, exist_ok=True)
        
        downloaded = []
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i, url in enumerate(photo_urls[:20]):
                dest = sale_dir / f"{i+1:02d}"
                tasks.append(self.download_photo(url, dest, session))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Path):
                    rel_path = result.relative_to(self.storage_path)
                    downloaded.append(str(rel_path))
        
        return downloaded
    
    def purge_listing_photos(self, mls_number: str) -> int:
        """Remove all photos for a listing. Returns count of deleted files."""
        listing_dir = self._get_listing_dir(mls_number)
        
        if not listing_dir.exists():
            return 0
        
        deleted = 0
        for file_path in listing_dir.iterdir():
            if file_path.is_file():
                file_path.unlink()
                deleted += 1
        
        # Remove empty directory
        if listing_dir.exists():
            listing_dir.rmdir()
        
        return deleted
    
    def purge_historical_sale_photos(self, sale_id: int) -> int:
        """Remove all photos for a historical sale."""
        sale_dir = self._get_historical_dir(sale_id)
        
        if not sale_dir.exists():
            return 0
        
        deleted = 0
        for file_path in sale_dir.iterdir():
            if file_path.is_file():
                file_path.unlink()
                deleted += 1
        
        if sale_dir.exists():
            sale_dir.rmdir()
        
        return deleted
    
    def purge_orphaned_photos(self, db) -> dict:
        """Remove photos for listings/sales that no longer exist in database.
        
        Returns dict with counts of deleted files.
        """
        stats = {"listings_deleted": 0, "historical_deleted": 0, "errors": []}
        
        # Get active MLS numbers from database
        active_mls = set()
        try:
            result = db.execute("SELECT mls_number FROM listing WHERE mls_number IS NOT NULL")
            active_mls = {row["mls_number"] for row in result}
        except Exception as e:
            stats["errors"].append(f"Could not fetch active listings: {e}")
        
        # Check listing directories
        if self.listings_path.exists():
            for mls_dir in self.listings_path.iterdir():
                if mls_dir.is_dir() and mls_dir.name not in active_mls:
                    count = len(list(mls_dir.iterdir()))
                    shutil.rmtree(mls_dir)
                    stats["listings_deleted"] += count
        
        # Get active historical sale IDs
        active_sale_ids = set()
        try:
            result = db.execute("SELECT id FROM historical_sale")
            active_sale_ids = {str(row["id"]) for row in result}
        except Exception as e:
            stats["errors"].append(f"Could not fetch historical sales: {e}")
        
        # Check historical sale directories
        if self.historical_path.exists():
            for sale_dir in self.historical_path.iterdir():
                if sale_dir.is_dir() and sale_dir.name not in active_sale_ids:
                    count = len(list(sale_dir.iterdir()))
                    shutil.rmtree(sale_dir)
                    stats["historical_deleted"] += count
        
        return stats
    
    def get_photo_url(self, relative_path: str) -> str:
        """Convert a relative storage path to public URL."""
        # This would be used with nginx to serve static files
        return f"/photos/{relative_path}"


# Global instance
_photo_service: Optional[PhotoService] = None


def get_photo_service() -> PhotoService:
    """Get or create photo service instance."""
    global _photo_service
    if _photo_service is None:
        _photo_service = PhotoService()
    return _photo_service
