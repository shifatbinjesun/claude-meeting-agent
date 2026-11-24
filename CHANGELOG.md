# Changelog

## 0.3.2 (2026-11-24)
- **Talks by itself after joining.** New *auto-announce* setting (on by default, checkbox on Overview): once the
  host admits Claumeet, it posts the AI notice in chat, unmutes, introduces itself out loud and starts listening.
  Turn it off to keep the manual "Announce & start listening" button.
- **Fix: the spoken intro could be lost.** It was sent 1.5 s after the voice session started; on a slower
  connection the session wasn't ready and the intro was silently dropped. It now waits for the session (up to 25 s)
  and tells you on the dashboard if the voice never connects.
- **Fix: mid-meeting text to the voice model** (intro, greetings, chat addressed to Claumeet) now uses Live
  "realtime text", which `gemini-3.1-flash-live-preview` needs, falling back to the older call when unsupported.
- New end-to-end test with a mock Meet page and a mock voice model: the intro and a chat reply both reach the mic.

## 0.3.1 (2026-11-24)
- **Fix: Claumeet didn't speak, and chat replies failed.** The first live trial on a real Windows PC found that the
  Gemini client was calling Google's `v1` API, which doesn't serve the free preview models (Live voice and TTS)
  and returns 404 for them. Every call now goes to `v1beta`.
- Chat replies retry once when Google is briefly busy (503) or slow, then try the next free model.
- The dashboard now says *why* it can't speak or reply (e.g. `not_found(404)`, `busy(503)`), instead of only "degraded".
- The setup "Test" step only counts as done when a voice model answers.

## 0.3.0 (2026-11-24)
- **Zoom support.** Zoom links (zoom.us, regional and company `*.zoom.us` hosts, or a bare meeting ID) open in Zoom's
  web client. Join, "Join Audio by Computer", mic, chat, roster and the two-step leave all work. Zoom plays voices
  through WebAudio, so the audio bridge taps that playback. Tested against a mock Zoom page only.
- **Any language.** New settings: *Claumeet speaks* (auto, or a default from 20 languages), *Style* (Bangladeshi or
  neutral native) and *AI notice languages*. Opt-out, stop phrases and Claumeet's name are recognised in many scripts.
- **Installer.** New Claumeet logo. After installing, two pages help you create or sign in the bot's Google account
  and paste a free Gemini key, with a how-to. The key is checked, then saved only to Windows Credential Manager.
- **Claude Code.** The repository now includes an install guide for Claude Code. New `claumeet setup` terminal wizard
  and `scripts/install.sh` (macOS/Linux, experimental).
- Control Center: logo, brand colors and a Language card.

## 0.2.0 (2026-11-24)
- Renamed the participant to **Claumeet**.
- `ClaumeetSetup.exe` per-user installer, built and smoke-tested by a public release workflow with a SHA-256.
- `Setup-Claumeet.cmd` one-file installer and a guided setup checklist in the Control Center.

## 0.1.0
- First public version: Google Meet participant, safety core, consent manager, memory and Control Center.
