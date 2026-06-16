# Parental Control System — Setup Guide

Control your child's Windows account from a desktop app or your phone.
Runs on your parent/admin account and enforces restrictions on the child's account.

---

## What you get

| Feature | Detail |
|---|---|
| Program blocking | Terminates blocked apps (Chrome, games, etc.) within 2 seconds |
| Website blocking | Edits the Windows hosts file — works in every browser |
| Time-limited sessions | Restrictions lift automatically when the timer expires |
| Remote control | Mobile-friendly web page on your phone (same WiFi) |
| Multi-account | Runs on your account, controls the child's account |
| Optional service | Runs even when you are not logged in (advanced) |

---

## Prerequisites

**Windows accounts**

You need two separate Windows accounts:

- **Parent account** — must be Administrator type. This is where you install and run everything.
- **Child account** — Standard User type. This is the account being restricted.

To check account types: Settings → Accounts → Family & other users.

**Python**

1. Download from **https://www.python.org/downloads/** (Python 3.10 or newer).
2. Run the installer. On the first screen, tick **"Add Python to PATH"** before clicking Install Now.
3. After install, close any open Command Prompt windows and open a new one.

**Verify Python works:**
```
python --version
```
Should print something like `Python 3.12.x`.

---

## Installation

### 1 — Copy the files

Create a folder on your PC, for example `C:\ParentalControl\`, and put all files there. The structure must be:

```
C:\ParentalControl\
├── parental_control.py
├── remote_server.py
├── parental_control_service.py
├── service_wrapper.bat
├── requirements.txt
└── templates\
    ├── login.html
    └── dashboard.html
```

### 2 — Install Python packages

Open **Command Prompt** (no need for Administrator here) and run:

```
pip install -r C:\ParentalControl\requirements.txt
```

You should see packages downloading and a final `Successfully installed …` message.

### 3 — First run — set your password

Right-click **Command Prompt** → **Run as administrator**, then:

```
cd C:\ParentalControl
python parental_control.py
```

A window will appear asking you to set a parent password. Choose one and confirm it. The app then opens the main screen.

### 4 — Select the child account to monitor

In the **"Child Accounts to Monitor"** section at the top, tick the checkbox next to your child's Windows username. This tells the app which account to watch.

---

## Daily use — Desktop app

Every time you want to create or manage sessions, open an **Administrator** Command Prompt and run:

```
cd C:\ParentalControl
python parental_control.py
```

Or make a shortcut: right-click `parental_control.py` → Send to → Desktop. Then right-click the shortcut → Properties → Shortcut tab → Advanced → tick "Run as administrator".

**To start a session:**

1. Select the child's username from the dropdown.
2. Set a duration in minutes (e.g. 60).
3. Tick which programs and/or websites to block.
4. Click **Start Session**.

The child's account is now restricted. When the timer runs out, restrictions lift automatically.

**To end a session early:**

Select the user and click **End Session**.

---

## Daily use — Remote control from your phone

This lets you tap a button on your phone to grant or revoke computer time without touching the PC.

### Start the remote server

Open a second **Administrator** Command Prompt and run:

```
cd C:\ParentalControl
python remote_server.py
```

The server will print a URL like:
```
Open on your phone:  http://192.168.1.42:5000
```

Keep this window open. The server stops when you close it.

### Connect from your phone

1. Make sure your phone is on the **same WiFi network** as the PC.
2. Open any browser on your phone.
3. Type the URL shown above (e.g. `http://192.168.1.42:5000`).
4. Log in with your parent password.

**What you can do from your phone:**

- See all active sessions and time remaining (auto-refreshes every 5 seconds).
- Tap a **Quick Action** button — one tap starts a preset session for the selected child.
- Use **Custom Session** to set an exact duration and pick exactly what to block.
- Tap **End Session** to lift restrictions immediately.

**Quick Actions available:**

| Button | Duration | What's blocked |
|---|---|---|
| Gaming 1 hr | 60 min | Chrome, Firefox, Edge |
| Gaming 2 hr | 120 min | Chrome, Firefox, Edge |
| Homework 1 hr | 60 min | Games + YouTube, TikTok, Instagram, Twitch |
| Homework 2 hr | 120 min | Games + YouTube, TikTok, Instagram, Twitch |
| Free Time 1 hr | 60 min | Nothing |
| Free Time 2 hr | 120 min | Nothing |

**Tip:** Bookmark the URL on your phone and add it to the home screen for instant access.

---

## Optional — Run as a Windows Service

