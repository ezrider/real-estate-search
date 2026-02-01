# CondoDork Playwright Scraper

Headless browser scraper for CondoDork Victoria listings. Runs on Linux servers without X11.

## Architecture

```
┌─────────────────┐     ┌─────────────┐     ┌─────────────────┐
│  Playwright     │────▶│  Extract    │────▶│  API Client     │
│  Headless       │     │  Listing    │     │                 │
│  Browser        │     │  Data       │     │  POST to API    │
└─────────────────┘     └─────────────┘     └─────────────────┘
```

## Installation

### Quick Install

```bash
cd scraper
bash install-playwright.sh
```

This installs:
- System dependencies (Chromium requirements)
- Python virtual environment
- Playwright and browsers

### Manual Install

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## Configuration

Copy the example environment file and edit:

```bash
cp .env.example .env
nano .env
```

```env
API_URL=https://condosapi.mistyrainbow.cloud/api/v1
API_KEY=your-api-key-from-server
```

Get your API key from the server:
```bash
ssh your-server "grep API_KEY /var/www/condosapi/api/.env"
```

## Testing

### Test Installation

```bash
source .venv/bin/activate
python test_installation.py
```

### Test Scraper (Dry Run)

```bash
python run_scraper.py --dry-run
```

This scrapes CondoDork but doesn't send to API. Shows preview of what would be sent.

## Usage

### Basic Scrape

```bash
source .venv/bin/activate
python run_scraper.py
```

### Scrape with Detail Pages

```bash
python run_scraper.py --details
```

This visits each listing page for more detailed info (slower).

### Debug Mode (With Browser Window)

```bash
python run_scraper.py --headed --dry-run
```

Shows the browser window for debugging. Only works if you have X11/display.

### Command Line Options

```
python run_scraper.py [OPTIONS]

Options:
  --dry-run      Scrape but don't send to API
  --headed       Show browser window (requires display)
  --details      Scrape individual listing pages
  --no-api       Scrape only, don't send to API
  -v, --verbose  Enable debug logging
```

## Scheduling

### Using Cron

```bash
bash setup-cron.sh
```

Choose from preset schedules or enter custom cron expression.

### Manual Cron Entry

```bash
# Edit crontab
crontab -e

# Add line (runs every hour)
0 * * * * cd /path/to/scraper && ./.venv/bin/python run_scraper.py >> logs/cron.log 2>&1
```

### Using Systemd Timer (Alternative)

Create `/etc/systemd/system/condodork-scraper.service`:

```ini
[Unit]
Description=CondoDork Scraper
After=network.target

[Service]
Type=oneshot
User=www-data
WorkingDirectory=/var/www/condosapi/scraper
ExecStart=/var/www/condosapi/scraper/.venv/bin/python run_scraper.py
Environment="API_URL=https://condosapi.mistyrainbow.cloud/api/v1"
Environment="API_KEY=your-key"
```

Create `/etc/systemd/system/condodork-scraper.timer`:

```ini
[Unit]
Description=Run CondoDork scraper every hour

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable condodork-scraper.timer
sudo systemctl start condodork-scraper.timer
```

## Logs

### View Recent Logs

```bash
# Cron logs
tail -f logs/cron.log

# Today's scraper logs
tail -f scraper_$(date +%Y%m%d).log
```

### Log Rotation

Add to `/etc/logrotate.d/condodork-scraper`:

```
/var/www/condosapi/scraper/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

## Troubleshooting

### Browser Won't Launch

```bash
# Check dependencies
ldd ~/.cache/ms-playwright/chromium-*/chrome-linux/chrome | grep "not found"

# Reinstall browsers
playwright install chromium --force
```

### Timeout Errors

Condodork may have anti-bot measures. Try:
- Increasing timeout in `condodork_scraper.py`
- Adding delays between requests
- Using residential proxy (advanced)

### API Connection Failed

```bash
# Test API connectivity
curl https://condosapi.mistyrainbow.cloud/health

# Check API key
grep API_KEY .env
```

### Memory Issues

For servers with limited RAM:

```python
# In condodork_scraper.py, reduce context pool
self.context = await self.browser.new_context(
    viewport={'width': 1280, 'height': 720},  # Smaller viewport
    reduced_motion='reduce',
)
```

## Development

### Adding New Selectors

If CondoDork changes their HTML structure, update selectors in `condodork_scraper.py`:

```python
selectors = [
    '[class*="new-listing-class"]',  # Add new selectors here
    '[data-testid="listing"]',
]
```

### Extending to Other Sites

Create new scraper class:

```python
class RealtorCaScraper:
    BASE_URL = "https://www.realtor.ca"
    # ... implement similar interface
```

## Performance

- **Main page scrape**: ~10-20 seconds
- **With detail pages**: ~2-3 minutes (for 10 listings)
- **Memory usage**: ~150MB per browser instance
- **CPU**: Low when idle, spikes during scraping

## Security Notes

- API key stored in `.env` file (not committed to git)
- Browser runs in isolated context
- No persistent cookies/storage
- Requests respect robots.txt (check CondoDork's policy)

## Next Steps

1. **Test locally** with `--dry-run`
2. **Deploy to server** and test headless
3. **Set up cron** for automated scraping
4. **Monitor logs** for errors
5. **Add proxy support** if needed for scale
