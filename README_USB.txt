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
✓ Uploads to Supabase with Clerk authentication
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
  "supabase_url": "https://your-project.supabase.co",
  "supabase_anon_key": "your-anon-key",
  "clerk_token": "your-clerk-session-token"
}

Get Clerk token from: https://your-app.clerk.com
(User Profile → API Tokens → Generate Long-Lived Token)

TROUBLESHOOTING:
----------------
"secrets.json not found"
  → Create secrets.json on this USB

"Missing required secrets"
  → Check secrets.json has all 3 fields

"Upload failed"
  → Check internet connection
  → Verify Clerk token is valid
  → Script saves to JSON as fallback

"Permission denied"
  → Run with: sudo bash bootstrap.sh

SECURITY:
---------
⚠️  Keep this USB secure - it contains database credentials!
⚠️  Never commit secrets.json to git
⚠️  Regenerate Clerk token if USB is lost

═══════════════════════════════════════════════════════════

EmashCo © 2025
https://emashco.com
