# J.A.R.V.I.S — Personal AI Assistant
## Just A Rather Very Intelligent System

```
  ╔══════════════════════════════════════════════════════╗
  ║   Built for Prashant | Powered by Anthropic Claude   ║
  ╚══════════════════════════════════════════════════════╝
```

---

## ✨ Features

| Module          | What JARVIS Can Do |
|----------------|---------------------|
| 🎙️ Voice        | Wake word detection, STT via Google, TTS (JARVIS-like male voice) |
| 🧠 AI Brain     | Anthropic Claude — full conversational intelligence |
| 💻 System       | Open apps, file explorer, hardware monitor, volume, screenshot |
| 📧 Email        | Check unread Gmail, send emails by voice |
| 📅 Calendar     | Today/upcoming events, add events, open Google Calendar |
| 🌤️ Weather      | Real-time weather + forecast (OpenWeatherMap) |
| 📰 News         | Top headlines, topic-specific news (NewsAPI) |
| 📝 Notes        | Voice notes, saved locally as JSON |
| ⏰ Reminders    | Set timed voice reminders |
| 🔍 File Search  | Search your entire file system by name |
| 🔒 Power        | Lock, shutdown, restart — with confirmation |
| 🌐 Web          | Google search, open YouTube/GitHub/Gmail instantly |

---

## ⚡ Quick Start

### 1. Install dependencies

**Windows:**
```
setup_windows.bat
```

**Linux / macOS:**
```bash
chmod +x setup_unix.sh
./setup_unix.sh
```

**Manual:**
```bash
pip install -r requirements.txt
```

---

### 2. Configure JARVIS

Edit `jarvis_config.json`:

```json
{
  "user_name": "Prashant",
  "anthropic_api_key": "sk-ant-...",        ← Get from console.anthropic.com
  "openweather_api_key": "...",              ← Free at openweathermap.org
  "news_api_key": "...",                     ← Free at newsapi.org
  "email": "prashant@gmail.com",
  "email_password": "xxxx xxxx xxxx xxxx"   ← Gmail App Password (not your login!)
}
```

#### Gmail App Password Setup:
1. Go to myaccount.google.com → Security
2. Enable 2-Step Verification
3. Go to "App Passwords" → Generate one for "Mail"
4. Paste that 16-character password in `email_password`

---

### 3. Run JARVIS

```bash
# Hybrid mode (voice + type fallback) — RECOMMENDED
python jarvis.py --mode hybrid

# Voice only (wake word: "JARVIS")
python jarvis.py --mode voice

# Text only (no microphone)
python jarvis.py --mode text
```

---

## 🎙️ Voice Commands Reference

### System
| Say                              | Action                        |
|----------------------------------|-------------------------------|
| "JARVIS, open Chrome"            | Launches Chrome               |
| "Open VS Code"                   | Launches VS Code              |
| "System status"                  | CPU, RAM, disk, battery       |
| "Network info"                   | IP address, data stats        |
| "Take a screenshot"              | Saves screenshot to Pictures  |
| "Set volume to 70"               | Sets system volume            |
| "Lock the screen"                | Locks your PC                 |
| "Shutdown"                       | Schedules shutdown (confirmed)|
| "Find file budget"               | Searches for files matching   |

### Email & Calendar
| Say                              | Action                        |
|----------------------------------|-------------------------------|
| "Check my emails"                | Reads latest unread emails    |
| "Send email to John"             | Guided email composition      |
| "What's on my calendar today"    | Today's events                |
| "My upcoming schedule"           | Next 7 days                   |
| "Add event Meeting tomorrow"     | Adds to local calendar        |
| "Open Google Calendar"           | Opens in browser              |

### Info & Productivity
| Say                              | Action                        |
|----------------------------------|-------------------------------|
| "What's the weather"             | Current weather               |
| "Weather in Mumbai"              | Weather for specific city     |
| "Top news today"                 | Latest headlines              |
| "News about AI"                  | Topic-specific news           |
| "Take a note: buy groceries"     | Saves voice note              |
| "Read my notes"                  | Reads saved notes             |
| "Remind me in 10 minutes"        | Sets a timed reminder         |

### AI Conversation
Anything not matched above goes to Claude AI — ask JARVIS anything:
- "Explain recursion to me"
- "Help me write a Python function to..."
- "What's the difference between TCP and UDP?"
- "Motivate me for JEE prep"

---

## 🗂️ File Structure

```
jarvis/
├── jarvis.py              ← Main assistant (all-in-one)
├── jarvis_config.json     ← Your personal config & API keys
├── requirements.txt       ← Python dependencies
├── setup_windows.bat      ← Windows auto-installer
├── setup_unix.sh          ← Linux/macOS auto-installer
├── jarvis_events.json     ← Calendar events (auto-created)
├── jarvis_notes.json      ← Notes (auto-created)
└── jarvis_reminders.json  ← Reminders (auto-created)
```

---

## 🛠️ Adding Custom Apps

In `jarvis_config.json`:
```json
"custom_apps": {
  "pycharm":    "pycharm",
  "kali":       "wsl -d kali-linux",
  "burpsuite":  "C:\\BurpSuite\\burpsuite_community.exe",
  "obs":        "obs"
}
```
Then say: *"JARVIS, open Burpsuite"* ✓

---

## 🔧 Troubleshooting

**PyAudio fails to install on Windows:**
```bash
pip install pipwin
pipwin install pyaudio
```
Or download from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

**Microphone not detected:**
- Check Windows Settings → Privacy → Microphone → Allow apps
- Use `--mode text` to bypass mic completely

**Voice sounds robotic:**
- Windows: Go to Control Panel → Speech → Install additional voices
- Try "Microsoft David" or "Microsoft Zira" voices

**Email fails:**
- Make sure you're using Gmail App Password, not your login password
- Enable IMAP: Gmail Settings → See All Settings → Forwarding and POP/IMAP

---

## 🚀 Pro Tips

- Say **"JARVIS"** (2 syllables, clearly) for best wake word detection
- Run in background: `pythonw jarvis.py` (Windows, no console window)
- Add to Windows startup: place shortcut in `shell:startup`
- For 4 AM sessions: JARVIS will detect morning and greet accordingly

---

*"Sometimes you gotta run before you can walk." — Tony Stark*
