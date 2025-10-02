#!/usr/bin/env python3
"""
HCO-Phone-Finder.py
Single-file Termux/Linux tool + small Flask server for ethically asking a finder to
voluntarily share location to help return a lost phone.

Features:
 - Termux lock UI on start: "Tool is locked 🔒", subscribe message, countdown 9..1
 - Attempts to open YouTube app on Android via `am start -d` (Termux) or fallback to web
 - After pressing Enter reveals the main menu (green title inside red background using ANSI)
 - Option to print public link, print QR in terminal, or start Flask server
 - Flask public page is transparent: shows owner contact, reward message (optional),
   and a "Share my location" button that requires explicit browser permission.
 - Reports saved to reports.csv and printed to console
 - Admin page `/admin?key=ACCESS_KEY` to download reports.csv

USAGE:
  Termux:
    pkg update -y
    pkg install -y python
    pip install --upgrade pip
    pip install flask qrcode pillow

  Linux (Debian/Ubuntu):
    sudo apt update
    sudo apt install -y python3 python3-pip
    pip3 install flask qrcode pillow

  ENV (recommended):
    export ACCESS_KEY="change_this_to_a_strong_key"
    export OWNER_NAME="Azhar"
    export OWNER_CONTACT="+91-XXXXXXXXXX"
    export PUBLIC_URL=""   # set AFTER you get tunnel URL (cloudflared/ngrok)
    export YT_CHANNEL_ID=""  # optional if you want deep link by channel id
    export YOUTUBE_URL="https://www.youtube.com/@hackers_colony_tech"

  Run:
    python3 HCO-Phone-Finder.py

LEGAL / ETHICAL:
 - Do NOT use deception to obtain consent. The public page explicitly states purpose and asks for permission.
"""

from __future__ import annotations
import os, sys, time, csv, io, base64, argparse, threading, json, datetime, subprocess, platform
from typing import Optional

# Optional imports for server and QR
try:
    from flask import Flask, request, render_template_string, send_file, abort
    import qrcode
    from PIL import Image
except Exception as e:
    # We'll check later and inform user if Flask/qrcode missing
    Flask = None
    qrcode = None
    Image = None

# ---------------- Config ----------------
ACCESS_KEY = os.environ.get("ACCESS_KEY", "changeme_change_this_key")
OWNER_NAME = os.environ.get("OWNER_NAME", "Azhar")
OWNER_CONTACT = os.environ.get("OWNER_CONTACT", "+91-XXXXXXXXXX")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "")  # set after you run a tunnel
YT_CHANNEL_ID = os.environ.get("YT_CHANNEL_ID", "")
YOUTUBE_URL = os.environ.get("YOUTUBE_URL", "https://www.youtube.com")
LOGFILE = "reports.csv"
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "5000"))
# ----------------------------------------

