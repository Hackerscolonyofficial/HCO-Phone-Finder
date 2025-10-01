#!/usr/bin/env python3
# HCO Phone Finder - Single File Termux Tool
# Author: Azhar
# License: MIT

import os
import time
import webbrowser
from colorama import init, Fore, Back, Style

# Initialize Colorama
init(autoreset=True)

# YouTube redirect link
YOUTUBE_LINK = "https://youtube.com/@hackers_colony_tech?si=pvdCWZggTIuGb0ya"

# Cloudflare link placeholder (replace with your actual link)
CLOUDFLARE_LINK = "https://your-cloudflare-link.example"

def countdown_timer():
    print(Fore.YELLOW + "\nCountdown to unlock the tool:")
    for i in range(9, 0, -1):
        print(Fore.CYAN + str(i))
        time.sleep(1)

def lock_screen():
    os.system("clear")
    print(Fore.RED + "="*50)
    print(Fore.RED + "⚠️  Subscribe to unlock the tool! ⚠️".center(50))
    print(Fore.RED + "="*50)
    countdown_timer()
    print(Fore.GREEN + "\nOpening YouTube to subscribe...")
    try:
        webbrowser.open(YOUTUBE_LINK)
    except:
        print(Fore.RED + "Failed to open YouTube. Open manually: " + YOUTUBE_LINK)
    input(Fore.YELLOW + "\nPress Enter after subscribing...")

def show_banner():
    os.system("clear")
    print(Back.BLUE + Fore.RED + "="*60)
    print(Back.BLUE + Fore.RED + "HCO Phone Finder – A Phone Tracking Tool by Azhar".center(60))
    print(Back.BLUE + Fore.RED + "="*60)
    print("\n" + Fore.GREEN + "Cloudflare link to access tool:")
    print(Fore.CYAN + CLOUDFLARE_LINK + "\n")

def main():
    lock_screen()
    show_banner()
    print(Fore.MAGENTA + "Tool is ready! Start tracking phones responsibly.")
    print(Fore.MAGENTA + "Remember: This tool is for educational purposes only!")

if __name__ == "__main__":
    main()
