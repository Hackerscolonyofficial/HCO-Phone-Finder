#!/usr/bin/env python3
# Filename: HCO-Phone-Finder.py
"""
HCO-Phone-Finder (single-file, advanced)
- Tokenized catcher links: /t/<token>
- Auto-capture public IP + browser fingerprint on page load (no geolocation prompt)
- IP enrichment via ip-api.com
- Owner endpoints protected with HTTP Basic Auth
- Owner dashboard (/dashboard), export logs (zip), FIR template generator
- Daily log rotation into logs/ directory
- Optional Telegram & Email alerts (configure via ENV)
- Optional AES encryption-at-rest if LOG_KEY (Fernet) is set (install cryptography)
Author: Azhar
Usage (Termux):
  pkg update -y
  pkg install python git -y
  pip install flask requests cryptography
  export OWNER_USER="azhar"
  export OWNER_PASS="verystrongpassword"
  python3 HCO-Phone-Finder.py
Legal: Use only for devices you own or with explicit permission. Do not confront suspects.
"""
import os, io, sys, json, csv, uuid, datetime, functools, traceback, zipfile, base64
from flask import Flask, request, jsonify, Response, url_for, send_file

app = Flask(__name__)

# ---------------- CONFIG ----------------
PORT = int(os.environ.get("PORT", 5000))
HOST = "0.0.0.0"

TOKENS_FILE = "tokens.json"
SUBMIT_FILE = "submissions.json"

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Optional alerts (set env vars to enable)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT") or 587)
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
ALERT_EMAIL_TO = os.environ.get("ALERT_EMAIL_TO")  # comma separated

# Owner credentials (required for owner endpoints)
OWNER_USER = os.environ.get("OWNER_USER", "admin")
OWNER_PASS = os.environ.get("OWNER_PASS", "changeme")

# IP enrichment API (free)
IP_API_URL = "http://ip-api.com/json/{ip}?fields=status,country,regionName,city,zip,timezone,isp,org,as,lat,lon,query"

# Optional encryption key (Fernet base64). Generate with:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
LOG_KEY = os.environ.get("LOG_KEY")  # optional

# Try to import cryptography if LOG_KEY set
FERNET = None
if LOG_KEY:
    try:
        from cryptography.fernet import Fernet
        FERNET = Fernet(LOG_KEY.encode())
    except Exception as e:
        print("LOG_KEY set but cryptography unavailable or key invalid:", e, file=sys.stderr)
        FERNET = None

# ----------------------------------------

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

def ensure_daily_files():
    date = datetime.datetime.utcnow().strftime("%Y%m%d")
    jfile = os.path.join(LOG_DIR, f"visitors-{date}.json")
    cfile = os.path.join(LOG_DIR, f"visitors-{date}.csv")
    if not os.path.exists(jfile):
        open(jfile, "a", encoding="utf-8").close()
    if not os.path.exists(cfile):
        with open(cfile, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(["timestamp","token","label","ip","ip_enrich_json","user_agent","fingerprint_summary"])
    return jfile, cfile

def encrypt_bytes(b: bytes) -> bytes:
    if FERNET:
        return FERNET.encrypt(b)
    return b

def decrypt_bytes(b: bytes) -> bytes:
    if FERNET:
        return FERNET.decrypt(b)
    return b

def append_json_log(entry):
    jfile, cfile = ensure_daily_files()
    line = json.dumps(entry, ensure_ascii=False)
    data = line.encode("utf-8")
    data = encrypt_bytes(data)
    with open(jfile, "ab") as f:
        f.write(base64.b64encode(data) + b"\n")
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

def read_all_logs():
    out = []
    for fname in sorted(os.listdir(LOG_DIR), reverse=True):
        if fname.startswith("visitors-") and fname.endswith(".json"):
            path = os.path.join(LOG_DIR, fname)
            try:
                with open(path, "rb") as f:
                    for raw in f:
                        raw = raw.strip()
                        if not raw:
                            continue
                        try:
                            b = base64.b64decode(raw)
                            b = decrypt_bytes(b)
                            entry = json.loads(b.decode("utf-8", errors="ignore"))
                            entry["_source_file"] = fname
                            out.append(entry)
                        except Exception:
                            continue
            except Exception:
                continue
    return out

def alert_telegram(text):
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
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
    except Exception as e:
        print("Email send failed:", e)
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
        "message": "HCO-Phone-Finder (advanced single-file)",
        "create_token_example": base + "/new?label=AzharPixel",
        "owner_ui": base + "/owner (auth)",
        "public_example": base + "/t/<token>"
    })

