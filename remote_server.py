"""
Parental Control System - Remote Web Server
Serves a mobile-friendly web interface so parents can control
sessions from their phone on the same WiFi network.
"""

import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, jsonify, session, redirect, url_for

CONFIG_FILE = "parental_config.json"

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

QUICK_ACTIONS = {
    "gaming_1hr": {
        "label": "Gaming 1 hr",
        "duration": 60,
        "blocked_programs": ["chrome.exe", "firefox.exe", "msedge.exe"],
        "blocked_websites": [],
    },
    "gaming_2hr": {
        "label": "Gaming 2 hr",
        "duration": 120,
        "blocked_programs": ["chrome.exe", "firefox.exe", "msedge.exe"],
        "blocked_websites": [],
    },
    "homework_1hr": {
        "label": "Homework 1 hr",
        "duration": 60,
        "blocked_programs": ["Minecraft.exe", "MinecraftLauncher.exe", "RobloxPlayerBeta.exe", "steam.exe"],
        "blocked_websites": ["youtube.com", "tiktok.com", "instagram.com", "twitch.tv"],
    },
    "homework_2hr": {
        "label": "Homework 2 hr",
        "duration": 120,
        "blocked_programs": ["Minecraft.exe", "MinecraftLauncher.exe", "RobloxPlayerBeta.exe", "steam.exe"],
        "blocked_websites": ["youtube.com", "tiktok.com", "instagram.com", "twitch.tv"],
    },
    "free_1hr": {
        "label": "Free Time 1 hr",
        "duration": 60,
        "blocked_programs": [],
        "blocked_websites": [],
    },
    "free_2hr": {
        "label": "Free Time 2 hr",
        "duration": 120,
        "blocked_programs": [],
        "blocked_websites": [],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"password_hash": None, "controlled_users": [], "active_sessions": {}}


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def verify_password(password):
    config = load_config()
    if not config.get("password_hash"):
        return False
    return hashlib.sha256(password.encode()).hexdigest() == config["password_hash"]


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return redirect(url_for("dashboard") if session.get("logged_in") else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if verify_password(request.form.get("password", "")):
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        error = "Incorrect password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.route("/api/users")
@login_required
def api_users():
    config = load_config()
    return jsonify({"users": config.get("controlled_users", [])})


@app.route("/api/status")
@login_required
def api_status():
    config = load_config()
    sessions = config.get("active_sessions", {})
    now = datetime.now()
    result = []
    changed = False

    for username, s in list(sessions.items()):
        end = datetime.fromisoformat(s["end_time"])
        if now > end:
            del sessions[username]
            changed = True
            continue
        mins = int((end - now).total_seconds() / 60)
        result.append({
            "username": username,
            "minutes_left": mins,
            "end_time": end.strftime("%I:%M %p"),
            "blocked_programs": s.get("blocked_programs", []),
            "blocked_websites": s.get("blocked_websites", []),
        })

    if changed:
        config["active_sessions"] = sessions
        save_config(config)

    return jsonify({"active": bool(result), "sessions": result})


@app.route("/api/start_session", methods=["POST"])
@login_required
def api_start_session():
    data = request.json or {}
    username = data.get("username", "").strip()
    if not username:
        return jsonify({"success": False, "message": "Username required."}), 400
    try:
        duration = int(data.get("duration", 60))
        assert duration > 0
    except Exception:
        return jsonify({"success": False, "message": "Invalid duration."}), 400

    config = load_config()
    end_time = datetime.now() + timedelta(minutes=duration)
    config["active_sessions"][username] = {
        "end_time": end_time.isoformat(),
        "blocked_programs": data.get("blocked_programs", []),
        "blocked_websites": data.get("blocked_websites", []),
    }
    save_config(config)
    return jsonify({"success": True, "message": f"Session started for {username}."})


@app.route("/api/end_session", methods=["POST"])
@login_required
def api_end_session():
    data = request.json or {}
    username = data.get("username", "").strip()
    if not username:
        return jsonify({"success": False, "message": "Username required."}), 400

    config = load_config()
    if username in config["active_sessions"]:
        del config["active_sessions"][username]
        save_config(config)
        return jsonify({"success": True, "message": f"Session ended for {username}."})
    return jsonify({"success": False, "message": f"No active session for {username}."}), 404


@app.route("/api/quick_action/<action>", methods=["POST"])
@login_required
def api_quick_action(action):
    if action not in QUICK_ACTIONS:
        return jsonify({"success": False, "message": "Unknown action."}), 400

    data = request.json or {}
    username = data.get("username", "").strip()
    if not username:
        return jsonify({"success": False, "message": "Username required."}), 400

    qa = QUICK_ACTIONS[action]
    config = load_config()
    end_time = datetime.now() + timedelta(minutes=qa["duration"])
    config["active_sessions"][username] = {
        "end_time": end_time.isoformat(),
        "blocked_programs": qa["blocked_programs"],
        "blocked_websites": qa["blocked_websites"],
    }
    save_config(config)
    return jsonify({"success": True, "message": f"{qa['label']} started for {username}."})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not os.path.exists(CONFIG_FILE):
        print("\nERROR: parental_config.json not found.")
        print("Run the desktop app first (parental_control.py) to set your password.\n")
        exit(1)

    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    print("\n" + "=" * 55)
    print("  PARENTAL CONTROL — REMOTE SERVER")
    print("=" * 55)
    print(f"\n  Open on your phone:  http://{local_ip}:5000")
    print("\n  Both devices must be on the same WiFi network.")
    print("  Keep this window open while using remote control.")
    print("\n  Press Ctrl+C to stop.")
    print("=" * 55 + "\n")

    app.run(host="0.0.0.0", port=5000, debug=False)
