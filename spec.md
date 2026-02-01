# Real Estate Search - Project Specifications

## Purpose
The Real Estate Search project is a personal tool designed to help monitor the condo market, track listings from Realtor.ca, and analyze pricing for favorable opportunities. This tool aims to streamline the process of researching and evaluating potential condo purchases.

## Key Features

### 1. Search & Tracking
- **Goal:** Enable manual exploration of Realtor.ca while capturing key data.
- Users navigate Realtor.ca manually, and the tool captures actions such as marking a listing as a favorite.
- Favorite listings are scraped and saved into a local database for analysis.

### 2. Database & Data Fields
Favorite listings will be stored in a local database, including:
- Listing ID
- Title/Description
- Location (Address + Neighborhood)
- Price
- Square Footage
- Number of Bedrooms/Bathrooms
- Listing Date
- Photos/Virtual Tours (if available)

### 3. Pricing Insights
- Track historical prices for listings to observe trends over time.
- Compare price-per-square-foot metrics across listings and neighborhoods.
- Generate alerts for underpriced or highly desirable listings.

### 4. Workflow Automation
- Semi-automated process:
  - User marks a listing as a favorite.
  - The tool scrapes and stores the listing’s details.
- Respects Realtor.ca’s anti-scraping policies by limiting automation only to listings explicitly marked by the user.

## Tech Stack Ideas
1. **Frontend**:
   - Browser extension or local app UI for capturing interactions.
   - Mobile-friendly access for portability.
2. **Backend**:
   - Python-based scraper triggered by user actions.
   - PostgreSQL database to store listing data.
3. **Other Utilities**:
   - Analysis scripts to calculate trends and alert thresholds.

## Open Questions
1. **Data Fields:** Are additional details like property photos or virtual tours essential to capture?
2. **Analysis Depth:** What specific metrics or insights should the pricing analysis focus on?
3. **Privacy/Ethics:** How strictly should we adhere to Realtor.ca’s policies beyond the user-triggered scraping?