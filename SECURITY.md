# Security policy

Please **don't** open a public issue for a vulnerability. Report it privately through GitHub:
**Security → Report a vulnerability** on this repository.

Especially relevant:
- Anything that lets meeting audio, chat, screens, documents or web pages raise Claumeet's authority
  (prompt injection that leads to an action).
- Ways to reach the local Control Center without the owner's pairing link or passphrase.
- Secrets (the Gemini key) ending up in logs, config, the frontend or model prompts.
- Anything that would charge money, or would bypass Google or Zoom sign-in, CAPTCHA, admission or host controls.

The threat model is in [docs/SECURITY.md](docs/SECURITY.md). Supported version: the latest release.
