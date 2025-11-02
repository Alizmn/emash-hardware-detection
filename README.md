# emash-hardware-detection

Automated hardware detection tool for laptops that extracts specifications and uploads to Supabase database. Designed to run from a Linux Live USB environment on bare laptops.

## Features

- **No OS/Storage Required** - Runs on Linux Live USB, laptop can be completely blank
- **Automated Detection** - Uses Linux commands to detect 90%+ of hardware specs
- **BestBuy Field Mapping** - Maps detected specs to BestBuy marketplace format
- **Secure Deployment** - Code from GitHub, secrets on USB only
- **Clerk Authentication** - Uploads with authenticated Clerk token
- **Minimal Manual Input** - Only 6 visual confirmation questions

## How It Works

```
USB Drive (secrets.json + bootstrap.sh)
  ↓
Boot Linux Live USB
  ↓
Script pulls latest code from GitHub
  ↓
Runs detection (dmidecode, lscpu, lspci, etc.)
  ↓
Maps to BestBuy fields
  ↓
Uploads to Supabase with Clerk authentication
```

## Prerequisites

### Hardware
- USB drive (8GB+ recommended for persistence)
- Target laptop (no OS/storage needed)

### Software
- Ubuntu Live USB (22.04+ recommended)
- Internet connection (to pull code and upload data)

### Credentials
- Supabase project URL
- Supabase service role key (from Dashboard → Settings → API)

## Quick Start (USB Deployment)

### 1. Create secrets.json on USB

Copy `secrets.json.example` to `secrets.json` and fill in your credentials:

```json
{
  "supabase_url": "https://qazzzqcgmsqqrqsmtipr.supabase.co",
  "supabase_anon_key": "your-supabase-service-role-key-here"
}
```

**Getting your Supabase Service Role Key:**
1. Go to Supabase Dashboard → Settings → API
2. Copy the **service_role** key (NOT the anon key)
3. Paste into secrets.json

**Important:** The service role key bypasses Row Level Security (RLS). This is necessary because:
- Python Supabase SDK doesn't support custom headers like JavaScript SDK
- Hardware detection runs standalone (no user session)
- USB is physically secured (equivalent to having credentials on your computer)

**Security:** Keep your USB drive secure - the service role key has full database access!

### 2. Copy bootstrap.sh to USB

The bootstrap script is in this repository. Copy it to your USB drive alongside secrets.json.

### 3. Boot Target Laptop

1. Boot laptop from Ubuntu Live USB
2. Connect to internet (WiFi or Ethernet)
3. Insert your USB drive with secrets

### 4. Run Detection

```bash
# Mount your USB drive (usually auto-mounted)
cd /media/ubuntu/YOUR_USB_NAME

# Run bootstrap script
bash bootstrap.sh
```

The script will:
- Pull latest detection code from GitHub
- Install Python dependencies
- Run hardware detection
- Upload to Supabase with authentication
- Clean up secrets from temp directory

## USB Structure

Your USB drive should contain:

```
USB:/
├── bootstrap.sh           # Bootstrap script (from this repo)
├── secrets.json          # Your credentials (NEVER commit to git)
└── README_USB.txt        # Quick reference (optional)
```

## Manual Installation (Development)

If you want to run the script directly without bootstrap:

```bash
# Clone repository
git clone https://github.com/EmashCo/emash-hardware-detection.git
cd emash-hardware-detection

# Install dependencies
pip3 install -r requirements.txt

# Create secrets file
cp secrets.json.example secrets.json
# Edit secrets.json with your credentials

# Run detection
sudo python3 hardware_detector.py

# Run detection with upload
sudo python3 hardware_detector.py --upload --secrets secrets.json
```

## What Gets Detected

### Automatically Detected (90%+ accuracy)
- **System**: Brand, Model, Serial Number, SKU
- **CPU**: Model, Speed, Cores, Cache
- **Memory**: Size, Type (DDR4/DDR5), Speed, Slots, Form Factor
- **Storage**: SSD/HDD capacity, type, controller
- **Display**: Size (inches), Resolution, Touchscreen detection
- **Graphics**: GPU model, Integrated vs Dedicated
- **Battery**: Capacity (mAh)
- **Network**: WiFi, Bluetooth, Ethernet
- **Peripherals**: Webcam, USB ports

### Manual Input Required (6 fields)
- Keyboard Language (English/French/etc.)
- Backlit Keyboard (Yes/No)
- Convertible/Hybrid (Yes/No)
- Color
- Product Condition (New/Refurbished/Used)

## Database Schema

Uploads to 5 Supabase tables:

1. **laptop_models** - Base hardware configuration
2. **laptop_hardware_data** - Detailed specs + raw detection JSON
3. **laptop_variants** - RAM/SSD configurations with generated SKU
4. **laptops** - Inventory tracking (initialized to 0)
5. **laptop_manual_fields** - Visually-verified fields

## Security

- ✅ No secrets in repository (public repo safe)
- ✅ Secrets only on physical USB drive
- ✅ Clerk JWT authentication for database access
- ✅ Code pulled fresh from GitHub on each use
- ✅ Secrets cleaned from temp directory after use

## Troubleshooting

### "secrets.json not found"
Create `secrets.json` on your USB drive from the example template.

### "Missing required secrets"
Ensure secrets.json has both required fields: supabase_url, supabase_anon_key

### "Upload failed"
- Check internet connection
- Verify Supabase service role key is correct
- Check Supabase URL is correct
- Script will save to JSON as fallback

### "Permission denied"
Run with sudo: `sudo bash bootstrap.sh`

## Development

### Project Structure

```
emash-hardware-detection/
├── hardware_detector.py              # Main detection logic
├── supabase_uploader.py              # Database upload functions
├── bestbuy_fields.json               # BestBuy field definitions
├── bestbuy_fields_categorized.json   # Categorized field mapping
├── bootstrap.sh                      # USB bootstrap script
├── setup_and_run.sh                  # Legacy setup script
├── requirements.txt                  # Python dependencies
├── secrets.json.example              # Template for credentials
├── .gitignore                        # Excludes secrets and output
├── LICENSE                           # EmashCo proprietary license
├── README.md                         # This file
└── QUICK_START.md                    # Quick reference guide
```

### Updating the Code

When you push changes to GitHub, all USBs automatically get the latest version on next run (no need to update USB files).

## License

Copyright (c) 2025 EmashCo. All Rights Reserved.

This software is proprietary and confidential. Unauthorized copying, modification, or distribution is strictly prohibited.

For licensing inquiries, contact: ali.zamani@emashco.com

## Contact

**EmashCo**
- Website: https://emashco.com
- Email: ali.zamani@emashco.com
