# backend/user.py
import os
import json

USER_FILE = "backend/users.json"

# Initialize users.json with default users if not exists
if not os.path.exists(USER_FILE):
    default_users = {
        "gov_user": {"password": "gov123", "role": "government"},
        "cust_user": {"password": "cust123", "role": "customer"},
        "seller_user": {"password": "sale123", "role": "seller"},
        "driver_user": {"password": "drive123", "role": "driver"}
    }
    with open(USER_FILE, "w") as f:
        json.dump(default_users, f, indent=4)

# Load users from JSON
def load_users():
    with open(USER_FILE, "r") as f:
        return json.load(f)

# Save users to JSON
def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=4)

# Authenticate user
def authenticate(username, password):
    users = load_users()
    user = users.get(username)
    return True if user and user["password"] == password else False

# Get role of a user
def get_role(username):
    users = load_users()
    user = users.get(username)
    return user["role"] if user else None

# Register new user
def register_user(username, password, role):
    users = load_users()
    if username in users:
        return False  # username already exists
    users[username] = {"password": password, "role": role}
    save_users(users)
    return True
