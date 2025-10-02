#!/usr/bin/env python3
"""
HCO-Phone-Finder.py
Single-file Flask app (Termux & Linux friendly)

Features requested by user:
 - "Tool is locked — redirecting to YouTube subscribe click bell 🔔 icon to unlock" overlay
 - Countdown: 9.8.7.6.5.4.3.2.1
 - Attempt to open YouTube app (vnd.youtube deep link) and fallback to web
 - Once user returns & presses Enter, reveal the main page:
       A red box containing the title in GREEN:
         HCO Phone Finder
         A Lost or Stolen Phone Tracker by Azhar
   (no ASCII art)
 - Below title: the public (Cloudflare/ngrok) link and QR code
 - Voluntary browser Geolocation "Share my location" button that POSTs coords to /report
 - Reports saved to reports.csv and printed to console
 - Admin page protected by ACCESS_KEY env var
 - Colorful UI (CSS)

USAGE (Termux / Linux):
1. Install Python + deps:
   Termux:
     pkg update -y
     pkg install -y python
     pip install --upgrade pip
     pip install flask qrcode[pil] pillow

   Linux (Debian/Ubuntu):
     sudo apt update
     sudo apt install -y python3 python3-pip
     python3 -m pip install --user --upgrade pip
     pip3 install flask qrcode[pil] pillow

2. Export env vars (example):
   export ACCESS_KEY="super_secret_admin_key"
   export OWNER_NAME="Azhar"
   export OWNER_CONTACT="+91-XXXXXXXXXX"
   export PUBLIC_URL="https://abcd-1234.trycloudflare.com"    # set after you start tunnel
   export YT_CHANNEL_ID="UCxxxxxxxxxxxxxxxx"                 # optional - deep link
   export YOUTUBE_URL="https://www.youtube.com/@hackers_colony_tech"  # fallback web

3. Run:
   python3 HCO-Phone-Finder.py --host 0.0.0.0 --port 5000

4. Expose with cloudflared/ngrok and set PUBLIC_URL env var (so QR appears).
   cloudflared tunnel --url http://localhost:5000

LEGAL & ETHICAL: Use only to recover your OWN lost/stolen device or with clear consent.
"""

from flask import Flask, request, render_template_string, send_file, abort
import os, csv, io, base64, datetime as dt, argparse, qrcode

app = Flask(__name__)

# Config via environment variables
ACCESS_KEY = os.environ.get("ACCESS_KEY", "changeme_change_this_key")
OWNER_NAME = os.environ.get("OWNER_NAME", "Azhar")
OWNER_CONTACT = os.environ.get("OWNER_CONTACT", "+91-XXXXXXXXXX")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "")
YT_CHANNEL_ID = os.environ.get("YT_CHANNEL_ID", "")
YOUTUBE_URL = os.environ.get("YOUTUBE_URL", "https://www.youtube.com")

LOGFILE = "reports.csv"

