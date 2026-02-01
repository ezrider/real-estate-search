-- Real Estate Tracker Database Schema
-- SQLite database for Victoria condo tracking

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- ============================================
-- NEIGHBORHOOD: Victoria neighborhoods
-- ============================================
CREATE TABLE IF NOT EXISTS neighborhood (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL DEFAULT 'Victoria',
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(name, city)
);

CREATE INDEX idx_neighborhood_name ON neighborhood(name);
CREATE INDEX idx_neighborhood_city ON neighborhood(city);

-- ============================================
-- BUILDING: Condo buildings and multi-unit properties
-- ============================================
CREATE TABLE IF NOT EXISTS building (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    address VARCHAR(300) NOT NULL,
    neighborhood_id INTEGER,
    city VARCHAR(50) DEFAULT 'Victoria',
    postal_code VARCHAR(10),
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    year_built INTEGER,
    total_units INTEGER,
    floors INTEGER,
    building_type VARCHAR(50), -- 'High-Rise', 'Mid-Rise', 'Low-Rise', 'Townhouse'
    amenities TEXT, -- JSON array: ["gym", "parking", "storage"]
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (neighborhood_id) REFERENCES neighborhood(id) ON DELETE SET NULL
);

CREATE INDEX idx_building_name ON building(name);
CREATE INDEX idx_building_neighborhood ON building(neighborhood_id);
CREATE INDEX idx_building_location ON building(latitude, longitude);

-- ============================================
-- LISTING: Active or recently active property listings
-- ============================================
CREATE TABLE IF NOT EXISTS listing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mls_number VARCHAR(20) UNIQUE,
    building_id INTEGER,
    unit_number VARCHAR(20),
    status VARCHAR(20) DEFAULT 'Active', -- 'Active', 'Pending', 'Sold', 'Expired', 'Cancelled'
    bedrooms INTEGER,
    bathrooms REAL,
    square_feet INTEGER,
    property_type VARCHAR(50), -- 'Condo', 'Townhouse', 'Penthouse', 'Studio'
    listing_date DATE,
    days_on_market INTEGER,
    description TEXT,
    listing_agent VARCHAR(100),
    listing_brokerage VARCHAR(100),
    source_url VARCHAR(500),
    source_platform VARCHAR(50), -- 'Realtor.ca', 'CondoDork', 'Manual'
    is_active BOOLEAN DEFAULT 1,
    first_seen_at DATETIME,
    last_seen_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (building_id) REFERENCES building(id) ON DELETE SET NULL
);

CREATE INDEX idx_listing_mls ON listing(mls_number);
CREATE INDEX idx_listing_building ON listing(building_id);
CREATE INDEX idx_listing_status ON listing(status, is_active);
CREATE INDEX idx_listing_dates ON listing(listing_date, last_seen_at);

-- ============================================
-- PRICE_HISTORY: All price observations for listings
-- ============================================
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    recorded_date DATE NOT NULL,
    event_type VARCHAR(20) DEFAULT 'Price Change', -- 'Initial', 'Price Drop', 'Price Increase', 'Sold', 'Delisted'
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (listing_id) REFERENCES listing(id) ON DELETE CASCADE
);

CREATE INDEX idx_price_history_listing ON price_history(listing_id);
CREATE INDEX idx_price_history_date ON price_history(recorded_date);
CREATE INDEX idx_price_history_listing_date ON price_history(listing_id, recorded_date);

-- ============================================
-- LISTING_PHOTO: Photos for current listings
-- ============================================
CREATE TABLE IF NOT EXISTS listing_photo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL,
    photo_url VARCHAR(500) NOT NULL, -- Local file path relative to storage root
    display_order INTEGER DEFAULT 0,
    caption VARCHAR(200),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (listing_id) REFERENCES listing(id) ON DELETE CASCADE
);

CREATE INDEX idx_photo_listing ON listing_photo(listing_id);

