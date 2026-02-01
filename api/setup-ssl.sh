#!/bin/bash
# SSL Setup for condosapi.mistyrainbow.cloud

set -e

DOMAIN="condosapi.mistyrainbow.cloud"

echo "=========================================="
echo "SSL Setup with Let's Encrypt"
echo "=========================================="
echo ""

if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Install certbot
echo "→ Installing certbot..."
apt-get update
apt-get install -y certbot python3-certbot-nginx

# Obtain certificate
echo "→ Obtaining SSL certificate for $DOMAIN..."
certbot --nginx -d $DOMAIN --agree-tos --non-interactive --email your-email@example.com

# Reload nginx
echo "→ Reloading nginx..."
systemctl reload nginx

echo ""
echo "=========================================="
echo "✓ SSL Setup Complete!"
echo "=========================================="
echo ""
echo "Your API is now accessible via HTTPS:"
echo "  https://$DOMAIN"
echo ""
echo "Certificate will auto-renew. To test renewal:"
echo "  certbot renew --dry-run"
echo ""
