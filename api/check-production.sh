#!/bin/bash
# Check production deployment status

echo "=========================================="
echo "Production Deployment Check"
echo "=========================================="
echo ""

DOMAIN="condosapi.mistyrainbow.cloud"
APP_DIR="/var/www/condosapi"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Some checks may fail without root. Run with sudo for full check."
    echo ""
fi

echo "1. Checking service status..."
if systemctl is-active --quiet condosapi 2>/dev/null; then
    echo "   ✓ condosapi service is running"
else
    echo "   ✗ condosapi service is NOT running"
fi

echo ""
echo "2. Checking nginx status..."
if systemctl is-active --quiet nginx 2>/dev/null; then
    echo "   ✓ nginx is running"
else
    echo "   ✗ nginx is NOT running"
fi

echo ""
echo "3. Checking file structure..."
if [ -d "$APP_DIR" ]; then
    echo "   ✓ Application directory exists: $APP_DIR"
else
    echo "   ✗ Application directory missing: $APP_DIR"
fi

if [ -f "$APP_DIR/api/.env" ]; then
    echo "   ✓ Environment file exists"
else
    echo "   ✗ Environment file missing"
fi

if [ -f "$APP_DIR/../real_estate.db" ]; then
    echo "   ✓ Database exists"
else
    echo "   ✗ Database missing"
fi

echo ""
echo "4. Checking API health..."
if command -v curl &> /dev/null; then
    HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health 2>/dev/null || echo "failed")
    if [ "$HEALTH" = "200" ]; then
        echo "   ✓ API is responding (HTTP 200)"
    else
        echo "   ✗ API not responding (HTTP $HEALTH)"
    fi
else
    echo "   - curl not installed, skipping"
fi

echo ""
echo "5. Checking SSL certificate..."
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo "   ✓ SSL certificate exists"
    EXPIRY=$(openssl x509 -enddate -noout -in /etc/letsencrypt/live/$DOMAIN/fullchain.pem 2>/dev/null | cut -d= -f2)
    echo "   - Expires: $EXPIRY"
else
    echo "   ✗ SSL certificate not found"
fi

echo ""
echo "6. Checking nginx configuration..."
if [ -f "/etc/nginx/sites-available/condosapi" ]; then
    echo "   ✓ Nginx config exists"
    if nginx -t 2>&1 | grep -q "successful"; then
        echo "   ✓ Nginx config is valid"
    else
        echo "   ✗ Nginx config has errors"
    fi
else
    echo "   ✗ Nginx config missing"
fi

echo ""
echo "7. Recent log entries..."
if [ "$EUID" -eq 0 ]; then
    echo "   Last 5 log lines:"
    journalctl -u condosapi --no-pager -n 5 2>/dev/null || echo "   - No logs available"
else
    echo "   (Run with sudo to see logs)"
fi

echo ""
echo "=========================================="
echo "API Key (from .env):"
grep "API_KEY=" $APP_DIR/api/.env 2>/dev/null | head -1 || echo "   Could not read API key"
echo "=========================================="
