"""
PhD Headhunter Web Dashboard
A Flask web server to control and monitor the PhD agent with custom inputs.
"""
from flask import Flask, render_template_string, jsonify, request
import subprocess
import os
import threading
import json
from datetime import datetime

app = Flask(__name__)

# Store run status
run_status = {
    "is_running": False,
    "last_run": None,
    "last_result": None,
    "log_output": "",
    "last_keywords": "",
    "last_recipient": ""
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PhD Headhunter Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 40px;
            max-width: 700px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        h1 { color: #1a1a2e; text-align: center; margin-bottom: 5px; font-size: 2em; }
        .subtitle { color: #666; text-align: center; margin-bottom: 25px; }
        .emoji { font-size: 3em; text-align: center; margin-bottom: 10px; }
        
        .input-section {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            border: 1px solid #dee2e6;
        }
        .input-section h3 {
            color: #495057;
            margin-bottom: 15px;
            font-size: 1.1em;
        }
        .input-group {
            margin-bottom: 15px;
        }
        .input-group label {
            display: block;
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }
        .input-group input, .input-group textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #dee2e6;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        .input-group input:focus, .input-group textarea:focus {
            border-color: #667eea;
            outline: none;
        }
        .input-group textarea {
            min-height: 80px;
            resize: vertical;
        }
        .input-hint {
            font-size: 12px;
            color: #888;
            margin-top: 5px;
        }
        
        .status-box {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px 20px;
            margin-bottom: 20px;
        }
        .status-item { display: flex; justify-content: space-between; margin: 8px 0; }
        .status-label { font-weight: 600; color: #333; }
        .status-value { color: #666; }
        .status-running { color: #f39c12; font-weight: bold; }
        .status-idle { color: #27ae60; }
        
        .run-btn {
            width: 100%;
            padding: 18px 40px;
            font-size: 1.2em;
            font-weight: bold;
            color: white;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 15px;
        }
        .run-btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }
        .run-btn:disabled { background: #ccc; cursor: not-allowed; }
        .run-btn.running {
            background: linear-gradient(135deg, #f39c12 0%, #e74c3c 100%);
            animation: pulse 2s infinite;
        }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
        
        .log-box {
            background: #1a1a2e;
            color: #0f0;
            font-family: 'Courier New', monospace;
            font-size: 11px;
            padding: 15px;
            border-radius: 10px;
            max-height: 180px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        .footer { text-align: center; margin-top: 20px; color: #999; font-size: 0.85em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="emoji">🎓</div>
        <h1>PhD Headhunter</h1>
        <p class="subtitle">Automated PhD Position Finder</p>
        
        <div class="input-section">
            <h3>🔧 Search Configuration</h3>
            
            <div class="input-group">
                <label for="keywords">📑 PhD Keywords (comma-separated)</label>
                <textarea id="keywords" placeholder="e.g., Machine Learning, 5G, Cybersecurity, Signal Processing, IoT"></textarea>
                <p class="input-hint">Leave empty to use default keywords from the config</p>
            </div>
            
            <div class="input-group">
                <label for="recipientEmail">📧 Send Results To (Email)</label>
                <input type="email" id="recipientEmail" placeholder="e.g., yourname@gmail.com" value="">
                <p class="input-hint">Results will be sent to this email. Status notifications go to owner.</p>
            </div>
        </div>
        
        <div class="status-box">
            <div class="status-item">
                <span class="status-label">Status:</span>
                <span id="status" class="status-value status-idle">Idle</span>
            </div>
            <div class="status-item">
                <span class="status-label">Last Run:</span>
                <span id="lastRun" class="status-value">Never</span>
            </div>
            <div class="status-item">
                <span class="status-label">Last Result:</span>
                <span id="lastResult" class="status-value">-</span>
            </div>
        </div>
        
        <button id="runBtn" class="run-btn" onclick="runAgent()">
            🚀 Run PhD Agent Now
        </button>
        
        <div class="log-box" id="logOutput">Waiting for action...</div>
        
        <div class="footer">
            PhD Headhunter v1.2 | Written by A.Mehrban (amehrb@gmail.com) | Hostinger VPS
        </div>
    </div>

    <script>
        function updateStatus() {
            fetch('/status')
                .then(res => res.json())
                .then(data => {
                    const statusEl = document.getElementById('status');
                    const runBtn = document.getElementById('runBtn');
                    
                    if (data.is_running) {
                        statusEl.textContent = '⏳ Running...';
                        statusEl.className = 'status-value status-running';
                        runBtn.disabled = true;
                        runBtn.textContent = '⏳ Agent is Running...';
                        runBtn.classList.add('running');
                    } else {
                        statusEl.textContent = '✅ Idle';
                        statusEl.className = 'status-value status-idle';
                        runBtn.disabled = false;
                        runBtn.textContent = '🚀 Run PhD Agent Now';
                        runBtn.classList.remove('running');
                    }
                    
                    document.getElementById('lastRun').textContent = data.last_run || 'Never';
                    document.getElementById('lastResult').textContent = data.last_result || '-';
                    document.getElementById('logOutput').textContent = data.log_output || 'Waiting for action...';
                });
        }
        
        function runAgent() {
            const keywords = document.getElementById('keywords').value.trim();
            const recipientEmail = document.getElementById('recipientEmail').value.trim();
            
            if (recipientEmail && !recipientEmail.includes('@')) {
                alert('Please enter a valid email address');
                return;
            }
            
            document.getElementById('runBtn').disabled = true;
            document.getElementById('logOutput').textContent = 'Starting PhD Agent...';
            
            fetch('/run', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ keywords: keywords, recipient_email: recipientEmail })
            })
                .then(res => res.json())
                .then(data => {
                    document.getElementById('logOutput').textContent = data.message;
                    updateStatus();
                });
        }
        
        setInterval(updateStatus, 3000);
        updateStatus();
    </script>
</body>
</html>
"""

def run_agent_background(keywords="", recipient_email=""):
    """Run the PhD agent in background with custom parameters"""
    global run_status
    run_status["is_running"] = True
    run_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_status["last_keywords"] = keywords
    run_status["last_recipient"] = recipient_email
    run_status["log_output"] = f"Starting PhD Headhunter Agent...\n"
    
    if keywords:
        run_status["log_output"] += f"Custom keywords: {keywords}\n"
    if recipient_email:
        run_status["log_output"] += f"Results will be sent to: {recipient_email}\n"
    run_status["log_output"] += "-" * 40 + "\n"
    
    try:
        # Build command with parameters
        cmd = ["python3", "main.py"]
        if recipient_email:
            cmd.extend(["--recipient", recipient_email])
        if keywords:
            cmd.extend(["--keywords", keywords])
        
        # Run main.py with parameters
        process = subprocess.Popen(
            cmd,
            cwd="/root/phd_agent",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Capture output
        output_lines = []
        for line in process.stdout:
            output_lines.append(line)
            run_status["log_output"] = "".join(output_lines[-50:])
        
        process.wait()
        
        if process.returncode == 0:
            run_status["last_result"] = "✅ Success"
        else:
            run_status["last_result"] = f"❌ Failed (code {process.returncode})"
            
    except Exception as e:
        run_status["last_result"] = f"❌ Error: {str(e)}"
        run_status["log_output"] += f"\nError: {str(e)}"
    
    run_status["is_running"] = False

@app.route('/')
@app.route('/PhD_hunt')
@app.route('/phd_hunt')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/status')
def status():
    return jsonify(run_status)

@app.route('/run', methods=['POST'])
def run():
    global run_status
    
    if run_status["is_running"]:
        return jsonify({"success": False, "message": "Agent is already running!"})
    
    # Get parameters from request
    data = request.get_json() or {}
    keywords = data.get("keywords", "")
    recipient_email = data.get("recipient_email", "")
    
    # Start agent in background thread
    thread = threading.Thread(target=run_agent_background, args=(keywords, recipient_email))
    thread.daemon = True
    thread.start()
    
    msg = "PhD Agent started!"
    if recipient_email:
        msg += f" Results will be sent to {recipient_email}"
    return jsonify({"success": True, "message": msg})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
