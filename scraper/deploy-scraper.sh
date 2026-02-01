#!/bin/bash
# Deploy scraper to production server

set -e

SCRAPER_DIR="/var/www/condosapi/scraper"

echo "=========================================="
echo "CondoDork Scraper Deployment"
echo "=========================================="
echo ""

if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Create scraper directory
echo "→ Creating scraper directory..."
mkdir -p $SCRAPER_DIR
mkdir -p $SCRAPER_DIR/logs
chown -R www-data:www-data $SCRAPER_DIR

# Copy files
echo "→ Copying scraper files..."
cp -r . $SCRAPER_DIR/ || {
    echo "Error: Failed to copy files"
    echo "Make sure you're running from the scraper directory"
    exit 1
}

# Set ownership
chown -R www-data:www-data $SCRAPER_DIR

# Install dependencies
echo "→ Installing dependencies..."
cd $SCRAPER_DIR
sudo -u www-data python3 -m venv .venv
sudo -u www-data .venv/bin/pip install --upgrade pip
sudo -u www-data .venv/bin/pip install -r requirements.txt

# Install Playwright browsers
echo "→ Installing Playwright browsers..."
sudo -u www-data .venv/bin/playwright install chromium

echo ""
echo "=========================================="
echo "✓ Scraper deployed to $SCRAPER_DIR"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Configure environment:"
echo "   sudo nano $SCRAPER_DIR/.env"
echo ""
echo "2. Test the scraper:"
echo "   cd $SCRAPER_DIR"
echo "   sudo -u www-data .venv/bin/python run_scraper.py --dry-run"
echo ""
echo "3. Install systemd timer:"
echo "   sudo cp condodork-scraper.service /etc/systemd/system/"
echo "   sudo cp condodork-scraper.timer /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable condodork-scraper.timer"
echo "   sudo systemctl start condodork-scraper.timer"
echo ""
