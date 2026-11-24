# Test report

**Date:** 2026-11-24 · **Where:** cloud Linux container (x86_64, 4 vCPU, 16 GB RAM, Python 3.13.18, Chromium 1243 headless).
Also run on **GitHub Actions `windows-latest`** (Windows Server 2025, Python 3.12.10, Google Chrome). The hash-pinned
`requirements-windows.lock` installed cleanly, **245/245 tests passed on Windows**, including the real-Chromium audio bridge and the
mock-Meet lifecycle. Doctor ran, the Secret store reported `WinVaultKeyring` (Windows Credential Manager), and all 4 PowerShell
scripts parse without errors. Windows CI also caught a real bug (missing `tzdata`, so `Asia/Dhaka` didn't resolve), which is now fixed.
**Not tested on the owner's own PC yet.** No real Google Meet, Google account or Gemini key was used.

## Commands
```
pytest -q                             # 245 passed in about 26 s
ruff check src tests --select E,F,W,B # all checks passed
pip-audit -r requirements-windows.lock --disable-pip --no-deps   # no known vulnerabilities
python scripts/benchmark.py
```

## Results by suite
| Suite | Tests | Result | Kind |
|---|---|---|---|
| test_policy (owner verification matrix) | 93 | pass | unit |
| test_addressing (synthetic Bangla/Banglish/English intents) | 33 | pass | unit, synthetic fixtures |
| test_url | 17 | pass | unit |
| test_dashboard (auth, CSRF, origin, host, WS, lockout, traversal, secrets) | 16 | pass | integration (ASGI) |
| test_memory (ACL, Bangla FTS, revoke, expiry, ingest) | 16 | pass | integration (SQLite) |
| test_supervisor_gate (consent, mute, interrupt, hold, stop, injection, privacy) | 13 | pass | integration, **mock** Live model and browser |
| test_arbiter (social timing scenarios) | 11 | pass | scenario replay |
| test_config_injection | 9 | pass | unit |
| test_research_ssrf | 8 | pass | unit |
| test_bridge_e2e (remote capture, mic injection, flush, camera refused) | 5 | pass | **real Chromium + WebRTC loopback** |
| test_consent, test_quota_registry, test_scheduler | 15 | pass | unit |
| test_meet_lifecycle_mock (join → admit → consent → newcomer → opt-out → leave; removal; busy) | 3 | pass | real Chromium, **mock Meet page** |
| test_vad_pcm, test_privacy | 6 | pass | unit |

## Owner PC install trial (2026-11-24, Windows 11 Pro build 26200, i5-8400, 8 GB RAM)
Run remotely and by hand: the installer's ExecutionPolicy step was blocked by the remote tool's guard, and the venv was built on F: in a test folder.
- Python 3.11 failed with `No matching distribution found for numpy==2.5.5` because the lock targets 3.12. **Fixed:** the installer now requires 3.12.
- With Python 3.12.10 (per-user winget): the hash-checked install succeeded (venv 237 MB). Doctor exited 0 (only the Gemini key was unset). The Control Center
  returned HTTP 200 in 3.9 s at about 69 MB working set. `stop` shut it down cleanly and freed the port.
- Observed constraints: 0.8 GB RAM free at test time, and 1.24 GB free on C:.
- Not done yet: `Install-Claude.cmd` run by the owner from Explorer, real Meet, Gemini.

## Measurements (Linux container, not the target PC)
| Metric | Value |
|---|---|
| In-page flush (bridge.js stop all nodes) | under 1 ms. Silence confirmed within 163 ms, including test polling |
| Emergency stop through the supervisor (fake browser) | under 250 ms asserted. Typical run is about 1 ms |
| VAD CPU | 0.40 ms per 1 s of audio (p50) |
| Resample 24→16 kHz | 0.32 ms per 1 s of audio |
| Memory search, 10k entries | 4.5 ms p50 / 5.6 ms p95 (English), 7.9 / 10.6 ms (Bangla) |
| Policy decision | 0.07 ms p50 |
| Control Center process (idle) | about 73 MB RSS |
| Headless Chromium + bridge + WebRTC loopback | about 1,040 MB summed RSS across 11 processes (shared pages are counted twice), about 22% of one core |
| Capture frame rate | 23.5 frames/s (2048 samples at 48 kHz) |

## Blocked (needs the owner) and how to reproduce
1. **Real Meet join/admission/chat selectors:** Install, SignIn, Start, join a private test meeting, and confirm each state on the Live tab.
2. **Gemini Live conversation, latency p50/p95, interruption on real audio:** add the key, Probe, run the meeting, and read the Provider & Performance latencies (`end_of_input_to_first_audio_ms`).
3. **Bangladeshi voice quality:** use Personality Studio → audition voices (Charon, Orus, Puck, Fenrir, Iapetus) and have native listeners score them.
4. **Bengali ASR intent ≥90%:** this needs 30 or more consented recordings.
5. **Windows installer end-to-end:** the scripts parse and the lockfile installs on Windows CI, but `Install-Claude.cmd` itself (with its prompts and shortcut) hasn't run on a real desktop yet.
6. **30/60-minute soak, Windows RAM/CPU with real Meet:** watch Overview → App RAM during a long private test.

## Known limitations
- Speaker attribution in mixed meeting audio is "Meeting audio" (unattributed). Names come only from chat and the roster.
- If the model says something the privacy filter catches, the transcript filter cuts speech *after* it begins. That's why private memory is never put into the Live context.
- When a model turn is dropped by the arbiter, the Live model still believes it spoke. This is minor context drift.
- Meet's DOM changes often. The chat and roster selectors (`data-message-id`, `data-participant-id`) have to be confirmed against live Meet.
