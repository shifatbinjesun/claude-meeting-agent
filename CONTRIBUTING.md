# Contributing to Claumeet

Thanks for helping! A few ground rules keep Claumeet safe and free for everyone:

1. **Read [`CLAUDE.md`](CLAUDE.md).** Its priorities apply to every change: consent first, owner authorization,
   free tier only, and never bypassing Google or Zoom security, admission or host controls.
2. **Be honest about status.** Don't mark a feature as working unless a test or a documented live trial shows it.
   Update `docs/TEST_REPORT.md` and `docs/REQUIREMENTS_MATRIX.md` when you add evidence.
3. **Run the checks** before opening a PR:
   ```
   pip install -e ".[dev]"
   pytest -q          # SKIP_BROWSER_TESTS=1 skips the Chromium tests
   ruff check src tests
   ```
4. **Keep dependencies pinned.** If you change `pyproject.toml`, regenerate `requirements-windows.lock` (see CLAUDE.md).

## Good first contributions
- **Translations.** Native speakers: please check the lines in `src/claude_agent/brain/languages.py` and the opt-out
  phrases in `src/claude_agent/brain/addressing.py`, then add your language. See [docs/LANGUAGES.md](docs/LANGUAGES.md).
- **Live trial reports.** Tried Claumeet in a real, consented Meet or Zoom call? Open an issue with the
  "Live trial report" template. Zoom's and Meet's UIs change often, so these reports are very valuable.
