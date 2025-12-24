#!/bin/bash
# PhD Agent VPS Setup Script
# Run this on the VPS after transferring files

set -e

echo "=== PhD Agent VPS Setup ==="

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python and pip
echo "Installing Python..."
sudo apt-get install -y python3 python3-pip python3-venv

# Install dependencies for Playwright
echo "Installing Playwright dependencies..."
sudo apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    libgtk-3-0 \
    xvfb

# Create project directory
echo "Setting up project directory..."
cd /home/ubuntu
mkdir -p phd_agent
cd phd_agent

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install playwright beautifulsoup4 python-dotenv jinja2

# Install Playwright browsers
echo "Installing Playwright Chromium browser..."
playwright install chromium
playwright install-deps chromium

echo "=== Setup Complete ==="
echo "To run the agent:"
echo "  cd /home/ubuntu/phd_agent"
echo "  source venv/bin/activate"
echo "  xvfb-run python3 main.py"