# Ensure reports CSV header
if not os.path.exists(LOGFILE):
    with open(LOGFILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_utc","ip","user_agent","latitude","longitude","accuracy","client_ts_ms","notes"])

# ---------------- Terminal Helpers ----------------
def supports_utf8() -> bool:
    try:
        return "UTF-8" in (sys.stdout.encoding or "UTF-8")
    except Exception:
        return True

# ANSI color helpers
def ansi(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"

def red_bg_green_text_block(title_lines: list[str]) -> None:
    """Print a red background with green text (no ASCII art)."""
    # Background red -> 41, green text -> 32, bold -> 1
    for line in title_lines:
        print("\033[41m\033[1;32m " + line + " \033[0m")

# Print QR to terminal using block characters
def print_qr_terminal(data: str) -> None:
    # Fallback if qrcode not available: print URL
    if qrcode is None:
        print("qrcode library not installed. Install with: pip install qrcode[pil]")
        print("Link:", data)
        return
    qr = qrcode.QRCode(border=1)
    qr.add_data(data)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    # Use ANSI blocks for better visibility
    black = "\033[40m  \033[0m"  # black background double space
    white = "\033[47m  \033[0m"  # white background double space
    # Surround with white border for scanner readability in many terminals
    border = 2
    w = len(matrix[0]) + border*2
    # top border
    for _ in range(border):
        print(white * w)
    for row in matrix:
        line = white * border
        for col in row:
            line += black if col else white
        line += white * border
        print(line)
    for _ in range(border):
        print(white * w)

# Try to open YouTube app on Android (Termux) using am start; fallback to webbrowser
def open_youtube_app():
    # Prefer deep link if channel id provided
    app_link = None
    if YT_CHANNEL_ID:
        app_link = f"vnd.youtube://channel/{YT_CHANNEL_ID}"
    else:
        # try open channel/user url if provided as YOUTUBE_URL
        app_link = None
    # If on Android (Termux) try am start
    if platform.system().lower() == "linux" and os.path.exists("/system/bin") or "ANDROID_ROOT" in os.environ:
        # Termux on Android environment
        try:
            if app_link:
                # Use am to open deep link (may open app)
                subprocess.run(['am', 'start', '-a', 'android.intent.action.VIEW', '-d', app_link], check=False)
                time.sleep(0.8)
                # fallback to web URL
                subprocess.run(['am', 'start', '-a', 'android.intent.action.VIEW', '-d', YOUTUBE_URL], check=False)
                return
            else:
                subprocess.run(['am', 'start', '-a', 'android.intent.action.VIEW', '-d', YOUTUBE_URL], check=False)
                return
        except Exception:
            pass
    # generic fallback: open in default browser
    try:
        import webbrowser
        webbrowser.open(YOUTUBE_URL)
    except Exception:
        print("Open this URL in your device's browser or YouTube app:", YOUTUBE_URL)

# ---------------- Termux Lock Flow ----------------
def termux_lock_flow():
    # Clear screen
    os.system('clear' if os.name == 'posix' else 'cls')
    print(ansi("Tool is Locked 🔒", "1;31"))  # bold red
    print()
    print("Redirecting to YouTube — please subscribe and click the 🔔 bell icon to unlock.")
    print()
    # Countdown 9..1
    for i in range(9, 0, -1):
        print(ansi(str(i), "1;33"), end=" ", flush=True)  # bold yellow
        time.sleep(1)
    print("\n")
    print(ansi("Opening YouTube app...", "1;34"))  # bold cyan
    # open youtube (attempt app on Android)
    open_youtube_app()
    # Wait for user to return & press Enter
    input(ansi("\nAfter subscribing/visiting YouTube, return here and press Enter to continue...", "1;37"))

# ---------------- Server (Flask) ----------------
def ensure_flask_available():
    if Flask is None:
        print("Flask and qrcode must be installed to start server.")
        print("Install with: pip install flask qrcode pillow")
        return False
    return True

PUBLIC_PAGE_HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Found a phone — Help return</title>
<style>
  body{font-family:system-ui, -apple-system, Roboto, Arial; background:#07111a;color:#e6f6ff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
  .card{background:#06121a;padding:20px;border-radius:12px;max-width:720px;width:92%}
  h1{color:#00ff66;margin:0 0 6px 0}
  .redbox{background:#ffecec;border:3px solid #d93025;padding:10px;border-radius:8px;display:inline-block}
  p{color:#cfe9f6}
  .btn{background:#0b84ff;color:white;padding:10px 14px;border-radius:8px;border:none;font-weight:700;cursor:pointer}
  .small{color:#98b2c2;font-size:13px}
</style>
</head>
<body>
  <div class="card">
    <div class="redbox">
      <h1>HCO Phone Finder</h1>
      <div style="color:#007a2e;font-weight:700">A Lost or Stolen Phone Tracker by {{owner}}</div>
    </div>
    <p style="margin-top:12px">This device is lost. The owner ({{owner_contact}}) offers a reward to return it.</p>
    <p class="small">To help return the phone, you can voluntarily share this device’s current location with the owner. No other personal information will be collected.</p>
    <div style="margin-top:12px">
      <button id="shareBtn" class="btn">Share my location</button>
    </div>
    <div id="status" style="margin-top:10px;color:#b4eec2"></div>
    <p style="margin-top:12px" class="small">If you prefer, call the owner directly using the number above.</p>
  </div>
<script>
const shareBtn = document.getElementById('shareBtn');
const status = document.getElementById('status');
shareBtn.addEventListener('click', () => {
  if (!navigator.geolocation) { status.textContent = "Geolocation not supported by your browser."; return; }
  shareBtn.disabled = true;
  shareBtn.textContent = 'Requesting location...';
  navigator.geolocation.getCurrentPosition(async (pos) => {
    try {
      const payload = { latitude: pos.coords.latitude, longitude: pos.coords.longitude, accuracy: pos.coords.accuracy, timestamp: pos.timestamp };
      const res = await fetch('/report', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      if (res.ok) {
        status.textContent = "Thanks — location shared with the owner.";
        shareBtn.textContent = 'Shared';
      } else {
        status.textContent = "Failed to send location.";
        shareBtn.disabled = false;
        shareBtn.textContent = 'Share my location';
      }
    } catch (e) {
      status.textContent = "Network error while sending location.";
      shareBtn.disabled = false;
      shareBtn.textContent = 'Share my location';
    }
  }, (err) => {
    status.textContent = "Could not get location: " + (err.message || 'permission denied');
    shareBtn.disabled = false;
    shareBtn.textContent = 'Share my location';
  }, { enableHighAccuracy:true, timeout:15000 });
});
</script>
</body>
</html>
"""

# Flask app setup (created only if modules available)
def start_flask_server(host=HOST, port=PORT):
    if not ensure_flask_available():
        return
    app = Flask(__name__)

    @app.route("/")
    def index():
        # PUBLIC_URL not required for page
        return render_template_string(PUBLIC_PAGE_HTML, owner=OWNER_NAME, owner_contact=OWNER_CONTACT)

    @app.route("/report", methods=["POST"])
    def report():
        try:
            data = request.get_json(force=True)
        except Exception:
            return ("Invalid JSON", 400)
        lat = data.get("latitude") or data.get("lat")
        lon = data.get("longitude") or data.get("lon")
        acc = data.get("accuracy") or data.get("acc")
        cts = data.get("timestamp") or ""
        try:
            latf = float(lat)
            lonf = float(lon)
        except Exception:
            return ("Invalid coordinates", 400)
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        ua = request.headers.get('User-Agent', '')
        ts = datetime.datetime.utcnow().isoformat() + "Z"
        with open(LOGFILE, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([ts, ip, ua, latf, lonf, acc, cts, "voluntary_share"])
        print(f"[{ts}] REPORT from {ip} UA:{ua} lat={latf} lon={lonf} acc={acc} client_ts={cts}")
        return ("OK", 200)

    @app.route("/admin")
    def admin():
        key = request.args.get("key","")
        if key != ACCESS_KEY:
            return abort(401, "Unauthorized")
        # show simple listing and link to download
        rows = []
        with open(LOGFILE, "r", encoding="utf-8", newline="") as f:
            r = csv.reader(f)
            next(r, None)
            for row in r:
                rows.append(row)
        # tiny HTML
        out = "<html><body><h2>Reports</h2><p><a href='/'>Public page</a> | <a href='/download?key={k}'>Download CSV</a></p><table border=1 cellpadding=6><tr><th>UTC</th><th>IP</th><th>UA</th><th>Lat</th><th>Lon</th><th>Acc</th></tr>".format(k=ACCESS_KEY)
        for r in reversed(rows):
            out += "<tr>" + "".join(f"<td>{x}</td>" for x in r[:6]) + "</tr>"
        out += "</table></body></html>"
        return out

    @app.route("/download")
    def download():
        key = request.args.get("key","")
        if key != ACCESS_KEY:
            return abort(401, "Unauthorized")
        return send_file(LOGFILE, as_attachment=True, download_name="reports.csv")

    # Start Flask server (blocking)
    print(f"Starting Flask server on http://{host}:{port}  — public page will ask finder to voluntarily share location.")
    app.run(host=host, port=port)

# ---------------- Main Interaction ----------------
def main():
    # Termux lock flow
    termux_lock_flow()
    # After unlock show title in green inside red box (no ascii)
    title_lines = ["HCO PHONE FINDER", f"A Lost or Stolen Phone Tracker by {OWNER_NAME}"]
    print()
    red_bg_green_text_block(title_lines)
    print()
    # menu loop
    while True:
        print("\nOptions:")
        print("1) Print public link")
        print("2) Print QR in terminal")
        print("3) Start Flask server (public page & report endpoint)")
        print("4) Exit")
        choice = input("\nChoose option (1-4): ").strip()
        if choice == "1":
            if PUBLIC_URL:
                print("\nPublic link (share this with finder or put on lock-screen):\n")
                print(ansi(PUBLIC_URL, "1;36"))
            else:
                print("\nPUBLIC_URL is not set. Start your tunnel (cloudflared/ngrok) and then set PUBLIC_URL env var.")
        elif choice == "2":
            if PUBLIC_URL:
                print("\nQR code (scan with device camera):\n")
                print_qr_terminal(PUBLIC_URL)
            else:
                print("\nPUBLIC_URL not set. Start tunnel and set PUBLIC_URL to generate QR.")
        elif choice == "3":
            # Start server in same process (blocking) — run in separate thread so menu remains responsive if desired
            print("\nStarting server (Ctrl-C to stop)...\n")
            start_flask_server(HOST, PORT)
            # when server stops, loop returns
        elif choice == "4":
            print("Exiting.")
            sys.exit(0)
        else:
            print("Invalid choice. Pick 1-4.")

if __name__ == "__main__":
    main()
