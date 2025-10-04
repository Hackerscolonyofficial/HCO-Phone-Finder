#!/usr/bin/env python3
"""
HCO-Phone-Finder.py - Auto-start ngrok/cloudflared (optional), clean UI, realistic reward CTA.
Author: Azhar (modified)
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

# ---------- Config ----------
ACCESS_KEY = os.environ.get("ACCESS_KEY", "changeme_change_this_key")
OWNER_NAME = os.environ.get("OWNER_NAME", "Azhar")
OWNER_CONTACT = os.environ.get("OWNER_CONTACT", "+91-XXXXXXXXXX")
YT_CHANNEL_ID = os.environ.get("YT_CHANNEL_ID", "")
YOUTUBE_URL = os.environ.get("YOUTUBE_URL", "https://www.youtube.com/@hackers_colony_tech")
LOGFILE = "reports.csv"
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "5000"))

# Behavioral flags (env)
AUTO_TUNNEL = os.environ.get("AUTO_TUNNEL", "0") in ("1", "true", "yes", "on")
HEADLESS = os.environ.get("HEADLESS", "0") in ("1", "true", "yes", "on")

home = os.path.expanduser("~")
saved_url_path = os.path.join(home, ".hco_public_url")
env_file = os.path.join(home, ".hco_phone_finder_env")
tunnel_proc: Optional[subprocess.Popen] = None

# ---------- util ----------
def which(name: str) -> Optional[str]:
    return shutil.which(name)

def is_port_open(host: str, port: int, timeout=0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

# ---------- ngrok/cloudflared helpers ----------
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

def start_ngrok_background(port: int = PORT, bin_path: Optional[str] = None, timeout=15.0) -> Optional[str]:
    global tunnel_proc
    ng = bin_path or which("ngrok")
    if not ng:
        return None
    try:
        tunnel_proc = subprocess.Popen([ng, "http", str(port)],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except Exception as e:
        print("Failed to start ngrok:", e)
        return None
    deadline = time.time() + timeout
    while time.time() < deadline:
        url = try_ngrok_api_once()
        if url:
            return url
        time.sleep(0.6)
    # Fallback: try to read stdout
    try:
        if tunnel_proc and tunnel_proc.stdout:
            out = tunnel_proc.stdout.read(4096)
            for token in out.split():
                if token.startswith("https://"):
                    return token.rstrip("/")
    except Exception:
        pass
    return None

def start_cloudflared_background(port: int = PORT, bin_path: Optional[str] = None, timeout=18.0) -> Optional[str]:
    global tunnel_proc
    cf = bin_path or which("cloudflared")
    if not cf:
        return None
    try:
        # use --no-autoupdate to be safer on some installs
        tunnel_proc = subprocess.Popen([cf, "tunnel", "--url", f"http://localhost:{port}", "--no-autoupdate"],
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except Exception as e:
        print("Failed to start cloudflared:", e)
        return None
    deadline = time.time() + timeout
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

# ---------- load .env-like file ----------
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

# ---------- detect / auto-start tunnel ----------
def detect_public_url_auto() -> str:
    # 1) PUBLIC_URL env
    env = os.environ.get("PUBLIC_URL", "").strip()
    if env:
        return env.rstrip("/")
    # 2) saved url
    try:
        if os.path.exists(saved_url_path):
            with open(saved_url_path, "r", encoding="utf-8") as f:
                u = f.read().strip()
                if u:
                    return u.rstrip("/")
    except Exception:
        pass
    # 3) running local ngrok API
    url = try_ngrok_api_once()
    if url:
        try:
            with open(saved_url_path, "w", encoding="utf-8") as f: f.write(url)
        except Exception:
            pass
        return url
    # 4) attempt auto-start if binaries present or AUTO_TUNNEL set
    if which("ngrok") or AUTO_TUNNEL:
        ng_path = which("ngrok")
        if ng_path:
            print("ngrok binary found — attempting to start ngrok automatically (background)...")
        else:
            print("AUTO_TUNNEL enabled — attempting to download/start ngrok (Termux best-effort disabled by default).")
        url = start_ngrok_background(PORT)
        if url:
            print("ngrok public URL:", url)
            try:
                with open(saved_url_path, "w", encoding="utf-8") as f: f.write(url)
            except Exception:
                pass
            return url
        else:
            print("ngrok started (or attempted) but no URL detected within timeout.")
    if which("cloudflared") or AUTO_TUNNEL:
        cf_path = which("cloudflared")
        if cf_path:
            print("cloudflared binary found — attempting to start cloudflared automatically (background)...")
        url = start_cloudflared_background(PORT)
        if url:
            print("cloudflared public URL:", url)
            try:
                with open(saved_url_path, "w", encoding="utf-8") as f: f.write(url)
            except Exception:
                pass
            return url
        else:
            print("cloudflared started (or attempted) but no URL detected within timeout.")
    # 5) nothing found: prompt only if not headless
    if HEADLESS:
        return ""
    # Provide friendly suggestion (single string)
    print("\nNo tunnel detected and no usable tunnel binary found in PATH.")
    plat = platform.system().lower()
    if "android" in platform.uname().system.lower() or "termux" in os.environ.get("PREFIX", ""):
        suggested = (
            "pkg update -y && pkg install -y wget unzip\n"
            "# Download ngrok (example for linux-arm64)\n"
            "wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-arm64.zip -O $HOME/ngrok.zip\n"
            "unzip ngrok.zip -d $HOME && chmod +x $HOME/ngrok\n"
            "ngrok authtoken <YOUR_TOKEN>   # optional (recommended)\n"
            "ngrok http 5000\n"
        )
    elif plat.startswith("linux"):
        suggested = (
            "sudo apt update && sudo apt install -y wget unzip\n"
            "# Download ngrok (amd64 example)\n"
            "wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip -O ~/ngrok.zip\n"
            "unzip ~/ngrok.zip -d ~ && chmod +x ~/ngrok\n"
            "sudo mv ~/ngrok /usr/local/bin/ngrok\n"
            "ngrok http 5000\n"
        )
    else:
        suggested = "Please install ngrok or cloudflared for your platform and re-run."

    print("Suggested install / run commands (copy-paste & follow):\n")
    print(suggested)
    # allow manual paste
    try:
        url = input("Paste public URL manually (or leave blank to skip): ").strip()
        if url:
            try:
                with open(saved_url_path, "w", encoding="utf-8") as f: f.write(url.rstrip("/"))
            except Exception:
                pass
            return url.rstrip("/")
    except Exception:
        pass
    return ""

PUBLIC_URL = detect_public_url_auto()

# ---------- ensure logfile ----------
if not os.path.exists(LOGFILE):
    try:
        with open(LOGFILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["timestamp_utc", "ip", "user_agent", "latitude", "longitude", "accuracy", "client_ts_ms", "notes"])
    except Exception:
        pass

# ---------- display helpers ----------
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
        if platform.system().lower()=="linux" and (os.path.exists("/system/bin") or "ANDROID_ROOT" in os.environ):
            if app_link:
                subprocess.run(['am','start','-a','android.intent.action.VIEW','-d',app_link], check=False)
                time.sleep(0.8)
            subprocess.run(['am','start','-a','android.intent.action.VIEW','-d',YOUTUBE_URL], check=False)
            return
    except Exception:
        pass
    try:
        import webbrowser; webbrowser.open(YOUTUBE_URL)
    except Exception:
        print("Open:", YOUTUBE_URL)

# ---------- public page (improved reward CTA) ----------
PUBLIC_PAGE_HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Found phone — {owner}</title>
<style>
  :root{{--bg:#04121a;--card:#061827;--accent:#0bb0ff;--accent2:#00d07a;--muted:#98b2c2}}
  body{{font-family:system-ui,Roboto,Arial;background:linear-gradient(180deg,#021017, #071225);color:#e6f6ff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
  .card{{background:var(--card);padding:20px;border-radius:12px;max-width:760px;width:94%;box-shadow:0 10px 30px rgba(0,0,0,0.6)}}
  .hdr{{display:flex;align-items:center;gap:12px}}
  .badge{{background:var(--accent2);color:#012218;padding:8px 10px;border-radius:8px;font-weight:800}}
  h1{{margin:0;font-size:20px}}
  p.small{{color:var(--muted);margin:8px 0 0 0;font-size:13px}}
  .reward{{margin-top:14px;padding:12px;border-radius:10px;background:linear-gradient(90deg, rgba(11,176,255,0.06), rgba(0,208,122,0.03));display:flex;justify-content:space-between;align-items:center}}
  .big{{font-weight:800;font-size:20px;color:var(--accent2)}}
  .btn{{background:var(--accent);color:white;padding:12px 14px;border-radius:10px;border:none;font-weight:800;cursor:pointer;box-shadow:0 6px 18px rgba(11,176,255,0.12)}}
  .btn-outline{{background:transparent;border:2px solid rgba(255,255,255,0.04);padding:10px 12px;color:var(--muted)}}
  .muted{{color:var(--muted)}}
  a.link{{color:var(--accent);word-break:break-all}}
</style>
</head>
<body>
<div class="card">
  <div class="hdr">
    <div class="badge">FOUND PHONE</div>
    <div>
      <h1>HCO Phone Finder</h1>
      <div style="color:#00ff88;font-weight:700;font-size:13px">{owner}</div>
    </div>
  </div>

  <p style="margin-top:12px">This device appears to be lost. The owner <strong class="muted">({owner_contact})</strong> is offering a reward for safe return.</p>

  <div class="reward">
    <div>
      <div class="big">Reward: ₹2,000</div>
      <div class="muted" style="font-size:13px">No questions asked — meet in a public place or call to arrange pickup.</div>
    </div>
    <div style="display:flex;gap:10px;align-items:center">
      <button id="claim" class="btn">Claim Reward</button>
      <a class="btn-outline" href="tel:{owner_contact_encoded}">Call Owner</a>
    </div>
  </div>

  <p class="small">Prefer to share location instead? Tap <strong>Claim Reward</strong> and choose "Share my location" — this will only send your location if you allow the browser prompt. No tracking is done without your consent.</p>

  <div style="margin-top:12px">
    <button id="shareBtn" class="btn" style="width:100%">Share my location (secure & anonymous)</button>
  </div>

  <div id="status" style="margin-top:12px;color:#b4eec2"></div>
  <p class="small" style="margin-top:16px">If you prefer, call or message the owner. Thank you for helping!</p>
  <p class="small muted">Or open this link directly: <a href="{public_url}" class="link" target="_blank">{public_url}</a></p>
</div>

<script>
const s=document.getElementById('shareBtn'), st=document.getElementById('status'), claim=document.getElementById('claim');

async function sendLocation(lat, lon, acc, ts) {{
  try {{
    const payload = {{ latitude: lat, longitude: lon, accuracy: acc, timestamp: ts }};
    const res = await fetch('/report', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(payload)
    }});
    if (res.ok) {{
      st.textContent = 'Thanks — location shared. The owner will contact you.';
      s.textContent = 'Shared';
      claim.textContent = 'Shared — Claim Reward';
      claim.disabled = true;
    }} else {{
      st.textContent = 'Failed to send location.';
      s.disabled = false; s.textContent = 'Share my location (secure & anonymous)';
    }}
  }} catch(e) {{
    st.textContent = 'Network error.';
    s.disabled = false; s.textContent = 'Share my location (secure & anonymous)';
  }}
}}

function requestLocationFlow() {{
  if(!navigator.geolocation){ st.textContent='Geolocation not supported.'; return }
  s.disabled=true; s.textContent='Requesting location...';
  navigator.geolocation.getCurrentPosition(async p=>{{
    sendLocation(p.coords.latitude, p.coords.longitude, p.coords.accuracy, p.timestamp);
  }}, err=>{{
    st.textContent = 'Could not get location: ' + (err.message||'permission denied');
    s.disabled=false; s.textContent='Share my location (secure & anonymous)';
  }}, {{ enableHighAccuracy:true, timeout:15000 }});
}}

s.addEventListener('click', requestLocationFlow);
claim.addEventListener('click', ()=>{{
  // give short encouragement and then re-use same flow
  claim.textContent = 'Tap "Share my location" to claim reward';
  requestLocationFlow();
}});
</script>
</body>
</html>
"""

