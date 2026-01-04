#!/usr/bin/env python3
"""
PhD Hunt - Admin Password Reset Script
Run this on the VPS to reset the admin password
"""
import json
import hashlib

USERS_FILE = "users.json"

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def reset_password():
    print("=" * 60)
    print("PhD Hunt - Password Reset Tool")
    print("=" * 60)
    
    # Load existing users
    try:
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
    except FileNotFoundError:
        print(f"Error: {USERS_FILE} not found!")
        return
    
    # Show existing users
    print("\nExisting users:")
    for username, data in users.items():
        admin_status = "Admin" if data.get("is_admin", False) else "User"
        print(f"  - {username} ({admin_status})")
    
    # Get username
    username = input("\nEnter username to reset password: ").strip()
    
    if username not in users:
        print(f"Error: User '{username}' not found!")
        return
    
    # Get new password
    new_password = input("Enter new password: ").strip()
    confirm_password = input("Confirm new password: ").strip()
    
    if new_password != confirm_password:
        print("Error: Passwords don't match!")
        return
    
    if len(new_password) < 4:
        print("Error: Password must be at least 4 characters!")
        return
    
    # Update password
    users[username]["password_hash"] = hash_password(new_password)
    
    # Save
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)
    
    print(f"\n✅ Password for '{username}' has been reset successfully!")
    print(f"You can now login with:")
    print(f"  Username: {username}")
    print(f"  Password: {new_password}")

if __name__ == "__main__":
    reset_password()
