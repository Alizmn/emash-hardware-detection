#!/bin/bash
# Hardware Detection Bootstrap Script
# Pulls latest code from GitHub and runs detection with USB secrets

set -e  # Exit on error

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_FILE_USB="$SCRIPT_DIR/secrets.json"
WORK_DIR="/tmp/hardware_detection"
SECRETS_FILE_WORK="$WORK_DIR/secrets.json"
REPO_URL="https://github.com/Alizmn/emash-hardware-detection"
ZIP_FILE="/tmp/hw_detect.zip"

echo "===================================="
echo "  Hardware Detection Bootstrap"
echo "===================================="
echo ""

# Check secrets on USB
if [ ! -f "$SECRETS_FILE_USB" ]; then
    echo "❌ ERROR: secrets.json not found on USB!"
    echo "   Expected: $SCRIPT_DIR/secrets.json"
    echo ""
    echo "   Create secrets.json from secrets.json.example"
    exit 1
fi

echo "✓ Found secrets.json on USB"
echo ""

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y python3-pip wget unzip >/dev/null 2>&1
echo "✓ System dependencies installed"
echo ""

# Download latest code from GitHub (using ZIP, no git needed)
echo "Downloading latest code from GitHub..."
rm -rf "$WORK_DIR" "$ZIP_FILE"  # Clean previous runs
wget -q --show-progress "$REPO_URL/archive/refs/heads/main.zip" -O "$ZIP_FILE"
echo "✓ Code downloaded"
echo ""

# Extract files
echo "Extracting files..."
unzip -q "$ZIP_FILE" -d /tmp/
mv /tmp/emash-hardware-detection-main "$WORK_DIR"
rm "$ZIP_FILE"
echo "✓ Files extracted to $WORK_DIR"
echo ""

# Copy secrets from USB (read-only) to work directory (writable)
echo "Copying secrets to work directory..."
cp "$SECRETS_FILE_USB" "$SECRETS_FILE_WORK"
echo "✓ Secrets copied"
echo ""

# Install Python dependencies
cd "$WORK_DIR"
echo "Installing Python packages..."
pip3 install --break-system-packages -q -r requirements.txt
echo "✓ Python packages installed"
echo ""

# Run hardware detection with sudo
echo "===================================="
echo "  Starting Hardware Detection"
echo "===================================="
echo ""

sudo -E python3 hardware_detector.py --upload --secrets secrets.json

# Cleanup
echo ""
echo "Cleaning up..."
rm -f "$SECRETS_FILE_WORK"
echo "✓ Secrets removed from temp directory"
echo "✓ USB can now be safely removed"

echo ""
echo "===================================="
echo "  Detection Complete!"
echo "===================================="