# Ensure CSV header
if not os.path.exists(LOGFILE):
    with open(LOGFILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp_utc","ip","user_agent","latitude","longitude","accuracy","client_ts_ms","notes"])

def make_qr_base64(url):
    if not url:
        return ""
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return "data:image/png;base64," + b64

INDEX_HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HCO Phone Finder</title>
<style>
  :root{
    --bg:#08101a; --card:#0f1720; --muted:#9fb0c2; --accent:#0b84ff; --good:#17d05a;
    --danger:#d93025; --panel:#071118;
  }
  html,body{height:100%;margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;background:linear-gradient(180deg,var(--bg),#041018);color:#e6f0f6}
  .wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
  .card{background:linear-gradient(180deg,var(--card),#071219);padding:22px;border-radius:14px;box-shadow:0 12px 40px rgba(2,6,10,0.7);max-width:820px;width:100%}
  .muted{color:var(--muted);font-size:14px}
  .btn{background:var(--accent);color:white;border:none;padding:10px 14px;border-radius:10px;font-weight:700;cursor:pointer}
  .btn:disabled{opacity:.6;cursor:default}
  .callbtn{background:#2fb871;margin-left:10px}
  .redBox{background:#ffecec;border:3px solid var(--danger);padding:14px;border-radius:10px;display:inline-block}
  .titleGreen{color:#00ff66;font-weight:800;font-size:20px;line-height:1.1}
  .infoRow{margin-top:12px}
  .small{font-size:13px;color:#9fb0c2}
  footer{margin-top:14px;color:#94a9b8;font-size:13px}
  img.qr{margin-top:10px;border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,0.5);}

  /* LOCK OVERLAY */
  #lockOverlay{position:fixed;left:0;top:0;width:100%;height:100%;background:linear-gradient(180deg,rgba(2,6,10,0.9),rgba(2,6,10,0.96));display:flex;align-items:center;justify-content:center;z-index:9999}
  #lockBox{background:linear-gradient(180deg,#07121a,#071522);padding:26px;border-radius:12px;max-width:560px;width:92%;text-align:center;color:#dbeefc;box-shadow:0 12px 50px rgba(0,0,0,0.8)}
  #count{font-size:44px;color:#ffd54d;margin:10px 0;font-weight:900}
  a.ytbtn{display:inline-block;padding:12px 16px;border-radius:10px;background:#ff0000;color:white;font-weight:800;text-decoration:none;margin-top:10px}
  .smallmuted{color:#9fb0c2;font-size:13px;margin-top:8px}
</style>
</head>
<body>
  <div class="wrap">
    <div class="card" id="mainCard" tabindex="0" role="main" aria-live="polite">
      <!-- Hidden header area (revealed after unlocking) -->
      <div id="headerArea" style="display:none">
        <div class="redBox">
          <div class="titleGreen">HCO Phone Finder<br><span style="font-size:14px;color:#007a2e;font-weight:700">A Lost or Stolen Phone Tracker by Azhar</span></div>
        </div>

        <div class="infoRow muted" style="margin-top:10px">
          Public link: <strong id="publicLink">{{public_display}}</strong>
        </div>

        <div class="infoRow">
          {% if qr_data %}
            <img class="qr" src="{{qr_data}}" alt="QR for public URL" />
          {% else %}
            <div class="small">(Set PUBLIC_URL env var after creating your tunnel to display QR)</div>
          {% endif %}
        </div>

        <hr style="border:none;border-top:1px solid rgba(255,255,255,0.04);margin:14px 0" />

        <p class="muted">This page will <strong>only</strong> be used to receive the finder’s location <em>if they voluntarily allow</em> the browser's location permission.</p>

        <div style="margin-top:8px">
          <button id="shareBtn" class="btn">Share my location</button>
          <a class="btn callbtn" href="tel:{{owner_phone_href}}">Call owner</a>
        </div>

        <div id="status" class="smallmuted" style="margin-top:12px"></div>

        <footer>
          Contact: {{owner_contact}} &nbsp; • &nbsp; Please act honestly — location is shared only if you allow it.
        </footer>
      </div>

      <noscript>
        <div class="redBox"><div class="titleGreen">HCO Phone Finder</div></div>
        <p class="muted">JavaScript is required for the unlock flow and location sharing. Please enable JavaScript.</p>
      </noscript>
    </div>
  </div>

  <!-- LOCK overlay: shows subscribe + bell instruction + countdown -->
  <div id="lockOverlay" aria-hidden="false">
    <div id="lockBox" role="dialog" aria-modal="true" aria-labelledby="lockTitle">
      <h2 id="lockTitle" style="margin:0;color:#fff">Tool Locked — Subscribe to Unlock</h2>
      <p class="smallmuted">Click subscribe and the 🔔 bell icon on our YouTube channel to unlock the page. After countdown we'll try to open YouTube in the YouTube app (if available). When you return, press <strong>Enter</strong> to continue.</p>

      <div id="count">9</div>

      <div>
        <a id="openYT" class="ytbtn" href="#" target="_blank">Open YouTube</a>
      </div>
      <div class="smallmuted" style="margin-top:8px">If YouTube doesn't open automatically, tap the button above. After subscribing, return and press Enter.</div>
    </div>
  </div>

<script>
const COUNT_START = 9;
let count = COUNT_START;
const countEl = document.getElementById('count');
const lockOverlay = document.getElementById('lockOverlay');
const openYT = document.getElementById('openYT');

const ytChannelId = "{{yt_channel_id}}";
const ytWeb = "{{youtube_url}}";
let appLink = "";
let webLink = ytWeb || "https://www.youtube.com";

if (ytChannelId && ytChannelId.length>6){
  // app deep link and web fallback to channel
  appLink = "vnd.youtube://channel/" + ytChannelId;
  webLink = "https://www.youtube.com/channel/" + ytChannelId;
}

// set the openYT href to web fallback (button)
openYT.href = webLink;

// countdown behaviour
function tick(){
  countEl.textContent = count;
  if (count <= 0){
    // show open button (already visible) and attempt to open app deep link
    try {
      if (appLink){
        // attempt to open youtube app; some browsers may block - fallback to web
        window.location = appLink;
        setTimeout(()=>{ window.open(webLink, '_blank'); }, 700);
      } else {
        window.open(webLink, '_blank');
      }
    } catch(e){}
    document.getElementById('count').textContent = "Opening YouTube...";
    return;
  }
  count -= 1;
  setTimeout(tick, 700);
}
tick();

// Reveal main content when user presses Enter
function revealMain(){
  lockOverlay.style.display = "none";
  document.getElementById('headerArea').style.display = "block";
  document.getElementById('mainCard').focus();
}
document.addEventListener('keydown', function(ev){
  if (ev.key === 'Enter' && lockOverlay.style.display !== 'none'){
    revealMain();
  }
});

// location sharing
const shareBtn = document.getElementById('shareBtn');
const status = document.getElementById('status');
if (shareBtn){
  shareBtn.addEventListener('click', () => {
    if (!navigator.geolocation){
      status.textContent = 'Geolocation not supported by this browser.';
      return;
    }
    shareBtn.disabled = true;
    shareBtn.textContent = 'Requesting permission...';
    navigator.geolocation.getCurrentPosition(async (pos) => {
      const payload = { latitude: pos.coords.latitude, longitude: pos.coords.longitude, accuracy: pos.coords.accuracy, timestamp: pos.timestamp };
      try {
        const res = await fetch('/report', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
        if (res.ok){
          status.innerHTML = '<span style="color:#7be37b;font-weight:700">Thanks — location shared. Owner will follow up.</span>';
          shareBtn.textContent = 'Shared';
        } else {
          status.textContent = 'Server error sending location.';
          shareBtn.disabled = false;
          shareBtn.textContent = 'Share my location';
        }
      } catch(e){
        status.textContent = 'Network error while sending location.';
        shareBtn.disabled = false;
        shareBtn.textContent = 'Share my location';
      }
    }, (err) => {
      status.textContent = 'Could not get location: ' + (err.message || 'permission denied');
      shareBtn.disabled = false;
      shareBtn.textContent = 'Share my location';
    }, { enableHighAccuracy:true, timeout:15000, maximumAge:0 });
  });
}
</script>
</body>
</html>
"""

ADMIN_HTML = """
<!doctype html>
<html><head><meta charset="utf-8"><title>Reports</title>
<style>body{font-family:system-ui;padding:20px;background:#f5f7fa}table{border-collapse:collapse;width:100%}th,td{padding:8px;border:1px solid #ddd}</style>
</head><body>
  <h2>HCO-Phone-Finder Reports</h2>
  <p><a href="/">Open public page</a> | <a href="/download?key={{key}}">Download CSV</a></p>
  <table>
  <thead><tr><th>UTC Time</th><th>IP</th><th>User Agent</th><th>Lat</th><th>Lon</th><th>Acc</th><th>Notes</th></tr></thead>
  <tbody>
  {% for r in rows %}
    <tr><td>{{r[0]}}</td><td>{{r[1]}}</td><td style="max-width:360px;overflow:auto">{{r[2]}}</td><td>{{r[3]}}</td><td>{{r[4]}}</td><td>{{r[5]}}</td><td>{{r[7]}}</td></tr>
  {% endfor %}
  </tbody>
  </table>
</body></html>
"""

@app.route("/")
def index():
    qr = make_qr_base64(PUBLIC_URL) if PUBLIC_URL else ""
    public_display = PUBLIC_URL if PUBLIC_URL else "(set PUBLIC_URL env var after creating tunnel)"
    owner_phone_href = OWNER_CONTACT if OWNER_CONTACT.startswith("+") else OWNER_CONTACT
    return render_template_string(INDEX_HTML,
                                  public_display=public_display,
                                  qr_data=qr,
                                  owner_contact=OWNER_CONTACT,
                                  owner_phone_href=owner_phone_href,
                                  yt_channel_id=YT_CHANNEL_ID,
                                  youtube_url=YOUTUBE_URL)

@app.route("/report", methods=["POST"])
def report():
    data = request.get_json(silent=True) or {}
    lat = data.get("latitude")
    lon = data.get("longitude")
    acc = data.get("accuracy")
    client_ts = data.get("timestamp")
    try:
        lat = float(lat)
        lon = float(lon)
    except Exception:
        return ("Invalid coordinates", 400)
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    ua = request.headers.get('User-Agent', '')
    ts = dt.datetime.utcnow().isoformat() + "Z"
    with open(LOGFILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([ts, ip, ua, lat, lon, acc, client_ts, "voluntary_share"])
    print(f"[{ts}] REPORT from {ip} UA:{ua} lat={lat} lon={lon} acc={acc} client_ts={client_ts}")
    return ("OK", 200)

@app.route("/admin")
def admin():
    key = request.args.get("key","")
    if key != ACCESS_KEY:
        return abort(401, "Unauthorized")
    rows = []
    with open(LOGFILE, "r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        next(r, None)
        for row in r:
            rows.append(row)
    rows = rows[::-1]
    return render_template_string(ADMIN_HTML, rows=rows, key=ACCESS_KEY)

@app.route("/download")
def download():
    key = request.args.get("key","")
    if key != ACCESS_KEY:
        return abort(401, "Unauthorized")
    return send_file(LOGFILE, as_attachment=True, download_name="reports.csv")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HCO-Phone-Finder single-file app")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT",5000)))
    args = parser.parse_args()
    print("Starting HCO-Phone-Finder on http://%s:%s" % (args.host, args.port))
    app.run(host=args.host, port=args.port)
