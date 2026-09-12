"""
auth.py  --  very small login helper

The important idea for this POC: the usernames and passwords are NOT written
inside the Python code. They are loaded from an external file `users.json`, so
you can change accounts without touching the app. (In a real system you would
store password *hashes* in that file and use HTTPS — here we keep plain text
just so the demo is easy to read.)
"""

import json
import os

USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")


def load_users():
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def authenticate(role, username, password):
    """Return True if the username/password match the given role in users.json."""
    users = load_users()
    account = users.get(role)
    if not account:
        return False
    return username == account.get("username") and password == account.get("password")