@app.route("/owner")
@require_auth
def owner_ui():
    base = request.url_root.rstrip("/")
    html = f"""
<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>HCO Owner</title></head><body style="font-family:system-ui">
<h2>HCO-Phone-Finder — Owner UI</h2>
<ul>
<li>Create token: <code>{base}/new?label=AzharPixel</code></li>
<li>Dashboard: <a href="/dashboard">/dashboard</a></li>
<li>List tokens: <a href="/tokens">/tokens</a></li>
<li>Export logs (zip): <a href="/export_logs">/export_logs</a></li>
</ul>
</body></html>
"""
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
    return html_template.format(token=token, label=label)

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
    append_json_log(entry)
    short = f"HCO hit {ts}\\nToken:{token} ({label})\\nIP:{ip} -> {ipinfo.get('city','')},{ipinfo.get('country','')}\\nUA:{ua}"
    try:
        alert_telegram(short)
        alert_email("HCO-Phone-Finder hit", short + "\\n\\nFull entry:\\n" + json.dumps(entry, indent=2))
    except:
        pass
    return jsonify({"ok": True, "entry": {"ip": ip, "ts": ts}})

@app.route("/dashboard")
@require_auth
def dashboard():
    logs = read_all_logs()
    items = logs[:50]
    rows = ""
    for i, e in enumerate(items):
        ipinfo = e.get("ip_enrich") or {}
        city = ipinfo.get("city","")
        isp = ipinfo.get("isp","")
        ua_trunc = (e.get("user_agent") or "")[:80]
        rows += "<tr>"
        rows += f"<td>{i+1}</td>"
        rows += f"<td>{e.get('timestamp')}</td>"
        rows += f"<td>{e.get('token')}</td>"
        rows += f"<td>{e.get('label')}</td>"
        rows += f"<td>{e.get('ip')}<br><small>{city} / {isp}</small></td>"
        rows += f"<td>{ua_trunc}</td>"
        rows += f"<td><pre style='white-space:pre-wrap'>{(e.get('fingerprint_summary') or '')}</pre></td>"
        rows += f"<td><a href='/generate_fir?file={e.get('_source_file')}&ts={e.get('timestamp')}'>FIR</a></td>"
        rows += "</tr>"
    html = f"""
<!doctype html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>HCO Dashboard</title>
<style>body{{font-family:system-ui;padding:12px}} table{{width:100%;border-collapse:collapse}} th,td{{border:1px solid #ddd;padding:6px;font-size:13px}} th{{background:#f3f4f6}}</style>
</head><body>
<h2>HCO-Phone-Finder — Dashboard (last {len(items)} hits)</h2>
<p><a href="/export_logs">Export logs (zip)</a> | <a href="/tokens">Tokens</a> | <a href="/owner">Owner UI</a></p>
<table><thead><tr><th>#</th><th>Time</th><th>Token</th><th>Label</th><th>IP (city / ISP)</th><th>UA (truncated)</th><th>FP summary</th><th>FIR</th></tr></thead><tbody>
{rows}
</tbody></table>
</body></html>
"""
    return html

