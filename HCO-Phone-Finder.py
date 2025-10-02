#!/usr/bin/env python3
"""
HCO-Phone-Finder.py - Auto tunnel edition
Attempts to auto-detect or auto-start ngrok/cloudflared so you DON'T have to paste PUBLIC_URL.
Author: Azhar
"""

from __future__ import annotations
import os, sys, time, csv, datetime, subprocess, platform, shutil, json, socket
from typing import Optional

# Optional imports
try:
    from flask import Flask, request, render_template_string, send_file, abort
    import qrcode
    from PIL import Image
    import requests
except Exception:
    # may be None, checked later
    try:
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

home = os.path.expanduser("~")
saved_url_path = os.path.join(home, ".hco_public_url")
env_file = os.path.join(home, ".hco_phone_finder_env")

# Keep tunnel process alive if we spawn one
tunnel_proc: Optional[subprocess.Popen] = None

# ---------------- Auto-load env file ----------------
if os.path.exists(env_file):
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key.startswith("export "):
                        key = key.split(" ", 1)[1]
                    os.environ[key] = val
    except Exception:
        pass

# ---------------- CSV header ----------------
if not os.path.exists(LOGFILE):
    with open(LOGFILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["timestamp_utc","ip","user_agent","latitude","longitude","accuracy","client_ts_ms","notes"])

# ---------------- Helpers ----------------
def find_executable(name: str) -> Optional[str]:
    """Return full path to executable if in PATH, else None"""
    path = shutil.which(name)
    return path

def check_port_open(host: str, port: int, timeout=0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def try_ngrok_api_once() -> Optional[str]:
    """Query ngrok local API for tunnels"""
    if requests is None:
        return None
    try:
        resp = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=1.0)
        if not resp.ok:
            return None
        data = resp.json()
        for t in data.get("tunnels", []):
            pu = t.get("public_url")
            if pu and pu.startswith("http"):
                return pu.rstrip("/")
    except Exception:
        return None
    return None

