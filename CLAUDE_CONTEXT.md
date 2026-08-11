# Parental Control System — Project Context for Claude Code

## Project Overview

A Windows 11 parental control system built in Python that allows a parent to control
a child's Windows account — blocking programs and websites within time-limited sessions.
Controllable from a desktop GUI on the parent account or remotely from a phone via a
mobile web interface on the same WiFi network.

---

## Repository

https://github.com/andreatrave/parental-control

---

## File Structure

```
ParentalControl/
├── parental_control.py           # Desktop GUI app — runs on parent account, enforces rules
├── remote_server.py              # Flask web server — phone/browser remote control
├── parental_control_service.py   # Headless monitor — for Windows Service installation
├── service_wrapper.bat           # Wrapper used by NSSM to run the service
├── requirements.txt              # psutil, flask, pywin32
└── templates/
    ├── login.html                # Mobile login page
    └── dashboard.html            # Mobile control dashboard
```

`parental_config.json` is created at runtime and is excluded from git via `.gitignore`.
It stores the password hash, controlled user list, and active sessions.

---

## How It Works

### Architecture

```
Parent (desktop app or phone browser)
        │
        ▼
parental_config.json   ← shared by all components
        │
        ▼
Monitor (parental_control.py or parental_control_service.py)
        ├── Reads config every 2 seconds
        ├── Terminates blocked programs owned by child account
        └── Updates Windows hosts file to block websites
```

### Account Setup

- **Parent account** (`atrav`): Administrator. Runs all components.
- **Child account** (`trave`): Standard User. Subject to restrictions.

### Sessions

Sessions are stored in `parental_config.json` under `active_sessions`:
```json
{
  "active_sessions": {
    "trave": {
      "end_time": "2026-08-10T15:06:14.433081",
      "blocked_programs": ["chrome.exe"],
      "blocked_websites": ["youtube.com", "tiktok.com"]
    }
  }
}
```

### Program Blocking

The monitor identifies processes owned by the child account using `win32security`
and terminates any that match the blocked programs list. Runs every 2 seconds.

### Website Blocking

Edits `C:\Windows\System32\drivers\etc\hosts` to redirect blocked domains to
`127.0.0.1`. Requires Administrator privileges. DNS cache is flushed after each update.

### Domain Expansion

When a primary domain is blocked, a hidden `DOMAIN_EXPANSIONS` dictionary
automatically expands it to include all related domains. The user only selects
`youtube.com` but all related CDN/asset domains are blocked transparently.

Current expansions (defined in both `parental_control.py` and `parental_control_service.py`):

```python
DOMAIN_EXPANSIONS = {
    "youtube.com":    ["youtube.com", "googlevideo.com", "ytimg.com",
                       "yt3.ggpht.com", "youtubekids.com", "youtube-nocookie.com", "yt.be"],
    "instagram.com":  ["instagram.com", "cdninstagram.com"],
    "tiktok.com":     ["tiktok.com", "tiktokcdn.com", "tiktokv.com", "musical.ly"],
    "facebook.com":   ["facebook.com", "fbcdn.net", "fbsbx.com"],
    "twitter.com":    ["twitter.com", "x.com", "t.co", "twimg.com"],
    "twitch.tv":      ["twitch.tv", "twitchapps.com", "jtvnw.net", "twitchsvc.net"],
}
```

### Remote Server

Flask app serving a mobile-friendly interface on port 5000.
- Password protected (same parent password as desktop app)
- Shows active sessions with countdown timers (auto-refreshes every 5 seconds)
- Quick action buttons (Gaming 1hr/2hr, Homework 1hr/2hr, Free Time 1hr/2hr)
- Custom session builder (duration + checkboxes for programs/websites)
- **Important**: remote server only reads/writes config — it does NOT enforce rules.
  Enforcement is always done by the desktop app or service.

---

## Key Design Decisions

1. **Block-list model** (current): everything allowed except what is explicitly blocked.
2. **Domain expansion is hidden**: UI only shows primary domains, expansion is internal.
3. **Remote server never cleans up sessions**: only the desktop app/service does that.
4. **Single config file**: all components share `parental_config.json` — last write wins.

---

## Known Limitations

- Website blocking via hosts file cannot do allowlist mode (block everything except X)
  without a different approach (local DNS proxy or Windows Firewall rules).
- YouTube partial blocking: with domain expansion active, YouTube is effectively blocked
  but the HTML skeleton of the page may still appear from browser cache.
- Incognito mode is disabled on the child account (intentional parental setting).

---

## Windows Service (Optional)

For running the monitor even when the parent is not logged in:
- Uses NSSM (Non-Sucking Service Manager) to run `parental_control_service.py`
  as a Windows Service under the Local System account.
- `service_wrapper.bat` is the entry point for NSSM.
- Not yet installed — documented in SETUP_GUIDE.md.

---

## Todo List

### 🔴 High Priority

**Default locked state (no active session)**
- When no session is active, the child's account should be blocked from doing anything useful.
- Approach A: Task Scheduler logon script — logs child out immediately if no session active.
  Works on Windows 11 Home (Group Policy not available on Home edition).
- Approach B: Monitor service kills all non-essential programs when no session active
  (browsers, games, etc.) leaving an empty desktop.
- Decision: implement both as options, or pick one.
- Windows accounts: `atrav` (parent/admin), `trave` (child/standard user).

### 🟡 Medium Priority

**Scheduled sessions**
- Define recurring sessions in advance (e.g. every Sunday 4:50–6:10pm).
- Needs a scheduler component that creates sessions automatically at the right time.
- UI needed in both desktop app and phone interface.
- Edge cases: PC off when schedule triggers, manual session already running.

**Multiple simultaneous sessions — conflict resolution**
- Currently only one session per user at a time.
- Three options:
  1. Last wins — new session replaces old entirely (simplest, current behavior).
  2. Merge restrictive — union of blocked items, longest timer wins (safest).
  3. Merge liberal — intersection of blocked items only (most flexible).
- Likely best default: option 2 (merge restrictive).
- Also decide: can a new session extend an existing one, or only replace it?

### 🟢 Future / Lower Priority

**Allowlist mode** (block everything except X)
- Block all websites except a specific list (e.g. allow only school sites during class).
- Block all programs except a specific list (e.g. allow only Zoom during class).
- Website allowlisting needs DNS proxy or Windows Firewall — more complex than hosts file.
- Program allowlisting is straightforward (kill anything not on the allowed list).
- Zoom class scenario: allow Zoom app + specific websites, block everything else.

**Login prevention**
- Prevent child from logging in at all when no session is active.
- Windows 11 Home: Task Scheduler logon script (GPO not available on Home edition).
- Overlaps with Default locked state above.

---

## Development Environment

- Language: Python 3.12
- IDE: VS Code with Git source control
- OS: Windows 11 Home
- Dependencies: `psutil`, `flask`, `pywin32`
- Install: `pip install -r requirements.txt`
- Run desktop app: `python parental_control.py` (as Administrator)
- Run remote server: `python remote_server.py` (as Administrator)

---

## Running the System

Both commands must run simultaneously in separate Administrator Command Prompt windows:

```bash
cd C:\Users\atrav\apps\ParentalControl
python parental_control.py
```

```bash
cd C:\Users\atrav\apps\ParentalControl
python remote_server.py
```

The remote server prints the phone URL on startup, e.g. `http://192.168.x.x:5000`.
