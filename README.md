# Real Estate Search

A personal tool for monitoring the Victoria, BC condo market. Track listings from Realtor.ca and CondoDork, analyze pricing trends, and identify favorable opportunities.

## Features

- **Listing Tracking**: Monitor active condo listings with price history
- **Building Analysis**: Track sales history for buildings of interest
- **Price Alerts**: Detect price drops and underpriced listings
- **Historical Data**: Import past sales data for market analysis
- **Photo Storage**: Download and manage listing photos locally

## Quick Start

### 1. Initialize the Database

```bash
python init_db.py
```

This creates:
- SQLite database (`real_estate.db`)
- Photo storage directories (`photos/listings/`, `photos/historical_sales/`)
- 15 Victoria neighborhoods pre-populated

### 2. Project Structure

```
.
├── DATA_MODEL.md          # Database schema documentation
├── schema.sql             # Database schema
├── init_db.py             # Database initialization script
├── photos/                # Local photo storage
│   ├── listings/          # Active listing photos
│   └── historical_sales/  # Historical sale photos
└── real_estate.db         # SQLite database (created by init_db.py)
```

## Database Schema

See [DATA_MODEL.md](DATA_MODEL.md) for complete documentation including:
- Entity relationship diagram
- Table specifications
- Sample queries
- Photo storage strategy
- CSV import format for historical sales

## Key Design Decisions

### Price History Tracking
Every price observation is stored as a new row in `PRICE_HISTORY`. This enables:
- Complete audit trail of price changes
- Price drop velocity calculations
- Days-at-price analysis

### Building-Centric Model
Listings and historical sales both link to a `BUILDING` record:
- Compare current listings to past sales in the same building
- Track building-level metrics (average $/sqft, turnover)
- Neighborhood aggregation

### Photo Storage
Photos are downloaded and stored locally:
```
photos/
├── listings/{mls_number}/
│   ├── 01.jpg
│   ├── 02.jpg
│   └── ...
└── historical_sales/{sale_id}/
    └── ...
```

Purge functions allow removing photos for listings no longer of interest.

## Pre-populated Victoria Neighborhoods

| Neighborhood | Type |
|--------------|------|
| Downtown | High-rise condos, business district |
| Harris Green | Dense residential, walkable |
| Chinatown | Historic character buildings |
| James Bay | Waterfront, Beacon Hill Park |
| Fairfield | Cook Street Village area |
| Fernwood | Arts district |
| Victoria West | Modern waterfront condos |
| Songhees | Upscale waterfront |
| Esquimalt | More affordable, west of downtown |
| Oak Bay | Upscale residential |
| Saanich East/West | Suburban, family-oriented |
| View Royal | Westshore, newer developments |
| Langford | Rapid growth, new condos |
| Colwood | Westshore, near Royal Roads |

## API Server

The API is built with FastAPI and ready to deploy.

```
api/
├── app/                   # FastAPI application
│   ├── main.py           # Entry point
│   ├── api/v1/           # API endpoints
│   ├── services/         # Business logic
│   └── core/             # Database, config
├── deploy.sh             # Deployment script
├── setup-ssl.sh          # SSL certificate setup
└── DEPLOY.md             # Deployment guide
```

### Deploy to your server

```bash
cd api
sudo bash deploy.sh       # Deploy application
sudo bash setup-ssl.sh    # Set up HTTPS
```

Then update the [Tampermonkey script](tampermonkey-script.js) with your API key.

See [DEPLOY.md](DEPLOY.md) for detailed instructions.

## Playwright Scraper

Automated headless browser scraper for CondoDork.

**New to Playwright?** Check out the [Playwright Tutorial](PLAYWRIGHT_TUTORIAL.md) - a comprehensive guide covering everything from basics to advanced patterns.

```
scraper/
├── condodork_scraper.py     # Main scraper logic
├── api_client.py            # API client
├── run_scraper.py           # CLI runner
├── install-playwright.sh    # Install on headless Linux
├── deploy-scraper.sh        # Deploy to production
└── README.md                # Scraper documentation
```

### Deploy Scraper

```bash
cd scraper
bash install-playwright.sh    # Install dependencies
bash deploy-scraper.sh        # Deploy to server
```

### Run Scraper

```bash
python run_scraper.py --dry-run   # Test mode
python run_scraper.py             # Production
bash setup-cron.sh                # Schedule with cron
```

## Next Steps

- [x] Design database schema with price history
- [x] Build FastAPI with all endpoints
- [x] Create test suite
- [x] Create deployment scripts
- [x] Add Playwright scraper for CondoDork
- [ ] Deploy to your server
- [ ] Configure Tampermonkey with production API
- [ ] Build CLI for viewing tracked listings
