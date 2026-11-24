# Troubleshooting

| Symptom | What to do |
|---|---|
| Installer says Python not found | Install Python 3.12 from python.org (tick "Add to PATH") or allow the winget offer, then run `Install-Claude.cmd` again. |
| "Claude is already running" | Run `Stop-Claude.cmd`. If it still says so, open Task Manager and end `python.exe` running claude_agent. |
| Control Center asks for a passphrase | Close the browser tab, then reopen the newest pairing link from the Start-Claude window (it is valid for 10 minutes and works once), or set a passphrase under Security. |
| Google says "This browser or app may not be secure" | Sign in with `SignIn-Claude.cmd` (a normal Chrome window), not inside the automated window. If Google still blocks automated Chrome for the account, report it. The project will not use bot-detection evasion. |
| Claude waits forever at "Asking to be let in" | The host has to admit Claude. After 10 minutes Claude gives up on its own. |
| Claude was removed or denied | By design it won't rejoin that meeting. Start a new join only if the host agrees. |
| No voice from Claude | Check that the Overview pill isn't "muted"/"paused", that consent was started, that the provider status shows `live:connected`, and that Meet hasn't muted Claude (hosts can). |
| Claude answers too often or too rarely | Personality Studio: lower or raise Initiative and the minimum gap, or use Quiet mode. |
| 429 / quota errors | You've hit the free tier's limits. Claude backs off and switches to chat-only replies. It never upgrades to paid. Wait, or use it less. |
| High RAM | Close other Chrome windows and apps. The resource tier on Overview drops vision, demos and research first. |
| Scheduled meeting not joined | The PC must be on and awake with Claude running. Missed windows are listed under Scheduling and are never joined late. |
| Logs | `%LOCALAPPDATA%\ClaudeMeetAgent\logs\agent.log` (secrets and emails are redacted). Run `Doctor-Claude.cmd` for a summary. |
