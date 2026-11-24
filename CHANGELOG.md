# Changelog

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