-- ============================================
-- HISTORICAL_SALE: Past sales for building history analysis
-- ============================================
CREATE TABLE IF NOT EXISTS historical_sale (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_id INTEGER,
    unit_number VARCHAR(20),
    sale_price DECIMAL(12,2) NOT NULL,
    sale_date DATE NOT NULL,
    bedrooms INTEGER,
    bathrooms REAL,
    square_feet INTEGER,
    property_type VARCHAR(50),
    days_on_market INTEGER,
    notes TEXT,
    data_source VARCHAR(100) DEFAULT 'CSV Import',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (building_id) REFERENCES building(id) ON DELETE SET NULL
);

CREATE INDEX idx_historical_sale_building ON historical_sale(building_id);
CREATE INDEX idx_historical_sale_date ON historical_sale(sale_date);
CREATE INDEX idx_historical_sale_unit ON historical_sale(building_id, unit_number);

-- ============================================
-- SALE_PHOTO: Photos for historical sales
-- ============================================
CREATE TABLE IF NOT EXISTS sale_photo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    historical_sale_id INTEGER NOT NULL,
    photo_url VARCHAR(500) NOT NULL, -- Local file path relative to storage root
    display_order INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (historical_sale_id) REFERENCES historical_sale(id) ON DELETE CASCADE
);

CREATE INDEX idx_sale_photo_sale ON sale_photo(historical_sale_id);

-- ============================================
-- TRACKING_EVENT: Audit log for system events
-- ============================================
CREATE TABLE IF NOT EXISTS tracking_event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER,
    event_type VARCHAR(50) NOT NULL, -- 'Discovered', 'PriceChange', 'StatusChange', 'Scraped', 'Error', 'Imported'
    details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (listing_id) REFERENCES listing(id) ON DELETE SET NULL
);

CREATE INDEX idx_tracking_event_listing ON tracking_event(listing_id);
CREATE INDEX idx_tracking_event_type ON tracking_event(event_type);
CREATE INDEX idx_tracking_event_time ON tracking_event(created_at);

-- ============================================
-- Views for common queries
-- ============================================

-- View: Latest price for each active listing
CREATE VIEW IF NOT EXISTS v_listing_current_price AS
SELECT 
    l.id as listing_id,
    l.mls_number,
    l.unit_number,
    l.status,
    l.bedrooms,
    l.bathrooms,
    l.square_feet,
    ph.price as current_price,
    CASE 
        WHEN l.square_feet > 0 THEN ROUND(ph.price / l.square_feet, 2)
        ELSE NULL 
    END as price_per_sqft,
    ph.recorded_date as price_date
FROM listing l
LEFT JOIN (
    SELECT ph1.*
    FROM price_history ph1
    INNER JOIN (
        SELECT listing_id, MAX(recorded_date) as max_date
        FROM price_history
        GROUP BY listing_id
    ) ph2 ON ph1.listing_id = ph2.listing_id AND ph1.recorded_date = ph2.max_date
) ph ON l.id = ph.listing_id
WHERE l.is_active = 1;

-- View: Building summary statistics
CREATE VIEW IF NOT EXISTS v_building_stats AS
SELECT 
    b.id as building_id,
    b.name as building_name,
    n.name as neighborhood,
    COUNT(DISTINCT l.id) as active_listings,
    AVG(vlcp.current_price) as avg_price,
    AVG(vlcp.price_per_sqft) as avg_price_per_sqft,
    COUNT(DISTINCT hs.id) as historical_sales_count,
    AVG(hs.sale_price) as avg_historical_sale_price
FROM building b
LEFT JOIN neighborhood n ON b.neighborhood_id = n.id
LEFT JOIN listing l ON b.id = l.building_id AND l.is_active = 1
LEFT JOIN v_listing_current_price vlcp ON l.id = vlcp.listing_id
LEFT JOIN historical_sale hs ON b.id = hs.building_id
GROUP BY b.id, b.name, n.name;
