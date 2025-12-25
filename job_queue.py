"""
Job Queue Manager for PhD Headhunter
Handles job queuing, locking, and cross-mode awareness.
"""
import json
import os
import time
import uuid
from datetime import datetime
from threading import Lock
from typing import Optional, Dict, List

LOCK_FILE = "job_lock.json"
QUEUE_FILE = "job_queue.json"
JOBS_DIR = "jobs"

# Thread lock for file operations
_file_lock = Lock()

def ensure_jobs_dir():
    """Create jobs directory if it doesn't exist"""
    if not os.path.exists(JOBS_DIR):
        os.makedirs(JOBS_DIR)

def get_lock_info() -> Optional[Dict]:
    """Get current lock info if a job is running"""
    with _file_lock:
        if os.path.exists(LOCK_FILE):
            try:
                with open(LOCK_FILE, "r") as f:
                    lock_data = json.load(f)
                    # Check if lock is stale (older than 4 hours = 14400 seconds)
                    if time.time() - lock_data.get("started_at", 0) > 14400:
                        os.remove(LOCK_FILE)
                        return None
                    return lock_data
            except:
                return None
        return None

def acquire_lock(mode: str, user: str = "cron", keywords: str = "", recipient: str = "") -> bool:
    """
    Try to acquire job lock.
    Returns True if lock acquired, False if another job is running.
    """
    with _file_lock:
        if os.path.exists(LOCK_FILE):
            # Check if lock is stale
            try:
                with open(LOCK_FILE, "r") as f:
                    lock_data = json.load(f)
                    if time.time() - lock_data.get("started_at", 0) < 14400:
                        return False  # Lock is valid, can't acquire
            except:
                pass  # Corrupted lock file, proceed to acquire
        
        # Acquire lock
        lock_data = {
            "mode": mode,
            "user": user,
            "keywords": keywords,
            "recipient": recipient,
            "started_at": time.time(),
            "started_at_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(LOCK_FILE, "w") as f:
            json.dump(lock_data, f)
        return True

def release_lock():
    """Release the job lock"""
    with _file_lock:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

def is_locked() -> bool:
    """Check if a job is currently running"""
    return get_lock_info() is not None

# ==================== QUEUE MANAGEMENT ====================

def load_queue() -> List[Dict]:
    """Load job queue from file"""
    with _file_lock:
        if os.path.exists(QUEUE_FILE):
            try:
                with open(QUEUE_FILE, "r") as f:
                    return json.load(f)
            except:
                return []
        return []

def save_queue(queue: List[Dict]):
    """Save job queue to file"""
    with _file_lock:
        with open(QUEUE_FILE, "w") as f:
            json.dump(queue, f, indent=2)

def add_to_queue(user: str, keywords: str, recipient: str) -> str:
    """
    Add a job to the queue.
    Returns job_id for tracking.
    """
    job_id = str(uuid.uuid4())[:8]
    job = {
        "job_id": job_id,
        "user": user,
        "keywords": keywords,
        "recipient": recipient,
        "status": "queued",
        "queued_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "queued_at_ts": time.time()
    }
    
    queue = load_queue()
    queue.append(job)
    save_queue(queue)
    
    return job_id

def get_queue_position(job_id: str) -> int:
    """Get position in queue (1-indexed), 0 if not found"""
    queue = load_queue()
    for i, job in enumerate(queue):
        if job["job_id"] == job_id:
            return i + 1
    return 0

def pop_next_job() -> Optional[Dict]:
    """Get and remove the next job from queue"""
    queue = load_queue()
    if queue:
        job = queue.pop(0)
        save_queue(queue)
        return job
    return None

def get_queue_length() -> int:
    """Get number of jobs in queue"""
    return len(load_queue())

# ==================== JOB STATUS TRACKING ====================

def create_job_status(job_id: str, user: str, keywords: str, recipient: str) -> str:
    """Create a job status file for tracking"""
    ensure_jobs_dir()
    status = {
        "job_id": job_id,
        "user": user,
        "keywords": keywords,
        "recipient": recipient,
        "status": "running",
        "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "log_output": "Starting PhD Headhunter Agent...\n",
        "result": None
    }
    
    status_file = os.path.join(JOBS_DIR, f"{job_id}.json")
    with open(status_file, "w") as f:
        json.dump(status, f, indent=2)
    
    return job_id

def update_job_log(job_id: str, log_line: str):
    """Update job log output"""
    status_file = os.path.join(JOBS_DIR, f"{job_id}.json")
    if os.path.exists(status_file):
        with open(status_file, "r") as f:
            status = json.load(f)
        
        status["log_output"] += log_line
        # Keep only last 100 lines
        lines = status["log_output"].split("\n")
        if len(lines) > 100:
            status["log_output"] = "\n".join(lines[-100:])
        
        with open(status_file, "w") as f:
            json.dump(status, f, indent=2)

def complete_job(job_id: str, success: bool, result_message: str = ""):
    """Mark job as completed"""
    status_file = os.path.join(JOBS_DIR, f"{job_id}.json")
    if os.path.exists(status_file):
        with open(status_file, "r") as f:
            status = json.load(f)
        
        status["status"] = "success" if success else "failed"
        status["result"] = result_message
        status["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(status_file, "w") as f:
            json.dump(status, f, indent=2)

def get_job_status(job_id: str) -> Optional[Dict]:
    """Get job status"""
    status_file = os.path.join(JOBS_DIR, f"{job_id}.json")
    if os.path.exists(status_file):
        with open(status_file, "r") as f:
            return json.load(f)
    return None

def cleanup_old_jobs(max_age_hours: int = 24):
    """Remove job status files older than max_age_hours"""
    ensure_jobs_dir()
    current_time = time.time()
    for filename in os.listdir(JOBS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(JOBS_DIR, filename)
            if current_time - os.path.getmtime(filepath) > max_age_hours * 3600:
                os.remove(filepath)
