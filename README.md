# Parental Control System for Windows 11

A lightweight parental control system for Windows 11 that lets parents manage their child's computer access through time-limited sessions. Control it from a desktop app on the parent account, or remotely from any phone or browser on the same WiFi network.

---

## Features

- **Program blocking** — terminates blocked apps (browsers, games, etc.) within 2 seconds
- **Website blocking** — works across all browsers via the Windows hosts file
- **Automatic domain expansion** — blocking `youtube.com` also blocks all related CDN domains automatically
- **Time-limited sessions** — restrictions lift automatically when the timer expires
- **Remote control** — mobile-friendly web interface accessible from any device on the same WiFi
- **Multi-account** — runs on the parent account, controls the child's account
- **Auto-startup** — can be configured to run automatically when the PC boots

---

## Requirements

- Windows 11 (Home or Pro)
- Two separate Windows accounts: one **Administrator** (parent), one **Standard User** (child)
- Python 3.10 or newer
- The child account must have logged in at least once before setup

---

## Installation

### 1. Install Python

Download from **https://www.python.org/downloads/**

> ⚠️ On the installer's first screen, tick **"Add Python to PATH"** before clicking Install Now.

After installing, close and reopen any Command Prompt windows.

### 2. Download the code

Clone or download this repository into a folder on the parent account, e.g. `C:\Users\YourName\apps\ParentalControl\`

### 3. Install dependencies

Open Command Prompt and run:

```
pip install -r requirements.txt
```

### 4. First run

Open Command Prompt **as Administrator** (right-click → Run as administrator):

```
cd C:\Users\YourName\apps\ParentalControl
python parental_control.py
```

A window will appear asking you to set a parent password. After setting it, the main app opens.

In the **"Child Accounts to Monitor"** section, tick the checkbox next to the child's Windows username.

---

## File Structure

```
ParentalControl/
├── parental_control.py           # Desktop GUI — monitor and enforce rules
├── remote_server.py              # Web server for phone/browser control
├── parental_control_service.py   # Headless monitor for Windows Service install
├── service_wrapper.bat           # Wrapper used by NSSM for the service
├── requirements.txt              # Python dependencies
└── templates/
    ├── login.html                # Phone interface — login page
    └── dashboard.html            # Phone interface — control dashboard
```

> `parental_config.json` is created on first run and stores the password hash, controlled accounts, and active sessions. It is excluded from the repo via `.gitignore` — do not share it.

---

## Running Manually

Both servers must run simultaneously. Open **two separate Administrator Command Prompt windows**.

**Window 1 — Desktop monitor (required for enforcement):**
```
cd C:\Users\YourName\apps\ParentalControl
python parental_control.py
```

**Window 2 — Remote web server (required for phone access):**
```
cd C:\Users\YourName\apps\ParentalControl
python remote_server.py
```

The remote server prints a URL when it starts, e.g.:
```
Open on your phone:  http://192.168.1.42:5000
```

Open that URL in any browser on a device connected to the same WiFi network.

> **Important:** The desktop monitor (`parental_control.py`) must always be running for restrictions to be enforced. The remote server alone does not enforce anything — it only reads and writes the config file.

---

## Using the Desktop App

1. Select the child's username from the dropdown
2. Set a duration in minutes
3. Tick which programs and/or websites to block
4. Click **Start Session**

The child's account is now restricted. Restrictions lift automatically when the timer expires. Click **End Session** to stop early.

---

## Using the Phone Interface

Open `http://YOUR_PC_IP:5000` in your phone browser. Both devices must be on the same WiFi.

**Quick Actions** — one tap to start a preset session:

| Button | Duration | What's blocked |
|---|---|---|
| Gaming 1 hr | 60 min | Chrome, Firefox, Edge |
| Gaming 2 hr | 120 min | Chrome, Firefox, Edge |
| Homework 1 hr | 60 min | Games + YouTube, TikTok, Instagram, Twitch |
| Homework 2 hr | 120 min | Games + YouTube, TikTok, Instagram, Twitch |
| Free Time 1 hr | 60 min | Nothing |
| Free Time 2 hr | 120 min | Nothing |

**Custom Session** — set any duration and choose exactly which programs and websites to block.

**Tip:** Add the URL to your phone's home screen for instant one-tap access.

---

## Website Blocking — Domain Expansion

Blocking a primary domain automatically blocks all related domains. You only need to select the main domain — the expansion happens silently in the background.

| You select | Also blocked automatically |
|---|---|
| `youtube.com` | `googlevideo.com`, `ytimg.com`, `yt3.ggpht.com`, `youtubekids.com`, `youtube-nocookie.com`, `yt.be` |
| `instagram.com` | `cdninstagram.com` |
| `tiktok.com` | `tiktokcdn.com`, `tiktokv.com`, `musical.ly` |
| `facebook.com` | `fbcdn.net`, `fbsbx.com` |
| `twitter.com` | `x.com`, `t.co`, `twimg.com` |
| `twitch.tv` | `twitchapps.com`, `jtvnw.net`, `twitchsvc.net` |

