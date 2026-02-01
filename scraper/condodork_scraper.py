"""Playwright-based scraper for CondoDork.com Victoria listings."""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout

from api_client import APIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CondoDorkScraper:
    """Scraper for CondoDork Victoria listings."""
    
    BASE_URL = "https://www.condodork.com"
    VICTORIA_URL = "https://www.condodork.com/en/victoria/condos-for-sale"
    
    def __init__(self, headless: bool = True, slow_mo: int = 0):
        """Initialize scraper.
        
        Args:
            headless: Run browser in headless mode (no GUI)
            slow_mo: Slow down operations by N milliseconds (for debugging)
        """
        self.headless = headless
        self.slow_mo = slow_mo
        self.browser: Optional[Browser] = None
        self.context = None
        self.page: Optional[Page] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.playwright = await async_playwright().start()
        
        # Launch browser with headless options for Linux server
        browser_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--disable-gpu',
            '--window-size=1920,1080',
        ]
        
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=browser_args,
            slow_mo=self.slow_mo
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.0'
        )
        
        self.page = await self.context.new_page()
        
        # Set default timeout
        self.page.set_default_timeout(30000)
        
        logger.info("Browser initialized (headless=%s)", self.headless)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")
    
    async def scrape_listings(self) -> List[Dict[str, Any]]:
        """Scrape all listings from Victoria page.
        
        Returns:
            List of listing dictionaries
        """
        if not self.page:
            raise RuntimeError("Scraper not initialized. Use async context manager.")
        
        logger.info(f"Navigating to {self.VICTORIA_URL}")
        
        try:
            await self.page.goto(self.VICTORIA_URL, wait_until='networkidle')
            
            # Wait for listings to load
            logger.info("Waiting for listings to load...")
            await self.page.wait_for_selector('[class*="listing"], [class*="property"], .card', timeout=10000)
            
        except PlaywrightTimeout:
            logger.error("Timeout waiting for page to load")
            # Try to get page content anyway for debugging
            content = await self.page.content()
            if "condodork" not in content.lower():
                logger.error("Page content doesn't match expected site")
            return []
        
        # Extract listings
        listings = await self._extract_listings_from_page()
        
        logger.info(f"Found {len(listings)} listings")
        
        return listings
    
    async def _extract_listings_from_page(self) -> List[Dict[str, Any]]:
        """Extract listing data from the current page."""
        listings = []
        
        # Try multiple selector strategies since CondoDork uses dynamic classes
        selectors = [
            '[class*="listing-card"]',
            '[class*="property-card"]',
            '.card',
            '[data-testid*="listing"]',
            'a[href*="/property/"]',
            'a[href*="/condo/"]',
        ]
        
        listing_elements = []
        for selector in selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    listing_elements = elements
                    logger.debug(f"Found {len(elements)} listings with selector: {selector}")
                    break
            except Exception:
                continue
        
        if not listing_elements:
            logger.warning("No listing elements found with any selector")
            # Debug: log page structure
            html = await self.page.content()
            logger.debug(f"Page HTML (first 2000 chars): {html[:2000]}")
            return []
        
        for element in listing_elements:
            try:
                listing = await self._parse_listing_element(element)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.warning(f"Failed to parse listing element: {e}")
                continue
        
        return listings
    
    async def _parse_listing_element(self, element) -> Optional[Dict[str, Any]]:
        """Parse a single listing element.
        
        Args:
            element: Playwright element handle
            
        Returns:
            Listing dictionary or None if parsing fails
        """
        listing = {
            "source_platform": "CondoDork",
            "source_url": self.VICTORIA_URL
        }
        
        # Try to get the detail page link
        link_elem = await element.query_selector('a')
        if link_elem:
            href = await link_elem.get_attribute('href')
            if href:
                listing["source_url"] = urljoin(self.BASE_URL, href)
                # Try to extract MLS from URL
                mls_match = re.search(r'/(?:listing|property|condo)/(\d+|[a-zA-Z0-9-]+)', href)
                if mls_match:
                    listing["mls_number"] = mls_match.group(1)
        
        # Extract price
        price_selectors = [
            '[class*="price"]',
            '.price',
            'text=/\\$[\\d,]+/',
        ]
        
        for selector in price_selectors:
            try:
                price_elem = await element.query_selector(selector)
                if price_elem:
                    price_text = await price_elem.text_content()
                    price = self._parse_price(price_text)
                    if price:
                        listing["price"] = price
                        break
            except Exception:
                continue
        
        # Extract address/building name
        address_selectors = [
            '[class*="address"]',
            '[class*="title"]',
            'h1', 'h2', 'h3',
        ]
        
        for selector in address_selectors:
            try:
                addr_elem = await element.query_selector(selector)
                if addr_elem:
                    address = await addr_elem.text_content()
                    if address:
                        address = address.strip()
                        listing["address"] = address
                        # Try to extract building name
                        listing["building_name"] = self._extract_building_name(address)
                        break
            except Exception:
                continue
        
        # Extract unit number
        if "address" in listing:
            unit_match = re.search(r'(?:Unit|#)\s*(\d+)', listing["address"], re.IGNORECASE)
            if unit_match:
                listing["unit_number"] = unit_match.group(1)
        
        # Extract bedrooms/bathrooms/sqft from text
        text_content = await element.text_content()
        if text_content:
            bedrooms = self._extract_bedrooms(text_content)
            bathrooms = self._extract_bathrooms(text_content)
            sqft = self._extract_sqft(text_content)
            
            if bedrooms:
                listing["bedrooms"] = bedrooms
            if bathrooms:
                listing["bathrooms"] = bathrooms
            if sqft:
                listing["square_feet"] = sqft
        
        # Extract property type
        if "bedrooms" in listing:
            listing["property_type"] = "Condo"
        
        # Set default neighborhood if not found
        listing["neighborhood"] = "Downtown"  # Default, can be refined
        
        # Set listing date to today (since we don't have exact date)
        listing["listing_date"] = datetime.now().strftime("%Y-%m-%d")
        
        # Validate minimum data
        if not listing.get("price") and not listing.get("address"):
            return None
        
        return listing
    
    def _parse_price(self, text: str) -> Optional[Decimal]:
        """Extract price from text."""
        if not text:
            return None
        
        # Match patterns like $500,000 or $500000
        match = re.search(r'\$\s*([\d,]+)', text)
        if match:
            try:
                price_str = match.group(1).replace(',', '')
                return Decimal(price_str)
            except (ValueError, TypeError):
                pass
        return None
    
    def _extract_building_name(self, address: str) -> Optional[str]:
        """Extract building name from address."""
        # Common patterns: "The Janion at 123 Street" or just "The Janion"
        patterns = [
            r'^The\s+\w+',  # The Janion, The Mondrian, etc.
            r'^\w+\s+(?:Tower|Place|Residences|Condos)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_bedrooms(self, text: str) -> Optional[int]:
        """Extract bedroom count from text."""
        match = re.search(r'(\d+)\s*(?:bd|bed|bedroom)', text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
    
    def _extract_bathrooms(self, text: str) -> Optional[float]:
        """Extract bathroom count from text."""
        match = re.search(r'(\d+(?:\.\d+)?)\s*(?:ba|bath|bathroom)', text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None
    
    def _extract_sqft(self, text: str) -> Optional[int]:
        """Extract square footage from text."""
        match = re.search(r'(\d+)\s*(?:sqft|sq\.?\s*ft|sf)', text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
    
    async def scrape_listing_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape detailed information from a listing page.
        
        Args:
            url: Listing detail page URL
            
        Returns:
            Detailed listing dictionary
        """
        logger.info(f"Scraping detail page: {url}")
        
        try:
            await self.page.goto(url, wait_until='networkidle')
            await asyncio.sleep(1)  # Wait for dynamic content
            
            listing = {
                "source_platform": "CondoDork",
                "source_url": url
            }
            
            # Extract MLS number from URL
            mls_match = re.search(r'/(?:listing|property|condo)/(\d+|[a-zA-Z0-9-]+)', url)
            if mls_match:
                listing["mls_number"] = mls_match.group(1)
            
            # Get page text for parsing
            text_content = await self.page.text_content('body')
            
            # Parse price
            price_elem = await self.page.query_selector('[class*="price"], .price')
            if price_elem:
                price_text = await price_elem.text_content()
                price = self._parse_price(price_text)
                if price:
                    listing["price"] = price
            
            # Parse address
            address_selectors = ['h1', '[class*="address"]', '[class*="title"]']
            for selector in address_selectors:
                elem = await self.page.query_selector(selector)
                if elem:
                    address = await elem.text_content()
                    if address:
                        listing["address"] = address.strip()
                        listing["building_name"] = self._extract_building_name(address)
                        break
            
            # Parse details
            bedrooms = self._extract_bedrooms(text_content)
            bathrooms = self._extract_bathrooms(text_content)
            sqft = self._extract_sqft(text_content)
            
            if bedrooms:
                listing["bedrooms"] = bedrooms
            if bathrooms:
                listing["bathrooms"] = bathrooms
            if sqft:
                listing["square_feet"] = sqft
            
            # Parse description
            desc_selectors = ['[class*="description"]', '[class*="details"]']
            for selector in desc_selectors:
                elem = await self.page.query_selector(selector)
                if elem:
                    description = await elem.text_content()
                    if description:
                        listing["description"] = description.strip()[:500]  # Limit length
                        break
            
            listing["listing_date"] = datetime.now().strftime("%Y-%m-%d")
            listing["property_type"] = "Condo"
            
            return listing
            
        except Exception as e:
            logger.error(f"Failed to scrape detail page {url}: {e}")
            return None


async def main():
    """Main entry point for testing."""
    logging.basicConfig(level=logging.DEBUG)
    
    async with CondoDorkScraper(headless=True) as scraper:
        listings = await scraper.scrape_listings()
        
        print(f"\nFound {len(listings)} listings:")
        for listing in listings[:3]:  # Show first 3
            print(f"\n--- Listing ---")
            for key, value in listing.items():
                print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
