#!/usr/bin/env python3
"""
HCO-Phone-Finder.py - Fully GitHub-ready single file Termux/Linux tool
Author: Azhar
License: MIT
"""

import os, sys, time, csv, subprocess, platform, datetime

# ---------------- AUTO-LOAD ENV FILE ----------------
home = os.path.expanduser("~")
env_file = os.path.join(home, ".hco_phone_finder_env")

if os.path.exists(env_file):
    print(f"Loading environment variables from {env_file} ...")
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):  # skip empty or comment lines
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                os.environ[key] = val

# ---------------- IMPORT OPTIONAL MODULES ----------------
try:
    from flask import Flask, request, render_template_string, send_file, abort
    import qrcode
    from PIL import Image
    import requests
except Exception:
    Flask = None
    qrcode = None
    Image = None
    requests = None

# ---------------- CONFIG ----------------
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
    env_url = os.environ.get("PUBLIC_URL")
    if env_url: return env_url.rstrip("/")
    home = os.path.expanduser("~")
    saved_path = os.path.join(home, ".hco_public_url")
    if os.path.exists(saved_path):
        with open(saved_path, "r") as f: return f.read().strip().rstrip("/")
    if requests:
        try:
            resp = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=1.5)
            if resp.ok:
                for t in resp.json().get("tunnels", []):
                    pu = t.get("public_url")
                    if pu: return pu.rstrip("/")
        except: pass
    url = input("\nPUBLIC_URL not found. Paste your tunnel URL: ").strip()
    if url:
        save = input("Save for future runs? (Y/n): ").strip().lower()
        if save in ("", "y", "yes"):
            try:
                with open(saved_path, "w") as f: f.write(url)
            except: pass
        return url.rstrip("/")
    return ""

PUBLIC_URL = detect_public_url()

# ---------------- CSV SETUP ----------------
if not os.path.exists(LOGFILE):
    with open(LOGFILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["timestamp_utc","ip","user_agent","latitude","longitude","accuracy","client_ts_ms","notes"])

# ---------------- TERMINAL HELPERS ----------------
def ansi(text: str, code: str) -> str: return f"\033[{code}m{text}\033[0m"
def red_bg_green_text_block(lines): 
    for l in lines: print("\033[41m\033[1;32m " + l + " \033[0m")
def print_qr_terminal(data):
    if not qrcode: 
        print("Install qrcode: pip install qrcode[pil]"); print("Link:", data); return
    qr = qrcode.QRCode(border=1); qr.add_data(data); qr.make(fit=True)
    matrix = qr.get_matrix(); black="\033[40m  \033[0m"; white="\033[47m  \033[0m"; border=2; w=len(matrix[0])+border*2
    for _ in range(border): print(white*w)
    for row in matrix:
        line=white*border
        for col in row: line+=black if col else white
        line+=white*border; print(line)
    for _ in range(border): print(white*w)

# ---------------- YOUTUBE ----------------
def open_youtube_app():
    app_link=f"vnd.youtube://channel/{YT_CHANNEL_ID}" if YT_CHANNEL_ID else None
    if platform.system().lower()=="linux" and ("ANDROID_ROOT" in os.environ or os.path.exists("/system/bin")):
        try:
            if app_link: subprocess.run(['am','start','-a','android.intent.action.VIEW','-d',app_link]); time.sleep(0.8)
            subprocess.run(['am','start','-a','android.intent.action.VIEW','-d',YOUTUBE_URL]); return
        except: pass
    try: import webbrowser; webbrowser.open(YOUTUBE_URL)
    except: print("Open manually:", YOUTUBE_URL)

# ---------------- TERMUX LOCK ----------------
def termux_lock_flow():
    os.system('clear' if os.name=='posix' else 'cls')
    print(ansi("Tool is Locked 🔒","1;31"))
    print("\nRedirecting to YouTube — subscribe to unlock.\n")
    for i in range(9,0,-1): print(ansi(str(i),"1;33"),end=" ",flush=True); time.sleep(1)
    print("\n"+ansi("Opening YouTube app...","1;34")); open_youtube_app()
    input(ansi("\nAfter visiting YouTube, press Enter...","1;37"))

# ---------------- FLASK SERVER ----------------
PUBLIC_PAGE_HTML="""
<!doctype html>
<html><head><meta charset="utf-8"><title>Found Phone</title></head>
<body>
<h2>Lost Phone</h2><p>Owner: {{owner}}, Contact: {{owner_contact}}</p>
<p>Share location voluntarily:</p>
<button onclick="navigator.geolocation.getCurrentPosition(async function(p){await fetch('/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy:p.coords.accuracy,timestamp:p.timestamp})})})">Share Location</button>
<p>Direct link: <a href="{{public_url}}">{{public_url}}</a></p>
</body></html>
"""

def ensure_flask(): return Flask is not None
def start_flask_server(host=HOST, port=PORT):
    if not ensure_flask(): print("Install flask/qrcode/pillow/requests"); return
    app = Flask(__name__)
    @app.route("/"): return PUBLIC_PAGE_HTML.replace("{{owner}}",OWNER_NAME).replace("{{owner_contact}}",OWNER_CONTACT).replace("{{public_url}}",PUBLIC_URL)
    @app.route("/report",methods=["POST"])
    def report():
        data=request.get_json(force=True)
        lat=data.get("latitude"); lon=data.get("longitude"); acc=data.get("accuracy"); cts=data.get("timestamp")
        ip=request.headers.get('X-Forwarded-For',request.remote_addr); ua=request.headers.get('User-Agent',''); ts=datetime.datetime.utcnow().isoformat()+"Z"
        with open(LOGFILE,"a",newline="",encoding="utf-8") as f: csv.writer(f).writerow([ts,ip,ua,lat,lon,acc,cts,"voluntary_share"])
        print(f"[{ts}] REPORT from {ip} UA:{ua} lat={lat} lon={lon} acc={acc}")
        return "OK",200
    @app.route("/admin")
    def admin(): 
        if request.args.get("key")!=ACCESS_KEY: return abort(401)
        with open(LOGFILE,"r",encoding="utf-8") as f: rows=list(csv.reader(f))[1:]
        out="<html><body><h2>Reports</h2><pre>"+str(rows)+"</pre></body></html>"; return out
    print(f"Flask server running at http://{host}:{port}")
    app.run(host=host,port=port,debug=False)

# ---------------- MAIN MENU ----------------
def main_menu():
    while True:
        print("\nOptions:\n1) Print public link\n2) Print QR\n3) Start Flask server\n4) Exit")
        choice=input("Choose (1-4): ").strip()
        if choice=="1": print("\nPUBLIC LINK:",PUBLIC_URL if PUBLIC_URL else "Not set")
        elif choice=="2": print_qr_terminal(PUBLIC_URL if PUBLIC_URL else "Not set")
        elif choice=="3": start_flask_server()
        elif choice=="4": sys.exit(0)
        else: print("Invalid choice.")

# ---------------- ENTRY ----------------
if __name__=="__main__":
    termux_lock_flow()
    main_menu()
