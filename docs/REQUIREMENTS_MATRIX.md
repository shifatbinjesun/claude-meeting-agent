# Requirements traceability matrix

Status key: **verified** (an automated test or measurement passes) · **impl-unverified** (code exists, but no live or Windows test yet) ·
**degraded** (a reduced version, with the reason given) · **blocked** (needs the owner or an external step) · **not implemented**.
Last updated 2026-11-24. "Mock" means the test used a fixture in place of the real service.

| Area | Requirement | Status | Evidence |
|---|---|---|---|
| Setup | Per-user install, no admin, hash-pinned deps, actionable errors | impl-unverified | `scripts/Install-Claude.ps1`, `requirements-windows.lock`. Not run on Windows yet |
| Setup | Doctor (Python, Chrome, RAM, disk, port, key, network, sleep) | verified on Linux / impl-unverified on Windows | `claude-agent doctor`, `Doctor-Claude.ps1` |
| Setup | Key validated server-side, stored in Credential Manager, never shown | verified (logic) | `test_status_never_contains_secret`, `/api/secrets/gemini` |
| Setup | One-click start/stop, no global policy changes | impl-unverified | `Start-Claude.cmd`, `Stop-Claude.cmd` (graceful stop verified on Linux) |
| Join | Manual link validation, only Meet host | verified | `test_url.py` (17 cases), `test_join_rejects_non_meet_url` |
| Join | Dedicated profile, camera off, mic muted pre-join | verified (mock) / impl-unverified (real Meet) | `test_camera_refused`, `test_full_lifecycle` |
| Join | Waiting, admitted, removed/denied (no rejoin), ended, reconnect with backoff | verified (mock) | `test_meet_lifecycle_mock.py` |
| Join | Never bypass sign-in, admission or bot detection | verified by design | No stealth code. Supervised join is the default |
| Roster/chat | Read participants and sent chat, post chat with rate limit | verified (mock) / impl-unverified (real Meet selectors) | `test_full_lifecycle` |
| Reactions | Native reactions when available | impl-unverified | `MeetBrowser.react` |
| Captions/raised hands | Read captions and hands | not implemented | Gemini transcription is used instead |
| @mentions | Real @mentions | not implemented | Plain names used, as the spec allows |
| Scheduling | Approved local schedule, Asia/Dhaka, recurrence, missed, no late joins | verified | `test_scheduler.py` |
| Scheduling | Google Calendar read-only OAuth | not implemented | Manual approval list instead |
| Audio | Remote-only capture at 16 kHz, no system loopback | verified (real Chromium + WebRTC loopback) | `test_captures_remote_audio_at_16k` |
| Audio | Claude's voice into the Meet mic, physical mic never opened | verified (Chromium) | `test_voice_reaches_mic_stale_dropped_and_flush` |
| Audio | Stale-generation discard, flush on stop | verified | Same test, plus `test_stale_generation_after_reconnect` |
| Audio | Same-PC and separate-device setups | impl-unverified | `docs/AUDIO_WIRING.md`. Needs a live test |
| Audio | VAD with hangover, no streaming of long silence | verified | `test_vad_pcm.py`, `Supervisor._on_meet_audio` |
| Gemini | Live adapter: transcription, interruption, resumption, compression, go_away, backoff | impl-unverified | `providers/gemini_live.py`. Needs a key |
| Gemini | Free-only registry, 429 suspension, no key rotation | verified | `test_quota_registry.py` |
| Gemini | Probe of real access | blocked (owner key) | Provider tab → Probe |
| Voice | Warm male Bangladeshi voice, locked after audition | blocked (audition by native listeners) | Audition UI exists. Default Charon |
| Language | Addressing, stop and opt-out in Bangla/Dhakaiya/Banglish/English | verified on 32 synthetic text cases (2 documented false positives) | `test_addressing.py` |
| Language | ASR accuracy ≥90% intent on real speech | blocked | Needs consented recordings |
| Authority | Typed ActionProposal + deterministic policy | verified | `test_policy.py` (93 cases: 20+ authorized, 30+ unauthorized) |
| Authority | Owner private channel, approval queue with expiry | verified (logic) | `test_model_privileged_proposal_goes_to_approval`, dashboard UI |
| Authority | Voice biometric verification | not implemented (deliberately) | RAM cost. The strong channel is the dashboard |
| Consent | Disclosure before processing, late joiners pending, decline pauses, opt-out always honoured | verified | `test_consent.py`, gate tests, mock lifecycle |
| Persona | Versioned prompt with modes and sliders | verified (assembly) / impl-unverified (behaviour) | `prompts/persona_v1.md`, `brain/persona.py` |
| Turn-taking | No talking over speakers, greeting batching, rate caps, silence handling | verified (scenario replay) | `test_arbiter.py` (11 scenarios) |
| Interruption | Trusted stop flush ≤ 250 ms at the control layer | verified: in-page JS stop under 1 ms, emergency stop under 250 ms in tests | `test_emergency_stop_latency`, bridge test |
| Memory | Domains, default-deny, revocation cascade, expiry, Bangla FTS | verified | `test_memory.py` |
| Docs | Safe ingest (types, size, traversal) | verified | `test_document_rejects` |
| Research | Free Wikipedia with source/date, SSRF guard, privacy-filtered query | verified (guards) / impl-unverified (live fetch) | `test_research_ssrf.py` |
| Vision | On-demand screenshot of Claude's own tab only, consent-gated, not stored | impl-unverified | `Supervisor.describe_screen` (off by default) |
| Demos | Isolated ephemeral browser, manual share picker | impl-unverified (partial) | `MeetBrowser.open_demo`. No demo generator UI yet |
| Dashboard | All 8 sections, auth, CSRF, origin, WebSocket, CSP | verified | `test_dashboard.py` (16), headless UI run with no console errors |
| Dashboard | Phone/LAN access with TLS | not implemented | Localhost only |
| Reliability | Watchdog, bounded reconnects, single instance, clean shutdown | verified (mock) | Lifecycle tests, lock |
| Resources | Governor tiers that drop optional features first | verified (logic) | `observability/governor.py` |
| Resources | ≤2 GB incremental on target PC | blocked | Measured about 1.0 GB RSS for headless Chromium + bridge on Linux. Real Meet on Windows not measured |
| Long session | 30/60-minute live soak | blocked | Needs a live meeting |
