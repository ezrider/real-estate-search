"""Main scraper runner - scrapes CondoDork and sends to API."""

import asyncio
import argparse
import logging
import sys
from datetime import datetime
from typing import List, Dict, Any

from condodork_scraper import CondoDorkScraper
from api_client import APIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"scraper_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger(__name__)


async def run_scraper(
    headless: bool = True,
    send_to_api: bool = True,
    dry_run: bool = False,
    detail_pages: bool = False
) -> List[Dict[str, Any]]:
    """Run the scraper and optionally send to API.
    
    Args:
        headless: Run browser headless
        send_to_api: Send scraped data to API
        dry_run: Don't actually send to API (preview only)
        detail_pages: Scrape individual listing detail pages
        
    Returns:
        List of scraped listings
    """
    listings = []
    
    async with CondoDorkScraper(headless=headless) as scraper:
        # Scrape main listings page
        logger.info("Starting scrape of CondoDork Victoria listings...")
        listings = await scraper.scrape_listings()
        
        if not listings:
            logger.warning("No listings found")
            return []
        
        logger.info(f"Scraped {len(listings)} listings from main page")
        
        # Optionally scrape detail pages for more info
        if detail_pages:
            logger.info("Scraping detail pages...")
            detailed_listings = []
            
            for listing in listings[:10]:  # Limit to first 10 for now
                if listing.get("source_url"):
                    try:
                        detail = await scraper.scrape_listing_detail(listing["source_url"])
                        if detail:
                            # Merge with basic listing data
                            detail.update({k: v for k, v in listing.items() if v})
                            detailed_listings.append(detail)
                    except Exception as e:
                        logger.warning(f"Failed to get detail for {listing.get('source_url')}: {e}")
                        detailed_listings.append(listing)
                else:
                    detailed_listings.append(listing)
            
            listings = detailed_listings
    
    # Send to API
    if send_to_api and not dry_run:
        logger.info(f"Sending {len(listings)} listings to API...")
        
        async with APIClient() as client:
            success_count = 0
            error_count = 0
            
            for listing in listings:
                try:
                    result = await client.create_or_update_listing(listing)
                    if result.get("success"):
                        success_count += 1
                    else:
                        error_count += 1
                        logger.warning(f"API rejected listing: {result}")
                except Exception as e:
                    error_count += 1
                    logger.error(f"Failed to send listing to API: {e}")
            
            logger.info(f"API upload complete: {success_count} success, {error_count} errors")
    
    elif dry_run:
        logger.info("DRY RUN - Not sending to API")
        print("\n" + "="*60)
        print("SCRAPED LISTINGS (DRY RUN)")
        print("="*60)
        
        for i, listing in enumerate(listings[:5], 1):
            print(f"\n{i}. {listing.get('address', 'Unknown Address')}")
            print(f"   Price: ${listing.get('price', 'N/A')}")
            print(f"   Beds: {listing.get('bedrooms', 'N/A')}, Baths: {listing.get('bathrooms', 'N/A')}")
            print(f"   Sqft: {listing.get('square_feet', 'N/A')}")
            print(f"   URL: {listing.get('source_url', 'N/A')}")
        
        if len(listings) > 5:
            print(f"\n... and {len(listings) - 5} more listings")
        
        print("="*60)
    
    return listings


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Scrape CondoDork Victoria listings and send to API"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape but don't send to API (print preview)"
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser with GUI (for debugging)"
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Scrape individual listing detail pages"
    )
    parser.add_argument(
        "--no-api",
        action="store_true",
        help="Scrape only, don't send to API"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run scraper
    try:
        listings = asyncio.run(run_scraper(
            headless=not args.headed,
            send_to_api=not args.no_api,
            dry_run=args.dry_run,
            detail_pages=args.details
        ))
        
        logger.info(f"Scraper completed. Total listings: {len(listings)}")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Scraper interrupted by user")
        return 130
    except Exception as e:
        logger.exception("Scraper failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
