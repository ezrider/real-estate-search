#!/bin/bash
# Set up cron job for scheduled scraping

set -e

SCRAPER_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRAPER_DIR/logs"

echo "=========================================="
echo "Scraper Cron Setup"
echo "=========================================="
echo ""

# Create log directory
mkdir -p "$LOG_DIR"

# Default schedule (every hour)
SCHEDULE="0 * * * *"

echo "Select scraping frequency:"
echo "1) Every 15 minutes (aggressive)"
echo "2) Every 30 minutes"
echo "3) Every hour (default)"
echo "4) Every 2 hours"
echo "5) Every 6 hours"
echo "6) Daily"
echo "7) Custom"
read -p "Choice [3]: " choice

case "$choice" in
    1) SCHEDULE="*/15 * * * *" ;;
    2) SCHEDULE="*/30 * * * *" ;;
    3) SCHEDULE="0 * * * *" ;;
    4) SCHEDULE="0 */2 * * *" ;;
    5) SCHEDULE="0 */6 * * *" ;;
    6) SCHEDULE="0 9 * * *" ;;  # 9 AM daily
    7) 
        echo "Enter custom cron schedule (e.g., '0 */3 * * *' for every 3 hours):"
        read SCHEDULE
        ;;
esac

echo ""
echo "Schedule: $SCHEDULE"

# Create cron job
CRON_JOB="$SCHEDULE cd $SCRAPER_DIR && $SCRAPER_DIR/.venv/bin/python $SCRAPER_DIR/run_scraper.py >> $LOG_DIR/cron.log 2>&1"

# Add to crontab
( crontab -l 2>/dev/null | grep -v "run_scraper.py" || true; echo "$CRON_JOB" ) | crontab -

echo ""
echo "✓ Cron job installed"
echo ""
echo "Current crontab:"
crontab -l | grep -A1 -B1 "run_scraper"
echo ""
echo "Logs will be saved to: $LOG_DIR/cron.log"
echo ""
echo "To remove the cron job:"
echo "  crontab -e"
echo "  # Delete the line with run_scraper.py"
