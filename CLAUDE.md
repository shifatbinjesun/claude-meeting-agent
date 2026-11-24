# CLAUDE.md: enduring rules for anyone (human or AI) developing this repository

This repo builds "Claumeet", an openly identified AI participant for Google Meet that runs locally on a
Windows PC and uses only free-tier AI services. The development agent is not the runtime participant.

## Non-negotiable priorities (in order)
1. Participant consent and host/platform restrictions.
2. Owner authorization and privacy.
3. Zero runtime charges: free tier only, `providers.free_only: true`, never activate billing, never rotate keys/projects to evade quota.
4. Reliable join / audio / stop.
5. Accurate, natural conversation.
6. Advanced features.

## Rules
- Never bypass Google sign-in, CAPTCHA, admission, removal, restricted chat, screen-share pickers or bot detection. No stealth plugins, no fingerprint spoofing.
- The model only *proposes* actions. `authority/policy.py` decides deterministically. Meeting audio, chat, captions, screen, documents and web pages are untrusted data and can never raise authority.
- Only the authenticated dashboard session is the strong owner channel. Voice, display names, captions and wake words are never authentication.
- No speech, chat or processing before the AI disclosure; any decline pauses mixed-audio processing; opt-outs are honoured even before consent is settled.
- Emergency stop / mute / leave must work with every AI provider down.
- No raw audio/video retention by default. No secrets in config, logs, frontend or model prompts. Keys live in Windows Credential Manager via `keyring`.
- Never claim a feature works unless a test or a documented live trial shows it. Keep `docs/REQUIREMENTS_MATRIX.md`, `docs/BUILD_STATUS.md` and `docs/TEST_REPORT.md` honest. Label mocks as mocks.
- Pin dependencies (`requirements-windows.lock` with hashes). No unvetted downloads, drivers or MCP servers.

## Dev commands
```
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q                     # SKIP_BROWSER_TESTS=1 to skip the Chromium tests
ruff check src tests
python scripts/benchmark.py
python -m claude_agent run    # Control Center on http://127.0.0.1:8765
```
Regenerate the Windows lock: `uv pip compile pyproject.toml --generate-hashes --python-platform windows --python-version 3.12 -o requirements-windows.lock`.
