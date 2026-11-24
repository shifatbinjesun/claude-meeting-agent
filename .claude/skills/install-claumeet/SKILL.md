---
name: install-claumeet
description: Install, set up, start or update Claumeet on the user's own computer when they ask Claude Code to install or use this repository.
---

# Install Claumeet for the user

Claumeet runs on the user's own PC. Windows 10/11 is the supported platform; macOS and Linux are experimental.
Follow CLAUDE.md's rules throughout: free tier only, never bypass Google sign-in or meeting admission.

## 1. Check the machine
- Windows: run `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Doctor-Claumeet.ps1` if a venv exists, otherwise go to step 2.
- Confirm Python 3.12 (`py -3.12 --version` on Windows, `python3 --version` elsewhere) and Google Chrome.
- Tell the user what is missing before installing anything. Installing Python or Chrome needs their yes.

## 2. Install
- Windows: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Install-Claumeet.ps1 -Yes`
  (add `-NoShortcut` if the user doesn't want a desktop shortcut). The log is in
  `%LOCALAPPDATA%\ClaudeMeetAgent\logs\install.log`.
- macOS / Linux (experimental): `bash scripts/install.sh`
- Then run the doctor: `"%LOCALAPPDATA%\ClaudeMeetAgent\venv\Scripts\python.exe" -m claude_agent doctor`
  (macOS/Linux: `~/.local/share/ClaudeMeetAgent/venv/bin/claumeet doctor`).

## 3. Hand the private steps to the user (never do these yourself)
These involve the user's credentials, so the user does them, not you:
- **Google account for the bot.** Suggest a separate free account named like "Claumeet (AI)"
  (<https://accounts.google.com/signup>). Signing in happens on Google's own page.
- **Free Gemini API key.** From <https://aistudio.google.com/apikey>, with billing left OFF.
- Ask the user NOT to paste the key into this chat. Have them run the guided setup in their own terminal:
  Windows `"%LOCALAPPDATA%\ClaudeMeetAgent\venv\Scripts\python.exe" -m claude_agent setup`,
  or use the setup checklist in the Control Center, which stores the key in the OS credential store.

## 4. Start it
- Windows: double-click `Start-Claumeet.cmd`, or run `"%LOCALAPPDATA%\ClaudeMeetAgent\venv\Scripts\python.exe" -m claude_agent run`.
- macOS/Linux: `~/.local/share/ClaudeMeetAgent/venv/bin/claumeet run`.
- The Control Center opens at <http://127.0.0.1:8765> with a one-time pairing link. Paste a Google Meet or Zoom link
  and press Join. A person always clicks "Ask to join"/"Join" and the host admits Claumeet.

## 5. Update
`git pull` (or download the new release), then run the install step again. It keeps the user's settings, memory and key.

## Don'ts
- Don't read, print or log the Gemini key, and don't store it in a file or config.
- Don't enable billing, switch to paid models or create extra keys/projects to get around quotas.
- Don't automate Google or Zoom sign-in, CAPTCHAs, admission or waiting rooms.
- Don't say live meeting features work unless the user has tried them (see docs/TEST_REPORT.md).