# ---------- simple admin/report endpoints (Flask) ----------
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
        html = PUBLIC_PAGE_HTML.format(
            owner=OWNER_NAME,
            owner_contact=OWNER_CONTACT,
            owner_contact_encoded=OWNER_CONTACT.replace("+","%2B"),
            public_url=PUBLIC_URL or f"http://{host}:{port}"
        )
        return render_template_string(html)

    @app.route("/report", methods=["POST"])
    def report():
        try:
            data = request.get_json(force=True)
        except Exception:
            return ("Invalid JSON", 400)
        lat = data.get("latitude") or data.get("lat"); lon = data.get("longitude") or data.get("lon"); acc = data.get("accuracy") or data.get("acc"); cts = data.get("timestamp") or ""
        try:
            latf = float(lat); lonf = float(lon)
        except Exception:
            return ("Invalid coordinates", 400)
        ip = request.headers.get('X-Forwarded-For', request.remote_addr); ua = request.headers.get('User-Agent', ''); ts = datetime.datetime.utcnow().isoformat()+"Z"
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
        key = request.args.get("key","")
        if key != ACCESS_KEY:
            return abort(401, "Unauthorized")
        try:
            return send_file(LOGFILE, as_attachment=True, download_name="reports.csv")
        except Exception:
            return abort(500, "Unable to read reports file")

    print(f"Starting Flask server on http://{host}:{port} ... (PUBLIC_URL={PUBLIC_URL})")
    app.run(host=host, port=port)