def start_ngrok_and_get_url(port: int = PORT, max_wait: float = 8.0) -> Optional[str]:
    """Start ngrok (if binary available) and try to detect its public URL via API."""
    global tunnel_proc
    ngrok_bin = find_executable("ngrok")
    if not ngrok_bin:
        return None
    # start ngrok
    try:
        # start ngrok http <port>
        tunnel_proc = subprocess.Popen([ngrok_bin, "http", str(port)],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except Exception:
        return None
    # wait for ngrok to initialise and its API to be available
    t0 = time.time()
    while time.time() - t0 < max_wait:
        # try API
        url = try_ngrok_api_once()
        if url:
            return url
        time.sleep(0.6)
    # fallback: try to parse stdout for "url=" or "Forwarding"
    try:
        if tunnel_proc and tunnel_proc.stdout:
            out = tunnel_proc.stdout.read(1024)
            for line in out.splitlines():
                if "https://" in line:
                    # take first https-looking token
                    for token in line.split():
                        if token.startswith("https://"):
                            return token.rstrip("/")
    except Exception:
        pass
    return None

def start_cloudflared_and_get_url(port: int = PORT, max_wait: float = 8.0) -> Optional[str]:
    """Start cloudflared if available and parse its output for trycloudflare URL."""
    global tunnel_proc
    cf_bin = find_executable("cloudflared")
    if not cf_bin:
        return None
    try:
        # Use --no-autoupdate where available to avoid prompts; some versions accept it.
        args = [cf_bin, "tunnel", "--url", f"http://localhost:{port}"]
        # In some cloudflared builds 'tunnel' exists, in some older it's 'access' or 'proxy'. We attempt 'tunnel' first.
        tunnel_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except Exception:
        return None
    # read output lines and search for https://*.trycloudflare.com or https://*.cloudflareroute.com etc.
    t0 = time.time()
    url = None
    try:
        while time.time() - t0 < max_wait:
            if tunnel_proc.stdout is None:
                break
            line = tunnel_proc.stdout.readline()
            if not line:
                time.sleep(0.3)
                continue
            # look for https
            if "https://" in line:
                # extract token that looks like url
                for token in line.split():
                    if token.startswith("https://"):
                        url = token.rstrip(",").rstrip()
                        break
            if url:
                break
    except Exception:
        pass
    return url

def detect_public_url_auto() -> str:
    """Auto-detect or auto-start tunnels. Returns public URL or empty string."""
    # 1) env var
    env = os.environ.get("PUBLIC_URL", "").strip()
    if env:
        return env.rstrip("/")

    # 2) saved file
    try:
        if os.path.exists(saved_url_path):
            with open(saved_url_path, "r", encoding="utf-8") as f:
                u = f.read().strip()
                if u:
                    return u.rstrip("/")
    except Exception:
        pass

    # 3) try ngrok API (if running)
    url = try_ngrok_api_once()
    if url:
        # save
        try:
            with open(saved_url_path, "w", encoding="utf-8") as f: f.write(url)
        except Exception:
            pass
        return url

    # 4) if ngrok binary exists, start it
    if find_executable("ngrok"):
        print("ngrok found — starting ngrok automatically...")
        url = start_ngrok_and_get_url(PORT, max_wait=10.0)
        if url:
            print("Detected ngrok URL:", url)
            try:
                with open(saved_url_path, "w", encoding="utf-8") as f: f.write(url)
            except Exception:
                pass
            return url
        else:
            print("ngrok start attempted but no URL detected.")

    # 5) try cloudflared
    if find_executable("cloudflared"):
        print("cloudflared found — starting cloudflared tunnel automatically...")
        url = start_cloudflared_and_get_url(PORT, max_wait=12.0)
        if url:
            print("Detected cloudflared URL:", url)
            try:
                with open(saved_url_path, "w", encoding="utf-8") as f: f.write(url)
            except Exception:
                pass
            return url
        else:
            print("cloudflared start attempted but no URL detected.")

    # 6) nothing automated worked — fall back to prompt (rare)
    try:
        url = input("\nPUBLIC_URL not found and automatic start failed. Paste the public URL (or leave blank to skip): ").strip()
        if url:
            url = url.rstrip("/")
            try:
                with open(saved_url_path, "w", encoding="utf-8") as f: f.write(url)
            except Exception:
                pass
            return url
    except Exception:
        pass

    return ""

# ---------------- load PUBLIC_URL ----------------
PUBLIC_URL = detect_public_url_auto()

# ---------------- Terminal helpers ----------------
def ansi(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"

def red_bg_green_text_block(lines):
    for l in lines:
        print("\033[41m\033[1;32m " + l + " \033[0m")

def print_qr_terminal(data: str):
    if not data:
        print("No PUBLIC_URL to show as QR.")
        return
    if qrcode is None:
        print("qrcode not installed. Install: pip install qrcode[pil]")
        print("Link:", data)
        return
    try:
        qr = qrcode.QRCode(border=1)
        qr.add_data(data)
        qr.make(fit=True)
        m = qr.get_matrix()
        black = "\033[40m  \033[0m"
        white = "\033[47m  \033[0m"
        border = 2
        w = len(m[0]) + border*2
        for _ in range(border): print(white * w)
        for row in m:
            line = white * border
            for col in row:
                line += black if col else white
            line += white * border
            print(line)
        for _ in range(border): print(white * w)
    except Exception as e:
        print("QR generation failed:", e)
        print("Link:", data)

# ---------------- YouTube helper ----------------
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
        print("Open manually:", YOUTUBE_URL)

# ---------------- Termux lock ----------------
def termux_lock_flow():
    os.system('clear' if os.name == 'posix' else 'cls')
    print(ansi("Tool is Locked 🔒", "1;31"))
    print("\nRedirecting to YouTube — subscribe and click the 🔔 bell icon to unlock.\n")
    for i in range(9, 0, -1):
        print(ansi(str(i), "1;33"), end=" ", flush=True)
        time.sleep(1)
    print("\n" + ansi("Opening YouTube app...", "1;34"))
    open_youtube_app()
    input(ansi("\nAfter subscribing/visiting YouTube, press Enter to continue...", "1;37"))

# ---------------- Flask page ----------------
PUBLIC_PAGE_HTML = """
<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Found phone</title>
<style>body{font-family:system-ui,Roboto,Arial;background:#07111a;color:#e6f6ff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}.card{background:#06121a;padding:20px;border-radius:12px;max-width:720px;width:92%}.btn{background:#0b84ff;color:white;padding:10px 14px;border-radius:8px;border:none;font-weight:700;cursor:pointer}.small{color:#98b2c2;font-size:13px}a.link{color:#0b84ff;word-break:break-all}</style></head><body>
<div class="card"><h1 style="color:#00ff66;margin:0 0 6px 0">HCO Phone Finder</h1><div style="color:#007a2e;font-weight:700">A Lost or Stolen Phone Tracker by {{owner}}</div>
<p style="margin-top:12px">This device is lost. The owner ({{owner_contact}}) offers a reward to return it.</p>
<p class="small">Or open this link directly: <a href="{{public_url}}" class="link" target="_blank">{{public_url}}</a></p>
<div style="margin-top:12px"><button id="shareBtn" class="btn">Share my location</button></div>
<div id="status" style="margin-top:10px;color:#b4eec2"></div>
<p style="margin-top:12px" class="small">If you prefer, call the owner directly using the number above.</p></div>
<script>
const shareBtn=document.getElementById('shareBtn'), status=document.getElementById('status');
shareBtn.addEventListener('click', ()=>{ if(!navigator.geolocation){ status.textContent="Geolocation not supported."; return;} shareBtn.disabled=true; shareBtn.textContent='Requesting location...';
navigator.geolocation.getCurrentPosition(async (pos)=>{ try{ const payload={latitude:pos.coords.latitude,longitude:pos.coords.longitude,accuracy:pos.coords.accuracy,timestamp:pos.timestamp};
const res=await fetch('/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}); if(res.ok){ status.textContent="Thanks — location shared."; shareBtn.textContent='Shared'; } else { status.textContent="Failed to send location."; shareBtn.disabled=false; shareBtn.textContent='Share my location'; } }catch(e){ status.textContent="Network error."; shareBtn.disabled=false; shareBtn.textContent='Share my location'; } }, (err)=>{ status.textContent="Could not get location: "+(err.message||'permission denied'); shareBtn.disabled=false; shareBtn.textContent='Share my location'; }, { enableHighAccuracy:true, timeout:15000 }); });
</script></body></html>
"""

def ensure_flask_available():
    if Flask is None:
        print("Flask or supporting libraries missing. Install with: pip install flask qrcode pillow requests")
        return False
    return True

def start_flask_server(host=HOST, port=PORT):
    if not ensure_flask_available():
        return
    app = Flask(__name__)

    @app.route("/")
    def index():
        html = PUBLIC_PAGE_HTML.replace("{{owner}}", OWNER_NAME).replace("{{owner_contact}}", OWNER_CONTACT).replace("{{public_url}}", PUBLIC_URL or "")
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
                csv.writer(f).writerow([ts, ip, ua, latf, lonf, acc, cts, "voluntary_share"])
        except Exception:
            pass
        print(f"[{ts}] REPORT from {ip} UA:{ua} lat={latf} lon={lonf} acc={acc}")
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

# ---------------- Main ----------------
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
                print("\nPUBLIC_URL not set.")
        elif choice == "2":
            if PUBLIC_URL:
                print("\nQR code:\n")
                print_qr_terminal(PUBLIC_URL)
            else:
                print("\nPUBLIC_URL not set.")
        elif choice == "3":
            if not PUBLIC_URL:
                print("\nWARNING: PUBLIC_URL is empty — the public page won't be reachable externally until you have a tunnel.")
            print("\nStarting server (Ctrl-C to stop)...\n")
            start_flask_server(HOST, PORT)
        elif choice == "4":
            print("Exiting.")
            # If we spawned a tunnel process, leave it running or clean up:
            try:
                if tunnel_proc and tunnel_proc.poll() is None:
                    # best-effort terminate
                    tunnel_proc.terminate()
            except Exception:
                pass
            sys.exit(0)
        else:
            print("Invalid choice. Pick 1-4.")

if __name__ == "__main__":
    main()
