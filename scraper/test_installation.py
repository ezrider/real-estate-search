#!/usr/bin/env python3
"""Test Playwright installation on headless Linux server."""

import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_browser():
    """Test that Playwright browser works in headless mode."""
    logger.info("Testing Playwright installation...")
    
    async with async_playwright() as p:
        logger.info("Launching Chromium in headless mode...")
        
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
            ]
        )
        
        logger.info("✓ Browser launched successfully")
        
        page = await browser.new_page()
        
        # Test navigation
        logger.info("Testing page navigation...")
        await page.goto('https://example.com')
        title = await page.title()
        
        logger.info(f"✓ Page loaded: {title}")
        
        await browser.close()
    
    logger.info("✓ Playwright installation test PASSED")
    return True


def main():
    """Main entry point."""
    try:
        asyncio.run(test_browser())
        print("\n" + "="*60)
        print("SUCCESS: Playwright is working correctly!")
        print("="*60)
        return 0
    except Exception as e:
        logger.exception("Test failed")
        print("\n" + "="*60)
        print(f"FAILED: {e}")
        print("="*60)
        return 1


if __name__ == "__main__":
    exit(main())
