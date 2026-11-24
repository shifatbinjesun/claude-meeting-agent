# Claumeet

An open-source, **openly identified** AI participant for Google Meet. It acts like a witty, warm
Bangladeshi friend (Bangla, Dhakaiya, Banglish and English) and works as your second brain in the call.
It runs on your own Windows PC, uses **free-tier AI only**, and you control it from a local
**Claumeet Control Center** dashboard.

> Community project. Not affiliated with Anthropic or Google. The in-meeting voice and reasoning run on
> Google's Gemini API free tier. "Claumeet" is only the participant's name, and it always says it is an AI.

## What it does

| Feature | How |
|---|---|
| Joins a Meet you approve | Its own Chrome profile and its own AI-labeled Google account. Mic starts muted, camera stays off. **You** click "Ask to join" and the host admits it (assisted mode can click for you). |
| Listens and talks | Captures **only the remote meeting audio** inside its own tab. It speaks through an in-page virtual mic. No VB-Cable or other driver is needed, and your physical mic is never opened. |
| Natural Bangladeshi conversation | Gemini Live native audio with a tuned persona: humor, greetings at natural pauses, short answers, it doesn't talk over people, and "চুপ থাক" stops it at once. |
| Safety gate | Every spoken turn passes a turn arbiter plus a deterministic permission policy. Only you (the authenticated dashboard) can make it leave, mute, share or read private memory. |
| Consent first | It processes nothing until the AI disclosure is given. It posts a bilingual disclosure in chat. Anyone can say or type "stop listening" to pause it. Late joiners are informed. |
| Second brain | Local SQLite + FTS5 memory split into public, owner-private and consented-participant domains. It can ingest documents (txt/md/csv/json) and look up public facts on Wikipedia with sources. |
| Control Center | Overview, Live Meeting, Owner Channel (private Q&A), Personality Studio, Memory & Knowledge, Scheduling, Provider & Performance, Security & Privacy. Emergency stop: **Ctrl+Shift+X**. |
| One-click Windows | `ClaumeetSetup.exe` installer with a guided setup checklist, plus `Install/Start/Stop/SignIn/Doctor-Claumeet.cmd`. |

## Install (Windows 10/11): the easy way

1. Open the [latest release](https://github.com/shifatbinjesun/claude-meeting-agent/releases/latest) and download **`ClaumeetSetup.exe`**.
2. Double-click it. It installs for your user only, so it needs **no admin rights** and installs **no drivers**.
   Before it starts it shows you exactly what Claumeet needs and where to get it:
   - **Python 3.12** and **Google Chrome**. If they are missing, the installer offers to install them with Windows' own `winget`.
   - A **separate Google account** for the bot, named something like "Claumeet (AI)" (free, <https://accounts.google.com/signup>).
   - A **free Gemini API key** (<https://aistudio.google.com/apikey>). Leave billing **off**. Claumeet only uses free-tier models.
3. When setup finishes, the **Claumeet Control Center** opens in your browser. A setup checklist at the top walks you
   through signing in the bot account, pasting the key and testing it. The key is stored in Windows Credential Manager, never in a file.
4. Paste a Meet link on **Overview** and click **Join**. Click **Ask to join** in Claumeet's Chrome window, and the host admits it.
5. After you've told everyone an AI is joining, click **Announce & start listening**.

Stop at any time with **Emergency stop** (or Ctrl+Shift+X). Use the **Stop Claumeet** shortcut to shut it down. Uninstall it from
Windows **Settings → Apps** like any other program.

### Is the installer safe?

No installer can promise "100% safe", so here is what you can check yourself:
- The code is open source, and `ClaumeetSetup.exe` is built from it by a **public GitHub Actions run** ([release workflow](.github/workflows/release.yml)). That run also installs, starts and uninstalls the app as a test.
- Each release lists the **SHA-256** of the exe. Check it with `Get-FileHash .\ClaumeetSetup.exe` in PowerShell.
- The exe is **not code-signed** (a certificate costs money). Windows SmartScreen may say "Windows protected your PC".
  Click **More info → Run anyway** only if you downloaded it from the release page above.
- Python packages are installed from a **hash-pinned lock file**, so a tampered package fails to install.
- It never turns on paid APIs, never bypasses Google sign-in or Meet admission, and keeps no audio recordings.

### Other ways to install
- **No exe:** download [`Setup-Claumeet.cmd`](Setup-Claumeet.cmd) and double-click it. It downloads this repository to
  `%USERPROFILE%\ClaudeMeetingAgent` and runs the same installer.
- **From source:** Code → Download ZIP, extract, double-click **`Install-Claumeet.cmd`**. Then use **`Start-Claumeet.cmd`**,
  **`Stop-Claumeet.cmd`**, **`SignIn-Claumeet.cmd`** and **`Doctor-Claumeet.cmd`**.

## Honest status

See [`docs/BUILD_STATUS.md`](docs/BUILD_STATUS.md) and [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md). In short:
the safety core, memory, dashboard, audio bridge and the meeting lifecycle are implemented and tested
(the lifecycle against real Chromium and a **mock** Meet page). The pieces that need your Google
account, API key and a real meeting have **not been tested live yet**. That covers joining real Google Meet, Gemini
Live conversation quality, the Bangladeshi voice and latency.

## Docs
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md) · [Research and model choices](docs/RESEARCH.md)
- [Audio wiring (both device setups)](docs/AUDIO_WIRING.md) · [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Security and threat model](docs/SECURITY.md) · [Privacy and consent templates](docs/PRIVACY.md)
- [Requirements matrix](docs/REQUIREMENTS_MATRIX.md) · [Test report](docs/TEST_REPORT.md)

## Contributing
PRs welcome. Read [`CLAUDE.md`](CLAUDE.md) first. Its rules on consent, security and free-only use are binding for every change.
Run `pytest -q` and `ruff check src tests` before you open a PR.

## License
MIT. See [LICENSE](LICENSE).