By default the monitoring only runs when you are logged in and the desktop app is open. Installing as a Windows Service means monitoring runs automatically at startup, even when no one is logged in.

### Step 1 — Test the service script first

In an Administrator Command Prompt:

```
cd C:\ParentalControl
python parental_control_service.py
```

You should see `Parental Control Service started.` with no errors. Press Ctrl+C to stop.

### Step 2 — Download NSSM

NSSM (Non-Sucking Service Manager) is a free tool that turns any script into a Windows Service.

1. Go to **https://nssm.cc/download**
2. Download the latest zip (e.g. `nssm-2.24.zip`).
3. Extract it. Copy `win64\nssm.exe` to `C:\Windows\System32\` so it works from any Command Prompt.

### Step 3 — Check your Python path

In Command Prompt:

```
where python
```

Note the full path, e.g. `C:\Users\YourName\AppData\Local\Programs\Python\Python312\python.exe`.

If it is **not** just `python.exe` (i.e. Python is not on your PATH), open `service_wrapper.bat` in Notepad and update the `PYTHON=` line with the full path.

### Step 4 — Install the service

In an **Administrator** Command Prompt:

```
nssm install ParentalControl
```

A GUI opens. Fill it in:

**Application tab:**
- Path: `C:\ParentalControl\service_wrapper.bat`
- Startup directory: `C:\ParentalControl`
- Arguments: *(leave blank)*

**Details tab:**
- Display name: `Parental Control`
- Startup type: `Automatic`

**I/O tab (optional — enables log files):**
- Output: `C:\ParentalControl\service.log`
- Error: `C:\ParentalControl\service_error.log`

Click **Install service**.

### Step 5 — Start the service

```
nssm start ParentalControl
```

Or open **Services** (Windows key → type `services.msc`) and click Start next to "Parental Control".

### Step 6 — Verify

In Services, the status should show **Running**. Restart your PC and check again — it should start automatically.

### Managing the service later

```
nssm stop ParentalControl        # stop it
nssm start ParentalControl       # start it
nssm restart ParentalControl     # restart after changes
nssm edit ParentalControl        # change settings
nssm remove ParentalControl      # uninstall the service
```

**When the service is running** you no longer need the desktop app open for monitoring to work. You still use the desktop app or phone interface to create and manage sessions — they all share the same `parental_config.json` file.

---

## How it works

```
You (phone or desktop app)
        │
        ▼
parental_config.json   ←── shared by everything
        │
        ▼
Monitor (desktop app or service)
        │
        ├── Terminates blocked programs every 2 sec
        └── Updates Windows hosts file to block websites
```

Session restrictions are stored in `parental_config.json`. The monitor reads it continuously and enforces whatever is set there.

Website blocking works system-wide (all browsers) by redirecting blocked domains to `127.0.0.1` in the hosts file. The file is cleaned up automatically when a session ends.

Program blocking terminates any process owned by the child's account that matches the blocked list. It runs every 2 seconds, so a blocked program can't stay open.

---

## Troubleshooting

**"pip is not recognized"**
Close and reopen Command Prompt after installing Python. Make sure you ticked "Add Python to PATH" during install.

**Websites not being blocked**
The app must be run as Administrator to edit the hosts file. Right-click Command Prompt → Run as administrator.

**Can't access phone interface**
Both devices must be on the same WiFi. Double-check the IP address shown when you started `remote_server.py`. Temporarily disabling Windows Firewall can help confirm if that's the blocker.

**Child's username not appearing**
Open Command Prompt and run `net user` to see all accounts. Make sure the child account is a real Windows account, not a Microsoft family account that hasn't been used to log in yet (it needs to have logged in at least once to appear).

**Programs not being blocked**
Verify the process name in Task Manager → Details tab. Names are case-sensitive on some systems. Make sure the monitoring app or service is running.

**Password forgotten**
Delete `parental_config.json` and run `python parental_control.py` again to set a new one. This also clears any active sessions.

---

## File reference

| File | Purpose |
|---|---|
| `parental_control.py` | Desktop GUI — login, session management, background monitor |
| `remote_server.py` | Web server for phone control |
| `parental_control_service.py` | Headless monitor for Windows Service installation |
| `service_wrapper.bat` | Wrapper used by NSSM to launch the service |
| `templates/login.html` | Phone interface login page |
| `templates/dashboard.html` | Phone interface dashboard |
| `requirements.txt` | Python package list |
| `parental_config.json` | Created on first run — stores password and sessions |
