#!/usr/bin/env python3
"""
HCO-Phone-Finder.py
Single-file Termux/Linux tool + small Flask server for ethically asking a finder to
voluntarily share location to help return a lost phone.

Features:
 - Auto-load ~/.hco_phone_finder_env (if present)
 - Auto-detect PUBLIC_URL (env, ~/.hco_public_url, ngrok local API), or prompt to paste and save
 - Termux lock UI with YouTube redirect and 9..1 countdown
 - Flask server public page with clickable public link + "Share my location" button
 - Reports saved to reports.csv and admin page /admin?key=ACCESS_KEY
"""

from __future__ import annotations
import os, sys, time, csv, datetime, subprocess, platform

# ---------------- AUTO-LOAD ENV FILE ----------------
home = os.path.expanduser("~")
env_file = os.path.join(home, ".hco_phone_finder_env")
if os.path.exists(env_file):
    try:
        print(f"Loading environment variables from {env_file} ...")
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    # allow lines like export VAR="value"
                    if key.startswith("export "):
                        key = key.split(" ", 1)[1]
                    os.environ[key] = val
    except Exception:
        pass

# ---------------- Optional modules ----------------
try:
    from flask import Flask, request, render_template_string, send_file, abort
    import qrcode
    from PIL import Image
    import requests
except Exception:
    # If any import fails, set to None and check before starting server
    try:
        # minimize NameError risk
        Flask
    except NameError:
        Flask = None
    qrcode = None
    Image = None
    try:
        requests
    except NameError:
        requests = None

# ---------------- Config ----------------
ACCESS_KEY = os.environ.get("ACCESS_KEY", "changeme_change_this_key")
OWNER_NAME = os.environ.get("OWNER_NAME", "Azhar")
OWNER_CONTACT = os.environ.get("OWNER_CONTACT", "+91-XXXXXXXXXX")
YT_CHANNEL_ID = os.environ.get("YT_CHANNEL_ID", "")
YOUTUBE_URL = os.environ.get("YOUTUBE_URL", "https://www.youtube.com/@hackers_colony_tech")
LOGFILE = "reports.csv"
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "5000"))

# ---------------- PUBLIC_URL DETECTION ----------------
def detect_public_url():
    # 1) env var
    env_url = os.environ.get("PUBLIC_URL", "").strip()
    if env_url:
        return env_url.rstrip("/")

    # 2) saved file
    saved_path = os.path.join(home, ".hco_public_url")
    try:
        if os.path.exists(saved_path):
            with open(saved_path, "r", encoding="utf-8") as f:
                url = f.read().strip()
                if url:
                    return url.rstrip("/")
    except Exception:
        pass

    # 3) try ngrok API
    if requests is not None:
        try:
            resp = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=1.2)
            if resp.ok:
                data = resp.json()
                tunnels = data.get("tunnels") or []
                # prefer https tunnels
                for t in tunnels:
                    pu = t.get("public_url")
                    if pu:
                        return pu.rstrip("/")
        except Exception:
            pass

    # 4) prompt user once and offer to save
    try:
        url = input("\nPUBLIC_URL not found. Start your tunnel (cloudflared/ngrok) and paste the public URL here (or leave blank to skip): ").strip()
        if not url:
            return ""
        url = url.rstrip("/")
        save = input("Save this URL to ~/.hco_public_url for future runs? (Y/n): ").strip().lower()
        if save in ("", "y", "yes"):
            try:
                with open(saved_path, "w", encoding="utf-8") as f:
                    f.write(url)
                print(f"Saved public URL to {saved_path}")
            except Exception:
                pass
        return url
    except Exception:
        return ""

PUBLIC_URL = detect_public_url()

