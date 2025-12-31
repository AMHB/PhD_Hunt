"""
PhD Headhunter Web Dashboard
A Flask web server with authentication, admin panel, and PhD agent control.
"""
from flask import Flask, render_template_string, jsonify, request, session, redirect, url_for
import subprocess
import os
import threading
import json
import hashlib
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'phd_hunter_secret_key_2024_secure_session'

# ==================== USER DATABASE ====================
USERS_FILE = "users.json"

def load_users():
    """Load users from JSON file"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    else:
        # Default admin user
        default_users = {
            "amehrb": {
                "password_hash": hash_password("Sullivan198766@p!"),
                "is_admin": True,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        save_users(default_users)
        return default_users

def save_users(users):
    """Save users to JSON file"""
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(username, password):
    """Verify username and password"""
    users = load_users()
    if username in users:
        return users[username]["password_hash"] == hash_password(password)
    return False

def is_admin(username):
    """Check if user is admin"""
    users = load_users()
    return users.get(username, {}).get("is_admin", False)

# ==================== AUTH DECORATORS ====================
def login_required(f):
    """Decorator for routes that require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator for routes that require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        if not is_admin(session['username']):
            return "Access Denied: Admin privileges required", 403
        return f(*args, **kwargs)
    return decorated_function

# ==================== RUN STATUS ====================
run_status = {
    "is_running": False,
    "last_run": None,
    "last_result": None,
    "log_output": "",
    "last_keywords": "",
    "last_recipient": ""
}

