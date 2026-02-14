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
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

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
    <title>Sign In - PhD Headhunter</title>
    <style>
        :root {
            --primary: #0A84FF;
            --bg: #000000;
            --surface: rgba(28, 28, 30, 0.65);
            --border: rgba(255, 255, 255, 0.12);
            --text: #ffffff;
            --text-secondary: rgba(235, 235, 245, 0.6);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif; }
        body {
            background-color: var(--bg);
            background-image: 
                radial-gradient(circle at 100% 0%, #1c1c1e 0%, transparent 40%),
                radial-gradient(circle at 0% 100%, #1c1c1e 0%, transparent 40%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: var(--text);
        }
        .login-container {
            width: 100%;
            max-width: 360px;
            padding: 48px 40px;
            background: var(--surface);
            backdrop-filter: blur(50px) saturate(180%);
            -webkit-backdrop-filter: blur(50px) saturate(180%);
            border: 0.5px solid var(--border);
            border-radius: 24px;
            box-shadow: 0 40px 80px -20px rgba(0,0,0,0.5);
        }
        h1 { font-size: 28px; font-weight: 700; text-align: center; margin-bottom: 8px; letter-spacing: -0.5px; }
        .subtitle { font-size: 15px; color: var(--text-secondary); text-align: center; margin-bottom: 40px; font-weight: 400; }
        
        .input-group { margin-bottom: 24px; }
        .input-group label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 8px; color: var(--text-secondary); }
        input {
            width: 100%;
            padding: 16px;
            background: rgba(0,0,0,0.2);
            border: 1px solid var(--border);
            border-radius: 14px;
            color: white;
            font-size: 17px;
            transition: all 0.2s cubic-bezier(0.25, 1, 0.5, 1);
        }
        input::placeholder { color: rgba(255,255,255,0.2); }
        input:focus {
            outline: none;
            border-color: var(--primary);
            background: rgba(0,0,0,0.4);
            box-shadow: 0 0 0 4px rgba(10, 132, 255, 0.25);
        }
        
        .login-btn {
            width: 100%;
            padding: 16px;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 14px;
            font-size: 17px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            margin-top: 12px;
        }
        .login-btn:hover { background: #0077ED; transform: translateY(-1px); }
        .login-btn:active { transform: scale(0.98); }
        
        .error { 
            color: #FF453A; font-size: 14px; text-align: center; margin-bottom: 24px; 
            background: rgba(255, 69, 58, 0.1); padding: 12px; border-radius: 12px; 
            border: 1px solid rgba(255, 69, 58, 0.2);
        }
        .footer { text-align: center; margin-top: 40px; font-size: 13px; color: rgba(255,255,255,0.3); }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>PhD Headhunter</h1>
        <p class="subtitle">Sign in to manage your agent</p>
        
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        
        <form method="POST">
            <div class="input-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required placeholder="name@example.com" autocomplete="username">
            </div>
            <div class="input-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required placeholder="••••••••" autocomplete="current-password">
            </div>
            <button type="submit" class="login-btn">Sign In</button>
        </form>
        
        <div class="footer">v1.4 • Private Access</div>
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
    <title>Admin - PhD Headhunter</title>
    <style>
        :root {
            --primary: #0A84FF;
            --bg: #000000;
            --surface: #1C1C1E;
            --surface-secondary: #2C2C2E;
            --border: #38383A;
            --text: #ffffff;
            --text-secondary: rgba(235, 235, 245, 0.6);
            --danger: #FF453A;
            --success: #30D158;
            --warning: #FFD60A;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif; }
        body {
            background-color: var(--bg);
            min-height: 100vh;
            color: var(--text);
            padding: 40px 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        .header { 
            display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; 
            padding-bottom: 20px; border-bottom: 1px solid var(--border);
        }
        h1 { font-size: 32px; font-weight: 700; letter-spacing: -0.5px; }
        
        .nav-link { 
            color: var(--primary); text-decoration: none; font-weight: 500; font-size: 15px; 
            padding: 8px 16px; border-radius: 8px; transition: background 0.2s;
        }
        .nav-link:hover { background: rgba(10, 132, 255, 0.1); }
        .nav-link.logout { color: var(--danger); }
        .nav-link.logout:hover { background: rgba(255, 69, 58, 0.1); }
        
        .section { margin-bottom: 40px; }
        .section h2 { 
            font-size: 20px; font-weight: 600; margin-bottom: 16px; color: var(--text); 
            display: flex; align-items: center; gap: 10px;
        }
        
        .card {
            background: var(--surface);
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--border);
        }
        
        table { width: 100%; border-collapse: collapse; }
        th { 
            text-align: left; padding: 16px 20px; 
            background: var(--surface-secondary); 
            font-size: 13px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;
        }
        td { 
            padding: 16px 20px; border-top: 1px solid var(--border); 
            font-size: 15px; color: var(--text);
        }
        tr:last-child td { border-bottom: none; }
        
        .badge { 
            display: inline-block; padding: 4px 10px; border-radius: 6px; 
            font-size: 12px; font-weight: 600; letter-spacing: 0.3px;
        }
        .badge-admin { background: rgba(255, 214, 10, 0.2); color: var(--warning); border: 1px solid rgba(255, 214, 10, 0.3); }
        .badge-user { background: rgba(48, 209, 88, 0.2); color: var(--success); border: 1px solid rgba(48, 209, 88, 0.3); }
        
        .action-btn { 
            background: none; border: none; cursor: pointer; padding: 6px 12px; 
            font-size: 13px; font-weight: 500; border-radius: 6px; transition: all 0.2s;
        }
        .btn-delete { color: var(--danger); background: rgba(255, 69, 58, 0.1); }
        .btn-delete:hover { background: rgba(255, 69, 58, 0.2); }
        
        .form-grid { 
            display: grid; grid-template-columns: 1fr 1fr 120px auto; gap: 16px; padding: 20px; 
            align-items: end; background: var(--surface);
        }
        .input-wrapper label { display: block; font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; font-weight: 500; }
        .input-wrapper input, .input-wrapper select {
            width: 100%; padding: 10px 14px; background: rgba(0,0,0,0.3);
            border: 1px solid var(--border); border-radius: 10px;
            color: white; font-size: 15px;
        }
        .input-wrapper input:focus, .input-wrapper select:focus {
            outline: none; border-color: var(--primary);
        }
        
        .btn-add {
            width: 100%; padding: 11px; background: var(--success); color: #000;
            border: none; border-radius: 10px; font-weight: 600; font-size: 15px; cursor: pointer;
        }
        .btn-add:hover { opacity: 0.9; }
        
        .message { padding: 16px; border-radius: 12px; margin-bottom: 24px; font-size: 15px; }
        .message-success { background: rgba(48, 209, 88, 0.15); color: var(--success); border: 1px solid rgba(48, 209, 88, 0.2); }
        .message-error { background: rgba(255, 69, 58, 0.15); color: var(--danger); border: 1px solid rgba(255, 69, 58, 0.2); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Admin Panel</h1>
            <div>
                <a href="/PhD_hunt" class="nav-link">Dashboard</a>
                <a href="/logout" class="nav-link logout">Sign Out</a>
            </div>
        </div>
        
        {% if message %}
        <div class="message message-{{ message_type }}">{{ message }}</div>
        {% endif %}
        
        <div class="section">
            <h2>User Management</h2>
            <div class="card">
                <table>
                    <thead>
                        <tr>
                            <th>Username</th>
                            <th>Role</th>
                            <th>Created</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for username, user in users.items() %}
                        <tr>
                            <td>{{ username }}</td>
                            <td>
                                <span class="badge {% if user.is_admin %}badge-admin{% else %}badge-user{% endif %}">
                                    {% if user.is_admin %}ADMIN{% else %}USER{% endif %}
                                </span>
                            </td>
                            <td style="color: var(--text-secondary); font-size: 13px;">{{ user.created }}</td>
                            <td>
                                {% if username != session.username %}
                                <form method="POST" action="/admin/delete" style="display:inline">
                                    <input type="hidden" name="username" value="{{ username }}">
                                    <button type="submit" class="action-btn btn-delete" onclick="return confirm('Delete user {{ username }}?')">Delete</button>
                                </form>
                                {% else %}
                                <span style="color: var(--text-secondary); font-size: 13px;">(You)</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="section">
            <h2>Add New User</h2>
            <div class="card">
                <form method="POST" action="/admin/add" class="form-grid">
                    <div class="input-wrapper">
                        <label>Username</label>
                        <input type="text" name="new_username" required placeholder="username">
                    </div>
                    <div class="input-wrapper">
                        <label>Password</label>
                        <input type="password" name="new_password" required placeholder="password">
                    </div>
                    <div class="input-wrapper">
                        <label>Role</label>
                        <select name="is_admin">
                            <option value="0">User</option>
                            <option value="1">Admin</option>
                        </select>
                    </div>
                    <button type="submit" class="btn-add">Add</button>
                </form>
            </div>
        </div>
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
    <title>Dashboard - PhD Headhunter</title>
    <style>
        :root {
            --primary: #0A84FF;
            --primary-hover: #0077ED;
            --bg: #000000;
            --surface: #1C1C1E;
            --surface-glass: rgba(28, 28, 30, 0.7);
            --border: rgba(255, 255, 255, 0.12);
            --text: #ffffff;
            --text-secondary: rgba(235, 235, 245, 0.6);
            --success: #30D158;
            --warning: #FFD60A;
            --danger: #FF453A;
            --terminal-bg: #151517;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif; }
        body {
            background-color: var(--bg);
            background-image: 
                radial-gradient(circle at 50% -20%, #1a1a40 0%, transparent 60%);
            min-height: 100vh;
            color: var(--text);
            padding: 40px 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        
        .header { 
            display: flex; justify-content: flex-end; margin-bottom: 60px; 
            font-size: 14px; color: var(--text-secondary);
        }
        .header a { color: var(--text); text-decoration: none; margin-left: 20px; font-weight: 500; transition: color 0.2s; }
        .header a:hover { color: var(--primary); }
        
        .hero { text-align: center; margin-bottom: 60px; }
        .hero h1 { 
            font-size: 56px; font-weight: 800; letter-spacing: -1px; margin-bottom: 16px; 
            background: linear-gradient(135deg, #fff 0%, #aaa 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .hero p { font-size: 21px; color: var(--text-secondary); font-weight: 400; }
        
        .grid { display: grid; grid-template-columns: 1.4fr 0.8fr; gap: 24px; margin-bottom: 40px; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
        
        .card {
            background: var(--surface);
            border-radius: 24px;
            padding: 32px;
            border: 1px solid var(--border);
            backdrop-filter: blur(20px);
        }
        .section-title { font-size: 19px; font-weight: 600; margin-bottom: 24px; color: var(--text); }
        
        .input-group { margin-bottom: 24px; }
        .input-label { display: block; font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
        
        input, textarea, select {
            width: 100%;
            background: rgba(0,0,0,0.3);
            border: 1px solid var(--border);
            color: white;
            border-radius: 12px;
            padding: 14px 16px;
            font-size: 16px;
            transition: all 0.2s;
        }
        textarea { min-height: 120px; line-height: 1.5; resize: vertical; }
        input:focus, textarea:focus, select:focus {
            outline: none; border-color: var(--primary); background: rgba(0,0,0,0.5);
            box-shadow: 0 0 0 4px rgba(10, 132, 255, 0.15);
        }
        
        .checkbox-group { display: flex; flex-direction: column; gap: 12px; }
        .checkbox-item {
            display: flex; align-items: flex-start; gap: 14px;
            padding: 16px;
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--border);
            border-radius: 14px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .checkbox-item:hover { background: rgba(255,255,255,0.06); }
        .checkbox-item input { width: 20px; height: 20px; accent-color: var(--primary); margin: 0; margin-top: 2px; }
        #aiPowered { accent-color: #FF9500; }
        .checkbox-label strong { display: block; color: var(--text); margin-bottom: 4px; font-weight: 600; }
        .checkbox-label { font-size: 14px; color: var(--text-secondary); line-height: 1.4; }
        
        .status-row { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; border-bottom: 1px solid var(--border); }
        .status-row:last-child { border-bottom: none; }
        .status-key { color: var(--text-secondary); font-size: 15px; }
        .status-val { font-weight: 600; font-size: 15px; }
        
        .status-idle { color: var(--success); }
        .status-running { color: var(--warning); display: flex; align-items: center; gap: 8px; }
        
        .timer-badge { 
            background: rgba(10, 132, 255, 0.2); color: var(--primary); 
            padding: 4px 8px; border-radius: 6px; font-family: "SF Mono", Menlo, monospace; font-size: 13px;
        }

        .btn-run {
            width: 100%; padding: 20px;
            background: var(--primary);
            color: white; font-size: 18px; font-weight: 700;
            border: none; border-radius: 18px;
            cursor: pointer; transition: all 0.2s;
            box-shadow: 0 10px 30px -10px rgba(10, 132, 255, 0.5);
        }
        .btn-run:hover:not(:disabled) { transform: scale(1.02); background: var(--primary-hover); }
        .btn-run:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-run.running { animation: pulse 2s infinite; }
        
        .btn-terminate {
            width: 100%; padding: 16px;
            background: rgba(255, 69, 58, 0.15); color: var(--danger);
            border: 1px solid rgba(255, 69, 58, 0.3);
            border-radius: 14px; font-weight: 600; font-size: 15px;
            cursor: pointer; display: none; margin-top: 12px;
        }
        .btn-terminate:hover { background: rgba(255, 69, 58, 0.25); }
        #terminateBtn.show { display: block; }
        
        details { background: var(--terminal-bg); border-radius: 16px; border: 1px solid var(--border); overflow: hidden; }
        summary { 
            padding: 16px 20px; cursor: pointer; color: var(--text-secondary); 
            font-weight: 500; font-size: 14px; user-select: none;
            background: rgba(255,255,255,0.02);
            transition: color 0.2s;
        }
        summary:hover { color: var(--text); }
        .log-box {
            padding: 20px; font-family: "SF Mono", Menlo, monospace; font-size: 12px; line-height: 1.6;
            color: #7BE188; border-top: 1px solid var(--border);
            max-height: 400px; overflow-y: auto; white-space: pre-wrap;
        }
        
        .status-msg { text-align: center; margin-bottom: 24px; min-height: 24px; color: var(--text-secondary); font-size: 15px; }
        
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
        
        .footer { text-align: center; margin-top: 60px; color: var(--text-secondary); font-size: 13px; opacity: 0.5; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span>Signed in as <strong>{{ username }}</strong></span>
            {% if is_admin %}<a href="/admin">Admin</a>{% endif %}
            <a href="/logout">Sign Out</a>
        </div>
        
        <div class="hero">
            <h1>PhD Headhunter</h1>
            <p>Automated Position Discovery & Analysis</p>
        </div>
        
        <div class="grid">
            <div class="card">
                <div class="section-title">Search Configuration</div>
                
                <div class="input-group">
                    <label class="input-label" for="keywords">Research Keywords</label>
                    <textarea id="keywords" placeholder="e.g. Machine Learning, 5G Networks, Bioinformatics..." required></textarea>
                </div>
                
                <div class="input-group">
                    <label class="input-label" for="positionType">Position Type</label>
                    <select id="positionType">
                        <option value="phd">PhD / Doctoral Candidate</option>
                        <option value="postdoc">PostDoc / Tenure Track</option>
                    </select>
                </div>
                
                <div class="input-group">
                    <label class="input-label">Sources & Methods</label>
                    <div class="checkbox-group">
                        <label class="checkbox-item">
                            <input type="checkbox" id="searchOpen" checked>
                            <div class="checkbox-label">
                                <strong>Job Portals</strong>
                                Search open positions on major aggregator sites
                            </div>
                        </label>
                        <label class="checkbox-item">
                            <input type="checkbox" id="searchInquiry">
                            <div class="checkbox-label">
                                <strong>Faculty Pages</strong>
                                Detect potential inquiry opportunities from lab sites
                            </div>
                        </label>
                        <label class="checkbox-item">
                            <input type="checkbox" id="searchProfessors">
                            <div class="checkbox-label">
                                <strong>Supervisor Search</strong>
                                Identify relevant professors in the field
                            </div>
                        </label>
                        <label class="checkbox-item" style="border-color: rgba(255, 149, 0, 0.3); background: rgba(255, 149, 0, 0.05);">
                            <input type="checkbox" id="aiPowered">
                            <div class="checkbox-label">
                                <strong style="color: #FF9500;">AI-Powered Crawler (Gemini)</strong>
                                Use LLM to intelligently navigate university websites
                            </div>
                        </label>
                    </div>
                </div>
                
                <div class="input-group">
                    <label class="input-label" for="recipientEmail">Email Report To</label>
                    <input type="email" id="recipientEmail" placeholder="name@example.com" required>
                </div>
            </div>
            
            <div>
                <div class="card" style="position: sticky; top: 40px;">
                    <div class="section-title">System Status</div>
                    
                    <div class="status-row">
                        <span class="status-key">Current State</span>
                        <div id="status" class="status-val status-idle">Ready</div>
                    </div>
                     <div class="status-row" id="timerRow" style="display:none;">
                        <span class="status-key">Duration</span>
                        <span id="jobTimer" class="timer-badge">00:00:00</span>
                    </div>
                    <div class="status-row">
                        <span class="status-key">Last Run</span>
                        <span id="lastRun" class="status-val">-</span>
                    </div>
                    <div class="status-row">
                        <span class="status-key">Result</span>
                        <span id="lastResult" class="status-val">-</span>
                    </div>
                    
                    <div style="margin-top: 32px;">
                        <button id="runBtn" class="btn-run" onclick="runAgent()">Start Search</button>
                        <button id="terminateBtn" class="btn-terminate" onclick="terminateJob()">Terminate Job</button>
                    </div>
                    
                    <div id="statusMessage" class="status-msg" style="margin-top: 20px; font-size: 13px;"></div>
                </div>
            </div>
        </div>
        
        <details>
            <summary>Terminal Output</summary>
            <div class="log-box" id="logOutput">System initialized. Waiting for command...</div>
        </details>
        
        <div class="footer">
            PhD Headhunter v1.4 &bull; Designed by A.Mehrban
        </div>
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
                    const timerRow = document.getElementById('timerRow');
                    
                    if (data.is_running) {
                        statusEl.textContent = 'Running...';
                        statusEl.className = 'status-val status-running';
                        runBtn.disabled = true;
                        runBtn.textContent = 'Agent Running...';
                        runBtn.classList.add('running');
                        terminateBtn.classList.add('show');
                        
                        if ((data.started_at_ts || data.last_run) && !data.is_locked_for_another_user) {
                            try {
                                let diffSec;
                                if (data.started_at_ts) {
                                    const nowSec = Math.floor(Date.now() / 1000);
                                    diffSec = Math.max(0, nowSec - data.started_at_ts);
                                } else {
                                    const startTime = new Date(data.last_run.replace(" ", "T") + "Z");
                                    const now = new Date();
                                    const diffMs = now - startTime;
                                    diffSec = Math.max(0, Math.floor(diffMs / 1000));
                                }
                                document.getElementById('jobTimer').textContent = formatTimeDuration(diffSec);
                                timerRow.style.display = 'flex';
                            } catch (e) {
                                timerRow.style.display = 'none';
                            }
                        } else {
                            timerRow.style.display = 'none';
                        }
                        
                        if (data.queue_len > 0) {
                             msgEl.textContent = `Queued (Position: ${data.queue_len})`;
                        } else {
                             msgEl.textContent = "Processing... Check email for results.";
                        }
                    } else if (data.is_locked_for_another_user) {
                        statusEl.textContent = 'Busy (Other User)';
                        statusEl.className = 'status-val status-running';
                        runBtn.disabled = false;
                        runBtn.textContent = 'Queue Search';
                        runBtn.classList.remove('running');
                        terminateBtn.classList.remove('show');
                        msgEl.textContent = `Server busy. Job will be queued.`;
                    } else {
                        statusEl.textContent = 'Ready';
                        statusEl.className = 'status-val status-idle';
                        runBtn.disabled = false;
                        runBtn.textContent = 'Start Search';
                        runBtn.classList.remove('running');
                        terminateBtn.classList.remove('show');
                        timerRow.style.display = 'none';
                        msgEl.textContent = "";
                    }
                    
                    document.getElementById('lastRun').textContent = data.last_run || '-';
                    document.getElementById('lastResult').textContent = data.last_result || '-';
                    document.getElementById('logOutput').textContent = data.log_output || 'Waiting for command...';
                });
        }
        
        function runAgent() {
            const keywords = document.getElementById('keywords').value.trim();
            const recipientEmail = document.getElementById('recipientEmail').value.trim();
            const positionType = document.getElementById('positionType').value;
            
            const searchTypes = [];
            if (document.getElementById('searchOpen').checked) searchTypes.push('open');
            if (document.getElementById('searchInquiry').checked) searchTypes.push('inquiry');
            if (document.getElementById('searchProfessors').checked) searchTypes.push('professors');
            
            if (!keywords) { alert('Please enter search keywords'); return; }
            if (!recipientEmail) { alert('Please enter email address'); return; }
            if (!recipientEmail.includes('@')) { alert('Invalid email address'); return; }
            if (searchTypes.length === 0) { alert('Select at least one search type'); return; }
            
            document.getElementById('runBtn').disabled = true;
            document.getElementById('statusMessage').textContent = 'Initiating...';
            
            fetch('/run', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    keywords: keywords, 
                    recipient_email: recipientEmail,
                    position_type: positionType,
                    search_types: searchTypes.join(','),
                    use_ai_crawler: document.getElementById('aiPowered').checked
                })
            })
                .then(res => res.json())
                .then(data => {
                    document.getElementById('statusMessage').textContent = data.message;
                    updateStatus();
                });
        }
        
        function terminateJob() {
            if (!confirm('Stop the current search? Results collected so far will be lost.')) return;
            
            document.getElementById('statusMessage').textContent = 'Stopping...';
            
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

def send_termination_email(recipient_email, job_info):
    """Send an email notification that the job was manually terminated"""
    gmail_user = os.getenv("GMAIL_USER")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
    
    if not gmail_user or not gmail_pass or not recipient_email:
        return

    subject = "🛑 PhD Agent - Search Terminated Manually"
    
    start_time = job_info.get('started_at_str', 'Unknown')
    keywords = job_info.get('keywords', 'Unknown')
    
    body = f"""
    The PhD Headhunter Agent search was manually terminated by the user via the dashboard.
    
    Job Details:
    - Started: {start_time}
    - Keywords: {keywords}
    - Status: Terminated/Cancelled
    
    No further results will be sent for this session.
    """
    
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = gmail_user
        msg["To"] = recipient_email
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_user, gmail_pass)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")

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

def run_agent_with_queue(job_id: str, keywords: str, recipient_email: str, username: str, position_type: str = "phd", search_types: str = "open", use_ai_crawler: bool = False):
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
        if use_ai_crawler:
            cmd.append("--ai-powered")
        
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
            args=(
                job_id, 
                next_job.get("keywords", ""), 
                next_job.get("recipient", ""), 
                next_job.get("user", ""), 
                next_job.get("position_type", "phd"), 
                next_job.get("search_types", "open"),
                next_job.get("use_ai_crawler", False)
            )
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
    use_ai_crawler = data.get("use_ai_crawler", False) or "ai_powered" in data # Handle both keys if JS uses old one
    if isinstance(use_ai_crawler, str):
        use_ai_crawler = use_ai_crawler.lower() == 'true'
    
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
        # Add to queue
        add_to_queue(username, keywords, recipient_email, position_type, search_types, use_ai_crawler)
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
        args=(job_id, keywords, recipient_email, username, position_type, search_types, use_ai_crawler)
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
            # Try to send email notification before killing
            try:
                lock_info = get_lock_info()
                if lock_info and lock_info.get('recipient'):
                     # Run in separate thread to not block termination
                     threading.Thread(target=send_termination_email, 
                                    args=(lock_info.get('recipient'), lock_info)).start()
            except Exception as e:
                print(f"Failed to send termination email: {e}")

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


