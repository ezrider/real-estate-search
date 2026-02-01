#!/bin/bash
# Deployment script for Real Estate Tracker API
# Run this on your server

set -e

APP_NAME="condosapi"
APP_DIR="/var/www/$APP_NAME"
DOMAIN="condosapi.mistyrainbow.cloud"

echo "=========================================="
echo "Real Estate Tracker API - Deployment"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Install system dependencies
echo "→ Installing system dependencies..."
apt-get update
apt-get install -y python3-venv python3-pip nginx sqlite3 curl

# Create application directory
echo "→ Creating application directory..."
mkdir -p $APP_DIR
mkdir -p $APP_DIR/photos/listings
mkdir -p $APP_DIR/photos/historical_sales
chown -R www-data:www-data $APP_DIR/photos
chmod -R 755 $APP_DIR/photos

# Copy application files
echo "→ Copying application files..."
# Note: Run this from the project root
cp -r api/* $APP_DIR/ || {
    echo "Error: Failed to copy API files"
    echo "Make sure you're running this from the project root"
    exit 1
}

cp init_db.py $APP_DIR/../
cp schema.sql $APP_DIR/../

# Set ownership
chown -R www-data:www-data $APP_DIR

# Create virtual environment
echo "→ Creating Python virtual environment..."
sudo -u www-data bash -c "cd $APP_DIR && python3 -m venv .venv"

# Install dependencies
echo "→ Installing Python dependencies..."
sudo -u www-data bash -c "cd $APP_DIR && .venv/bin/pip install --upgrade pip"
sudo -u www-data bash -c "cd $APP_DIR && .venv/bin/pip install -r requirements.txt"

# Initialize database
echo "→ Initializing database..."
cd $APP_DIR/..
sudo -u www-data python3 init_db.py

# Create .env file if it doesn't exist
if [ ! -f "$APP_DIR/.env" ]; then
    echo "→ Creating environment configuration..."
    API_KEY=$(openssl rand -hex 32)
    cat > $APP_DIR/.env << EOF
API_KEY=$API_KEY
API_HOST=127.0.0.1
API_PORT=8000
DEBUG=false
DATABASE_URL=sqlite:///../real_estate.db
PHOTO_STORAGE_PATH=/var/www/condosapi/photos
MAX_PHOTO_SIZE_MB=10
CORS_ORIGINS=https://condosapi.$DOMAIN,https://www.realtor.ca,https://www.condodork.com
EOF
    chown www-data:www-data $APP_DIR/.env
    chmod 600 $APP_DIR/.env
    echo "✓ API Key generated: $API_KEY"
    echo "  Save this key for your Tampermonkey script!"
fi

# Install systemd service
echo "→ Installing systemd service..."
cp $APP_DIR/condosapi.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable condosapi

# Install nginx configuration
echo "→ Installing nginx configuration..."
cp $APP_DIR/nginx-condosapi.conf /etc/nginx/sites-available/condosapi

# Update nginx config with correct paths
sed -i "s|/path/to/your/certificate.crt|/etc/letsencrypt/live/$DOMAIN/fullchain.pem|g" /etc/nginx/sites-available/condosapi
sed -i "s|/path/to/your/private.key|/etc/letsencrypt/live/$DOMAIN/privkey.pem|g" /etc/nginx/sites-available/condosapi
sed -i "s|/path/to/real-estate-search/photos|$APP_DIR/photos|g" /etc/nginx/sites-available/condosapi
sed -i "s|condosapi.mistyrainbow.cloud|$DOMAIN|g" /etc/nginx/sites-available/condosapi

# Enable site
ln -sf /etc/nginx/sites-available/condosapi /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

# Test nginx configuration
nginx -t

# Start services
echo "→ Starting services..."
systemctl start condosapi
systemctl restart nginx

echo ""
echo "=========================================="
echo "✓ Deployment Complete!"
echo "=========================================="
echo ""
echo "Your API is now running at:"
echo "  HTTP:  http://$DOMAIN"
echo "  HTTPS: https://$DOMAIN (after SSL setup)"
echo ""
echo "API Documentation:"
echo "  https://$DOMAIN/docs"
echo ""
echo "Health Check:"
echo "  curl https://$DOMAIN/health"
echo ""
echo "Next steps:"
echo "1. Set up SSL with Let's Encrypt:"
echo "   certbot --nginx -d $DOMAIN"
echo ""
echo "2. Update your Tampermonkey script with:"
echo "   API_URL: https://$DOMAIN/api/v1/listings"
echo "   API_KEY: (from $APP_DIR/.env)"
echo ""
echo "3. Check service status:"
echo "   systemctl status condosapi"
echo "   journalctl -u condosapi -f"
echo ""
