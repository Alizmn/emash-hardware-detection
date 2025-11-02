# Quick Start Guide - Ubuntu Live USB

## One-Command Setup & Run

### Step 1: Boot Ubuntu Live USB
1. Insert USB into laptop
2. Power on and press boot menu key (F12, F2, Esc, or Del)
3. Select USB drive
4. Choose "Try Ubuntu"

### Step 2: Run the Script
```bash
# Open terminal (Ctrl+Alt+T)
cd /media/cdom
bash setup_and_run.sh
```

**That's it!** The script will:
- ✅ Update apt packages
- ✅ Install python3-pip
- ✅ Install supabase package
- ✅ Run hardware detection
- ✅ Upload to database

### Step 3: Answer Manual Questions

The script will prompt you for:
1. **Screen size** (if not auto-detected) - e.g., 14.0
2. **Keyboard Language** - English/French/Bilingual
3. **Backlit Keyboard** - Yes/No
4. **Convertible/Hybrid** - Yes/No
5. **Main Color** - e.g., Black, Silver
6. **Product Condition** - Brand New/Refurbished/etc.

**Note:** Touchscreen is now auto-detected (no prompt needed!)

---

## What Gets Detected Automatically

✅ **Hardware:**
- Brand, Model, SKU, Serial Number
- CPU: Model, Speed (4.9 GHz max), Cores, Cache
- RAM: Size (24 GB), Type (DDR4), Speed, Slots
- GPU: Clean name (e.g., "Intel UHD Graphics")
- Screen: Resolution, Size, Touchscreen
- Battery: Capacity (mAh)
- Network: WiFi, Bluetooth, Ethernet
- Webcam: Yes/No

✅ **Storage:**
- Filters out USB drives automatically
- Reports actual internal SSD/HDD only

---

## Troubleshooting

**Error: "supabase package not installed"**
```bash
# Install manually:
pip3 install supabase --break-system-packages
```

**Error: "Read-only file system"**
- This is normal on Live USB
- Script doesn't save JSON files in --upload mode
- Data goes directly to Supabase database

**Duplicate detected message:**
```
✅ Found existing model: 723e43e3-...
ℹ️  Skipping model creation (exact match found)
```
- This is correct! The script prevents duplicates
- No new database entries created

---

## After Detection

The data is now in your Supabase database! Next steps:

1. ✅ Check `laptop_models` table - base hardware
2. ✅ Check `laptop_hardware_data` table - all detected specs
3. ✅ Check `laptop_variants` table - RAM/SSD configuration
4. ✅ Check `laptops` table - inventory (count = 0, update manually)

**Manual updates needed:**
- Update `laptops.inventory_count` (how many units you have)
- Update `laptop_models.soldered_ram_gb` (if applicable, e.g., 16)
- Update `laptop_models.removable_ram_slots` (e.g., 1)
- Create additional variants (different RAM/SSD configs)
- Upload product images
- Fill remaining BestBuy fields

---

## Files on USB

- `hardware_detector.py` - Main detection script
- `supabase_uploader.py` - Database upload logic
- `setup_and_run.sh` - This automated setup script
- `requirements.txt` - Python dependencies
- `QUICK_START.md` - This guide
