#!/bin/bash
# Automated Setup and Run Script for Ubuntu Live USB
# Hardware Detection for BestBuy Marketplace

set -e  # Exit on any error

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║     Laptop Hardware Detector - Auto Setup & Upload        ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Update package list
echo "📦 Step 1/4: Updating package list..."
sudo apt update -qq

# Step 2: Install pip3 if not already installed
echo "📦 Step 2/4: Installing python3-pip..."
if ! command -v pip3 &> /dev/null; then
    sudo apt install python3-pip -y -qq
    echo "   ✅ pip3 installed"
else
    echo "   ✅ pip3 already installed (skipping)"
fi

# Step 3: Install supabase package
echo "📦 Step 3/4: Installing supabase Python package..."
if ! python3 -c "import supabase" 2>/dev/null; then
    pip3 install supabase --break-system-packages -q
    echo "   ✅ supabase package installed"
else
    echo "   ✅ supabase already installed (skipping)"
fi

# Step 4: Run hardware detector
echo "🚀 Step 4/4: Running hardware detector..."
echo ""

python3 hardware_detector.py --upload

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║                    ✅ All Done!                            ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
