# Scraping Options for Headless Linux Server

Your server has no X11/display, but you can still run browsers in **headless mode**. Here are your options from simplest to most robust.

---

## Option 1: Tampermonkey + API (Your Current Approach)

**How it works:**
- Browser runs on your desktop/laptop (with display)
- Tampermonkey extracts data from rendered pages
- Data is POSTed to your server API

**Pros:**
- ✅ Zero server resources for rendering
- ✅ Handles any JavaScript-heavy site (CondoDork, React apps)
- ✅ No server configuration needed
- ✅ Works around anti-bot measures (you're a real user)

**Cons:**
- ❌ Requires your computer to be on and browsing
- ❌ Not automated/scheduled

**Enhancement - Scheduled Browser on Server:**
```bash
# Install a browser + Xvfb (virtual framebuffer) on server
sudo apt-get install chromium-browser xvfb

# Run browser with virtual display
xvfb-run -a chromium-browser --headless --dump-dom https://condodork.com/...
```

---

## Option 2: Puppeteer (Node.js) - RECOMMENDED

**Best for:** JavaScript-heavy sites like CondoDork

```javascript
// scraper.js
const puppeteer = require('puppeteer');

async function scrapeCondoDork() {
  // Launch headless browser (no X11 needed!)
  const browser = await puppeteer.launch({
    headless: 'new',  // New headless mode
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-accelerated-2d-canvas',
      '--disable-gpu'
    ]
  });
  
  const page = await browser.newPage();
  
  // Navigate and wait for React to render
  await page.goto('https://www.condodork.com/en/victoria/condos-for-sale', {
    waitUntil: 'networkidle2'
  });
  
  // Wait for listings to load
  await page.waitForSelector('.listing-card'); // adjust selector
  
  // Extract data
  const listings = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('.listing-card')).map(card => ({
      price: card.querySelector('.price').textContent,
      address: card.querySelector('.address').textContent,
      // ... extract other fields
    }));
  });
  
  // POST to your API
  for (const listing of listings) {
    await fetch('https://your-domain.com/api/v1/listings', {
      method: 'POST',
      headers: {
        'X-API-Key': 'your-key',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(listing)
    });
  }
  
  await browser.close();
}

scrapeCondoDork();
```

**Installation on server:**
```bash
# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Chromium dependencies
sudo apt-get install -y libnss3 libatk-bridge2.0-0 libxss1 libgtk-3-0

# Create scraper project
mkdir ~/condo-scraper && cd ~/condo-scraper
npm init -y
npm install puppeteer

# Run it
node scraper.js
```

**Scheduling with cron:**
```bash
# Run every hour
crontab -e
0 * * * * cd ~/condo-scraper && /usr/bin/node scraper.js >> scraper.log 2>&1
```

**Pros:**
- ✅ Handles SPAs (React, Angular, Vue)
- ✅ Real Chrome rendering
- ✅ Screenshots for debugging
- ✅ Stealth mode to avoid detection

**Cons:**
- ❌ Memory intensive (~100MB per browser instance)
- ❌ Slower than API scraping

---

## Option 3: Playwright (Python) - ALSO GREAT

**Best for:** Python ecosystem, multiple browser support

```python
# scraper.py
import asyncio
from playwright.async_api import async_playwright
import aiohttp

API_URL = "https://your-domain.com/api/v1/listings"
API_KEY = "your-api-key"

async def submit_listing(session, listing_data):
    async with session.post(
        API_URL,
        json=listing_data,
        headers={"X-API-Key": API_KEY}
    ) as resp:
        return await resp.json()

async def scrape_condodork():
    async with async_playwright() as p:
        # Launch headless browser
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        page = await browser.new_page()
        
        # Navigate and wait for content
        await page.goto('https://www.condodork.com/en/victoria/condos-for-sale')
        await page.wait_for_selector('[data-testid="listing-card"]', timeout=10000)
        
        # Extract listings
        listings = await page.eval_on_selector_all(
            '[data-testid="listing-card"]',
            '''elements => elements.map(el => ({
                price: el.querySelector('.price')?.textContent,
                address: el.querySelector('.address')?.textContent,
                // ...
            }))'''
        )
        
        # Submit to API
        async with aiohttp.ClientSession() as session:
            for listing in listings:
                await submit_listing(session, listing)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_condodork())
```

**Installation:**
```bash
# Install Playwright
pip install playwright
playwright install chromium

# Or with uv
uv pip install playwright
uv run playwright install chromium

# System dependencies (Debian/Ubuntu)
sudo apt-get install libglib2.0-0 libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libdbus-1-3 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2
```

**Pros:**
- ✅ Python (same ecosystem as your API)
- ✅ Multiple browsers (Chromium, Firefox, WebKit)
- ✅ Auto-waits for elements
- ✅ Mobile emulation

---

## Option 4: Selenium (Legacy but Stable)

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')

driver = webdriver.Chrome(options=options)
driver.get('https://condodork.com/...')

# Extract data
listings = driver.find_elements_by_css_selector('.listing-card')
```

**Pros:**
- ✅ Mature, well-documented
- ✅ Large community

**Cons:**
- ❌ Slower than Puppeteer/Playwright
- ❌ More resource intensive
- ❌ Less suited for modern SPAs

---

## Option 5: Browserless / Puppeteer-Cluster (For Scale)

If you need to scrape multiple pages/sites concurrently:

```yaml
# docker-compose.yml
version: '3'
services:
  browserless:
    image: browserless/chrome
    ports:
      - "3000:3000"
    environment:
      - MAX_CONCURRENT_SESSIONS=5
      - CONNECTION_TIMEOUT=30000
```

Then connect remotely:
```javascript
const browser = await puppeteer.connect({
  browserWSEndpoint: 'ws://localhost:3000'
});
```

---

## Comparison Summary

| Approach | Best For | Resource Usage | JS Sites | Setup Complexity |
|----------|----------|----------------|----------|------------------|
| Tampermonkey | Manual browsing, complex sites | Low (client-side) | ✅ | Low |
| Puppeteer | SPA scraping, screenshots | High (~100MB) | ✅ | Medium |
| Playwright | Python ecosystem, testing | High (~100MB) | ✅ | Medium |
| Selenium | Legacy compatibility | Very High | ⚠️ | High |
| Browserless | Scale, multiple concurrent | Medium | ✅ | High |

---

## Recommended Setup for You

### Phase 1: Tampermonkey + API (Now)
- Build the FastAPI server
- Create Tampermonkey script to push data
- Manual but immediate

### Phase 2: Playwright Scheduler (Next)
- Install Playwright on server
- Create scheduled scraper for CondoDork
- Runs hourly via cron
- Falls back to Tampermonkey for complex cases

### Phase 3: Hybrid (Future)
- Playwright handles routine scraping
- Tampermonkey for one-off discoveries
- API receives from both sources

---

## Quick Start: Playwright on Your Server

```bash
# 1. Install dependencies
sudo apt-get update
sudo apt-get install -y python3-pip libglib2.0-0 libnss3 libatk1.0-0

# 2. Install Playwright
pip3 install playwright
playwright install chromium

# 3. Test headless browser
python3 << 'EOF'
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://example.com')
    print(page.title())
    browser.close()
    print("✓ Headless browser works!")
EOF
```

If that prints the title, you're ready to scrape!
