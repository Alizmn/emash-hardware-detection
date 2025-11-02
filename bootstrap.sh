#!/bin/bash
# Hardware Detection Bootstrap Script
# Pulls latest code from GitHub and runs detection with USB secrets

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_FILE="$SCRIPT_DIR/secrets.json"
REPO_URL="https://github.com/EmashCo/emash-hardware-detection.git"
WORK_DIR="/tmp/hardware_detection"

echo "===================================="
echo "  Hardware Detection Bootstrap"
echo "===================================="
echo ""

# Check if secrets file exists
if [ ! -f "$SECRETS_FILE" ]; then
    echo "ERROR: secrets.json not found on USB!"
    echo "Please create secrets.json from secrets.json.example"
    exit 1
fi

echo "✓ Found secrets.json"
echo ""

# Update system packages
echo "Updating system packages..."
sudo apt-get update -qq

# Install required system packages
echo "Installing dependencies..."
sudo apt-get install -y python3-pip git >/dev/null 2>&1

echo "✓ System dependencies installed"
echo ""

# Clone or update repository
if [ -d "$WORK_DIR" ]; then
    echo "Updating existing repository..."
    cd "$WORK_DIR"
    git pull origin main
else
    echo "Cloning repository from GitHub..."
    git clone "$REPO_URL" "$WORK_DIR"
    cd "$WORK_DIR"
fi

echo "✓ Latest code pulled from GitHub"
echo ""

# Install Python dependencies
echo "Installing Python packages..."
pip3 install -q -r requirements.txt

echo "✓ Python dependencies installed"
echo ""

# Copy secrets to work directory
cp "$SECRETS_FILE" "$WORK_DIR/secrets.json"

# Run hardware detection
echo "===================================="
echo "  Starting Hardware Detection"
echo "===================================="
echo ""

python3 hardware_detector.py --upload --secrets secrets.json

# Cleanup secrets from temp directory
rm -f "$WORK_DIR/secrets.json"

echo ""
echo "===================================="
echo "  Detection Complete!"
echo "===================================="
