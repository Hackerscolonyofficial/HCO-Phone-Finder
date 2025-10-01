#!/usr/bin/env python3
# Filename: HCO-Phone-Finder.py
"""
HCO-Phone-Finder (single-file)
- Auto IP + fingerprint on page load (no geolocation prompt)
- Tokenized catcher links: /t/<token>
- IP enrichment via ip-api.com
- Basic Auth for owner endpoints
- Optional Telegram & email alerts (configure via ENV vars)
Author: Azhar
"""
import os
import json
import csv
import uuid
import datetime
import functools
import traceback
from flask import Flask, request, jsonify, Response, url_for

app = Flask(__name__)

# ---------------- CONFIG ----------------
PORT = int(os.environ.get("PORT", 5000))
HOST = "0.0.0.0"

TOKENS_FILE = "tokens.json"
VISIT_LOG = "visitors.json"
VISIT_CSV = "visitors.csv"
SUBMIT_FILE = "submissions.json"

# Alerts (optional) - set these env vars to enable
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT") or 587)
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
ALERT_EMAIL_TO = os.environ.get("ALERT_EMAIL_TO")  # comma separated

# Owner credentials (HTTP Basic Auth) - MUST change for production via environment
OWNER_USER = os.environ.get("OWNER_USER", "admin")
OWNER_PASS = os.environ.get("OWNER_PASS", "changeme")

# free IP enrichment endpoint
IP_API_URL = "http://ip-api.com/json/{ip}?fields=status,country,regionName,city,zip,timezone,isp,org,as,lat,lon,query"
# ----------------------------------------

def ensure_files():
    for f in (TOKENS_FILE, VISIT_LOG, VISIT_CSV, SUBMIT_FILE):
        if not os.path.exists(f):
            open(f, "a").close()
    if os.path.exists(VISIT_CSV) and os.path.getsize(VISIT_CSV) == 0:
        with open(VISIT_CSV, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(["timestamp","token","label","ip","ip_enrich","ua","fingerprint_summary"])
ensure_files()

def load_tokens():
    try:
        return json.load(open(TOKENS_FILE, encoding="utf-8"))
    except:
        return {}

def save_tokens(d):
    json.dump(d, open(TOKENS_FILE, "w", encoding="utf-8"), indent=2)

def create_token(label="device"):
    toks = load_tokens()
    token = uuid.uuid4().hex[:10]
    toks[token] = {"label": label, "created": datetime.datetime.utcnow().isoformat()+"Z"}
    save_tokens(toks)
    return token

def client_ip(req):
    for h in ("X-Forwarded-For","X-Real-IP","CF-Connecting-IP","True-Client-IP"):
        v = req.headers.get(h)
        if v:
            return v.split(",")[0].strip()
    return req.remote_addr

def ip_enrich(ip):
    try:
        import requests
        r = requests.get(IP_API_URL.format(ip=ip), timeout=6)
        if r.ok:
            return r.json()
    except Exception as e:
        return {"error": str(e)}
    return {}

def log_visit(entry):
    with open(VISIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    with open(VISIT_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            entry.get("timestamp"),
            entry.get("token"),
            entry.get("label",""),
            entry.get("ip",""),
            json.dumps(entry.get("ip_enrich","{}"), ensure_ascii=False),
            entry.get("user_agent",""),
            entry.get("fingerprint_summary","")
        ])

def log_submit(e):
    with open(SUBMIT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")

def alert_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        import requests
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=6)
        return True
    except Exception:
        return False

def alert_email(subject, body):
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS and ALERT_EMAIL_TO):
        return False
    try:
        import smtplib
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["From"] = SMTP_USER
        msg["To"] = ALERT_EMAIL_TO
        msg["Subject"] = subject
        msg.set_content(body)
        s = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
        s.quit()
        return True
    except Exception:
        return False