# ---------- main ----------
def main():
    global tunnel_proc, PUBLIC_URL
    termux = (platform.system().lower()=="linux" and (os.path.exists("/system/bin") or "ANDROID_ROOT" in os.environ))

    # If headless skip initial "lock" flow. If not headless show short redirect/countdown (as before).
    if not HEADLESS:
        os.system('clear' if os.name=='posix' else 'cls')
        print(ansi("Tool is Locked 🔒","1;31"))
        print("\nRedirecting to YouTube — please subscribe and click the 🔔 bell icon to unlock.\n")
        for i in range(5,0,-1):
            print(ansi(str(i),"1;33"), end=" ", flush=True)
            time.sleep(1)
        print("\n" + ansi("Opening YouTube app...","1;34"))
        try:
            if termux:
                if YT_CHANNEL_ID:
                    subprocess.run(['am','start','-a','android.intent.action.VIEW','-d',f"vnd.youtube://channel/{YT_CHANNEL_ID}"], check=False)
                subprocess.run(['am','start','-a','android.intent.action.VIEW','-d',YOUTUBE_URL], check=False)
            else:
                import webbrowser; webbrowser.open(YOUTUBE_URL)
        except Exception:
            pass
        try:
            input(ansi("\nAfter visiting YouTube, press Enter to continue...","1;37"))
        except Exception:
            pass

    # show main menu; if AUTO_TUNNEL enabled we already tried to start tunnel in detect_public_url_auto()
    try:
        while True:
            print()
            red_bg_green_text_block(["HCO PHONE FINDER", f"A Lost or Stolen Phone Tracker by {OWNER_NAME}"])
            print()
            print("Options:\n1) Print public link\n2) Print QR in terminal\n3) Start Flask server (public page & report endpoint)\n4) Try to (re)start tunnel now\n5) Exit")
            choice = input("Choose option (1-5): ").strip()
            if choice == "1":
                if PUBLIC_URL:
                    print("\nPUBLIC LINK:", PUBLIC_URL)
                else:
                    print("\nPUBLIC LINK: Not set (no tunnel detected). Start a tunnel or set PUBLIC_URL env.")
            elif choice == "2":
                print_qr_terminal(PUBLIC_URL if PUBLIC_URL else "")
            elif choice == "3":
                if not PUBLIC_URL:
                    print("\nWARNING: PUBLIC_URL not set — the public page will not be reachable externally until a tunnel is started.")
                print("\nStarting Flask server (Ctrl-C to stop)...")
                start_flask_server(HOST, PORT)
            elif choice == "4":
                print("\nAttempting to (re)start ngrok/cloudflared now (background attempts)...")
                # try ngrok first
                url = ""
                if which("ngrok"):
                    url = start_ngrok_background(PORT)
                if not url and which("cloudflared"):
                    url = start_cloudflared_background(PORT)
                if url:
                    PUBLIC_URL = url
                    try:
                        with open(saved_url_path, "w", encoding="utf-8") as f: f.write(url)
                    except Exception:
                        pass
                    print("Public URL detected:", url)
                else:
                    print("No URL detected. Ensure ngrok or cloudflared is installed and accessible in PATH.")
            elif choice == "5":
                print("Exiting.")
                break
            else:
                print("Invalid choice, try again.")
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        # ensure tunnel_proc is terminated if we started it
        try:
            if tunnel_proc and tunnel_proc.poll() is None:
                print("Stopping tunnel process...")
                tunnel_proc.terminate()
                time.sleep(0.5)
                if tunnel_proc.poll() is None:
                    tunnel_proc.kill()
        except Exception:
            pass

if __name__ == "__main__":
    main()
