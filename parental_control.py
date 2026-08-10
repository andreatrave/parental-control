"""
Parental Control System for Windows 11 - Desktop App
Runs on the parent account and monitors child accounts.
Requires Administrator privileges.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import hashlib
import os
import psutil
import threading
import time
from datetime import datetime, timedelta
import subprocess
import ctypes
import sys


CONFIG_FILE = "parental_config.json"

PROGRAMS = [
    "chrome.exe",
    "firefox.exe",
    "msedge.exe",
    "Minecraft.exe",
    "MinecraftLauncher.exe",
    "RobloxPlayerBeta.exe",
    "steam.exe",
]

WEBSITES = [
    "youtube.com",
    "tiktok.com",
    "instagram.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "twitch.tv",
]


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "password_hash": None,
        "controlled_users": [],
        "active_sessions": {},
    }


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def get_process_owner(pid):
    try:
        import win32api, win32con, win32security
        handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, False, pid)
        token = win32security.OpenProcessToken(handle, win32con.TOKEN_QUERY)
        sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
        return win32security.LookupAccountSid(None, sid)[0].lower()
    except Exception:
        return None


def terminate_process_for_user(process_name, username):
    for proc in psutil.process_iter(["name", "pid"]):
        try:
            if proc.info["name"].lower() == process_name.lower():
                owner = get_process_owner(proc.info["pid"])
                if owner and owner == username.lower():
                    proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
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


def update_hosts_file(blocked_sites):
    """Replace all PARENTAL_CONTROL entries in the hosts file."""
    if not is_admin():
        return False
    hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
    all_domains = expand_domains(blocked_sites)
    try:
        with open(hosts_path, "r") as f:
            lines = [l for l in f.readlines() if "# PARENTAL_CONTROL" not in l]
        for site in sorted(all_domains):
            lines.append(f"127.0.0.1 {site} # PARENTAL_CONTROL\n")
            lines.append(f"127.0.0.1 www.{site} # PARENTAL_CONTROL\n")
        with open(hosts_path, "w") as f:
            f.writelines(lines)
        subprocess.run(
            ["ipconfig", "/flushdns"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return True
    except Exception as e:
        print(f"Hosts file error: {e}")
        return False


def get_windows_users():
    """Return non-system user accounts on this machine."""
    try:
        result = subprocess.run(
            ["net", "user"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        users = []
        in_list = False
        for line in result.stdout.splitlines():
            if "---" in line:
                in_list = True
                continue
            if not in_list:
                continue
            # Stop at the blank line or the "The command completed" footer
            if not line.strip() or line.strip().lower().startswith("the command"):
                break
            users.extend(line.split())
        skip = {
            "DefaultAccount", "Guest", "WDAGUtilityAccount", "Administrator",
            "WsiAccount", "HomeGroupUser$",
        }
        # Only keep tokens that are actually usernames (no spaces, no all-lowercase
        # dictionary words from the footer line)
        footer_words = {"the", "command", "completed", "successfully"}
        return [u for u in users if u not in skip and u.lower() not in footer_words and len(u) >= 2]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Background monitor thread
# ---------------------------------------------------------------------------

class Monitor:
    def __init__(self):
        self.running = False
        self._thread = None
        self._last_sites = set()

    def start(self):
        if not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            try:
                config = load_config()
                now = datetime.now()
                sessions = config.get("active_sessions", {})
                changed = False
                all_sites = set()

                for username in list(sessions.keys()):
                    session = sessions[username]
                    end_time = datetime.fromisoformat(session["end_time"])

                    if now > end_time:
                        del sessions[username]
                        changed = True
                        continue

                    # Block programs
                    for prog in session.get("blocked_programs", []):
                        terminate_process_for_user(prog, username)

                    all_sites.update(session.get("blocked_websites", []))

                if changed:
                    config["active_sessions"] = sessions
                    save_config(config)

                # Only update hosts file when the site list changes
                if all_sites != self._last_sites:
                    update_hosts_file(all_sites)
                    self._last_sites = all_sites

            except Exception as e:
                print(f"Monitor error: {e}")

            time.sleep(2)


monitor = Monitor()


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Parental Control")
        self.resizable(False, False)
        # Centre the root window so dialogs appear visibly on screen
        self.geometry("400x200")
        self.eval("tk::PlaceWindow . center")
        self.update()

        if not is_admin():
            messagebox.showwarning(
                "Administrator Required",
                "Please right-click the Command Prompt and choose 'Run as administrator'.\n\n"
                "The app will continue but website blocking won't work.",
            )

        config = load_config()
        if config["password_hash"] is None:
            self._setup_password(config)
        else:
            self._login(config)

    # --- auth ---

    def _setup_password(self, config):
        win = self._dialog("Set Parent Password", 320, 220)
        tk.Label(win, text="Choose a parent password:", font=("Segoe UI", 11)).pack(pady=(20, 5))
        p1 = tk.Entry(win, show="*", font=("Segoe UI", 11), width=22)
        p1.pack(pady=4)
        tk.Label(win, text="Confirm password:", font=("Segoe UI", 10)).pack()
        p2 = tk.Entry(win, show="*", font=("Segoe UI", 11), width=22)
        p2.pack(pady=4)

        def save():
            if len(p1.get()) < 4:
                messagebox.showerror("Error", "Password must be at least 4 characters.", parent=win)
                return
            if p1.get() != p2.get():
                messagebox.showerror("Error", "Passwords do not match.", parent=win)
                return
            config["password_hash"] = hash_password(p1.get())
            save_config(config)
            win.destroy()
            self._show_main()

        tk.Button(win, text="Set Password", command=save,
                  bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"), width=16).pack(pady=14)
        win.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_window(win)

    def _login(self, config):
        win = self._dialog("Parent Login", 300, 170)
        tk.Label(win, text="Enter parent password:", font=("Segoe UI", 11)).pack(pady=(20, 5))
        entry = tk.Entry(win, show="*", font=("Segoe UI", 11), width=22)
        entry.pack(pady=4)
        entry.focus()

        def check():
            if hash_password(entry.get()) == config["password_hash"]:
                win.destroy()
                self._show_main()
            else:
                messagebox.showerror("Error", "Incorrect password.", parent=win)
                entry.delete(0, tk.END)

        entry.bind("<Return>", lambda _: check())
        tk.Button(win, text="Login", command=check,
                  bg="#2196F3", fg="white", font=("Segoe UI", 10, "bold"), width=14).pack(pady=12)
        win.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_window(win)

    def _dialog(self, title, w, h):
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry(f"{w}x{h}")
        win.transient(self)
        win.grab_set()
        win.resizable(False, False)
        win.lift()
        win.focus_force()
        win.attributes("-topmost", True)
        win.after(100, lambda: win.attributes("-topmost", False))
        return win

    # --- main UI ---

    def _show_main(self):
        self.deiconify()
        self.geometry("680x620")

        # Header
        hdr = tk.Frame(self, bg="#1565C0", height=56)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Parental Control", font=("Segoe UI", 17, "bold"),
                 bg="#1565C0", fg="white").pack(side=tk.LEFT, padx=16, pady=12)
        tk.Label(hdr, text="Running as Administrator ✓" if is_admin() else "⚠ Not Administrator",
                 font=("Segoe UI", 9), bg="#1565C0",
                 fg="#A5D6A7" if is_admin() else "#EF9A9A").pack(side=tk.RIGHT, padx=16)

        body = tk.Frame(self, padx=18, pady=14)
        body.pack(fill=tk.BOTH, expand=True)

        # --- Controlled users ---
        uf = tk.LabelFrame(body, text="Child Accounts to Monitor",
                           font=("Segoe UI", 10, "bold"), padx=10, pady=8)
        uf.pack(fill=tk.X, pady=(0, 12))

        all_users = get_windows_users()
        current = os.environ.get("USERNAME", "").lower()
        config = load_config()
        controlled = config.get("controlled_users", [])

        self._user_vars = {}
        row = tk.Frame(uf)
        row.pack(anchor="w")
        for u in all_users:
            if u.lower() == current:
                continue
            var = tk.BooleanVar(value=(u in controlled))
            self._user_vars[u] = var
            tk.Checkbutton(row, text=u, variable=var,
                           command=self._save_users, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=8)

        if not self._user_vars:
            tk.Label(uf, text="No other user accounts found on this PC.",
                     fg="#888", font=("Segoe UI", 9)).pack(anchor="w")

        # --- Active sessions ---
        sf = tk.LabelFrame(body, text="Active Sessions",
                           font=("Segoe UI", 10, "bold"), padx=10, pady=8)
        sf.pack(fill=tk.X, pady=(0, 12))

        self._status_text = tk.Text(sf, height=4, font=("Segoe UI", 9),
                                    state="disabled", bg="#F5F5F5", relief=tk.FLAT)
        self._status_text.pack(fill=tk.X)

        # --- Create session ---
        cf = tk.LabelFrame(body, text="Create Session",
                           font=("Segoe UI", 10, "bold"), padx=10, pady=8)
        cf.pack(fill=tk.X, pady=(0, 12))

        # User + duration row
        row1 = tk.Frame(cf)
        row1.pack(fill=tk.X, pady=(0, 8))

        tk.Label(row1, text="For user:", font=("Segoe UI", 10)).pack(side=tk.LEFT)
        self._sel_user = tk.StringVar()
        user_names = list(self._user_vars.keys())
        self._user_combo = ttk.Combobox(row1, textvariable=self._sel_user,
                                        values=user_names, state="readonly", width=16)
        if user_names:
            self._user_combo.current(0)
        self._user_combo.pack(side=tk.LEFT, padx=(6, 24))

        tk.Label(row1, text="Duration (min):", font=("Segoe UI", 10)).pack(side=tk.LEFT)
        self._duration = tk.StringVar(value="60")
        tk.Entry(row1, textvariable=self._duration, width=6,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=6)

        # Programs + websites columns
        cols = tk.Frame(cf)
        cols.pack(fill=tk.X, pady=(4, 0))

        left = tk.LabelFrame(cols, text="Block Programs", font=("Segoe UI", 9), padx=6, pady=4)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        self._prog_vars = {}
        for p in PROGRAMS:
            var = tk.BooleanVar()
            self._prog_vars[p] = var
            tk.Checkbutton(left, text=p, variable=var, font=("Segoe UI", 9)).pack(anchor="w")

        right = tk.LabelFrame(cols, text="Block Websites", font=("Segoe UI", 9), padx=6, pady=4)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._site_vars = {}
        for s in WEBSITES:
            var = tk.BooleanVar()
            self._site_vars[s] = var
            tk.Checkbutton(right, text=s, variable=var, font=("Segoe UI", 9)).pack(anchor="w")

        # Buttons
        btns = tk.Frame(cf)
        btns.pack(pady=(12, 0))
        tk.Button(btns, text="▶  Start Session", command=self._start_session,
                  bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"),
                  width=16, cursor="hand2").pack(side=tk.LEFT, padx=6)
        tk.Button(btns, text="■  End Session", command=self._end_session,
                  bg="#E53935", fg="white", font=("Segoe UI", 10, "bold"),
                  width=16, cursor="hand2").pack(side=tk.LEFT, padx=6)

        # Tip banner
        tip = tk.Frame(body, bg="#E3F2FD", padx=10, pady=6)
        tip.pack(fill=tk.X)
        tk.Label(tip, text="💡  Run start_remote_server.bat to control this from your phone.",
                 bg="#E3F2FD", font=("Segoe UI", 9)).pack()

        monitor.start()
        self._refresh_status()

    def _save_users(self):
        config = load_config()
        config["controlled_users"] = [u for u, v in self._user_vars.items() if v.get()]
        save_config(config)

    def _start_session(self):
        username = self._sel_user.get()
        if not username:
            messagebox.showerror("Error", "Please select a user.")
            return
        try:
            duration = int(self._duration.get())
            assert duration > 0
        except Exception:
            messagebox.showerror("Error", "Enter a valid duration (minutes).")
            return

        blocked_progs = [p for p, v in self._prog_vars.items() if v.get()]
        blocked_sites = [s for s, v in self._site_vars.items() if v.get()]
        end_time = datetime.now() + timedelta(minutes=duration)

        config = load_config()
        config["active_sessions"][username] = {
            "end_time": end_time.isoformat(),
            "blocked_programs": blocked_progs,
            "blocked_websites": blocked_sites,
        }
        save_config(config)

        lines = [f"Session started for {username} — ends at {end_time.strftime('%I:%M %p')}"]
        if blocked_progs:
            lines.append(f"Blocked programs: {', '.join(blocked_progs)}")
        if blocked_sites:
            lines.append(f"Blocked websites: {', '.join(blocked_sites)}")
        messagebox.showinfo("Session Started", "\n".join(lines))
        self._refresh_status()

    def _end_session(self):
        username = self._sel_user.get()
        if not username:
            messagebox.showerror("Error", "Please select a user.")
            return
        config = load_config()
        if username in config["active_sessions"]:
            del config["active_sessions"][username]
            save_config(config)
            messagebox.showinfo("Done", f"Session ended for {username}.")
        else:
            messagebox.showinfo("Info", f"No active session for {username}.")
        self._refresh_status()

    def _refresh_status(self):
        config = load_config()
        sessions = config.get("active_sessions", {})
        now = datetime.now()

        self._status_text.config(state="normal")
        self._status_text.delete("1.0", tk.END)

        if not sessions:
            self._status_text.insert(tk.END, "No active sessions.")
        else:
            for user, s in sessions.items():
                end = datetime.fromisoformat(s["end_time"])
                mins = max(0, int((end - now).total_seconds() / 60))
                line = f"👤 {user}  —  {mins} min remaining  (ends {end.strftime('%I:%M %p')})"
                if s.get("blocked_programs"):
                    line += f"\n   Programs: {', '.join(s['blocked_programs'])}"
                if s.get("blocked_websites"):
                    line += f"\n   Websites: {', '.join(s['blocked_websites'])}"
                self._status_text.insert(tk.END, line + "\n\n")

        self._status_text.config(state="disabled")
        self.after(5000, self._refresh_status)


if __name__ == "__main__":
    if sys.platform != "win32":
        print("Windows only.")
        sys.exit(1)
    App().mainloop()