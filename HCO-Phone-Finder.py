#!/usr/bin/env python3
# HCO-Phone-Finder.py
# Single-file, simple, ready for GitHub + Termux
# - run Flask server, create token links, capture IP + fingerprint on page load
# - owner endpoints with Basic Auth: /new, /tokens, /logs, /dashboard
# - store logs rotated daily in logs/
# - launcher: hacker-style countdown, open YouTube (termux-friendly), show banner + public URL if CLOUDFLARE_URL env var set
# Author: Azhar (packaged by assistant)
# Legal: Use only for devices you own or with explicit permission.

import os, sys, json, csv, uuid, datetime, functools, time, random, subprocess, socket
from flask import Flask, request, jsonify, Response, url_for

# try optional libs
try:
    import requests
except Exception:
    requests = None

try:
    from colorama import init as colorama_init, Fore, Back, Style
    colorama_init(autoreset=True)
except Exception:
    class _F: RED=GREEN=YELLOW=CYAN=MAGENTA=""
    class _B: BLUE=""
    class _S: BRIGHT=RESET_ALL=""
    Fore=_F(); Back=_B(); Style=_S()

app = Flask(__name__)

# ---------- CONFIG ----------
PORT = int(os.environ.get("PORT", 5000))
HOST = "0.0.0.0"

TOKENS_FILE = "tokens.json"
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

OWNER_USER = os.environ.get("OWNER_USER", "admin")
OWNER_PASS = os.environ.get("OWNER_PASS", "changeme")

IP_API = "http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp,lat,lon,query"
# optional public URL environment variable (set after starting your tunnel)
CLOUDFLARE_URL = os.environ.get("CLOUDFLARE_URL")  # set this to your public tunnel URL if you have one
YOUTUBE_LINK = os.environ.get("HCO_YOUTUBE", "https://youtube.com/@hackers_colony_tech?si=pvdCWZggTIuGb0ya")
# ----------------------------

def ensure_tokens():
    if not os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

def load_tokens():
    ensure_tokens()
    try:
        return json.load(open(TOKENS_FILE, encoding="utf-8"))
    except:
        return {}

def save_tokens(d):
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)

def create_token(label="device"):
    toks = load_tokens()
    token = uuid.uuid4().hex[:10]
    toks[token] = {"label": label, "created": datetime.datetime.utcnow().isoformat()+"Z"}
    save_tokens(toks)
    return token

def client_ip(req):
    for h in ("X-Forwarded-For","X-Real-IP","CF-Connecting-IP"):
        v = req.headers.get(h)
        if v:
            return v.split(",")[0].strip()
    return req.remote_addr

def enrich_ip(ip):
    if not requests:
        return {"note": "requests not installed"}
    try:
        r = requests.get(IP_API.format(ip=ip), timeout=5)
        if r.ok:
            return r.json()
    except Exception as e:
        return {"error": str(e)}
    return {}

