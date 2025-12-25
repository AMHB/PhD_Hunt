"""
PhD Headhunter Web Dashboard
A simple Flask web server to control and monitor the PhD agent.
"""
from flask import Flask, render_template_string, jsonify, request
import subprocess
import os
import threading
from datetime import datetime

app = Flask(__name__)

# Store run status
run_status = {
    "is_running": False,
    "last_run": None,
    "last_result": None,
    "log_output": ""
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PhD Headhunter Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
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
            max-width: 600px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        h1 {
            color: #1a1a2e;
            text-align: center;
            margin-bottom: 10px;
            font-size: 2em;
        }
        .subtitle {
            color: #666;
            text-align: center;
            margin-bottom: 30px;
        }
        .status-box {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .status-item {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
        }
        .status-label {
            font-weight: 600;
            color: #333;
        }
        .status-value {
            color: #666;
        }
        .status-running {
            color: #f39c12;
            font-weight: bold;
        }
        .status-idle {
            color: #27ae60;
        }
        .run-btn {
            width: 100%;
            padding: 20px 40px;
            font-size: 1.3em;
            font-weight: bold;
            color: white;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 20px;
        }
        .run-btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }
        .run-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .run-btn.running {
            background: linear-gradient(135deg, #f39c12 0%, #e74c3c 100%);
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .log-box {
            background: #1a1a2e;
            color: #0f0;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            padding: 15px;
            border-radius: 10px;
            max-height: 200px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        .footer {
            text-align: center;
            margin-top: 20px;
            color: #999;
            font-size: 0.9em;
        }
        .emoji {
            font-size: 3em;
            text-align: center;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="emoji">🎓</div>
        <h1>PhD Headhunter</h1>
        <p class="subtitle">Automated PhD Position Finder</p>
        
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
        
        <div class="log-box" id="logOutput">
            Waiting for action...
        </div>
        
        <div class="footer">
            PhD Headhunter v1.1 | Hostinger VPS
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
            document.getElementById('runBtn').disabled = true;
            document.getElementById('logOutput').textContent = 'Starting PhD Agent...';
            
            fetch('/run', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    document.getElementById('logOutput').textContent = data.message;
                    updateStatus();
                });
        }
        
        // Update status every 3 seconds
        setInterval(updateStatus, 3000);
        updateStatus();
    </script>
</body>
</html>
"""

def run_agent_background():
    """Run the PhD agent in background"""
    global run_status
    run_status["is_running"] = True
    run_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_status["log_output"] = "Starting PhD Headhunter Agent...\n"
    
    try:
        # Run main.py
        process = subprocess.Popen(
            ["python3", "main.py"],
            cwd="/root/phd_agent",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Capture output
        output_lines = []
        for line in process.stdout:
            output_lines.append(line)
            run_status["log_output"] = "".join(output_lines[-50:])  # Keep last 50 lines
        
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
    
    # Start agent in background thread
    thread = threading.Thread(target=run_agent_background)
    thread.daemon = True
    thread.start()
    
    return jsonify({"success": True, "message": "PhD Agent started! Check status for updates."})

if __name__ == '__main__':
    # Run on all interfaces, port 5000
    app.run(host='0.0.0.0', port=5000, debug=False)
