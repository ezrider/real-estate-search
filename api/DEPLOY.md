# Real Estate Tracker API - Deployment Guide

## Quick Start

### 1. Install Dependencies

```bash
cd api/
pip install -r requirements.txt

# Or using uv
uv pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Required settings:**
```env
API_KEY=your-secure-random-key-here
API_HOST=0.0.0.0
API_PORT=8000
PHOTO_STORAGE_PATH=/path/to/real-estate-search/photos
```

### 3. Ensure Database Exists

```bash
cd ..
python init_db.py
```

### 4. Start the API

**Development:**
```bash
cd api
./start.sh dev
```

**Production:**
```bash
cd api
./start.sh
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

---

## Production Deployment with Nginx

### 1. Install Nginx

```bash
sudo apt-get update
sudo apt-get install nginx
```

### 2. Configure API to Use Unix Socket (Recommended)

Edit `start.sh` to use a Unix socket instead of TCP:

```bash
uvicorn app.main:app --uds /tmp/condosapi.sock --workers 4
```

### 3. Configure Nginx

Copy the nginx configuration:

```bash
sudo cp nginx-condosapi.conf /etc/nginx/sites-available/condosapi

# Edit the configuration to update paths
sudo nano /etc/nginx/sites-available/condosapi
```

**Update these paths:**
- SSL certificate paths
- Photo storage path: `alias /path/to/real-estate-search/photos/;`

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/condosapi /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 4. Set Up SSL with Let's Encrypt

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d condosapi.mistyrainbow.cloud
```

### 5. Run API as Systemd Service

Create `/etc/systemd/system/condosapi.service`:

```ini
[Unit]
Description=Real Estate Tracker API
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/real-estate-search/api
Environment="PATH=/path/to/real-estate-search/api/venv/bin"
EnvironmentFile=/path/to/real-estate-search/api/.env
ExecStart=/path/to/real-estate-search/api/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable condosapi
sudo systemctl start condosapi
sudo systemctl status condosapi
```

---

## API Authentication

All API requests must include the API key in the `Authorization` header:

```bash
curl -H "Authorization: Bearer your-api-key" \
     https://condosapi.mistyrainbow.cloud/api/v1/listings
```

Or in Tampermonkey:

```javascript
fetch('https://condosapi.mistyrainbow.cloud/api/v1/listings', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer your-api-key',
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(listingData)
});
```

---

## Directory Structure

```
api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI entry point
│   ├── core/
│   │   ├── config.py        # Settings
│   │   └── database.py      # Database connection
│   ├── models/              # Pydantic models
│   ├── services/            # Business logic
│   └── api/
│       └── v1/              # API routes
├── requirements.txt
├── .env.example
├── start.sh
└── nginx-condosapi.conf
```

---

## Testing the API

### Health Check

```bash
curl https://condosapi.mistyrainbow.cloud/health
```

### Create a Listing

```bash
curl -X POST https://condosapi.mistyrainbow.cloud/api/v1/listings \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "mls_number": "R3052391",
    "building_name": "The Janion",
    "address": "123 Store Street",
    "neighborhood": "Downtown",
    "unit_number": "1206",
    "bedrooms": 1,
    "bathrooms": 1.0,
    "square_feet": 615,
    "property_type": "Condo",
    "price": 487000,
    "source_platform": "Realtor.ca"
  }'
```

### List Listings

```bash
curl "https://condosapi.mistyrainbow.cloud/api/v1/listings?limit=10" \
  -H "Authorization: Bearer your-api-key"
```

---

## Troubleshooting

### Database Locked

SQLite can have issues with multiple workers. If you see "database is locked" errors:

1. Reduce workers to 1 in `start.sh`
2. Or switch to PostgreSQL (see below)

### Permission Denied for Photos

Ensure the web server user can write to the photos directory:

```bash
sudo chown -R www-data:www-data /path/to/real-estate-search/photos
sudo chmod -R 755 /path/to/real-estate-search/photos
```

### CORS Errors

Update `CORS_ORIGINS` in `.env`:

```env
CORS_ORIGINS=https://www.realtor.ca,https://www.condodork.com
```

---

## Upgrading to PostgreSQL (Optional)

For higher concurrency, consider PostgreSQL:

```bash
# Install psycopg2
pip install psycopg2-binary

# Update DATABASE_URL
DATABASE_URL=postgresql://user:password@localhost/realestate
```

Update `app/core/database.py` to use SQLAlchemy for database-agnostic queries.

---

## Monitoring

View logs:

```bash
# API logs
sudo journalctl -u condosapi -f

# Nginx logs
sudo tail -f /var/log/nginx/condosapi.error.log
```
