# Deployment Guide - Real Estate Tracker API

This guide walks you through deploying the API to your server at `condosapi.mistyrainbow.cloud`.

## Prerequisites

- Ubuntu/Debian Linux server
- Root (sudo) access
- Domain `condosapi.mistyrainbow.cloud` pointing to your server
- Ports 80 and 443 open

## Quick Deploy

### 1. Copy Files to Server

On your local machine, copy the project to your server:

```bash
rsync -avz --exclude '.venv' --exclude '__pycache__' \
  /root/repos/real-estate-search/ \
  user@your-server:/tmp/real-estate-search/
```

### 2. Run Deployment Script

SSH into your server and run:

```bash
cd /tmp/real-estate-search/api
sudo bash deploy.sh
```

This will:
- Install Python, nginx, and dependencies
- Set up the application at `/var/www/condosapi/`
- Create a virtual environment
- Initialize the database
- Generate an API key
- Install systemd service
- Configure nginx

### 3. Set Up SSL

```bash
sudo bash /tmp/real-estate-search/api/setup-ssl.sh
```

Or manually:

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d condosapi.mistyrainbow.cloud
```

### 4. Verify Deployment

```bash
# Check service status
sudo systemctl status condosapi

# Check logs
sudo journalctl -u condosapi -f

# Test API
curl https://condosapi.mistyrainbow.cloud/health
```

## Manual Deployment

If you prefer manual setup:

### Step 1: Install Dependencies

```bash
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip nginx sqlite3
```

### Step 2: Create Application Directory

```bash
sudo mkdir -p /var/www/condosapi
sudo mkdir -p /var/www/condosapi/photos/listings
sudo mkdir -p /var/www/condosapi/photos/historical_sales
sudo chown -R www-data:www-data /var/www/condosapi/photos
```

### Step 3: Copy Application

```bash
sudo cp -r api /var/www/condosapi/
sudo cp init_db.py schema.sql /var/www/condosapi/
```

### Step 4: Set Up Virtual Environment

```bash
cd /var/www/condosapi/api
sudo python3 -m venv .venv
sudo .venv/bin/pip install -r requirements.txt
```

### Step 5: Initialize Database

```bash
cd /var/www/condosapi
sudo python3 init_db.py
sudo chown www-data:www-data real_estate.db
```

### Step 6: Configure Environment

```bash
sudo nano /var/www/condosapi/api/.env
```

Add:
```env
API_KEY=your-generated-api-key-here
API_HOST=127.0.0.1
API_PORT=8000
DEBUG=false
DATABASE_URL=sqlite:///../real_estate.db
PHOTO_STORAGE_PATH=/var/www/condosapi/photos
MAX_PHOTO_SIZE_MB=10
CORS_ORIGINS=https://condosapi.mistyrainbow.cloud,https://www.realtor.ca,https://www.condodork.com
```

Generate API key:
```bash
openssl rand -hex 32
```

### Step 7: Install Systemd Service

```bash
sudo cp /var/www/condosapi/api/condosapi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable condosapi
sudo systemctl start condosapi
```

### Step 8: Configure Nginx

```bash
sudo cp /var/www/condosapi/api/nginx-condosapi.conf /etc/nginx/sites-available/condosapi
sudo ln -s /etc/nginx/sites-available/condosapi /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### Step 9: Set Up SSL

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d condosapi.mistyrainbow.cloud
```

## Update Deployment

To update the code after making changes:

```bash
# On server
cd /var/www/condosapi/api
sudo git pull  # If using git

# Or copy new files
sudo cp -r /path/to/new/api/* /var/www/condosapi/api/

# Restart service
sudo systemctl restart condosapi
```

## Monitoring

### Check Service Status

```bash
sudo systemctl status condosapi
```

### View Logs

```bash
# Application logs
sudo journalctl -u condosapi -f

# Nginx access logs
sudo tail -f /var/log/nginx/condosapi.access.log

# Nginx error logs
sudo tail -f /var/log/nginx/condosapi.error.log
```

### Health Check

```bash
curl https://condosapi.mistyrainbow.cloud/health
```

## Backup

### Database

```bash
# Backup SQLite database
sudo cp /var/www/condosapi/real_estate.db /backup/real_estate-$(date +%Y%m%d).db
```

### Photos

```bash
# Backup photos
sudo tar -czf /backup/photos-$(date +%Y%m%d).tar.gz -C /var/www/condosapi photos/
```

## Troubleshooting

### Service Won't Start

```bash
# Check for errors
sudo journalctl -u condosapi --no-pager

# Check permissions
sudo ls -la /var/www/condosapi/

# Try running manually
cd /var/www/condosapi/api
sudo -u www-data .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Database Issues

```bash
# Check database exists
sudo ls -la /var/www/condosapi/real_estate.db

# Check permissions
sudo chown www-data:www-data /var/www/condosapi/real_estate.db
sudo chmod 644 /var/www/condosapi/real_estate.db
```

### Photo Upload Issues

```bash
# Check photo directory permissions
sudo chown -R www-data:www-data /var/www/condosapi/photos
sudo chmod -R 755 /var/www/condosapi/photos
```

### Nginx Issues

```bash
# Test config
sudo nginx -t

# Check nginx error log
sudo tail -f /var/log/nginx/error.log
```

## Security

### Firewall (UFW)

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

### Fail2Ban (Optional)

```bash
sudo apt-get install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### API Key Rotation

To rotate the API key:

```bash
# Generate new key
NEW_KEY=$(openssl rand -hex 32)
echo "New API Key: $NEW_KEY"

# Update .env
sudo sed -i "s/API_KEY=.*/API_KEY=$NEW_KEY/" /var/www/condosapi/api/.env

# Restart service
sudo systemctl restart condosapi
```

## Next Steps

1. **Update Tampermonkey Script**
   - Set `API_URL` to `https://condosapi.mistyrainbow.cloud/api/v1/listings`
   - Set `API_KEY` from your `.env` file

2. **Test with Browser Extension**
   - Navigate to Realtor.ca
   - Click "Track Listing" button
   - Verify data appears in API

3. **Set Up Automated Scraping** (Optional)
   - Install Playwright on server
   - Create cron job for CondoDork scraping

4. **Monitor and Iterate**
   - Check logs regularly
   - Adjust API key if needed
   - Add more buildings to track
