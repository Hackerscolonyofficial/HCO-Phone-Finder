#!/usr/bin/env python3
# HCO Phone Finder - Advanced Hacker-style Termux Tool
# Author: Azhar
# License: MIT

import os
import sys
import time
from colorama import init, Fore, Back, Style

# Initialize colorama
init(autoreset=True)

# YouTube redirect link
YOUTUBE_LINK = "https://youtube.com/@hackers_colony_tech?si=pvdCWZggTIuGb0ya"

# Cloudflare link placeholder
CLOUDFLARE_LINK = "https://your-cloudflare-link.example"

def glitch_countdown():
    """Glitchy hacker-style countdown"""
    countdown = [9,8,7,6,5,4,3,2,1]
    for num in countdown:
        # Random glitch effect
        print(Fore.RED + Style.BRIGHT + f"[{num}] " + Fore.CYAN + "~!@#$%^&*()", end="\r")
        time.sleep(0.7)
        print(Fore.YELLOW + Style.BRIGHT + f"[{num}] " + Fore.MAGENTA + "TRACKING...", end="\r")
        time.sleep(0.7)
    print("\n")

def open_youtube():
    """Open YouTube in Termux properly"""
    print(Fore.GREEN + "\nOpening YouTube for subscription...")
    try:
        # termux-open-url opens the link in the default Android app
        os.system(f"termux-open-url {YOUTUBE_LINK}")
    except:
        print(Fore.RED + "Failed to open YouTube automatically. Open manually: " + YOUTUBE_LINK)

def lock_screen():
    os.system("clear")
    print(Fore.RED + "="*50)
    print(Fore.RED + "⚠️  Subscribe to unlock the tool! ⚠️".center(50))
    print(Fore.RED + "="*50)
    glitch_countdown()
    open_youtube()
    input(Fore.YELLOW + "\nPress Enter after subscribing...")

def show_banner():
    os.system("clear")
    print(Back.BLUE + Fore.RED + "="*70)
    print(Back.BLUE + Fore.RED + "HCO Phone Finder – A Phone Tracking Tool by Azhar".center(70))
    print(Back.BLUE + Fore.RED + "="*70)
    print("\n" + Fore.GREEN + "Cloudflare link to access tool:")
    print(Fore.CYAN + CLOUDFLARE_LINK + "\n")

def main():
    lock_screen()
    show_banner()
    print(Fore.MAGENTA + "Tool is ready! Start tracking phones responsibly.")
    print(Fore.MAGENTA + "Remember: This tool is for educational purposes only!")

if __name__ == "__main__":
    main()
