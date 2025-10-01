#!/usr/bin/env python3
# Filename: HCO-Phone-Finder.py
"""
HCO Phone Finder - Termux-friendly launcher with automatic Cloudflared startup
- Glitchy countdown lock + redirects to YouTube (termux-open-url / am / webbrowser)
- Attempts to auto-run cloudflared tunnel and capture the public URL
- Shows blue box with red HCO Phone Finder banner and the auto-found Cloudflare URL
- Best-effort: will try `pkg install cloudflared -y` if cloudflared binary missing (Termux)
Author: Azhar
"""
import os
import sys
import time
import random
import re
import subprocess
import shutil
import webbrowser
from shutil import which

# colorama (optional fallback)
try:
    from colorama import init as _colorama_init, Fore, Back, Style
    _colorama_init(autoreset=True)
except Exception:
    class _Fake:
        RESET_ALL = BRIGHT = ""
    class _F:
        RED = GREEN = YELLOW = MAGENTA = CYAN = ""
    class _B:
        BLUE = ""
    Fore = _F(); Back = _B(); Style = _Fake()

# Config
YOUTUBE_LINK = os.environ.get("HCO_YOUTUBE", "https://youtube.com/@hackers_colony_tech?si=pvdCWZggTIuGb0ya")
CLOUDFLARE_ENV = "CLOUDFLARE_URL"
CLOUDFLARE_URL = os.environ.get(CLOUDFLARE_ENV)  # may be None
CLOUDFLARE_CMD = ["cloudflared", "tunnel", "--url", "http://127.0.0.1:5000"]

CLOUDFLARE_PROCESS = None

def clear():
    os.system("clear" if os.name != "nt" else "cls")

def glitch_line(text, width=66):
    noise = "".join(random.choice("~!@#$%^&*()_+<>?/\\|") for _ in range(random.randint(0,6)))
    s = text
    if len(s) > width:
        s = s[:width]
    return f"{s} {noise}"

def hacker_countdown():
    seq = list(range(9, 0, -1))
    clear()
    print(Fore.YELLOW + Style.BRIGHT + "="*66)
    print(Fore.RED + Style.BRIGHT + "  SUBSCRIBE TO UNLOCK HCO PHONE FINDER".center(66))
    print(Fore.YELLOW + Style.BRIGHT + "="*66 + "\n")
    for n in seq:
        print(Fore.CYAN + Style.BRIGHT + (" " * 25) + f"[ {n} ]")
        for _ in range(2):
            line = glitch_line(f"scanning network interfaces... {random.randint(100,999)} packets", 66)
            print(Fore.MAGENTA + line)
            time.sleep(0.15)
        time.sleep(0.45)
        print("\n")
    for i in range(3):
        print(Fore.GREEN + Style.BRIGHT + glitch_line("INITIALIZING LAUNCH SEQUENCE", 60))
        time.sleep(0.12)

