# Research and technology choices

Research date: **2026-11-24**. Re-check these before you rely on them, because model lists and free tiers change often.

## Gemini models (Gemini Developer API)
Sources, read 2026-11-24: <https://ai.google.dev/gemini-api/docs/models>, the
[live guide](https://ai.google.dev/gemini-api/docs/live-guide), [session management](https://ai.google.dev/gemini-api/docs/live-session),
[pricing](https://ai.google.dev/gemini-api/docs/pricing) and [speech generation](https://ai.google.dev/gemini-api/docs/speech-generation).

| Model ID | Kind | Status | Free tier on pricing page | Used as |
|---|---|---|---|---|
| `gemini-3.1-flash-live-preview` | Live audio↔audio | Preview (legacy) | **Yes**, "Free of charge" | Live default #1 |
| `gemini-2.5-flash-native-audio-preview-12-2025` | Live audio↔audio | Preview | Yes (from a summary of the page section) | Live #2 (proactive audio, affective dialog) |
| `gemini-3.8-live` | Live | Stable, default Live model | **Not listed**, so unknown | Excluded while `free_only` is on |
| `gemini-3.1-flash-lite` | Text | Stable | Yes | Text #1 (owner Q&A, chat fallback, vision) |
| `gemini-3.5-flash` | Text | Stable | Yes | Text #2 |
| `gemini-2.5-flash-lite` | Text | Stable (limited access) | Yes (from the summary) | Text #3 |
| `gemini-3.1-flash-tts-preview` | TTS | Preview | Yes | Voice audition / TTS fallback |
| `gemini-2.5-flash-preview-tts` | TTS | Preview | Yes (from the summary) | TTS #2 |

Live API facts used in code (from the live guide and session pages):
- Audio is raw little-endian 16-bit PCM. Input is 16 kHz (`audio/pcm;rate=16000`) and output is 24 kHz.
- `response_modalities` takes one modality per session (we use AUDIO, with input and output transcription turned on).
- Audio-only sessions last about 15 minutes without compression, and a connection lasts about 10 minutes. We use `context_window_compression=SlidingWindow()`
  and `session_resumption` handles (valid for 2 hours), and we reconnect when the server sends `go_away`.
- `server_content.interrupted` means stop playback and clear the queue. This is wired to `flush()`.
- There are 30 prebuilt voices. Charon is our default warm male candidate, and Orus, Puck, Fenrir and Iapetus are the alternatives to audition.
  Native audio models choose the language themselves, and Bengali is listed only as `bn` (no `bn-BD` setting). The Bangladeshi accent
  therefore depends on the persona prompt and **must be checked by native listeners** (not done yet).
- SDK: `google-genai==3.6.1` (PyPI, checked 2026-11-24). We confirmed in code that the field names exist: `LiveConnectConfig.proactivity`,
  `context_window_compression`, `session_resumption`, `input_audio_transcription`, `output_audio_transcription`.

**Not verified yet:** real access and free eligibility with your key. Run Provider → *Probe free models*.
Free-tier content may be used by Google to improve its products, which is why the disclosure says so.

## Meet integration
- The **Meet Media API** developer preview is discontinued, and its endpoints shut down on 2027-01-15, so we don't use it. The Meet REST API
  has no two-way live media.
- Our choice is **Playwright (1.65.2)** driving real Google Chrome with a **dedicated persistent profile** and a signed-in,
  AI-labeled account. Locators use accessible names and visible text. The browser locale is pinned to en-US, with Bangla fallbacks.
- **Audio without drivers.** `meet/bridge.js` wraps `RTCPeerConnection` to read remote audio tracks, replaces `getUserMedia`
  with a WebAudio stream that carries Claumeet's voice, and refuses camera requests. Chrome runs with
  `--use-fake-device-for-media-stream`, so the physical mic and camera are never opened. Data moves through Playwright's
  `expose_binding` and `evaluate`, so we don't need a CSP bypass. This fits both device setups without VB-Cable.
- Sign-in happens in a normal, non-automated Chrome window (`SignIn-Claumeet.cmd`) using the same profile. If Google blocks
  automated Chrome for the account, the documented fallback is to report the blocker. We do **not** use stealth or evasion.

## Speech alternatives considered
- `edge-tts` (rany2/edge-tts 7.3.1) with `bn-BD-PradeepNeural`: unofficial and with no service entitlement, so it ships **off**
  (`providers.experimental_edge_tts`). It needs ffmpeg.
- Local TTS/ASR (Piper, Whisper.cpp): we didn't find a natural Bangladeshi male voice, and models of 0.5–1.5 GB are too heavy next to Chrome on 8 GB. Not used.
- Speaker verification (SpeechBrain ECAPA) would need PyTorch (over 1 GB of RAM). Not used. The authenticated dashboard is the strong owner channel.

## Other picks
| Need | Choice | Why |
|---|---|---|
| Server/UI | FastAPI 0.165 + Uvicorn 0.38 + vanilla JS/CSS | Small, async, no Electron |
| Memory | SQLite FTS5 (stdlib) | Zero install. Tokenizes Bangla (tested) |
| Secrets | `keyring` 25.7, which uses Windows Credential Manager | DPAPI-backed, no plaintext |
| VAD | Energy VAD with an adaptive floor | About 0.4 ms of CPU per second of audio. The provider handles ASR |
| Research | Wikipedia REST API (en/bn) | Free, permitted, has sources. SSRF-guarded |
| Backups | Windows DPAPI (`ProtectedData`) | Only your Windows account can decrypt |