---

## Auto-Startup via Task Scheduler

To have both servers start automatically when the PC boots, without needing to open Command Prompt manually.

### Step 1 — Find your Python path

Open Command Prompt and run:
```
where python
```

Note the path that does **not** contain `WindowsApps`, e.g.:
```
C:\Users\YourName\AppData\Local\Python\bin\python.exe
```

### Step 2 — Create the monitor task

1. Press Windows key, search **Task Scheduler**, open it
2. Click **Create Task** (not Basic Task)
3. Configure each tab:

**General tab:**
- Name: `Parental Control Monitor`
- ✅ Run whether user is logged on or not
- ✅ Run with highest privileges
- Configure for: `Windows 10`

**Triggers tab:**
- New → Begin the task: **At startup** → OK

**Actions tab:**
- New → Action: Start a program
- Program/script: `C:\Users\YourName\AppData\Local\Python\bin\python.exe`
- Add arguments: `C:\Users\YourName\apps\ParentalControl\parental_control.py`
- Start in: `C:\Users\YourName\apps\ParentalControl`
- OK

**Conditions tab:**
- ❌ Uncheck "Start only if on AC power"

**Settings tab:**
- ✅ Run task as soon as possible after a scheduled start is missed
- ✅ If the task fails, restart every: `1 minute`, up to `3 times`

4. Click OK and enter your Windows password when prompted

### Step 3 — Create the remote server task

Repeat Step 2 with these differences:
- Name: `Parental Control Remote Server`
- Add arguments: `C:\Users\YourName\apps\ParentalControl\remote_server.py`

### Step 4 — Allow port 5000 through the firewall

1. Press Windows key, search **Windows Defender Firewall with Advanced Security**
2. Click **Inbound Rules** → **New Rule**
3. Rule type: **Port** → TCP → Specific local port: `5000`
4. Action: **Allow the connection**
5. Profile: ✅ Domain, ✅ Private (uncheck Public)
6. Name: `Parental Control Remote Server`
7. Finish

### Step 5 — Test without rebooting

Right-click each task → **Run**. Then open `http://localhost:5000` in a browser on the PC to verify the remote server is up.

---

## Optional — Windows Service (Advanced)

For a more robust installation using NSSM (Non-Sucking Service Manager). This runs the monitor as a true Windows Service under the System account, even more reliably than Task Scheduler.

### Install NSSM

1. Download from **https://nssm.cc/download**
2. Extract and copy `win64\nssm.exe` to `C:\Windows\System32\`

### Install the service

Open an Administrator Command Prompt:

```
nssm install ParentalControl
```

In the GUI that opens:
- **Path:** `C:\Users\YourName\apps\ParentalControl\service_wrapper.bat`
- **Startup directory:** `C:\Users\YourName\apps\ParentalControl`
- **Startup type:** Automatic

Click **Install service**, then:

```
nssm start ParentalControl
```

### Manage the service

```
nssm start ParentalControl      # start
nssm stop ParentalControl       # stop
nssm restart ParentalControl    # restart
nssm remove ParentalControl     # uninstall
```

---

## Troubleshooting

**"pip is not recognized"**
Close and reopen Command Prompt after installing Python. Make sure "Add Python to PATH" was ticked during installation.

**Websites not being blocked**
The app must run as Administrator. Right-click Command Prompt → Run as administrator.

**Phone can't connect to remote server**
- Both devices must be on the same WiFi network
- Check the IP address shown when `remote_server.py` starts
- Make sure the firewall rule for port 5000 has been added (see Auto-Startup Step 4)

**Already-open browser tabs not blocked immediately**
This is expected — the hosts file only intercepts new connections. Close and reopen the browser on the child's account after starting a session.

**Child's username not appearing in the app**
The child account must have logged in at least once. Run `net user` in Command Prompt to see all accounts on the PC.

**Password forgotten**
Delete `parental_config.json` and run `python parental_control.py` again to set a new password. This also clears any active sessions.

**Task Scheduler task fails with error 2147942402**
Task Scheduler can't find Python. Use the full Python path in the Actions tab (see Auto-Startup Step 1).

---

## Security Notes

- The parent password is stored as a SHA-256 hash, never in plain text
- The remote server is only accessible on the local network — it is not exposed to the internet
- The child account should be a Standard User (not Administrator) to prevent bypassing controls
- `parental_config.json` contains your password hash — keep it local and do not commit it to version control

---

## Known Limitations

- Website blocking uses the hosts file — effective for most sites but a determined user could bypass it with a VPN
- Already-loaded browser tabs are not force-closed when a session starts — only new page loads are blocked
- The system currently works as a block-list (allow everything except X). Allowlist mode (block everything except X) is planned for a future version

---

## Roadmap

- [ ] Default locked state — block everything when no session is active
- [ ] Scheduled sessions — recurring sessions at set times (e.g. every Sunday 5pm)
- [ ] Allowlist mode — only allow specific programs or websites
- [ ] Multiple session conflict resolution
- [ ] Login prevention when no session is active

---

## License

Free to use and modify for personal use.