# ==================== HTML TEMPLATES ====================
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - PhD Headhunter</title>
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
        .login-container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 50px 40px;
            max-width: 400px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        .emoji { font-size: 4em; text-align: center; margin-bottom: 15px; }
        h1 { color: #1a1a2e; text-align: center; margin-bottom: 10px; font-size: 1.8em; }
        .subtitle { color: #666; text-align: center; margin-bottom: 30px; }
        .input-group { margin-bottom: 20px; }
        .input-group label { display: block; font-weight: 600; color: #333; margin-bottom: 8px; }
        .input-group input {
            width: 100%;
            padding: 15px;
            border: 2px solid #dee2e6;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        .input-group input:focus { border-color: #667eea; outline: none; }
        .login-btn {
            width: 100%;
            padding: 15px;
            font-size: 1.1em;
            font-weight: bold;
            color: white;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .login-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4); }
        .error { background: #ffe6e6; color: #c00; padding: 12px; border-radius: 8px; margin-bottom: 20px; text-align: center; }
        .footer { text-align: center; margin-top: 25px; color: #999; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="emoji">🔐</div>
        <h1>PhD Headhunter</h1>
        <p class="subtitle">Please login to continue</p>
        
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        
        <form method="POST">
            <div class="input-group">
                <label for="username">👤 Username</label>
                <input type="text" id="username" name="username" required placeholder="Enter username">
            </div>
            <div class="input-group">
                <label for="password">🔑 Password</label>
                <input type="password" id="password" name="password" required placeholder="Enter password">
            </div>
            <button type="submit" class="login-btn">🚀 Login</button>
        </form>
        
        <div class="footer">PhD Headhunter v1.3 | Secured Access</div>
    </div>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel - PhD Headhunter</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #2d1f3d 0%, #1a1a2e 100%);
            min-height: 100vh;
            padding: 30px;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 40px;
            max-width: 900px;
            margin: 0 auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        h1 { color: #1a1a2e; font-size: 1.8em; }
        .nav-links a { color: #667eea; text-decoration: none; margin-left: 20px; font-weight: 600; }
        .nav-links a:hover { text-decoration: underline; }
        
        .section { background: #f8f9fa; border-radius: 15px; padding: 25px; margin-bottom: 25px; }
        .section h2 { color: #333; margin-bottom: 20px; font-size: 1.3em; }
        
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #dee2e6; }
        th { background: #667eea; color: white; font-weight: 600; }
        tr:hover { background: #f0f0f0; }
        .badge { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
        .badge-admin { background: #ffc107; color: #333; }
        .badge-user { background: #28a745; color: white; }
        
        .delete-btn { background: #dc3545; color: white; border: none; padding: 6px 12px; border-radius: 5px; cursor: pointer; }
        .delete-btn:hover { background: #c82333; }
        
        .add-form { display: grid; grid-template-columns: 1fr 1fr 1fr auto; gap: 15px; align-items: end; }
        .add-form .input-group { margin: 0; }
        .add-form label { display: block; font-weight: 600; margin-bottom: 5px; color: #333; }
        .add-form input, .add-form select { width: 100%; padding: 10px; border: 2px solid #dee2e6; border-radius: 8px; }
        .add-btn { background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; border: none; padding: 12px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; }
        .add-btn:hover { transform: translateY(-1px); }
        
        .message { padding: 12px; border-radius: 8px; margin-bottom: 20px; }
        .message-success { background: #d4edda; color: #155724; }
        .message-error { background: #f8d7da; color: #721c24; }
        
        .footer { text-align: center; margin-top: 20px; color: #999; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚙️ Admin Panel</h1>
            <div class="nav-links">
                <a href="/PhD_hunt">📊 Dashboard</a>
                <a href="/logout">🚪 Logout</a>
            </div>
        </div>
        
        {% if message %}
        <div class="message message-{{ message_type }}">{{ message }}</div>
        {% endif %}
        
        <div class="section">
            <h2>👥 User Management</h2>
            <table>
                <tr>
                    <th>Username</th>
                    <th>Role</th>
                    <th>Created</th>
                    <th>Action</th>
                </tr>
                {% for username, user in users.items() %}
                <tr>
                    <td>{{ username }}</td>
                    <td><span class="badge {% if user.is_admin %}badge-admin{% else %}badge-user{% endif %}">
                        {% if user.is_admin %}Admin{% else %}User{% endif %}
                    </span></td>
                    <td>{{ user.created }}</td>
                    <td>
                        {% if username != session.username %}
                        <form method="POST" action="/admin/delete" style="display:inline">
                            <input type="hidden" name="username" value="{{ username }}">
                            <button type="submit" class="delete-btn" onclick="return confirm('Delete user {{ username }}?')">🗑️ Delete</button>
                        </form>
                        {% else %}
                        <span style="color:#999">Current user</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
        
        <div class="section">
            <h2>➕ Add New User</h2>
            <form method="POST" action="/admin/add" class="add-form">
                <div class="input-group">
                    <label>Username</label>
                    <input type="text" name="new_username" required placeholder="username">
                </div>
                <div class="input-group">
                    <label>Password</label>
                    <input type="password" name="new_password" required placeholder="password">
                </div>
                <div class="input-group">
                    <label>Role</label>
                    <select name="is_admin">
                        <option value="0">User</option>
                        <option value="1">Admin</option>
                    </select>
                </div>
                <button type="submit" class="add-btn">➕ Add User</button>
            </form>
        </div>
        
        <div class="footer">PhD Headhunter Admin Panel | Logged in as: {{ session.username }}</div>
    </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
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
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .user-info { color: #666; font-size: 0.9em; }
        .user-info a { color: #667eea; text-decoration: none; margin-left: 10px; }
        h1 { color: #1a1a2e; text-align: center; font-size: 2em; }
        .subtitle { color: #666; text-align: center; margin-bottom: 25px; }
        .emoji { font-size: 3em; text-align: center; margin-bottom: 10px; }
        
        .input-section {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            border: 1px solid #dee2e6;
        }
        .input-section h3 { color: #495057; margin-bottom: 15px; font-size: 1.1em; }
        .input-group { margin-bottom: 15px; }
        .input-group label { display: block; font-weight: 600; color: #333; margin-bottom: 5px; }
        .input-group input, .input-group textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #dee2e6;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        .input-group input:focus, .input-group textarea:focus { border-color: #667eea; outline: none; }
        .input-group textarea { min-height: 80px; resize: vertical; }
        .input-hint { font-size: 12px; color: #888; margin-top: 5px; }
        
        .status-box { background: #f8f9fa; border-radius: 10px; padding: 15px 20px; margin-bottom: 20px; }
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
        .run-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4); }
        .run-btn:disabled { background: #ccc; cursor: not-allowed; }
        .run-btn.running { background: linear-gradient(135deg, #f39c12 0%, #e74c3c 100%); animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
        
        .terminate-btn {
            width: 100%;
            padding: 12px 40px;
            font-size: 1em;
            font-weight: bold;
            color: white;
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 15px;
            display: none;
        }
        .terminate-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(220, 53, 69, 0.4); }
        .terminate-btn.show { display: block; }
        
        .log-box {
            background: #000;
            color: #0f0;
            font-family: 'Courier New', monospace;
            font-size: 11px;
            padding: 15px;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
            border-top: 1px solid #333;
        }
        details {
            margin-top: 20px;
            background: #1a1a2e;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #333;
        }
        summary {
            padding: 12px 15px;
            cursor: pointer;
            color: #aaa;
            font-weight: bold;
            user-select: none;
            outline: none;
            background: #222;
        }
        summary:hover {
            color: #fff;
            background: #333;
        }
        .status-msg-box {
            margin-top: 20px;
            text-align: center;
            font-size: 1.1em;
            min-height: 24px;
            color: #4cd137;
        }
        .footer { text-align: center; margin-top: 20px; color: #999; font-size: 0.85em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div></div>
            <div class="user-info">
                👤 {{ username }}
                {% if is_admin %}<a href="/admin">⚙️ Admin</a>{% endif %}
                <a href="/logout">🚪 Logout</a>
            </div>
        </div>
        
        <div class="emoji">🎓</div>
        <h1>PhD Headhunter</h1>
        <p class="subtitle">Automated PhD Position Finder</p>
        
        <div class="input-section">
            <h3>🔧 Search Configuration</h3>
            <div class="input-group">
                <label for="keywords">📑 Search Keywords (comma-separated) <span style="color: red;">*</span></label>
                <textarea id="keywords" placeholder="e.g., Machine Learning, 5G, Cybersecurity, Signal Processing, IoT" required></textarea>
                <p class="input-hint">Required: Enter at least one keyword</p>
            </div>
            <div class="input-group">
                <label for="positionType">🎯 Position Type</label>
                <select id="positionType" style="width:100%; padding:12px; border:2px solid #dee2e6; border-radius:8px; font-size:14px;">
                    <option value="phd">PhD / Doctoral Positions</option>
                    <option value="postdoc">PostDoc / Tenure Track (Professorship)</option>
                </select>
                <p class="input-hint">Select the type of academic position to search for</p>
            </div>
            <div class="input-group">
                <label>🔍 I would like you to find:</label>
                <div style="margin-top: 12px;">
                    <label style="display: flex; align-items: flex-start; gap: 12px; margin-bottom: 12px; padding: 12px 16px; cursor: pointer; border-radius: 10px; background: rgba(102, 126, 234, 0.05); border: 1px solid rgba(102, 126, 234, 0.15); transition: all 0.2s ease;" onmouseover="this.style.background='rgba(102, 126, 234, 0.1)'" onmouseout="this.style.background='rgba(102, 126, 234, 0.05)'">
                        <input type="checkbox" id="searchOpen" checked style="width: 18px; height: 18px; cursor: pointer; flex-shrink: 0; margin: 0; accent-color: #667eea;" />
                        <span style="line-height: 1.4;"><strong>1. Open PhD/PostDoc Positions</strong> (Job Portals)</span>
                    </label>
                    <label style="display: flex; align-items: flex-start; gap: 12px; margin-bottom: 12px; padding: 12px 16px; cursor: pointer; border-radius: 10px; background: rgba(102, 126, 234, 0.05); border: 1px solid rgba(102, 126, 234, 0.15); transition: all 0.2s ease;" onmouseover="this.style.background='rgba(102, 126, 234, 0.1)'" onmouseout="this.style.background='rgba(102, 126, 234, 0.05)'">
                        <input type="checkbox" id="searchInquiry" style="width: 18px; height: 18px; cursor: pointer; flex-shrink: 0; margin: 0; accent-color: #667eea;" />
                        <span style="line-height: 1.4;"><strong>2. Possible PhD/PostDoc Inquiry Positions</strong> (Faculty Pages)</span>
                    </label>
                    <label style="display: flex; align-items: flex-start; gap: 12px; margin-bottom: 12px; padding: 12px 16px; cursor: pointer; border-radius: 10px; background: rgba(102, 126, 234, 0.05); border: 1px solid rgba(102, 126, 234, 0.15); transition: all 0.2s ease;" onmouseover="this.style.background='rgba(102, 126, 234, 0.1)'" onmouseout="this.style.background='rgba(102, 126, 234, 0.05)'">
                        <input type="checkbox" id="searchProfessors" style="width: 18px; height: 18px; cursor: pointer; flex-shrink: 0; margin: 0; accent-color: #667eea;" />
                        <span style="line-height: 1.4;"><strong>3. Professors/Supervisors in Your Field</strong></span>
                    </label>
                </div>
                <p class="input-hint">Select at least one search type</p>
            </div>
            <div class="input-group">
                <label for="recipientEmail">📧 Send Results To (Email) <span style="color: red;">*</span></label>
                <input type="email" id="recipientEmail" placeholder="e.g., yourname@gmail.com" required>
                <p class="input-hint">Required: Enter a valid email address</p>
            </div>
        </div>
        
        <div class="status-box">
            <div class="status-item">
                <span class="status-label">Status:</span>
                <span id="status" class="status-value status-idle">Idle</span>
                <span id="jobTimerBadge" class="badge bg-info text-dark" style="display: none; margin-left: 10px; font-family: monospace; background-color: #0dcaf0; color: #000; padding: 2px 6px; border-radius: 4px; font-size: 0.9em;">
                    ⏱️ <span id="jobTimer">00:00:00</span>
                </span>
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
        
        <button id="runBtn" class="run-btn" onclick="runAgent()">🚀 Run PhD Agent Now</button>
        <button id="terminateBtn" class="terminate-btn" onclick="terminateJob()">🛑 Terminate Current Job</button>
        
        <div id="statusMessage" class="status-msg-box"></div>
        
        <details>
            <summary>🖥️ Show Real-Time Terminal Output</summary>
            <div class="log-box" id="logOutput">Waiting for action...</div>
        </details>
        
        <div class="footer">PhD Headhunter v1.4 | Written by A.Mehrban (amehrb@gmail.com) | Hostinger VPS</div>
    </div>

    <script>
        function formatTimeDuration(seconds) {
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = Math.floor(seconds % 60);
            return [h, m, s].map(v => v < 10 ? "0" + v : v).join(":");
        }

        function updateStatus() {
            fetch('/status')
                .then(res => res.json())
                .then(data => {
                    const statusEl = document.getElementById('status');
                    const runBtn = document.getElementById('runBtn');
                    const terminateBtn = document.getElementById('terminateBtn');
                    const msgEl = document.getElementById('statusMessage');
                    const jobTimerBadge = document.getElementById('jobTimerBadge');
                    
                    if (data.is_running) {
                        // User's job is running or queued
                        statusEl.textContent = '⏳ Running...';
                        statusEl.className = 'status-value status-running';
                        runBtn.disabled = true;
                        runBtn.textContent = '⏳ Agent is Running...';
                        runBtn.classList.add('running');
                        terminateBtn.classList.add('show');
                        
                        // Update Timer
                        if ((data.started_at_ts || data.last_run) && !data.is_locked_for_another_user) {
                            try {
                                let diffSec;
                                if (data.started_at_ts) {
                                    // Use Unix timestamp (timezone-safe) - preferred method
                                    const nowSec = Math.floor(Date.now() / 1000);
                                    diffSec = Math.max(0, nowSec - data.started_at_ts);
                                } else {
                                    // Fallback: Parse date string for jobs started before timestamp was added
                                    const startTime = new Date(data.last_run.replace(" ", "T"));
                                    const now = new Date();
                                    const diffMs = now - startTime;
                                    diffSec = Math.max(0, Math.floor(diffMs / 1000));
                                }
                                document.getElementById('jobTimer').textContent = formatTimeDuration(diffSec);
                                jobTimerBadge.style.display = 'inline-block';
                            } catch (e) {
                                console.error("Timer calculation error", e);
                                jobTimerBadge.style.display = 'none';
                            }
                        } else {
                            jobTimerBadge.style.display = 'none';
                        }
                        
                        if (data.queue_len > 0) {
                             msgEl.textContent = `📋 You are in queue (position ${data.queue_len}).`;
                        } else {
                             msgEl.textContent = "🔄 Job is running in background. Please check your email for results when complete.";
                        }
                    } else if (data.is_locked_for_another_user) {
                        // Server is locked but not for this user
                        statusEl.textContent = '⏳ Running (for another user)';
                        statusEl.className = 'status-value status-running';
                        runBtn.disabled = false;
                        runBtn.textContent = '🚀 Run PhD Agent Now (will queue)';
                        runBtn.classList.remove('running');
                        terminateBtn.classList.remove('show');
                        
                        msgEl.textContent = `ℹ️ Server is busy with another user's request. Your job will be queued.`;
                    } else {
                        // Server is completely idle
                        statusEl.textContent = '✅ Idle';
                        statusEl.className = 'status-value status-idle';
                        runBtn.disabled = false;
                        runBtn.textContent = '🚀 Run PhD Agent Now';
                        runBtn.classList.remove('running');
                        terminateBtn.classList.remove('show');
                        jobTimerBadge.style.display = 'none';
                        
                        if (msgEl.textContent.includes('Running')) {
                            msgEl.textContent = "✅ Ready for new job.";
                        }
                    }
                    
                    document.getElementById('lastRun').textContent = data.last_run || 'Never';
                    document.getElementById('lastResult').textContent = data.last_result || '-';
                    document.getElementById('logOutput').textContent = data.log_output || 'Waiting for action...';
                });
        }
        
        function runAgent() {
            const keywords = document.getElementById('keywords').value.trim();
            const recipientEmail = document.getElementById('recipientEmail').value.trim();
            const positionType = document.getElementById('positionType').value;
            
            // Get search types
            const searchTypes = [];
            if (document.getElementById('searchOpen').checked) searchTypes.push('open');
            if (document.getElementById('searchInquiry').checked) searchTypes.push('inquiry');
            if (document.getElementById('searchProfessors').checked) searchTypes.push('professors');
            
            // Validate required fields
            if (!keywords) {
                alert('⚠️ Please enter search keywords!');
                return;
            }
            if (!recipientEmail) {
                alert('⚠️ Please enter your email address!');
                return;
            }
            if (!recipientEmail.includes('@')) {
                alert('⚠️ Please enter a valid email address!');
                return;
            }
            if (searchTypes.length === 0) {
                alert('⚠️ Please select at least one search type!');
                return;
            }
            
            document.getElementById('runBtn').disabled = true;
            document.getElementById('statusMessage').textContent = '🚀 Submitting request...';
            
            fetch('/run', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    keywords: keywords, 
                    recipient_email: recipientEmail,
                    position_type: positionType,
                    search_types: searchTypes.join(',')  // NEW: Send search types
                })
            })
                .then(res => res.json())
                .then(data => {
                    document.getElementById('statusMessage').textContent = data.message;
                    updateStatus();
                });
        }
        
        function terminateJob() {
            if (!confirm('Are you sure you want to terminate the current job?')) {
                return;
            }
            
            document.getElementById('statusMessage').textContent = '🛑 Terminating job...';
            
            fetch('/terminate', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    document.getElementById('statusMessage').textContent = data.message;
                    updateStatus();
                });
        }
        
        setInterval(updateStatus, 3000);
        updateStatus();
    </script>
</body>
</html>
"""

# ==================== BACKGROUND RUNNER ====================
def run_agent_background(keywords="", recipient_email=""):
    """Run the PhD agent in background with custom parameters"""
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
        cmd = ["python3", "main.py"]
        if recipient_email:
            cmd.extend(["--recipient", recipient_email])
        if keywords:
            cmd.extend(["--keywords", keywords])
        
        process = subprocess.Popen(
            cmd,
            cwd="/root/phd_agent",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
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

# ==================== ROUTES ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        if verify_password(username, password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            error = "Invalid username or password"
    
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/')
@app.route('/PhD_hunt')
@app.route('/phd_hunt')
@login_required
def dashboard():
    username = session.get('username', '')
    return render_template_string(DASHBOARD_TEMPLATE, 
                                  username=username, 
                                  is_admin=is_admin(username))

@app.route('/admin')
@admin_required
def admin():
    users = load_users()
    return render_template_string(ADMIN_TEMPLATE, users=users, session=session, message=None, message_type=None)

@app.route('/admin/add', methods=['POST'])
@admin_required
def admin_add():
    users = load_users()
    new_username = request.form.get('new_username', '').strip()
    new_password = request.form.get('new_password', '')
    is_admin_role = request.form.get('is_admin', '0') == '1'
    
    if not new_username or not new_password:
        return render_template_string(ADMIN_TEMPLATE, users=users, session=session, 
                                      message="Username and password required", message_type="error")
    
    if new_username in users:
        return render_template_string(ADMIN_TEMPLATE, users=users, session=session,
                                      message=f"User '{new_username}' already exists", message_type="error")
    
    users[new_username] = {
        "password_hash": hash_password(new_password),
        "is_admin": is_admin_role,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_users(users)
    
    return render_template_string(ADMIN_TEMPLATE, users=users, session=session,
                                  message=f"User '{new_username}' added successfully!", message_type="success")

@app.route('/admin/delete', methods=['POST'])
@admin_required
def admin_delete():
    users = load_users()
    username = request.form.get('username', '')
    
    if username == session.get('username'):
        return render_template_string(ADMIN_TEMPLATE, users=users, session=session,
                                      message="Cannot delete yourself!", message_type="error")
    
    if username in users:
        del users[username]
        save_users(users)
        return render_template_string(ADMIN_TEMPLATE, users=users, session=session,
                                      message=f"User '{username}' deleted", message_type="success")
    
    return render_template_string(ADMIN_TEMPLATE, users=users, session=session,
                                  message="User not found", message_type="error")

# ==================== JOB QUEUE INTEGRATION ====================
import sys
sys.path.insert(0, '/root/phd_agent')

from job_queue import (
    is_locked, get_lock_info, acquire_lock, release_lock,
    add_to_queue, get_queue_position, get_queue_length,
    pop_next_job, create_job_status, update_job_log, 
    complete_job, get_job_status
)

# Per-user job tracking
user_jobs = {}  # {username: job_id}

# Global process tracker for termination
current_process = None
current_process_lock = threading.Lock()

def run_agent_with_queue(job_id: str, keywords: str, recipient_email: str, username: str, position_type: str = "phd", search_types: str = "open"):
    """Run the PhD agent for a queued job"""
    global current_process
    try:
        pos_label = "PhD" if position_type == "phd" else "PostDoc/Tenure"
        
        # Build command (use venv Python to access all dependencies)
        cmd = ["/root/phd_agent/venv/bin/python3", "main.py", "--job-id", job_id, "--position-type", position_type, "--search-types", search_types]
        if recipient_email:
            cmd.extend(["--recipient", recipient_email])
        if keywords:
            cmd.extend(["--keywords", keywords])
        
        # Start process FIRST to get PID
        process = subprocess.Popen(
            cmd,
            cwd="/root/phd_agent",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Store process for potential termination
        with current_process_lock:
            current_process = process
        
        # Acquire lock WITH PID for process validation
        if not acquire_lock("Mode 2 (Web Dashboard)", username, keywords, recipient_email, pid=process.pid):
            update_job_log(job_id, "\n❌ Could not acquire lock\n")
            complete_job(job_id, False, "Could not acquire lock")
            process.terminate()
            return
        
        update_job_log(job_id, f"🔐 Lock acquired (PID: {process.pid}), starting {pos_label} position search...\n")
        
        try:
            for line in process.stdout:
                update_job_log(job_id, line)
            
            process.wait()
            
            if process.returncode == 0:
                complete_job(job_id, True, "✅ Success")
            else:
                complete_job(job_id, False, f"❌ Failed (code {process.returncode})")
        finally:
            # Clear process reference
            with current_process_lock:
                current_process = None
                
    except Exception as e:
        complete_job(job_id, False, f"❌ Error: {str(e)}")
    finally:
        release_lock()
        # Process next job in queue
        process_queue()

def process_queue():
    """Process the next job in queue if any"""
    next_job = pop_next_job()
    if next_job:
        job_id = next_job["job_id"]
        update_job_log(job_id, "\n🚀 Your turn! Starting job from queue...\n")
        thread = threading.Thread(
            target=run_agent_with_queue, 
            args=(job_id, next_job["keywords"], next_job["recipient"], next_job["user"], "phd", "open")  # TODO: Store search_types in queue
        )
        thread.daemon = True
        thread.start()

@app.route('/status')
@login_required
def status():
    username = session.get('username', '')
    
    # Check if user has an active job
    job_id = user_jobs.get(username)
    
    if job_id:
        job_status = get_job_status(job_id)
        if job_status:
            # Check queue position
            queue_pos = get_queue_position(job_id)
            
            if job_status["status"] == "running":
                return jsonify({
                    "is_running": True,
                    "last_run": job_status.get("started_at"),
                    "started_at_ts": job_status.get("started_at_ts"),
                    "last_result": None,
                    "log_output": job_status.get("log_output", "")
                })
            elif queue_pos > 0:
                # Job is in queue
                return jsonify({
                    "is_running": True,
                    "last_run": None,
                    "last_result": None,
                    "log_output": f"📋 Your request is in queue (position {queue_pos}).\n\n"
                                  f"Currently the server is running for another user's request, "
                                  f"but your request is in queue and will run afterwards.\n\n"
                                  f"The result will be emailed to you when complete."
                })
            else:
                # Job completed
                # BUT check if server is now running for someone else
                is_server_locked = is_locked()
                run_info = get_lock_info() if is_server_locked else None
                queue_len = get_queue_length() if is_server_locked else 0
                
                return jsonify({
                    "is_running": False,
                    "is_locked_for_another_user": is_server_locked,
                    "last_run": job_status.get("started_at"),
                    "last_result": job_status.get("result"),
                    "log_output": job_status.get("log_output", ""),
                    "queue_len": queue_len
                })
    
    # No active job in memory - check if server is locked
    if is_locked():
        lock_info = get_lock_info()
        queue_len = get_queue_length()
        
        # KEY FIX: Check if the lock belongs to the current user!
        if lock_info and lock_info.get("user") == username:
            # It's OUR job running! Recover the state.
            return jsonify({
                "is_running": True,
                "last_run": lock_info.get("started_at_str"),
                "last_result": None,
                "log_output": "🔄 Resumed session. job is running in background...\n" + \
                              f"Started at: {lock_info.get('started_at_str')}\n" + \
                              "Please check your email for results when complete."
            })
            
        # Server is running for another user
        return jsonify({
            "is_running": False,
            "is_locked_for_another_user": True,
            "last_run": None,
            "last_result": None,
            "log_output": f"ℹ️ Server is currently running for another user.\n"
                          f"Queue length: {queue_len}\n\n"
                          f"You can submit a new request - it will be queued and run automatically."
        })
    
    # Server is completely idle
    return jsonify({
        "is_running": False,
        "is_locked_for_another_user": False,
        "last_run": None,
        "last_result": None,
        "log_output": "✅ Server is ready. Enter keywords and email, then click 'Run PhD Agent Now'."
    })

@app.route('/run', methods=['POST'])
@login_required
def run():
    username = session.get('username', '')
    data = request.get_json() or {}
    keywords = data.get("keywords", "")
    recipient_email = data.get("recipient_email", "")
    position_type = data.get("position_type", "phd")  # Default to PhD
    search_types = data.get("search_types", "open")  # Default to open positions
    
    # Create a new job
    job_id = create_job_status(
        job_id=str(uuid.uuid4())[:8],
        user=username,
        keywords=keywords,
        recipient=recipient_email
    )
    user_jobs[username] = job_id
    
    pos_label = "PhD" if position_type == "phd" else "PostDoc/Tenure"
    
    # Check if a job is already running
    if is_locked():
        # Add to queue (note: queue doesn't support position_type yet, but it's passed when run starts)
        add_to_queue(username, keywords, recipient_email)
        queue_pos = get_queue_length()
        
        update_job_log(job_id, 
            f"📋 Your {pos_label} position search has been queued (position {queue_pos}).\n\n"
            f"Currently the server is running for another user's request, "
            f"but your request is in queue and will run afterwards.\n\n"
            f"The result will be emailed to: {recipient_email or 'owner'}"
        )
        
        return jsonify({
            "success": True, 
            "queued": True,
            "message": f"📋 Request queued! Currently the server is running for another user. "
                       f"Your request is in queue (position {queue_pos}) and will run afterwards. "
                       f"Results will be emailed to you."
        })
    
    # Start immediately
    thread = threading.Thread(
        target=run_agent_with_queue, 
        args=(job_id, keywords, recipient_email, username, position_type, search_types)
    )
    thread.daemon = True
    thread.start()
    
    pos_label = "PhD" if position_type == "phd" else "PostDoc/Tenure"
    msg = f"🚀 {pos_label} Position Search started!"
    if recipient_email:
        msg += f" Results will be sent to {recipient_email}"
    return jsonify({"success": True, "queued": False, "message": msg})

@app.route('/terminate', methods=['POST'])
@login_required
def terminate():
    """Terminate the currently running job"""
    global current_process
    
    # Kill the running process if exists
    with current_process_lock:
        if current_process:
            try:
                current_process.terminate()
                current_process.wait(timeout=5)
            except:
                try:
                    current_process.kill()
                except:
                    pass
            current_process = None
    
    # Release the lock
    release_lock()
    
    # Clear the job queue
    save_queue([])
    
    return jsonify({
        "success": True,
        "message": "⛔ Job terminated. Lock released. Queue cleared."
    })

if __name__ == '__main__':
    import uuid
    # Initialize users file if needed
    load_users()
    app.run(host='0.0.0.0', port=5000, debug=False)


