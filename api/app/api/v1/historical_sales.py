"""API routes for historical sales."""

from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query, UploadFile, File

from app.models.historical_sale import (
    HistoricalSaleCreate, HistoricalSaleResponse,
    HistoricalSaleListResponse, CSVImportResponse
)
from app.services.historical_sale_service import get_historical_sale_service

router = APIRouter()


@router.post("", response_model=HistoricalSaleResponse)
def create_historical_sale(sale: HistoricalSaleCreate):
    """Create a historical sale record."""
    service = get_historical_sale_service()
    
    data = sale.model_dump(exclude_unset=True)
    result = service.create_sale(data)
    
    return result


@router.get("", response_model=HistoricalSaleListResponse)
def list_historical_sales(
    building_id: Optional[int] = Query(None, description="Filter by building ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """List historical sales with filters."""
    service = get_historical_sale_service()
    
    result = service.list_sales(
        building_id=building_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    
    return result


@router.post("/import", response_model=CSVImportResponse)
async def import_csv(file: UploadFile = File(...)):
    """Import historical sales from CSV file."""
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV"
        )
    
    content = await file.read()
    csv_content = content.decode('utf-8')
    
    service = get_historical_sale_service()
    result = service.import_csv(csv_content)
    
    return result


@router.get("/csv-template")
def get_csv_template():
    """Get a CSV template for importing historical sales."""
    template = """building_name,address,neighborhood,unit_number,sale_price,sale_date,bedrooms,bathrooms,square_feet,property_type,days_on_market,notes
The Janion,123 Store Street,Downtown,1206,450000,2024-06-15,1,1.0,615,Condo,12,Sold above asking
The Mondrian,456 Johnson Street,Downtown,502,520000,2024-08-20,1,1.5,700,Condo,8,
"""
    
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content=template,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=historical_sales_template.csv"}
    )