# Basic auth decorator
def require_auth(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username != OWNER_USER or auth.password != OWNER_PASS:
            return Response('Authentication required', 401, {'WWW-Authenticate':'Basic realm="HCO-Owner"'})
        return f(*args, **kwargs)
    return wrapper

# ---------------- Routes ----------------

@app.route("/")
def info():
    base = request.url_root.rstrip("/")
    return jsonify({
        "ok": True,
        "message": "HCO-Phone-Finder (auto IP + fingerprint)",
        "create_token_example": base + "/new?label=AzharPixel",
        "owner_ui": base + "/owner (auth)",
        "public_example": base + "/t/<token>"
    })

@app.route("/owner")
@require_auth
def owner_ui():
    base = request.url_root.rstrip("/")
    html = """
<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>HCO Owner</title></head><body style="font-family:system-ui">
<h2>HCO-Phone-Finder — Owner UI</h2>
<p>Create token: <code>{base}/new?label=AzharPixel</code></p>
<p>List tokens: <a href="/tokens">/tokens</a></p>
<p>View logs: <a href="/logs">/logs</a></p>
</body></html>
""".replace("{base}", base)
    return html

@app.route("/new")
@require_auth
def new_token():
    label = request.args.get("label", "device")
    token = create_token(label)
    link = url_for("serve_token", token=token, _external=True)
    return jsonify({"token": token, "label": label, "link": link})

@app.route("/tokens")
@require_auth
def tokens_list():
    return jsonify(load_tokens())

@app.route("/t/<token>")
def serve_token(token):
    toks = load_tokens()
    if token not in toks:
        return "Invalid token", 404
    label = toks[token].get("label","device")
    # HTML template uses double braces for literal JS/JSON braces so .format() works safely
    html_template = """
<!doctype html>
<html>
<head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Found a phone — Help return it</title>
<style>body{{font-family:system-ui;background:#f8fafc;color:#0f172a;padding:18px}} .card{{max-width:720px;margin:18px auto;padding:16px;border-radius:10px;background:#fff;box-shadow:0 4px 14px rgba(2,6,23,.08)}}</style>
</head><body>
<div class="card" role="main">
  <h1>Found a phone?</h1>
  <p>This device appears to belong to <strong>{label}</strong>. If you help by contacting the owner we will arrange return and offer a reward.</p>
  <p>Contact: <a href="mailto:your-email@example.com">your-email@example.com</a></p>
  <p style="font-size:0.95rem;color:#334155">This page automatically notifies the owner (IP and device info) when opened. No photos or messages are accessed.</p>
  <div id="status" style="margin-top:12px">Notified: <span id="not">no</span></div>
</div>

<script>
const token = "{token}";
function gather(){{
  try{{
    const fp = {{
      ts: new Date().toISOString(),
      ua: navigator.userAgent || "",
      platform: navigator.platform || "",
      language: navigator.language || "",
      languages: navigator.languages || [],
      screen: {{w: screen.width, h: screen.height}},
      connection: (navigator.connection ? {{type: navigator.connection.effectiveType || navigator.connection.type, downlink: navigator.connection.downlink, rtt: navigator.connection.rtt}} : {{}}),
      battery: null
    }};
    if (navigator.getBattery){{
      navigator.getBattery().then(b=>{{
        fp.battery = {{charging: b.charging, level: b.level}};
        send(fp);
      }}).catch(e=>{{ send(fp); }});
    }} else {{
      send(fp);
    }}
  }}catch(e){{
    send({{error: String(e)}});
  }}
}}

function send(fp){{
  fetch("/report", {{method:"POST", headers:{{"Content-Type":"application/json"}}, body: JSON.stringify({{token:token, fingerprint: fp}})}})
    .then(r=>r.json()).then(j=>{{
      document.getElementById("not").innerText = "yes";
    }}).catch(e=>{{
      document.getElementById("not").innerText = "error";
    }});
}}

window.addEventListener("load", function(){{ setTimeout(gather, 400); }});
</script>
</body></html>
"""
    html = html_template.format(token=token, label=label)
    return html

@app.route("/report", methods=["POST"])
def report():
    try:
        data = request.get_json(force=True)
    except:
        return jsonify({"ok": False, "error": "invalid json"}), 400
    token = data.get("token")
    toks = load_tokens()
    label = toks.get(token,{}).get("label","") if token else ""
    ip = client_ip(request)
    ua = request.headers.get("User-Agent","")
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    ipinfo = ip_enrich(ip)
    fp = data.get("fingerprint", {})
    # small summary of fingerprint to include in CSV
    try:
        pf_platform = fp.get("platform","")
        pf_ua = fp.get("ua","")
    except:
        pf_platform = ""
        pf_ua = ""
    fp_summary = f"{pf_platform} | {pf_ua}"
    entry = {
        "timestamp": ts,
        "token": token,
        "label": label,
        "ip": ip,
        "ip_enrich": ipinfo,
        "user_agent": ua,
        "fingerprint": fp,
        "fingerprint_summary": fp_summary,
        "raw": data
    }
    log_visit(entry)
    # alert owner (concise)
    short = f"HCO hit {ts}\\nToken:{token} ({label})\\nIP:{ip} -> {ipinfo.get('city','')},{ipinfo.get('country','')}\\nUA:{ua}"
    try:
        alert_telegram(short)
        alert_email("HCO-Phone-Finder hit", short + "\\n\\nFull entry:\\n" + json.dumps(entry, indent=2))
    except:
        pass
    return jsonify({"ok": True, "entry": {"ip": ip, "ts": ts}})

@app.route("/submit", methods=["POST"])
@require_auth
def submit():
    try:
        d = request.get_json(force=True)
    except:
        return jsonify({"ok": False, "error": "invalid json"}), 400
    e = {"timestamp": datetime.datetime.utcnow().isoformat()+"Z", "imei": d.get("imei"), "link": d.get("link"), "label": d.get("label")}
    log_submit(e)
    return jsonify({"ok": True, "entry": e})

@app.route("/logs")
@require_auth
def logs():
    out=[]
    if os.path.exists(VISIT_LOG):
        with open(VISIT_LOG,"r", encoding="utf-8") as f:
            for ln in f:
                ln=ln.strip()
                if ln:
                    try:
                        out.append(json.loads(ln))
                    except:
                        pass
    return jsonify(out)

@app.route("/health")
def health():
    return jsonify({"ok":True,"time":datetime.datetime.utcnow().isoformat()+"Z"})

if __name__ == "__main__":
    print("Starting HCO-Phone-Finder on port", PORT)
    app.run(host=HOST, port=PORT)
