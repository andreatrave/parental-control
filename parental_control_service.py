"""
Parental Control System - Background Service
Runs without a GUI. Used with NSSM or Task Scheduler so monitoring
works even when no one is logged in.
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime

import psutil


CONFIG_FILE = "parental_config.json"
DEFAULT_LOCKDOWN_PROGRAMS = [
    "chrome.exe",
    "firefox.exe",
    "msedge.exe",
    "Minecraft.exe",
    "MinecraftLauncher.exe",
    "RobloxPlayerBeta.exe",
    "steam.exe",
]
DEFAULT_LOCKDOWN_WEBSITES = [
    "youtube.com",
    "tiktok.com",
    "instagram.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "twitch.tv",
]


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"controlled_users": [], "active_sessions": {}}


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_process_owner(pid):
    try:
        import win32api, win32con, win32security
        handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, False, pid)
        token = win32security.OpenProcessToken(handle, win32con.TOKEN_QUERY)
        sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
        return win32security.LookupAccountSid(None, sid)[0].lower()
    except Exception:
        return None


def terminate_for_user(process_name, username):
    for proc in psutil.process_iter(["name", "pid"]):
        try:
            if proc.info["name"].lower() == process_name.lower():
                if get_process_owner(proc.info["pid"]) == username.lower():
                    proc.terminate()
                    log(f"Terminated {process_name} for {username}")
        except Exception:
            pass


# Hidden domain expansions - applied automatically when a primary domain is blocked
DOMAIN_EXPANSIONS = {
    "youtube.com": [
        "youtube.com",
        "googlevideo.com",
        "ytimg.com",
        "yt3.ggpht.com",
        "youtubekids.com",
        "youtube-nocookie.com",
        "yt.be",
    ],
    "instagram.com": [
        "instagram.com",
        "cdninstagram.com",
    ],
    "tiktok.com": [
        "tiktok.com",
        "tiktokcdn.com",
        "tiktokv.com",
        "musical.ly",
    ],
    "facebook.com": [
        "facebook.com",
        "fbcdn.net",
        "fbsbx.com",
    ],
    "twitter.com": [
        "twitter.com",
        "x.com",
        "t.co",
        "twimg.com",
    ],
    "twitch.tv": [
        "twitch.tv",
        "twitchapps.com",
        "jtvnw.net",
        "twitchsvc.net",
    ],
}

def expand_domains(blocked_sites):
    """Expand each blocked site to include all related domains transparently."""
    expanded = set()
    for site in blocked_sites:
        if site in DOMAIN_EXPANSIONS:
            expanded.update(DOMAIN_EXPANSIONS[site])
        else:
            expanded.add(site)
    return expanded


def get_effective_restrictions(username, session=None, default_programs=None, default_websites=None):
    """Return the active restrictions for a user, falling back to lockdown defaults when no session exists."""
    if session is not None:
        return session.get("blocked_programs", []), session.get("blocked_websites", [])
    return (default_programs or []), (default_websites or [])


def update_hosts(blocked_sites):
    hosts = r"C:\Windows\System32\drivers\etc\hosts"
    all_domains = expand_domains(blocked_sites)
    try:
        with open(hosts, "r") as f:
            lines = [l for l in f if "# PARENTAL_CONTROL" not in l]
        for site in sorted(all_domains):
            lines.append(f"127.0.0.1 {site} # PARENTAL_CONTROL\n")
            lines.append(f"127.0.0.1 www.{site} # PARENTAL_CONTROL\n")
        with open(hosts, "w") as f:
            f.writelines(lines)
        subprocess.run(["ipconfig", "/flushdns"], capture_output=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        log(f"Hosts file error: {e}")


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def run():
    # Work from the folder where this script lives
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    log("Parental Control Service started.")
    log(f"Config: {os.path.abspath(CONFIG_FILE)}")

    last_sites: set = set()

    while True:
        try:
            config = load_config()
            now = datetime.now()
            sessions = config.get("active_sessions", {})
            changed = False
            all_sites: set = set()
            controlled_users = list(dict.fromkeys(config.get("controlled_users", []) + list(sessions.keys())))

            for username in controlled_users:
                session = sessions.get(username)
                if session is None:
                    continue

                end = datetime.fromisoformat(session["end_time"])
                if now > end:
                    log(f"Session expired for {username}")
                    del sessions[username]
                    changed = True
                    continue

                blocked_programs, blocked_websites = get_effective_restrictions(
                    username,
                    session=session,
                    default_programs=DEFAULT_LOCKDOWN_PROGRAMS,
                    default_websites=DEFAULT_LOCKDOWN_WEBSITES,
                )

                for prog in blocked_programs:
                    terminate_for_user(prog, username)

                all_sites.update(blocked_websites)

            if changed:
                config["active_sessions"] = sessions
                save_config(config)

            if all_sites != last_sites:
                update_hosts(all_sites)
                last_sites = all_sites

        except Exception as e:
            log(f"Error: {e}")

        time.sleep(2)


if __name__ == "__main__":
    if sys.platform != "win32":
        print("Windows only.")
        sys.exit(1)
    try:
        run()
    except KeyboardInterrupt:
        log("Service stopped.")