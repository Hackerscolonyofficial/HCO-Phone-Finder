#!/usr/bin/env python3
# Filename: HCO-Phone-Finder.py
"""
HCO Phone Finder - Termux-friendly single-file launcher (hacker-style lock + banner)
- Shows a glitchy countdown: 9..1
- Opens YouTube with several fallbacks (termux-open-url -> am start -> webbrowser)
- Waits for ENTER, then shows a blue box with red banner:
    HCO Phone Finder – A Phone Tracking Tool by Azhar
- Displays a Cloudflare/public link if provided via env var CLOUDFLARE_URL (recommended)
- Safe defaults: if CLOUDFLARE_URL not set, shows a friendly instruction rather than a broken placeholder

Run in Termux:
  pkg install python -y
  pip install colorama
  export CLOUDFLARE_URL="https://your-public-url.trycloudflare.com"   # set this after starting cloudflared
  python3 HCO-Phone-Finder.py
"""
import os
import sys
import time
import random
import webbrowser
from shutil import which

# Try to import colorama; if unavailable, provide simple fallback
try:
    from colorama import init as _colorama_init, Fore, Back, Style
    _colorama_init(autoreset=True)
except Exception:
    class _C:
        RESET_ALL = ""
        BRIGHT = ""
    class _F:
        RED = ""
        GREEN = ""
        YELLOW = ""
        MAGENTA = ""
        CYAN = ""
    class _B:
        BLUE = ""
    Fore = _F()
    Back = _B()
    Style = _C()

# Config: YouTube channel to open and Cloudflare/public URL
YOUTUBE_LINK = os.environ.get("HCO_YOUTUBE", "https://youtube.com/@hackers_colony_tech?si=pvdCWZggTIuGb0ya")
CLOUDFLARE_URL = os.environ.get("CLOUDFLARE_URL")  # set this env var to your public tunnel URL

def clear():
    os.system("clear" if os.name != "nt" else "cls")

def try_termux_open(url):
    """Attempt to open URL using termux-open-url (recommended on Termux)."""
    if which("termux-open-url"):
        try:
            os.system(f"termux-open-url '{url}' &")
            return True
        except Exception:
            return False
    return False

def try_am_start(url):
    """Attempt to open URL via Android 'am start' (works when Termux has access)."""
    if which("am"):
        try:
            # -a android.intent.action.VIEW -d <url>
            os.system(f"am start -a android.intent.action.VIEW -d '{url}' >/dev/null 2>&1 &")
            return True
        except Exception:
            return False
    return False

def open_url_fallback(url):
    """Open URL with best available method on Termux/Android, falling back to webbrowser."""
    # 1) termux-open-url
    if try_termux_open(url):
        return True
    # 2) am start
    if try_am_start(url):
        return True
    # 3) xdg-open (if present)
    if which("xdg-open"):
        try:
            os.system(f"xdg-open '{url}' >/dev/null 2>&1 &")
            return True
        except Exception:
            pass
    # 4) Python webbrowser
    try:
        webbrowser.open(url, new=2)
        return True
    except Exception:
        return False

def glitch_line(text, width=60):
    """Return a glitchy text with random noise appended/truncated for display."""
    noise = "".join(random.choice("~!@#$%^&*()_+<>?/\\|") for _ in range(random.randint(0,6)))
    s = text
    if len(s) > width:
        s = s[:width]
    return f"{s} {noise}"

def hacker_countdown():
    """Glitchy countdown from 9 to 1 with small fake scanning lines."""
    seq = list(range(9, 0, -1))
    clear()
    print(Fore.YELLOW + Style.BRIGHT + "="*66)
    print(Fore.RED + Style.BRIGHT + "  SUBSCRIBE TO UNLOCK HCO PHONE FINDER".center(66))
    print(Fore.YELLOW + Style.BRIGHT + "="*66 + "\n")
    for n in seq:
        # top line — large digit
        print(Fore.CYAN + Style.BRIGHT + (" " * 25) + f"[ {n} ]")
        # scanning lines (fake)
        for _ in range(2):
            line = glitch_line(f"scanning network interfaces... {random.randint(100,999)} packets", 66)
            print(Fore.MAGENTA + line)
            time.sleep(0.15)
        time.sleep(0.45)
        # overwrite small pause (visual effect)
        print("\n")
    # final flourish
    for i in range(3):
        print(Fore.GREEN + Style.BRIGHT + glitch_line("INITIALIZING LAUNCH SEQUENCE", 60))
        time.sleep(0.12)

def lock_and_redirect():
    """Run the lock screen countown and open YouTube via best available method."""
    hacker_countdown()
    print(Fore.GREEN + "\nOpening YouTube channel (will try app first)...")
    success = open_url_fallback(YOUTUBE_LINK)
    if success:
        print(Fore.CYAN + "YouTube opened. If nothing happened, open this link manually:")
        print(Fore.YELLOW + YOUTUBE_LINK)
    else:
        print(Fore.RED + "Could not automatically open YouTube. Please open this link manually:")
        print(Fore.YELLOW + YOUTUBE_LINK)
    print(Fore.MAGENTA + "\nAfter subscribing or viewing, return here and press ENTER.")
    try:
        input(Fore.GREEN + "Press ENTER to continue: ")
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
        sys.exit(0)

def show_banner():
    """Show the blue box with red HCO Phone Finder text and the Cloudflare/public link or instructions."""
    clear()
    box_width = 72
    title = "HCO Phone Finder – A Phone Tracking Tool by Azhar"
    top = Back.BLUE + " " * box_width + Style.RESET_ALL
    print(Back.BLUE + " " * box_width)
    # center red text
    padded = title.center(box_width)
    print(Back.BLUE + Fore.RED + Style.BRIGHT + padded + Style.RESET_ALL)
    print(Back.BLUE + " " * box_width + Style.RESET_ALL + "\n")
    # helpful info
    if CLOUDFLARE_URL and CLOUDFLARE_URL.strip():
        print(Fore.GREEN + "Your public Cloudflare (tunnel) URL:")
        print(Fore.CYAN + CLOUDFLARE_URL.strip() + "\n")
    else:
        print(Fore.YELLOW + "Cloudflare/Public URL not configured.")
        print(Fore.YELLOW + "Start cloudflared (or your tunnel) and set environment variable CLOUDFLARE_URL.")
        print(Fore.CYAN + "Example (cloudflared):")
        print(Fore.CYAN + "  cloudflared tunnel --url http://localhost:5000")
        print(Fore.CYAN + "Then in Termux:")
        print(Fore.CYAN + "  export CLOUDFLARE_URL=\"https://your-public-url.trycloudflare.com\"\n")
    print(Fore.MAGENTA + "Tool unlocked. Use responsibly and only on devices you own.")
    print(Fore.MAGENTA + "Do NOT attempt to confront anyone — hand evidence to police.\n")

def main():
    # friendly header
    clear()
    print(Fore.CYAN + Style.BRIGHT + "HCO-Phone-Finder (launcher)".center(66))
    print(Fore.CYAN + "-"*66 + "\n")
    # lock screen & redirect
    lock_and_redirect()
    # show final banner
    show_banner()

if __name__ == "__main__":
    main()