@app.route("/export_logs")
@require_auth
def export_logs():
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(TOKENS_FILE):
            zf.write(TOKENS_FILE, arcname=os.path.basename(TOKENS_FILE))
        if os.path.exists(SUBMIT_FILE):
            zf.write(SUBMIT_FILE, arcname=os.path.basename(SUBMIT_FILE))
        for f in sorted(os.listdir(LOG_DIR)):
            path = os.path.join(LOG_DIR, f)
            if os.path.isfile(path):
                if f.endswith(".json"):
                    plain_lines = []
                    with open(path, "rb") as fh:
                        for raw in fh:
                            raw = raw.strip()
                            if not raw:
                                continue
                            try:
                                b = base64.b64decode(raw)
                                b = decrypt_bytes(b)
                                plain_lines.append(b.decode("utf-8", errors="ignore"))
                            except Exception:
                                continue
                    if plain_lines:
                        zf.writestr(f"plain_{f}", "\n".join(plain_lines))
                else:
                    zf.write(path, arcname=f)
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name="hco_phone_finder_logs.zip", mimetype="application/zip")

@app.route("/generate_fir")
@require_auth
def generate_fir():
    file = request.args.get("file")
    ts = request.args.get("ts")
    if not file or not ts:
        return "Provide file and ts (timestamp) query parameters", 400
    path = os.path.join(LOG_DIR, file)
    if not os.path.exists(path):
        return "File not found", 404
    target = None
    with open(path, "rb") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                b = base64.b64decode(raw)
                b = decrypt_bytes(b)
                e = json.loads(b.decode("utf-8", errors="ignore"))
                if e.get("timestamp") == ts:
                    target = e
                    break
            except Exception:
                continue
    if not target:
        return "Entry not found", 404
    body = f"""To: [Officer-in-charge / ISP Abuse Desk]

Subject: Request to Trace Device / Subscriber — Lost phone (IMEI: <YOUR-IMEI>)

I report my lost phone (owner: <Your Name>, model/brand: {target.get('label','')}, IMEI: <YOUR-IMEI>, last known contact time: {target.get('timestamp')}). I observed a connection to my server from IP: {target.get('ip')} with ISP: {target.get('ip_enrich',{{}}).get('isp','')}. Attached are server logs showing the exact request and headers.

Request:
Please advise steps to request subscriber details associated with IP {target.get('ip')} at time {target.get('timestamp')} for the purposes of recovery.

Server log excerpt:
{json.dumps(target, indent=2)}

Regards,
<Your full name>
<Contact phone/email>
"""
    send_now = request.args.get("send")
    if send_now and (SMTP_HOST and SMTP_USER and SMTP_PASS and ALERT_EMAIL_TO):
        ok = alert_email("FIR Request - HCO Phone Finder", body)
        return jsonify({"sent": ok, "to": ALERT_EMAIL_TO})
    html = f"""
<!doctype html><html><body style="font-family:system-ui;padding:12px">
<h2>FIR Template (copy & paste)</h2>
<pre style="white-space:pre-wrap;background:#f3f4f6;padding:12px;border-radius:8px">{body}</pre>
<p>Edit IMEI & contact details then copy/paste into police/ISP email or print.</p>
</body></html>
"""
    return html

@app.route("/submit", methods=["POST"])
@require_auth
def submit():
    try:
        d = request.get_json(force=True)
    except:
        return jsonify({"ok": False, "error": "invalid json"}), 400
    e = {"timestamp": datetime.datetime.utcnow().isoformat()+"Z", "imei": d.get("imei"), "link": d.get("link"), "label": d.get("label")}
    with open(SUBMIT_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    return jsonify({"ok": True, "entry": e})

@app.route("/logs")
@require_auth
def logs():
    return jsonify(read_all_logs())

@app.route("/health")
def health():
    return jsonify({"ok":True,"time":datetime.datetime.utcnow().isoformat()+"Z"})

if __name__ == "__main__":
    print("Starting HCO-Phone-Finder (advanced) on port", PORT)
    app.run(host=HOST, port=PORT)
