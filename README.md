# emash-hardware-detection

Automated hardware detection tool for laptops that extracts specifications and uploads them to the EmashCo API. Designed to run from a Linux Live USB environment on bare laptops.

## Features

- **No OS/Storage Required** - Runs on Linux Live USB, laptop can be completely blank
- **Automated Detection** - Uses Linux commands to detect 90%+ of hardware specs
- **BestBuy Field Mapping** - Maps detected specs to BestBuy marketplace format
- **Secure Deployment** - Code from GitHub, secrets on USB only
- **API Upload** - Posts to the EmashCo intake endpoint with a scoped API key
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
Uploads to the EmashCo API (one atomic create)
```

## Prerequisites

### Hardware
- USB drive (8GB+ recommended for persistence)
- Target laptop (no OS/storage needed)

### Software
- Ubuntu Live USB (22.04+ recommended)
- Internet connection (to pull code and upload data)

### Credentials
- EmashCo API URL (e.g. `https://bbapi.anew-tech.com`)
- Intake API key (ask your administrator)

## Quick Start (USB Deployment)

### 1. Create secrets.json on USB

Copy `secrets.json.example` to `secrets.json` and fill in your credentials:

```json
{
  "api_key": "your-intake-api-key-here"
}
```

The backend URL is compiled into the tool (`DEFAULT_API_URL`), so it is not part
of `secrets.json`. Add an `api_url` entry only to point at staging or a local
server.

**Getting your intake API key:** ask your administrator. It is a shared secret
scoped to a single capability — creating a laptop model from a hardware dump. It
cannot read, edit or delete anything.

> **Existing USB sticks need no changes.** Sticks created before the PostgreSQL
> migration have `supabase_url` / `supabase_anon_key` in `secrets.json`. The same
> secret was re-issued as the intake key, so the tool reads the key from either
> entry and the URL is built in. Those sticks keep working untouched; the tool
> prints a one-line notice suggesting an update when convenient.

**Security:** Keep your USB drive secure - the api_key can create catalog entries!

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
- Upload to the EmashCo API
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
git clone https://github.com/Alizmn/emash-hardware-detection.git
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

## What the upload creates

A single `POST /api/v2/intake/model` call. The API writes all five tables in one
atomic transaction (nothing half-created if a step fails) and deduplicates on the
model configuration, so re-scanning the same laptop never creates a duplicate:

1. **laptop_models** - Base hardware configuration
2. **laptop_hardware_data** - Detailed specs + raw detection JSON
3. **laptop_variants** - RAM/SSD configurations with generated SKU
4. **laptops** - Inventory tracking (initialized to 0)
5. **laptop_manual_fields** - Visually-verified fields

## Security

- ✅ No secrets in repository (public repo safe)
- ✅ Secrets only on physical USB drive
- ✅ No database credentials anywhere - the tool only holds a scoped API key
- ✅ The key grants one capability (create a model); it cannot read, edit or delete
- ✅ Code pulled fresh from GitHub on each use
- ✅ Secrets cleaned from temp directory after use

## Troubleshooting

### "secrets.json not found"
Create `secrets.json` on your USB drive from the example template.

### "Missing required secrets"
Ensure secrets.json has an `api_key` entry (or the older `supabase_anon_key`)

### "Rejected (401)"
The `api_key` is wrong or was rotated. Get a fresh one from your administrator.

### "Rejected (503)"
Intake is not configured on the server. Contact your administrator.

### "Could not reach ..." / "Timed out"
- Check internet connection
- Verify `api_url` in secrets.json is correct
- Script will save to JSON as fallback, but it lands in /tmp (wiped by reboot and
  by the next bootstrap.sh run) — copy it onto the USB stick before re-running

### "Permission denied"
Run with sudo: `sudo bash bootstrap.sh`

## Development

### Project Structure

```
emash-hardware-detection/
├── hardware_detector.py              # Main detection logic
├── api_uploader.py                   # EmashCo API upload client
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
