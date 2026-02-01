# Real Estate Tracker API

REST API for receiving scraped listing data from browser scripts and headless scrapers.

## Base URL

```
https://your-domain.com/api/v1
```

## Authentication

All requests require an API key passed in the header:

```
X-API-Key: your-api-key-here
```

The API key is configured in the FastAPI application environment.

## Endpoints

### 1. Listings

#### Create or Update Listing

```http
POST /listings
```

Creates a new listing or updates an existing one (matched by `mls_number`).

**Request Body:**
```json
{
  "mls_number": "R3052391",
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
  "description": "Beautiful downtown condo with ocean views...",
  "listing_agent": "Jane Smith",
  "listing_brokerage": "Royal LePage",
  "source_url": "https://www.realtor.ca/listing/...",
  "source_platform": "Realtor.ca",
  "price": 487000,
  "photos": [
    "https://photos.realtor.ca/.../photo1.jpg",
    "https://photos.realtor.ca/.../photo2.jpg"
  ]
}
```

**Response:**
```json
{
  "success": true,
  "listing_id": 42,
  "mls_number": "R3052391",
  "is_new": true,
  "price_recorded": true,
  "photo_download_queued": 3,
  "message": "New listing created"
}
```

**Notes:**
- If `mls_number` exists, updates the listing and records new price if changed
- Building is auto-created if not found (matched by name/address)
- Neighborhood is auto-created if not found
- Photos are queued for async download

---

#### Get Listing

```http
GET /listings/{mls_number}
```

**Response:**
```json
{
  "id": 42,
  "mls_number": "R3052391",
  "building": {
    "id": 5,
    "name": "The Janion",
    "address": "123 Store Street"
  },
  "unit_number": "1206",
  "status": "Active",
  "bedrooms": 1,
  "bathrooms": 1.0,
  "square_feet": 615,
  "property_type": "Condo",
  "listing_date": "2026-01-31",
  "days_on_market": 5,
  "current_price": 487000,
  "price_per_sqft": 791.87,
  "price_history": [
    {"date": "2026-01-31", "price": 487000, "event_type": "Initial"}
  ],
  "photos": [
    "/photos/listings/R3052391/01.jpg",
    "/photos/listings/R3052391/02.jpg"
  ],
  "source_url": "https://www.realtor.ca/listing/...",
  "first_seen_at": "2026-01-31T10:30:00",
  "last_seen_at": "2026-01-31T10:30:00"
}
```

---

#### List Listings

```http
GET /listings?status=active&building_id=5&min_price=400000&max_price=600000
```

**Query Parameters:**
- `status` - Filter by status (active, pending, sold, expired)
- `building_id` - Filter by building
- `neighborhood_id` - Filter by neighborhood
- `min_price`, `max_price` - Price range
- `bedrooms` - Exact bedroom count
- `property_type` - Condo, Townhouse, etc.
- `sort` - price_asc, price_desc, date_desc, days_on_market
- `limit` - Max results (default 50, max 200)
- `offset` - Pagination offset

**Response:**
```json
{
  "total": 156,
  "offset": 0,
  "limit": 50,
  "listings": [
    {
      "mls_number": "R3052391",
      "building_name": "The Janion",
      "unit_number": "1206",
      "bedrooms": 1,
      "bathrooms": 1.0,
      "square_feet": 615,
      "current_price": 487000,
      "price_per_sqft": 791.87,
      "status": "Active",
      "days_on_market": 5,
      "photo_thumbnail": "/photos/listings/R3052391/01_thumb.jpg",
      "source_url": "https://www.realtor.ca/listing/..."
    }
  ]
}
```

---

#### Mark Listing as Sold/Expired

```http
PATCH /listings/{mls_number}/status
```

**Request Body:**
```json
{
  "status": "Sold",
  "sale_price": 475000,
  "sale_date": "2026-02-15"
}
```

---

#### Delete Listing

```http
DELETE /listings/{mls_number}
```

**Query Parameters:**
- `purge_photos=true` - Also delete associated photos

---

### 2. Price History

#### Add Price Point

```http
POST /listings/{mls_number}/prices
```

**Request Body:**
```json
{
  "price": 475000,
  "date": "2026-02-01",
  "event_type": "Price Drop",
  "notes": "Reduced by $12k"
}
```

**Response:**
```json
{
  "success": true,
  "price_history_id": 123,
  "previous_price": 487000,
  "price_change": -12000,
  "percent_change": -2.46
}
```

---

#### Get Price History

```http
GET /listings/{mls_number}/prices
```

---

### 3. Photos

#### Upload Photo

```http
POST /listings/{mls_number}/photos
Content-Type: multipart/form-data
```

**Form Fields:**
- `photo` - Binary image file
- `display_order` - Integer (optional)
- `caption` - String (optional)

---

#### Get Photo URLs

```http
GET /listings/{mls_number}/photos
```

**Response:**
```json
{
  "mls_number": "R3052391",
  "photos": [
    {
      "url": "/photos/listings/R3052391/01.jpg",
      "thumbnail": "/photos/listings/R3052391/01_thumb.jpg",
      "display_order": 0,
      "caption": "Living room"
    }
  ]
}
```

---

#### Purge Photos

```http
DELETE /listings/{mls_number}/photos
```

Removes all photos for a listing. Use when no longer tracking.

---

### 4. Historical Sales

#### Import Historical Sale

```http
POST /historical-sales
```

**Request Body:**
```json
{
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
  "photos": []
}
```

---

#### Bulk Import (CSV)

```http
POST /historical-sales/import
Content-Type: multipart/form-data
```

**Form Fields:**
- `file` - CSV file

**CSV Format:**
```csv
building_name,address,neighborhood,unit_number,sale_price,sale_date,bedrooms,bathrooms,square_feet
The Janion,123 Store Street,Downtown,1206,450000,2024-06-15,1,1.0,615
The Mondrian,456 Johnson Street,Downtown,502,520000,2024-08-20,1,1.5,700
```

---

#### List Historical Sales

```http
GET /historical-sales?building_id=5&start_date=2024-01-01
```

---

### 5. Buildings

#### List Buildings

```http
GET /buildings?neighborhood_id=3&has_active_listings=true
```

---

#### Get Building Details

```http
GET /buildings/{building_id}
```

**Response includes:**
- Building info
- Active listings count
- Historical sales count
- Average $/sqft for both

---

### 6. Analytics

#### Price Drops

```http
GET /analytics/price-drops?days=7&min_drop_percent=2
```

Returns listings with price drops in the last N days.

---

#### Market Summary

```http
GET /analytics/market-summary?neighborhood_id=3
```

Returns aggregated stats:
- Active listings count
- Average price
- Average $/sqft
- Days on market stats

---

## Error Responses

All errors follow this format:

```json
{
  "success": false,
  "error": {
    "code": "LISTING_NOT_FOUND",
    "message": "Listing with MLS number R999999 not found",
    "details": {}
  }
}
```

**HTTP Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `401` - Unauthorized (invalid API key)
- `404` - Not Found
- `409` - Conflict (duplicate MLS number with different data)
- `500` - Internal Server Error

---

## Rate Limiting

Default limits (configurable):
- 100 requests per minute per API key
- 10 photo uploads per minute

---

## WebSocket (Future)

For real-time updates:

```
ws://your-domain.com/api/v1/ws
```

Subscribe to events:
- `price_drop` - New price reduction detected
- `new_listing` - New listing added
- `status_change` - Listing status changed