def try_termux_open(url):
    if which("termux-open-url"):
        try:
            subprocess.Popen(["termux-open-url", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False
    return False

def try_am_start(url):
    if which("am"):
        try:
            subprocess.Popen(["am", "start", "-a", "android.intent.action.VIEW", "-d", url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False
    return False

def open_url_fallback(url):
    if try_termux_open(url):
        return True
    if try_am_start(url):
        return True
    if which("xdg-open"):
        try:
            subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            pass
    try:
        webbrowser.open(url, new=2)
        return True
    except Exception:
        return False

def open_youtube():
    print(Fore.GREEN + "\nOpening YouTube channel (will try app first)...")
    ok = open_url_fallback(YOUTUBE_LINK)
    if ok:
        print(Fore.CYAN + "(YouTube opened; if nothing happened, open this link manually):")
    else:
        print(Fore.RED + "Could not auto-open YouTube. Please open this link manually:")
    print(Fore.YELLOW + YOUTUBE_LINK)

# --- Cloudflared helpers ---

def ensure_cloudflared_installed():
    """Check for cloudflared; if missing, try to install via pkg (best-effort)."""
    if which("cloudflared"):
        return True
    print(Fore.YELLOW + "cloudflared not found on system.")
    # Best-effort attempt to install in Termux
    if which("pkg"):
        print(Fore.CYAN + "Attempting: pkg install cloudflared -y (Termux). This may prompt for confirmation or fail)")
        try:
            rc = subprocess.call(["pkg", "install", "cloudflared", "-y"])
            if rc == 0 and which("cloudflared"):
                print(Fore.GREEN + "cloudflared installed.")
                return True
            else:
                print(Fore.RED + "pkg install cloudflared failed or cloudflared not available in package repo.")
                return False
        except Exception:
            return False
    else:
        return False

def start_cloudflared_and_get_url(timeout=30):
    """
    Start cloudflared tunnel --url http://127.0.0.1:5000 and read stdout to find the public URL.
    Returns (process, url) or (None, None) on failure.
    """
    if not which("cloudflared"):
        ok = ensure_cloudflared_installed()
        if not ok:
            return None, None

    try:
        # spawn cloudflared
        p = subprocess.Popen(CLOUDFLARE_CMD, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    except Exception as e:
        print(Fore.RED + f"Failed to start cloudflared: {e}")
        return None, None

    url = None
    start = time.time()
    url_regex = re.compile(r"https://[^\s]+trycloudflare\.com|https://[A-Za-z0-9\-]+\.trycloudflare\.com|https://[^\s]+\.trycloudflare\.com")
    # also check for any https://... when printed
    generic_https = re.compile(r"https://[^\s]+")
    print(Fore.CYAN + "Starting cloudflared tunnel; waiting for public URL (timeout {}s)...".format(timeout))
    try:
        # read lines until timeout or url found
        while True:
            if time.time() - start > timeout:
                break
            line = p.stdout.readline()
            if not line:
                # process might have exited or still producing nothing; check poll
                if p.poll() is not None:
                    break
                time.sleep(0.1)
                continue
            line = line.strip()
            # debug print suppressed; only show concise lines
            # try to find trycloudflare URL
            m = url_regex.search(line)
            if m:
                url = m.group(0)
                break
            m2 = generic_https.search(line)
            if m2:
                # as a fallback accept first https line (could be about updates, but ok)
                url = m2.group(0)
                # don't break immediately if it's something like https://developers.google.com ... but we'll accept
                break
            # continue looping
        if url:
            print(Fore.GREEN + "Public URL detected: " + url)
            return p, url
        else:
            # didn't find url within timeout
            print(Fore.YELLOW + "Cloudflared did not produce a public URL within timeout.")
            # show last few lines from process output for debugging
            try:
                # attempt to read remaining output
                remaining = p.stdout.read(1024)
                if remaining:
                    print(Fore.MAGENTA + "cloudflared output (snippet):")
                    print(remaining.strip())
            except Exception:
                pass
            return p, None
    except Exception as e:
        print(Fore.RED + "Error while reading cloudflared output: " + str(e))
        return p, None

def stop_cloudflared(proc):
    try:
        if proc and proc.poll() is None:
            proc.terminate()
            time.sleep(0.5)
            if proc.poll() is None:
                proc.kill()
    except Exception:
        pass

# --- Main lock & flow ---

def lock_and_open_youtube_and_cloudflared():
    hacker_countdown()
    open_youtube()
    print(Fore.MAGENTA + "\nAttempting to start Cloudflared (for public URL). This may take a moment...")
    global CLOUDFLARE_URL, CLOUDFLARE_PROCESS
    # if user already provided a URL env var, skip starting
    if CLOUDFLARE_URL and CLOUDFLARE_URL.strip():
        print(Fore.GREEN + f"Using existing CLOUDFLARE_URL from environment: {CLOUDFLARE_URL}")
    else:
        proc, url = start_cloudflared_and_get_url(timeout=30)
        CLOUDFLARE_PROCESS = proc
        if url:
            CLOUDFLARE_URL = url
            os.environ[CLOUDFLARE_ENV] = url
            print(Fore.GREEN + "Cloudflared public URL set automatically: " + url)
        else:
            print(Fore.RED + "Could not auto-obtain Cloudflared URL. See instructions after unlocking.")
    print(Fore.MAGENTA + "\nWhen you're done with YouTube/subscription, return here and press ENTER.")
    try:
        input(Fore.GREEN + "Press ENTER to continue: ")
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
        # cleanup
        stop_cloudflared(CLOUDFLARE_PROCESS)
        sys.exit(0)

def show_banner_and_cleanup():
    clear()
    box_width = 72
    title = "HCO Phone Finder – A Phone Tracking Tool by Azhar"
    print(Back.BLUE + " " * box_width)
    print(Back.BLUE + Fore.RED + Style.BRIGHT + title.center(box_width) + Style.RESET_ALL)
    print(Back.BLUE + " " * box_width + Style.RESET_ALL + "\n")
    if CLOUDFLARE_URL and CLOUDFLARE_URL.strip():
        print(Fore.GREEN + "Your public Cloudflare (tunnel) URL (auto-detected):")
        print(Fore.CYAN + CLOUDFLARE_URL.strip() + "\n")
    else:
        print(Fore.YELLOW + "Cloudflare/Public URL not configured or auto-detection failed.")
        print(Fore.YELLOW + "To create a public tunnel, install cloudflared and run:")
        print(Fore.CYAN + "  cloudflared tunnel --url http://127.0.0.1:5000")
        print(Fore.CYAN + "Or set CLOUDFLARE_URL env var with the public URL.")
        print()
    print(Fore.MAGENTA + "Tool unlocked. Use responsibly and only on devices you own.")
    print(Fore.MAGENTA + "Do NOT attempt to confront anyone — hand evidence to police.\n")
    # keep cloudflared running (if started), but warn
    if CLOUDFLARE_PROCESS:
        print(Fore.CYAN + "cloudflared process started in background (PID {}).".format(CLOUDFLARE_PROCESS.pid))
        print(Fore.CYAN + "To stop it later, run: pkill cloudflared  OR close this Termux session.\n")

def main():
    clear()
    print(Fore.CYAN + Style.BRIGHT + "HCO-Phone-Finder (launcher)".center(66))
    print(Fore.CYAN + "-"*66 + "\n")
    lock_and_open_youtube_and_cloudflared()
    show_banner_and_cleanup()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(Fore.RED + "Unexpected error: " + str(e))
    finally:
        # don't kill cloudflared automatically if it was successfully started and gave URL
        # but if it was started and didn't give URL, terminate it to avoid stray process
        if CLOUDFLARE_PROCESS and (not CLOUDFLARE_URL):
            stop_cloudflared(CLOUDFLARE_PROCESS)
