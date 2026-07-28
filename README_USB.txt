╔════════════════════════════════════════════════════════════╗
║                                                            ║
║          HARDWARE DETECTION USB - QUICK START             ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝

REQUIREMENTS:
-------------
1. Boot laptop from Ubuntu Live USB
2. This USB drive with:
   - bootstrap.sh
   - secrets.json (with your credentials)
3. Internet connection

USAGE:
------
1. Boot target laptop from Ubuntu Live USB
2. Connect to internet (WiFi or Ethernet)
3. Insert this USB drive
4. Open terminal
5. cd /media/ubuntu/YOUR_USB_NAME
6. bash bootstrap.sh
7. Follow the prompts

WHAT IT DOES:
-------------
✓ Pulls latest detection code from GitHub
✓ Installs Python dependencies
✓ Detects all laptop hardware
✓ Asks 6 manual questions (color, keyboard, condition, etc.)
✓ Uploads to the EmashCo API (model + variant + inventory in one step)
✓ Cleans up secrets after upload

FILES ON THIS USB:
------------------
• bootstrap.sh       - Main script (pulls code and runs)
• secrets.json       - Your credentials (KEEP SECURE!)
• README_USB.txt     - This file

SECRETS SETUP:
--------------
Your secrets.json must contain:

{
  "api_url": "https://bbapi.anew-tech.com",
  "api_key": "your-intake-api-key"
}

Get the intake API key from your administrator.

⚠️  UPGRADING AN OLD USB STICK:
   Older sticks have a secrets.json with "supabase_url" and
   "supabase_anon_key". Those NO LONGER WORK - the platform moved off
   Supabase. Replace secrets.json with the two fields above. Nothing else
   on the stick needs to change.

TROUBLESHOOTING:
----------------
"secrets.json not found"
  → Create secrets.json on this USB

"This USB stick still has the OLD Supabase credentials"
  → Replace secrets.json with the new api_url/api_key version (see above)

"Missing required secrets"
  → Check secrets.json has both api_url and api_key

"Rejected (401)"
  → The api_key is wrong or was rotated - get a new one from your admin

"Rejected (503)"
  → Intake is not configured on the server - contact your admin

"Could not reach ..." / "Timed out"
  → Check internet connection; verify api_url is correct
  → Detection results are saved to JSON as a fallback — but in /tmp, which is
    WIPED by a reboot and by the next bootstrap.sh run. Copy the file onto
    the USB stick before rebooting or re-scanning.

"Permission denied"
  → Run with: sudo bash bootstrap.sh

SECURITY:
---------
⚠️  Keep this USB secure - the api_key can create catalog entries!
⚠️  Never commit secrets.json to git
⚠️  Ask your admin to rotate the api_key if the USB is lost

═══════════════════════════════════════════════════════════

EmashCo © 2025
https://emashco.com
