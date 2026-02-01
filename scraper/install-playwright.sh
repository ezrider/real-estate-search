#!/bin/bash
# Install Playwright and dependencies on headless Linux server

set -e

echo "=========================================="
echo "Playwright Installation for Headless Linux"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "Running as root - will install system dependencies"
    IS_ROOT=true
else
    echo "Running as user - skipping system dependencies"
    IS_ROOT=false
fi

# Install system dependencies (requires root)
if [ "$IS_ROOT" = true ]; then
    echo "→ Installing system dependencies..."
    
    # Update package list
    apt-get update
    
    # Install dependencies for Chromium
    apt-get install -y \
        libnss3 \
        libatk-bridge2.0-0 \
        libxss1 \
        libgtk-3-0 \
        libgbm1 \
        libasound2 \
        fonts-liberation \
        libappindicator3-1 \
        xdg-utils \
        wget \
        curl \
        unzip \
        libcurl4 \
        libcurl3-gnutls \
        libcurl3-nss
    
    echo "✓ System dependencies installed"
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found. Please install Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "→ Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "→ Activating virtual environment..."
source .venv/bin/activate

# Install Python dependencies
echo "→ Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers
echo "→ Installing Playwright browsers..."
playwright install chromium

echo ""
echo "=========================================="
echo "✓ Playwright Installation Complete!"
echo "=========================================="
echo ""
echo "To test the installation:"
echo "  source .venv/bin/activate"
echo "  python test_installation.py"
echo ""
echo "To run the scraper:"
echo "  python run_scraper.py --dry-run"
echo ""
