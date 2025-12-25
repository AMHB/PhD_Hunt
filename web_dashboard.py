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
                <label for="keywords">📑 Search Keywords (comma-separated)</label>
                <textarea id="keywords" placeholder="e.g., Machine Learning, 5G, Cybersecurity, Signal Processing, IoT"></textarea>
                <p class="input-hint">Leave empty to use default keywords</p>
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
                <label for="recipientEmail">📧 Send Results To (Email)</label>
                <input type="email" id="recipientEmail" placeholder="e.g., yourname@gmail.com">
                <p class="input-hint">Results will be sent to this email</p>
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
        
        <button id="runBtn" class="run-btn" onclick="runAgent()">🚀 Run PhD Agent Now</button>
        
        <div class="log-box" id="logOutput">Waiting for action...</div>
        
        <div class="footer">PhD Headhunter v1.3 | Written by A.Mehrban (amehrb@gmail.com) | Hostinger VPS</div>
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
            const positionType = document.getElementById('positionType').value;
            
            if (recipientEmail && !recipientEmail.includes('@')) {
                alert('Please enter a valid email address');
                return;
            }
            
            document.getElementById('runBtn').disabled = true;
            const posLabel = positionType === 'phd' ? 'PhD' : 'PostDoc/Tenure';
            document.getElementById('logOutput').textContent = 'Starting ' + posLabel + ' Position Search...';
            
            fetch('/run', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    keywords: keywords, 
                    recipient_email: recipientEmail,
                    position_type: positionType 
                })
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

# ==================== BACKGROUND RUNNER ====================
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

def run_agent_with_queue(job_id: str, keywords: str, recipient_email: str, username: str, position_type: str = "phd"):
    """Run the PhD agent for a queued job"""
    try:
        # Acquire lock for this job
        if not acquire_lock("Mode 2 (Web Dashboard)", username, keywords, recipient_email):
            update_job_log(job_id, "\n❌ Could not acquire lock\n")
            complete_job(job_id, False, "Could not acquire lock")
            return
        
        pos_label = "PhD" if position_type == "phd" else "PostDoc/Tenure"
        update_job_log(job_id, f"🔐 Lock acquired, starting {pos_label} position search...\n")
        
        cmd = ["python3", "main.py", "--job-id", job_id, "--position-type", position_type]
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
        
        for line in process.stdout:
            update_job_log(job_id, line)
        
        process.wait()
        
        if process.returncode == 0:
            complete_job(job_id, True, "✅ Success")
        else:
            complete_job(job_id, False, f"❌ Failed (code {process.returncode})")
            
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
            args=(job_id, next_job["keywords"], next_job["recipient"], next_job["user"])
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
                return jsonify({
                    "is_running": False,
                    "last_run": job_status.get("started_at"),
                    "last_result": job_status.get("result"),
                    "log_output": job_status.get("log_output", "")
                })
    
    # No active job for this user
    if is_locked():
        lock_info = get_lock_info()
        queue_len = get_queue_length()
        return jsonify({
            "is_running": False,
            "last_run": None,
            "last_result": None,
            "log_output": f"ℹ️ Server is currently busy with another request.\n"
                          f"Current queue length: {queue_len}\n\n"
                          f"You can submit a new request - it will be queued."
        })
    
    return jsonify({
        "is_running": False,
        "last_run": None,
        "last_result": None,
        "log_output": "Ready to run. Enter keywords and click the button."
    })

@app.route('/run', methods=['POST'])
@login_required
def run():
    username = session.get('username', '')
    data = request.get_json() or {}
    keywords = data.get("keywords", "")
    recipient_email = data.get("recipient_email", "")
    position_type = data.get("position_type", "phd")  # Default to PhD
    
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
        args=(job_id, keywords, recipient_email, username, position_type)
    )
    thread.daemon = True
    thread.start()
    
    pos_label = "PhD" if position_type == "phd" else "PostDoc/Tenure"
    msg = f"🚀 {pos_label} Position Search started!"
    if recipient_email:
        msg += f" Results will be sent to {recipient_email}"
    return jsonify({"success": True, "queued": False, "message": msg})

if __name__ == '__main__':
    import uuid
    # Initialize users file if needed
    load_users()
    app.run(host='0.0.0.0', port=8080, debug=False)