# ---------------- CSV Setup ----------------
if not os.path.exists(LOGFILE):
    try:
        with open(LOGFILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp_utc","ip","user_agent","latitude","longitude","accuracy","client_ts_ms","notes"])
    except Exception:
        pass

# ---------------- Terminal Helpers ----------------
def ansi(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"

def red_bg_green_text_block(title_lines: list[str]) -> None:
    for line in title_lines:
        print("\033[41m\033[1;32m " + line + " \033[0m")

def print_qr_terminal(data: str) -> None:
    if not data:
        print("No data to generate QR.")
        return
    if qrcode is None:
        print("qrcode library not installed. Install with: pip install qrcode[pil]")
        print("Link:", data)
        return
    try:
        qr = qrcode.QRCode(border=1)
        qr.add_data(data)
        qr.make(fit=True)
        matrix = qr.get_matrix()
        black = "\033[40m  \033[0m"
        white = "\033[47m  \033[0m"
        border = 2
        w = len(matrix[0]) + border*2
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
    except Exception as e:
        print("Failed to render QR:", e)
        print("Link:", data)

# ---------------- YouTube Launch ----------------
def open_youtube_app():
    app_link = f"vnd.youtube://channel/{YT_CHANNEL_ID}" if YT_CHANNEL_ID else None
    try:
        if platform.system().lower() == "linux" and (os.path.exists("/system/bin") or "ANDROID_ROOT" in os.environ):
            if app_link:
                subprocess.run(['am', 'start', '-a', 'android.intent.action.VIEW', '-d', app_link], check=False)
                time.sleep(0.8)
            subprocess.run(['am', 'start', '-a', 'android.intent.action.VIEW', '-d', YOUTUBE_URL], check=False)
            return
    except Exception:
        pass
    try:
        import webbrowser
        webbrowser.open(YOUTUBE_URL)
    except Exception:
        print("Open this URL in your browser or YouTube app:", YOUTUBE_URL)

# ---------------- Termux Lock Flow ----------------
def termux_lock_flow():
    os.system('clear' if os.name == 'posix' else 'cls')
    print(ansi("Tool is Locked 🔒", "1;31"))
    print("\nRedirecting to YouTube — please subscribe and click the 🔔 bell icon to unlock.\n")
    for i in range(9, 0, -1):
        print(ansi(str(i), "1;33"), end=" ", flush=True)
        time.sleep(1)
    print("\n" + ansi("Opening YouTube app...", "1;34"))
    open_youtube_app()
    input(ansi("\nAfter subscribing/visiting YouTube, press Enter to continue...", "1;37"))

# ---------------- Flask Public Page (template) ----------------
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
  a.link{color:#0b84ff; text-decoration:underline; word-break:break-all;}
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
    <p class="small">Or open this link directly in your browser: <a href="{{public_url}}" class="link" target="_blank">{{public_url}}</a></p>
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

# ---------------- Flask helpers & server ----------------
def ensure_flask_available():
    if Flask is None:
        print("Flask/qrcode/requests not installed. Install with: pip install flask qrcode pillow requests")
        return False
    return True

def start_flask_server(host=HOST, port=PORT):
    if not ensure_flask_available():
        return
    app = Flask(__name__)

    @app.route("/")
    def index():
        html = PUBLIC_PAGE_HTML
        html = html.replace("{{owner}}", OWNER_NAME)
        html = html.replace("{{owner_contact}}", OWNER_CONTACT)
        html = html.replace("{{public_url}}", PUBLIC_URL or "")
        return render_template_string(html)

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
        try:
            with open(LOGFILE, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow([ts, ip, ua, latf, lonf, acc, cts, "voluntary_share"])
        except Exception:
            pass
        print(f"[{ts}] REPORT from {ip} UA:{ua} lat={latf} lon={lonf} acc={acc} client_ts={cts}")
        return ("OK", 200)

    @app.route("/admin")
    def admin():
        key = request.args.get("key","")
        if key != ACCESS_KEY:
            return abort(401, "Unauthorized")
        rows = []
        try:
            with open(LOGFILE, "r", encoding="utf-8", newline="") as f:
                r = csv.reader(f)
                next(r, None)
                for row in r:
                    rows.append(row)
        except Exception:
            pass
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
        try:
            return send_file(LOGFILE, as_attachment=True, download_name="reports.csv")
        except Exception:
            return abort(500, "Unable to read reports file")

    print(f"Starting Flask server on http://{host}:{port} ...")
    app.run(host=host, port=port)

# ---------------- Main interaction ----------------
def main():
    termux_lock_flow()
    title_lines = ["HCO PHONE FINDER", f"A Lost or Stolen Phone Tracker by {OWNER_NAME}"]
    print()
    red_bg_green_text_block(title_lines)
    print()
    while True:
        print("\nOptions:")
        print("1) Print public link")
        print("2) Print QR in terminal")
        print("3) Start Flask server (public page & report endpoint)")
        print("4) Exit")
        choice = input("\nChoose option (1-4): ").strip()
        if choice == "1":
            if PUBLIC_URL:
                print("\nPublic link:\n")
                print(ansi(PUBLIC_URL, "1;36"))
            else:
                print("\nPUBLIC_URL is not set. Start tunnel (cloudflared/ngrok) and set PUBLIC_URL or let the script prompt you on next run.")
        elif choice == "2":
            if PUBLIC_URL:
                print("\nQR code:\n")
                print_qr_terminal(PUBLIC_URL)
            else:
                print("\nPUBLIC_URL not set. Start tunnel and set PUBLIC_URL to generate QR.")
        elif choice == "3":
            print("\nStarting server (Ctrl-C to stop)...\n")
            start_flask_server(HOST, PORT)
        elif choice == "4":
            print("Exiting.")
            sys.exit(0)
        else:
            print("Invalid choice. Pick 1-4.")

if __name__ == "__main__":
    main()
