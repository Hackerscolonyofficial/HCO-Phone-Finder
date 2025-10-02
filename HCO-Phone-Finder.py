#!/usr/bin/env python3
"""
HCO-Phone-Finder.py - Auto-start ngrok/cloudflared if available, robust detection & run.
Author: Azhar
"""

from __future__ import annotations
import os, sys, time, csv, datetime, subprocess, platform, shutil, socket
from typing import Optional

# Optional imports (Flask, qrcode, requests)
try:
    from flask import Flask, request, render_template_string, send_file, abort
    import qrcode
    from PIL import Image
    import requests
except Exception:
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

tunnel_proc: Optional[subprocess.Popen] = None

# ---------------- Helpers ----------------
def which(name: str) -> Optional[str]:
    return shutil.which(name)

def is_port_open(host: str, port: int, timeout=0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def try_ngrok_api_once() -> Optional[str]:
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

def start_ngrok_background(port: int = PORT) -> Optional[str]:
    global tunnel_proc
    ng = which("ngrok")
    if not ng:
        return None
    try:
        tunnel_proc = subprocess.Popen([ng, "http", str(port)],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except Exception as e:
        print("Failed to start ngrok:", e)
        return None
    deadline = time.time() + 15.0
    while time.time() < deadline:
        url = try_ngrok_api_once()
        if url:
            return url
        time.sleep(0.6)
    try:
        if tunnel_proc and tunnel_proc.stdout:
            out = tunnel_proc.stdout.read(2048)
            for token in out.split():
                if token.startswith("https://"):
                    return token.rstrip("/")
    except Exception:
        pass
    try:
        if tunnel_proc and tunnel_proc.stderr:
            err = tunnel_proc.stderr.read(1024)
            if err:
                print("ngrok stderr (truncated):", err.strip()[:1000])
    except Exception:
        pass
    return None

def start_cloudflared_background(port: int = PORT) -> Optional[str]:
    global tunnel_proc
    cf = which("cloudflared")
    if not cf:
        return None
    try:
        tunnel_proc = subprocess.Popen([cf, "tunnel", "--url", f"http://localhost:{port}"],
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except Exception as e:
        print("Failed to start cloudflared:", e)
        return None
    deadline = time.time() + 18.0
    url = None
    try:
        while time.time() < deadline:
            if tunnel_proc.stdout is None:
                break
            line = tunnel_proc.stdout.readline()
            if not line:
                time.sleep(0.3)
                continue
            if "https://" in line:
                for tok in line.split():
                    if tok.startswith("https://"):
                        url = tok.rstrip(",").rstrip()
                        break
            if url:
                break
    except Exception:
        pass
    return url

# ---------------- Auto-load env file ----------------
if os.path.exists(env_file):
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln or ln.startswith("#"):
                    continue
                if "=" in ln:
                    k, v = ln.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k.startswith("export "):
                        k = k.split(" ", 1)[1]
                    os.environ.setdefault(k, v)
    except Exception:
        pass

# ---------------- PUBLIC_URL detection & auto-start ----------------
def detect_public_url_auto() -> str:
    env = os.environ.get("PUBLIC_URL", "").strip()
    if env:
        return env.rstrip("/")
    try:
        if os.path.exists(saved_url_path):
            with open(saved_url_path, "r", encoding="utf-8") as f:
                u = f.read().strip()
                if u:
                    return u.rstrip("/")
    except Exception:
        pass
    url = try_ngrok_api_once()
    if url:
        try:
            with open(saved_url_path, "w", encoding="utf-8") as f: f.write(url)
        except Exception:
            pass
        return url
    if which("ngrok"):
        print("ngrok found — attempting to start ngrok automatically (background)...")
        url = start_ngrok_background(PORT)
        if url:
            print("ngrok public URL:", url)
            try:
                with open(saved_url_path, "w", encoding="utf-8") as f: f.write(url)
            except Exception:
                pass
            return url
        else:
            print("ngrok started but no URL detected within timeout.")
    if which("cloudflared"):
        print("cloudflared found — attempting to start cloudflared automatically (background)...")
        url = start_cloudflared_background(PORT)
        if url:
            print("cloudflared public URL:", url)
            try:
                with open(saved_url_path, "w", encoding="utf-8") as f: f.write(url)
            except Exception:
                pass
            return url
        else:
            print("cloudflared started but no URL detected within timeout.")
    print("
No tunnel detected and no usable tunnel binary found in PATH.")
    plat = platform.system().lower()
    if "android" in platform.uname().system.lower() or "termux" in os.environ.get("PREFIX", ""):
        suggested = ("pkg update -y && pkg install -y wget unzip
"
                     "wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-arm64.zip -O /data/data/com.termux/files/home/ngrok.zip
"
                     "unzip ngrok.zip -d $HOME && chmod +x $HOME/ngrok
"
                     "ngrok authtoken <YOUR_TOKEN>   # optional (recommended)
"
                     "ngrok http 5000")
    elif plat.startswith("linux"):
        suggested = ("sudo apt update && sudo apt install -y wget unzip
"
                     "wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip -O ~/ngrok.zip
"
                     "unzip ~/ngrok.zip -d ~ && chmod +x ~/ngrok
"
                     "sudo mv ~/ngrok /usr/local/bin/ngrok
"
                     "ngrok http 5000")
    else:
        suggested = "Please install ngrok or cloudflared for your platform and re-run."
    print("Suggested install / run commands (copy-paste & follow):
")
    print(suggested)
    if which("ngrok") is None and which("cloudflared") is None:
        try:
            resp = ""
            if sys.stdin.isatty():
                resp = input("
Do you want me to attempt to run the installer commands for you now? (Y/n): ").strip().lower()
            else:
                print("No TTY detected; skipping auto-install prompt.")
                resp = "n"
        except Exception:
            resp = "n"
        if resp in ("", "y", "yes"):
            try:
                if "linux" in plat:
                    print("Running apt-based installer commands (requires sudo)...")
                    subprocess.run(["sudo", "apt", "update"], check=False)
                    subprocess.run(["sudo", "apt", "install", "-y", "wget", "unzip"], check=False)
                    url_dl = "https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip"
                    dl_target = os.path.join(home, "ngrok.zip")
                    subprocess.run(["wget", "-O", dl_target, url_dl], check=False)
                    subprocess.run(["unzip", "-o", dl_target, "-d", home], check=False)
                    ngbin = os.path.join(home, "ngrok")
                    if os.path.exists(ngbin):
                        subprocess.run(["chmod", "+x", ngbin], check=False)
                        try:
                            subprocess.run(["sudo", "mv", ngbin, "/usr/local/bin/ngrok"], check=False)
                        except Exception:
                            pass
                        print("Downloaded ngrok; attempting to start it...")
                        url = start_ngrok_background(PORT)
                        if url:
                            print("ngrok URL detected:", url)
                            with open(saved_url_path, "w", encoding="utf-8") as f: f.write(url)
                            return url
                else:
                    print("Attempting Termux-style ngrok download (best-effort)...")
                    dl_target = os.path.join(home, "ngrok.zip")
                    url_dl = "https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-arm64.zip"
                    subprocess.run(["wget", "-O", dl_target, url_dl], check=False)
                    subprocess.run(["unzip", "-o", dl_target, "-d", home], check=False)
                    ngbin = os.path.join(home, "ngrok")
                    if os.path.exists(ngbin):
                        subprocess.run(["chmod", "+x", ngbin], check=False)
                        print("Downloaded ngrok to $HOME. Starting...")
                        url = start_ngrok_background(PORT)
                        if url:
                            print("ngrok URL detected:", url)
                            with open(saved_url_path, "w", encoding="utf-8") as f: f.write(url)
                            return url
            except Exception as e:
                print("Automatic installer attempt failed:", e)
    try:
        manual_url = ""
        if sys.stdin.isatty():
            manual_url = input("
Paste public URL manually (or leave blank to skip): ").strip()
        if manual_url:
            try:
                with open(saved_url_path, "w", encoding="utf-8") as f: f.write(manual_url.rstrip("/"))
            except Exception:
                pass
            return manual_url.rstrip("/")
    except Exception:
        pass
    return ""

PUBLIC_URL = detect_public_url_auto()

# ---------------- CSV header ----------------
if not os.path.exists(LOGFILE):
    with open(LOGFILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["timestamp_utc", "ip", "user_agent", "latitude", "longitude", "accuracy", "client_ts_ms", "notes"])

# ---------------- Terminal helpers ----------------
def ansi(text: str, code: str) -> str:
    return f"\u001B[{code}m{text}\u001B[0m"

def red_bg_green_text_block(lines):
    for l in lines:
        print("\u001B[41m\u001B[1;32m " + l + " \u001B[0m")

def print_qr_terminal(data: str):
    if not data:
        print("No PUBLIC_URL to render as QR.")
        return
    if qrcode is None:
        print("Install qrcode: pip install qrcode[pil]")
        print("Link:", data)
        return
    try:
        qr = qrcode.QRCode(border=1); qr.add_data(data); qr.make(fit=True)
        m = qr.get_matrix(); black="\u001B[40m  \u001B[0m"; white="\u001B[47m  \u001B[0m"; border=2; w=len(m[0])+border*2
        for _ in range(border): print(white*w)
        for row in m:
            line = white*border
            for col in row: line += black if col else white
            line += white*border; print(line)
        for _ in range(border): print(white*w)
    except Exception as e:
        print("QR failed:", e); print("Link:", data)

def open_youtube_app():
    app_link = f"vnd.youtube://channel/{YT_CHANNEL_ID}" if YT_CHANNEL_ID else None
    try:
        if platform.system().lower() == "linux" and (os.path.exists("/system/bin") or "ANDROID_ROOT" in os.environ):
            if app_link: subprocess.run(['am', 'start', '-a', 'android.intent.action.VIEW', '-d', app_link], check=False); time.sleep(0.8)
            subprocess.run(['am', 'start', '-a', 'android.intent.action.VIEW', '-d', YOUTUBE_URL], check=False); return
    except Exception:
        pass
    try:
        import webbrowser; webbrowser.open(YOUTUBE_URL)
    except Exception:
        print("Open:", YOUTUBE_URL)

def termux_lock_flow():
    os.system('clear' if os.name == 'posix' else 'cls')
    print(ansi("Tool is Locked 🔒", "1;31"))
    print("
Redirecting to YouTube — subscribe to unlock.
")
    for i in range(9, 0, -1): print(ansi(str(i), "1;33"), end=" ", flush=True); time.sleep(1)
    print("
" + ansi("Opening YouTube app...", "1;34")); open_youtube_app()
    if sys.stdin.isatty():
        input(ansi("
After subscribing/visiting YouTube, press Enter to continue...", "1;37"))

# ------------- Flask page and handlers -------------
PUBLIC_PAGE_HTML = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Found phone</title><style>body{font-family:system-ui,Roboto,Arial;background:#07111a;color:#e6f6ff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}.card{background:#06121a;padding:20px;border-radius:12px;max-width:720px;width:92%}.btn{background:#0b84ff;color:white;padding:10px 14px;border-radius:8px;border:none;font-weight:700;cursor:pointer}.small{color:#98b2c2;font-size:13px}a.link{color:#0b84ff;word-break:break-all}</style></head><body><div class="card"><h1 style="color:#00ff66;margin:0 0 6px 0">HCO Phone Finder</h1><div style="color:#007a2e;font-weight:700">A Lost or Stolen Phone Tracker by {{owner}}</div><p style="margin-top:12px">This device is lost. The owner ({{owner_contact}}) offers a reward to return it.</p><p class="small">Or open this link directly: <a href="{{public_url}}" class="link" target="_blank">{{public_url}}</a></p><div style="margin-top:12px"><button id="shareBtn" class="btn">Share my location</button></div><div id="status" style="margin-top:10px;color:#b4eec2"></div><p style="margin-top:12px" class="small">If you prefer, call the owner directly using the number above.</p></div><script>const s=document.getElementById('shareBtn'),st=document.getElementById('status');s.addEventListener('click',()=>{if(!navigator.geolocation){st.textContent='Geolocation not supported.';return}s.disabled=true;s.textContent='Requesting location...';navigator.geolocation.getCurrentPosition(async p=>{try{const payload={latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy:p.coords.accuracy,timestamp:p.timestamp};const res=await fetch('/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(res.ok){st.textContent='Thanks — location shared.';s.textContent='Shared'}else{st.textContent='Failed to send location.';s.disabled=false;s.textContent='Share my location'}}catch(e){st.textContent='Network error.';s.disabled=false;s.textContent='Share my location'}},err=>{st.textContent='Could not get location: '+(err.message||'permission denied');s.disabled=false;s.textContent='Share my location'},{enableHighAccuracy:true,timeout:15000})});</script></body></html>"""

def ensure_flask():
    if Flask is None:
        print("Flask/qrcode/requests missing. Install: pip install flask qrcode pillow requests")
        return False
    return True

def start_flask_server(host=HOST, port=PORT):
    if not ensure_flask():
        return
    app = Flask(__name__)
    @app.route("/")
    def index():
        html = PUBLIC_PAGE_HTML.replace("{{owner}}", OWNER_NAME).replace("{{owner_contact}}", OWNER_CONTACT).replace("{{public_url}}", PUBLIC_URL or "")
        return render_template_string(html)
    @app.route("/report", methods=["POST"])
    def report():
        try: data = request.get_json(force=True)
        except Exception: return ("Invalid JSON", 400)
        lat = data.get("latitude") or data.get("lat"); lon = data.get("longitude") or data.get("lon"); acc = data.get("accuracy") or data.get("acc"); cts = data.get("timestamp") or ""
        try:
            latf = float(lat); lonf = float(lon)
        except Exception:
            return ("Invalid coordinates", 400)
        ip = request.headers.get('X-Forwarded-For', request.remote_addr); ua = request.headers.get('User-Agent', ''); ts = datetime.datetime.utcnow().isoformat()+"Z"
        try:
            with open(LOGFILE, "a", newline="", encoding="utf-8") as f: csv.writer(f).writerow([ts, ip, ua, latf, lonf, acc, cts, "voluntary_share"])
        except Exception:
            pass
        print(f"[{ts}] REPORT from {ip} UA:{ua} lat={latf} lon={lonf} acc={acc}")
        return ("OK", 200)
    @app.route("/admin")
    def admin():
        key = request.args.get("key", ""); 
        if key != ACCESS_KEY: return abort(401, "Unauthorized")
        rows=[]
        try:
            with open(LOGFILE, "r", encoding="utf-8", newline="") as f:
                r = csv.reader(f); next(r, None)
                for row in r: rows.append(row)
        except Exception:
            pass
        out = "<html><body><h2>Reports</h2><p><a href='/'>Public page</a> | <a href='/download?key={k}'>Download CSV</a></p><table border=1 cellpadding=6><tr><th>UTC</th><th>IP</th><th>UA</th><th>Lat</th><th>Lon</th><th>Acc</th></tr>".format(k=ACCESS_KEY)
        for r in reversed(rows): out += "<tr>" + "".join(f"<td>{x}</td>" for x in r[:6]) + "</tr>"
        out += "</table></body></html>"
        return out
    @app.route("/download")
    def download():
        key = request.args.get("key", ""); 
        if key != ACCESS_KEY: return abort(401, "Unauthorized")
        try: return send_file(LOGFILE, as_attachment=True, download_name="reports.csv")
        except Exception: return abort(500, "Unable to read reports file")
    print(f"Starting Flask server on http://{host}:{port} ...")
    app.run(host=host, port=port)

def main():
    termux = (platform.system().lower() == "linux" and (os.path.exists("/system/bin") or "ANDROID_ROOT" in os.environ))
    os.system('clear' if os.name == 'posix' else 'cls')
    print(ansi("Tool is Locked 🔒", "1;31"))
    print("
Redirecting to YouTube — please subscribe and click the 🔔 bell icon to unlock.
")
    for i in range(9, 0, -1): print(ansi(str(i), "1;33"), end=" ", flush=True); time.sleep(1)
    print("
" + ansi("Opening YouTube app...", "1;34")) 
    try:
        if termux:
            if YT_CHANNEL_ID: subprocess.run(['am', 'start', '-a', 'android.intent.action.VIEW', '-d', f"vnd.youtube://channel/{YT_CHANNEL_ID}"], check=False)
            subprocess.run(['am', 'start', '-a', 'android.intent.action.VIEW', '-d', YOUTUBE_URL], check=False)
        else:
            import webbrowser; webbrowser.open(YOUTUBE_URL)
    except Exception:
        pass
    if sys.stdin.isatty():
        input(ansi("
After visiting YouTube, press Enter to continue...", "1;37"))

    while True:
        print(); red_bg_green_text_block(["HCO PHONE FINDER", f"A Lost or Stolen Phone Tracker by {OWNER_NAME}"]); print()
        print("Options:
1) Print public link
2) Print QR in terminal
3) Start Flask server (public page & report endpoint)
4) Exit")
        try:
            choice = input("
Choose option (1-4): ").strip()
        except EOFError:
            print("No input. Exiting.")
            break
        if choice == "1":
            print("
PUBLIC LINK:", PUBLIC_URL if PUBLIC_URL else "Not set (no tunnel detected).")
        elif choice == "2":
            print_qr_terminal(PUBLIC_URL if PUBLIC_URL else "")
        elif choice == "3":
            if not PUBLIC_URL:
                print("
WARNING: PUBLIC_URL not set — the public page will not be reachable externally until a tunnel is started.")
            print("
Starting Flask server (Ctrl-C to stop)...")
            start_flask_server(HOST, PORT)
        elif choice == "4":
            print("Exiting.")
            try:
                if tunnel_proc and tunnel_proc.poll() is None:
                    tunnel_proc.terminate()
            except Exception:
                pass
            sys.exit(0)
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    try:
        if not PUBLIC_URL:
            PUBLIC_URL = detect_public_url_auto()
        main()
    finally:
        try:
            if tunnel_proc and tunnel_proc.poll() is None:
                tunnel_proc.terminate()
        except Exception:
            pass
