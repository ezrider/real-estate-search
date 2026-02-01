"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1 import listings, photos, historical_sales, buildings, analytics

api_router = APIRouter()

api_router.include_router(listings.router, prefix="/listings", tags=["listings"])
api_router.include_router(photos.router, prefix="/photos", tags=["photos"])
api_router.include_router(historical_sales.router, prefix="/historical-sales", tags=["historical-sales"])
api_router.include_router(buildings.router, prefix="/buildings", tags=["buildings"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
