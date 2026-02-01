# Playwright Tutorial for Web Scraping

A comprehensive guide to using Playwright for browser automation and web scraping, written for the Real Estate Tracker project but applicable to any scraping task.

---

## Table of Contents

1. [What is Playwright?](#what-is-playwright)
2. [Installation](#installation)
3. [Core Concepts](#core-concepts)
4. [Your First Scraper](#your-first-scraper)
5. [Selecting Elements](#selecting-elements)
6. [Extracting Data](#extracting-data)
7. [Handling Dynamic Content](#handling-dynamic-content)
8. [Headless Mode](#headless-mode)
9. [Best Practices](#best-practices)
10. [Common Patterns](#common-patterns)
11. [Troubleshooting](#troubleshooting)

---

## What is Playwright?

**Playwright** is a Python (and Node.js/Java/.NET) library for automating browsers. It can:

- Control Chrome, Firefox, and Safari programmatically
- Navigate websites, click buttons, fill forms
- Extract data from pages
- Take screenshots
- Run in **headless mode** (no visible browser window)
- Handle JavaScript-heavy sites (SPAs like React, Angular, Vue)

### Why Playwright vs Other Tools?

| Tool | Best For | Notes |
|------|----------|-------|
| **Playwright** | Modern SPAs, testing, scraping | Fast, reliable, auto-waits |
| **Selenium** | Legacy support, wide adoption | Slower, more resource-heavy |
| **Requests + BeautifulSoup** | Static HTML pages | Can't run JavaScript |
| **Scrapy** | Large-scale crawling | Needs middleware for JS |

**Playwright's killer feature:** It automatically waits for elements to appear before interacting with them. No more `time.sleep()` guessing games!

---

## Installation

### Local Development (with GUI)

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Playwright
pip install playwright

# Install browsers (Chromium, Firefox, WebKit)
playwright install
```

### Headless Server (no GUI)

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y libnss3 libatk-bridge2.0-0 libxss1 libgtk-3-0 libgbm1 libasound2

# Install Playwright
pip install playwright
playwright install chromium
```

**Why only Chromium?** It's the fastest and most lightweight for scraping. Install others if you need cross-browser testing.

---

## Core Concepts

### 1. Async Context Manager Pattern

Playwright is designed to work with Python's `asyncio`. Always use the context manager pattern:

```python
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # Browser is launched here
        browser = await p.chromium.launch()
        
        # Your code here
        
        # Browser automatically closes when exiting context
        await browser.close()

# Run the async function
asyncio.run(main())
```

**Why async?** Browsers are I/O-bound. Async lets you run multiple pages simultaneously without blocking.

### 2. Browser → Context → Page

```
Browser (Chromium/Firefox/WebKit)
    └── BrowserContext (isolated session)
            └── Page (individual tab)
```

```python
# Launch browser
browser = await p.chromium.launch()

# Create isolated context (like incognito mode)
context = await browser.new_context()

# Open a page
def page = await context.new_page()

# Navigate
await page.goto('https://example.com')
```

**Why contexts?** Each context has its own cookies, storage, and session. Great for scraping as different "users."

---

## Your First Scraper

Create `first_scraper.py`:

```python
import asyncio
from playwright.async_api import async_playwright

async def scrape_example():
    """Scrape the title and first heading from example.com."""
    
    async with async_playwright() as p:
        # Launch browser (headless by default)
        browser = await p.chromium.launch(headless=True)
        
        # Create new page
        page = await browser.new_page()
        
        # Navigate to website
        print("Navigating to example.com...")
        await page.goto('https://example.com')
        
        # Get page title
        title = await page.title()
        print(f"Page title: {title}")
        
        # Extract first heading
        heading = await page.text_content('h1')
        print(f"First heading: {heading}")
        
        # Take screenshot
        await page.screenshot(path='example.png')
        print("Screenshot saved to example.png")
        
        # Close browser
        await browser.close()

# Run it
if __name__ == "__main__":
    asyncio.run(scrape_example())
```

Run it:
```bash
python first_scraper.py
```

Output:
```
Navigating to example.com...
Page title: Example Domain
First heading: Example Domain
Screenshot saved to example.png
```

---

## Selecting Elements

Playwright supports multiple selector engines:

### 1. CSS Selectors (most common)

```python
# By tag
await page.query_selector('h1')

# By class
await page.query_selector('.price')
await page.query_selector('.listing-card.active')

# By ID
await page.query_selector('#search-button')

# By attribute
await page.query_selector('[data-testid="price"]')
await page.query_selector('a[href="/listings"]')

# Complex selectors
await page.query_selector('div.listing > h2.title')
await page.query_selector('ul.properties li:first-child')
```

### 2. Text Selectors (very useful!)

```python
# Find by text content
await page.click('text=Search')
await page.click('text=View Details')

# Case-insensitive
await page.click('text=/search/i')

# Partial match
await page.click('text=View')
```

### 3. XPath

```python
await page.query_selector('xpath=//div[@class="price"]')
```

### 4. Combining Selectors

```python
# Try multiple selectors (Playwright tries each in order)
price_elem = await page.query_selector('.price, [class*="price"], .cost')
```

---

## Extracting Data

### Single Element

```python
# Get text content
text = await page.text_content('.price')

# Get HTML
html = await page.inner_html('.description')

# Get attribute
href = await page.get_attribute('a.more-info', 'href')

# Get input value
value = await page.input_value('#search-input')
```

### Multiple Elements

```python
# Get all listing cards
cards = await page.query_selector_all('.listing-card')

for card in cards:
    # Extract from each card
    title = await card.text_content('.title')
    price = await card.text_content('.price')
    print(f"{title}: {price}")
```

### Using evaluate() for Complex Extraction

```python
# Run JavaScript in the browser
listings = await page.evaluate('''() => {
    // This runs in the browser!
    const cards = document.querySelectorAll('.listing-card');
    return Array.from(cards).map(card => ({
        title: card.querySelector('.title')?.textContent,
        price: card.querySelector('.price')?.textContent,
        url: card.querySelector('a')?.href
    }));
}''')

print(listings)
# [{'title': 'The Janion', 'price': '$500,000', 'url': '...'}, ...]
```

---

## Handling Dynamic Content

Modern websites (React, Angular, Vue) load content dynamically. Playwright handles this automatically!

### Wait for Elements

```python
# Wait for element to appear (default 30 seconds)
await page.wait_for_selector('.listing-card')

# Wait with custom timeout
await page.wait_for_selector('.price', timeout=10000)  # 10 seconds

# Wait for element to be visible
await page.wait_for_selector('.loading-spinner', state='hidden')
```

### Wait for Navigation

```python
# Click and wait for navigation
await page.click('a.next-page')
await page.wait_for_load_state('networkidle')

# Or combine
async with page.expect_navigation():
    await page.click('a.next-page')
```

### Wait for API Calls

```python
# Wait for specific API call to finish
async with page.expect_response('**/api/listings**') as response_info:
    await page.click('button.load-more')

response = await response_info.value
print(await response.json())
```

---

## Headless Mode

### What is Headless?

Headless mode runs the browser **without a visible window**. Perfect for:
- Servers (no display needed)
- Automated scraping
- Running in Docker/containers
- Faster execution

### Launch Options for Headless

```python
browser = await p.chromium.launch(
    headless=True,  # No GUI
    args=[
        '--no-sandbox',              # Required for Docker/root
        '--disable-setuid-sandbox',  # Required for Docker/root
        '--disable-dev-shm-usage',   # Overcome limited resource problems
        '--disable-gpu',             # No GPU in headless
        '--window-size=1920,1080',   # Set viewport size
    ]
)
```

### Debugging Headless Issues

```python
# Slow down operations to see what's happening
browser = await p.chromium.launch(
    headless=False,  # Show browser
    slow_mo=1000     # Wait 1 second between actions
)

# Take screenshots on error
try:
    await page.click('.submit-button')
except:
    await page.screenshot(path='error.png')
    raise
```

---

## Best Practices

### 1. Always Use Context Managers

```python
# Good - automatically closes browser
async with async_playwright() as p:
    browser = await p.chromium.launch()
    # ... do work

# Bad - browser stays open if exception occurs
browser = await p.chromium.launch()
# ... do work
await browser.close()
```

### 2. Set Realistic User Agents

```python
context = await browser.new_context(
    user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
)
```

### 3. Add Random Delays

```python
import random

# Random delay between 1-3 seconds
await asyncio.sleep(random.uniform(1, 3))
```

### 4. Handle Errors Gracefully

```python
from playwright.async_api import TimeoutError

try:
    await page.wait_for_selector('.price', timeout=5000)
except TimeoutError:
    print("Price not found, skipping...")
    return None
```

### 5. Reuse Browser Contexts

```python
# Create one context, multiple pages (faster)
context = await browser.new_context()

for url in urls:
    page = await context.new_page()
    await page.goto(url)
    # ... scrape
    await page.close()
```

---

## Common Patterns

### Pattern 1: Login and Scrape

```python
async def login_and_scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Login
        await page.goto('https://example.com/login')
        await page.fill('#username', 'myuser')
        await page.fill('#password', 'mypass')
        await page.click('button[type="submit"]')
        
        # Wait for login to complete
        await page.wait_for_url('**/dashboard')
        
        # Now scrape protected content
        await page.goto('https://example.com/data')
        data = await page.text_content('.secret-data')
        
        await browser.close()
```

### Pattern 2: Infinite Scroll

```python
async def scrape_infinite_scroll():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        await page.goto('https://example.com/listings')
        
        # Scroll until no more content loads
        previous_height = 0
        while True:
            # Scroll to bottom
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            
            # Wait for new content
            await asyncio.sleep(2)
            
            # Check if height changed
            current_height = await page.evaluate('document.body.scrollHeight')
            if current_height == previous_height:
                break
            previous_height = current_height
        
        # Now scrape all content
        items = await page.query_selector_all('.item')
        
        await browser.close()
```

### Pattern 3: Handling Popups

```python
# Wait for popup and interact with it
async with page.expect_popup() as popup_info:
    await page.click('a[target="_blank"]')

popup = await popup_info.value
await popup.wait_for_load_state()

# Scrape popup content
data = await popup.text_content('.popup-content')
await popup.close()
```

---

## Troubleshooting

### "Browser not found" Error

```bash
# Reinstall browsers
playwright install --force
```

### Timeout on Navigation

```python
# Increase timeout
await page.goto(url, timeout=60000)  # 60 seconds

# Or wait for specific element instead of full load
await page.goto(url, wait_until='domcontentloaded')
```

### Element Not Found (But It's There!)

The element might be in an iframe:

```python
# Switch to iframe
frame = page.frame_locator('iframe#content')
element = await frame.locator('.price').text_content()
```

Or it might not be visible yet:

```python
# Wait for element to be visible
await page.wait_for_selector('.price', state='visible')
```

### Memory Issues

```python
# Close pages when done
page = await context.new_page()
# ... scrape
await page.close()  # Free memory

# Limit concurrent pages
semaphore = asyncio.Semaphore(5)  # Max 5 pages

async def scrape_with_limit(url):
    async with semaphore:
        page = await context.new_page()
        # ... scrape
        await page.close()
```

---

## Advanced: CondoDork Example

Here's a condensed version of our actual scraper:

```python
import asyncio
from playwright.async_api import async_playwright

async def scrape_condodork():
    async with async_playwright() as p:
        # Launch headless browser
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        page = await browser.new_page()
        
        # Navigate
        await page.goto('https://www.condodork.com/en/victoria/condos-for-sale')
        
        # Wait for listings to load
        await page.wait_for_selector('.listing-card', timeout=10000)
        
        # Extract all listings using JavaScript
        listings = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('.listing-card')).map(card => {
                const priceText = card.querySelector('.price')?.textContent || '';
                const price = priceText.match(/\$([\d,]+)/)?.[1]?.replace(/,/g, '');
                
                return {
                    price: price ? parseInt(price) : null,
                    address: card.querySelector('.address')?.textContent?.trim(),
                    bedrooms: card.textContent.match(/(\d+)\s*bed/i)?.[1],
                    url: card.querySelector('a')?.href
                };
            });
        }''')
        
        print(f"Found {len(listings)} listings")
        for listing in listings[:3]:
            print(f"  ${listing['price']} - {listing['address']}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_condodork())
```

---

## Further Learning

### Official Resources

- **Documentation:** https://playwright.dev/python/
- **API Reference:** https://playwright.dev/python/docs/api/class-playwright
- **GitHub:** https://github.com/microsoft/playwright-python

### Practice Projects

1. **Scrape your favorite news site** - Extract headlines and links
2. **Screenshot tool** - Take screenshots of multiple URLs
3. **Price tracker** - Monitor a product page for price changes
4. **Form filler** - Automate filling out a contact form

---

## Quick Reference Card

```python
# Launch
browser = await p.chromium.launch(headless=True)
context = await browser.new_context()
page = await context.new_page()

# Navigate
await page.goto('https://example.com')
await page.reload()
await page.go_back()

# Interact
await page.click('button.submit')
await page.fill('#input', 'text');
await page.select_option('select#country', 'Canada')
await page.check('input#agree')

# Extract
await page.text_content('.price')
await page.get_attribute('a', 'href')
await page.input_value('input#name')

# Wait
await page.wait_for_selector('.loaded')
await page.wait_for_load_state('networkidle')

# Screenshot
await page.screenshot(path='page.png')
await page.screenshot(path='element.png', element=elem)
```

---

Happy scraping! 🎭