def ensure_daily_files():
    date = datetime.datetime.utcnow().strftime("%Y%m%d")
    jfile = os.path.join(LOG_DIR, f"visitors-{date}.json")
    cfile = os.path.join(LOG_DIR, f"visitors-{date}.csv")
    if not os.path.exists(jfile):
        open(jfile, "a", encoding="utf-8").close()
    if not os.path.exists(cfile):
        with open(cfile, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(["timestamp","token","label","ip","ip_enrich","ua","fp_summary"])
    return jfile, cfile

def append_log(entry):
    jfile, cfile = ensure_daily_files()
    with open(jfile, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    with open(cfile, "a", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerow([
            entry.get("timestamp"),
            entry.get("token"),
            entry.get("label",""),
            entry.get("ip",""),
            json.dumps(entry.get("ip_enrich","{}"), ensure_ascii=False),
            entry.get("user_agent",""),
            entry.get("fingerprint_summary","")
        ])

# Basic Auth decorator
def require_auth(f):
    @functools.wraps(f)
    def wrapper(*a, **k):
        auth = request.authorization
        if not auth or auth.username != OWNER_USER or auth.password != OWNER_PASS:
            return Response('Auth required', 401, {'WWW-Authenticate':'Basic realm="HCO-Owner"'})
        return f(*a, **k)
    return wrapper

# ------------------ Flask routes ------------------

@app.route("/")
def info():
    base = request.url_root.rstrip("/")
    return jsonify({
        "ok": True,
        "message": "HCO-Phone-Finder (simple single file)",
        "create_token_example": base + "/new?label=AzharPixel",
        "owner_ui": base + "/owner (auth)",
        "public_example": base + "/t/<token>"
    })

@app.route("/owner")
@require_auth
def owner_ui():
    base = request.url_root.rstrip("/")
    return f"""
<html><body style="font-family:system-ui">
<h2>HCO Owner UI</h2>
<p>Create token: <code>{base}/new?label=AzharPixel</code></p>
<p>Tokens: <a href="/tokens">/tokens</a></p>
<p>Logs (JSON): <a href="/logs">/logs</a></p>
</body></html>
"""

@app.route("/new")
@require_auth
def new_token():
    label = request.args.get("label", "device")
    token = create_token(label)
    link = url_for("serve_token", token=token, _external=True)
    return jsonify({"token": token, "label": label, "link": link})

@app.route("/tokens")
@require_auth
def tokens():
    return jsonify(load_tokens())

@app.route("/t/<token>")
def serve_token(token):
    toks = load_tokens()
    if token not in toks:
        return "Invalid token", 404
    label = toks[token].get("label","device")
    # simple page that auto posts fingerprint to /report
    html = f"""<!doctype html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Found a phone?</title>
<style>body{{font-family:system-ui;background:#f8fafc;padding:18px}} .card{{max-width:720px;margin:18px auto;padding:16px;border-radius:10px;background:#fff;box-shadow:0 6px 18px rgba(0,0,0,.06)}}</style>
</head><body>
<div class="card">
  <h1>Found a phone?</h1>
  <p>This device appears to belong to <strong>{label}</strong>. Please contact the owner: <a href='mailto:your-email@example.com'>your-email@example.com</a></p>
  <p style="color:#555;font-size:13px">This page notifies the owner with IP & basic device info when opened.</p>
  <div id="status">Notified: <span id="not">no</span></div>
</div>
<script>
const token = "{token}";
function gather(){{
  const fp = {{
    ts: new Date().toISOString(),
    ua: navigator.userAgent || "",
    platform: navigator.platform || "",
    language: navigator.language || "",
    screen: {{w: screen.width, h: screen.height}}
  }};
  if (navigator.getBattery){{
    navigator.getBattery().then(b=>{{ fp.battery = {{charging: b.charging, level: b.level}}; send(fp); }}).catch(e=>send(fp));
  }} else send(fp);
}}
function send(fp){{
  navigator.sendBeacon && navigator.sendBeacon('/report', JSON.stringify({{token:token, fingerprint:fp}})) || fetch('/report', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{token:token, fingerprint:fp}})}}).then(r=>r.json()).then(j=>{{document.getElementById('not').innerText='yes'}}).catch(e=>{{document.getElementById('not').innerText='error'}})
}}
window.addEventListener('load', ()=> setTimeout(gather, 300));
</script>
</body></html>"""
    return html

@app.route("/report", methods=["POST"])
def report():
    try:
        data = request.get_json(force=True)
    except:
        return jsonify({"ok": False, "error": "invalid json"}), 400
    token = data.get("token")
    toks = load_tokens()
    label = toks.get(token, {}).get("label","")
    ip = client_ip(request)
    ua = request.headers.get("User-Agent","")
    ts = datetime.datetime.utcnow().isoformat()+"Z"
    ipinfo = enrich_ip(ip)
    fp = data.get("fingerprint", {})
    fp_summary = f"{fp.get('platform','')} | {fp.get('ua','')}" if isinstance(fp, dict) else ""
    entry = {"timestamp": ts, "token": token, "label": label, "ip": ip, "ip_enrich": ipinfo, "user_agent": ua, "fingerprint": fp, "fingerprint_summary": fp_summary}
    append_log(entry)
    return jsonify({"ok": True, "entry": {"ip": ip, "ts": ts}})

@app.route("/logs")
@require_auth
def logs():
    # return last 200 log entries from log files
    out = []
    for fname in sorted(os.listdir(LOG_DIR), reverse=True):
        if fname.startswith("visitors-") and fname.endswith(".json"):
            path = os.path.join(LOG_DIR, fname)
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line=line.strip()
                    if not line: continue
                    try:
                        out.append(json.loads(line))
                        if len(out) >= 200:
                            return jsonify(out)
                    except:
                        continue
    return jsonify(out)

@app.route("/dashboard")
@require_auth
def dashboard():
    base = request.url_root.rstrip("/")
    return f"""
<html><body style="font-family:system-ui;padding:12px">
<h2>HCO Dashboard</h2>
<p>Local server: {base}</p>
<p>Public URL (if set): {os.environ.get('CLOUDFLARE_URL') or 'Not set'}</p>
<p>Use /new?label=NAME to create token, then send the /t/&lt;token&gt; link to the phone.</p>
</body></html>
"""

# ---------------- helper CLI launcher (small & simple) ----------------

def get_local_ip():
    # best-effort local IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't need to succeed; just to choose correct interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def clear_screen():
    os.system("clear" if os.name!="nt" else "cls")

def glitch_countdown():
    seq=list(range(9,0,-1))
    clear_screen()
    print(Fore.YELLOW + "="*56)
    print(Fore.RED + "  SUBSCRIBE TO UNLOCK HCO PHONE FINDER".center(56))
    print(Fore.YELLOW + "="*56 + "\n")
    for n in seq:
        print(Fore.CYAN + f"   [ {n} ] " + Fore.MAGENTA + ("scanning..." + "."*random.randint(1,5)))
        time.sleep(0.6)
    print()

def open_youtube_termux():
    # try termux-open-url -> am -> webbrowser
    if shutil_which("termux-open-url"):
        try:
            subprocess.Popen(["termux-open-url", YOUTUBE_LINK])
            return True
        except:
            pass
    if shutil_which("am"):
        try:
            subprocess.Popen(["am","start","-a","android.intent.action.VIEW","-d",YOUTUBE_LINK])
            return True
        except:
            pass
    try:
        import webbrowser
        webbrowser.open(YOUTUBE_LINK, new=2)
        return True
    except:
        return False

def shutil_which(name):
    return shutil.which(name) if hasattr(shutil, "which") else None

def launcher():
    clear_screen()
    print(Fore.CYAN + "HCO-Phone-Finder launcher".center(56))
    print(Fore.CYAN + "-"*56 + "\n")
    glitch_countdown()
    print(Fore.GREEN + "Opening YouTube channel (try to open in app)...")
    ok = open_youtube_termux()
    if not ok:
        print(Fore.YELLOW + "Could not auto-open YouTube. Open manually:")
        print(YOUTUBE_LINK)
    else:
        print(Fore.CYAN + "YouTube attempted. Return and press ENTER when ready.")
    try:
        input(Fore.GREEN + "Press ENTER to continue: ")
    except KeyboardInterrupt:
        print("\nExiting launcher.")
        return
    # show banner + public link if env provided
    clear_screen()
    title = "HCO Phone Finder – A Phone Tracking Tool by Azhar"
    print(Back.BLUE + " " * 60)
    print(Back.BLUE + Fore.RED + title.center(60))
    print(Back.BLUE + " " * 60 + Style.RESET_ALL + "\n")
    pub = os.environ.get("CLOUDFLARE_URL")
    if pub:
        print(Fore.GREEN + "Public URL (from CLOUDFLARE_URL env):")
        print(Fore.CYAN + pub)
    else:
        ip = get_local_ip()
        print(Fore.YELLOW + "No public URL set. You can create one with cloudflared or ngrok. Example:")
        print(Fore.CYAN + "  cloudflared tunnel --url http://127.0.0.1:5000")
        print(Fore.CYAN + "Then set in Termux: export CLOUDFLARE_URL=\"https://abcd-1234.trycloudflare.com\"")
        print(Fore.CYAN + f"Local links will work on LAN, e.g. http://{ip}:{PORT}")
    print("\n" + Fore.MAGENTA + "Tool ready. Create tokens with /new?label=NAME (owner auth).")

# -------------------- Run server & simple CLI --------------------

def print_startup_info():
    ip = get_local_ip()
    print("\n" + Fore.CYAN + "HCO-Phone-Finder running")
    print(Fore.CYAN + f"Local: http://127.0.0.1:{PORT}")
    print(Fore.CYAN + f"LAN:   http://{ip}:{PORT}")
    if os.environ.get("CLOUDFLARE_URL"):
        print(Fore.CYAN + "Public (from CLOUDFLARE_URL): " + os.environ.get("CLOUDFLARE_URL"))
    print(Fore.YELLOW + f"Owner user: {OWNER_USER}  (set OWNER_USER/OWNER_PASS env vars to change)\n")
    print(Fore.YELLOW + "To create a token (owner auth):")
    print(Fore.YELLOW + f"  curl -u {OWNER_USER}:{OWNER_PASS} http://127.0.0.1:{PORT}/new?label=MyPhone\n")

if __name__ == "__main__":
    # Start server in interactive mode: if run in terminal, give option to run launcher first
    if len(sys.argv) > 1 and sys.argv[1] == "launcher":
        # run only launcher (not server)
        launcher()
        sys.exit(0)
    # Else run server and print info. User can run launcher in separate termux session: python HCO-Phone-Finder.py launcher
    try:
        print_startup_info()
        print(Fore.MAGENTA + "Run launcher in another session: python3 HCO-Phone-Finder.py launcher\n")
        # start Flask app (development server)
        app.run(host=HOST, port=PORT)
    except Exception as e:
        print("Error:", e)
