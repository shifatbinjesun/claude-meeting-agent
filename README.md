# Claude Meeting Agent

An open-source, **openly identified** AI participant for Google Meet. It acts like a witty, warm
Bangladeshi friend (Bangla, Dhakaiya, Banglish and English) and works as your second brain in the call.
It runs on your own Windows PC, uses **free-tier AI only**, and you control it from a local
**Claude Control Center** dashboard.

> Community project. Not affiliated with Anthropic or Google. The in-meeting voice and reasoning run on
> Google's Gemini API free tier. "Claude" is only the participant's name, and it always says it is an AI.

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
| One-click Windows | `Install-Claude.cmd`, `Start-Claude.cmd`, `Stop-Claude.cmd`, `SignIn-Claude.cmd`, `Doctor-Claude.cmd`. |

## Quick start (Windows 10/11)

1. **Download** this repository (Code → Download ZIP) and extract it, for example to `C:\ClaudeMeetingAgent`.
2. Double-click **`Install-Claude.cmd`**. It checks for Python 3.12 and Chrome and offers to install them with winget (it asks first). Then it sets up a private environment and runs a health check.
3. Create a **separate Google account** for the bot and name it something like "Claude (AI)". Double-click **`SignIn-Claude.cmd`** and sign that account in through Google's normal page. You only do this once.
4. Get a **free Gemini API key** at <https://aistudio.google.com/apikey>. Leave billing **off** on its project.
5. Double-click **`Start-Claude.cmd`**. Your browser opens the Control Center (paired automatically through a one-time link). Go to **Provider & Performance**, paste the key, then click **Probe free models**.
6. Go to **Overview**, paste a Meet link and click **Join**. Claude's Chrome window opens. Click **Ask to join** there, and the host admits Claude.
7. After you've told the meeting about the AI, click **Announce & start listening**. Claude posts the disclosure in chat, introduces itself and starts listening.

Stop at any time with **Emergency stop** (or Ctrl+Shift+X). Close the meeting with **Leave meeting**, and shut everything down with `Stop-Claude.cmd`.

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
