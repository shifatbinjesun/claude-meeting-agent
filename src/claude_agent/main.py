"""Command line entry point.

    claude-agent run            start Control Center + supervisor (prints a one-time pairing link)
    claude-agent doctor         check this PC (Python, Chrome, RAM, disk, network, key, ports)
    claude-agent signin         open Claumeet's dedicated browser profile to sign in the AI Google account
    claude-agent set-key        store the Gemini API key in Windows Credential Manager (hidden input)
    claude-agent probe          probe free models with the stored key
    claude-agent setup          guided first-run setup in the terminal (Google account, free Gemini key, test)
    claude-agent stop           ask a running instance to shut down
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import logging
import os
import platform
import shutil
import signal
import socket
import sys
import time
import webbrowser

from . import __version__, paths, secrets, setup_state
from .config import Config
from .observability import log as obslog

log = logging.getLogger("claude_agent")


def _port_free(host: str, port: int) -> bool:
    with socket.socket() as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def doctor(as_json: bool = False) -> int:
    import psutil
    cfg = Config.load()
    checks = []

    def add(name, ok, detail, fix=""):
        checks.append({"check": name, "ok": ok, "detail": detail, "fix": fix})

    add("Python", sys.version_info[:2] >= (3, 12), platform.python_version(), "Install Python 3.12 (the Windows lockfile targets 3.12)")
    add("OS", True, f"{platform.system()} {platform.release()} ({platform.version()})")
    add("CPU", True, f"{platform.processor() or platform.machine()}, {psutil.cpu_count(logical=False)} cores / "
                     f"{psutil.cpu_count()} threads")
    vm = psutil.virtual_memory()
    add("RAM", vm.total >= 7.5 * 2**30, f"{vm.total / 2**30:.1f} GB total, {vm.available / 2**30:.1f} GB free",
        "8 GB recommended; close heavy apps before meetings")
    du = shutil.disk_usage(paths.data_dir())
    add("Disk", du.free > 2 * 2**30, f"{du.free / 2**30:.1f} GB free in data folder", "Free up 2 GB")
    from .meet.browser import find_chrome
    chrome = find_chrome()
    add("Google Chrome", bool(chrome), chrome or "not found", "Install Google Chrome (stable)")
    try:
        import playwright  # noqa: F401
        add("Playwright", True, "installed")
    except ImportError:
        add("Playwright", False, "missing", "Run Install-Claumeet.ps1 again")
    host, port = cfg.get("dashboard.host"), int(cfg.get("dashboard.port"))
    add("Dashboard port", _port_free(host, port), f"{host}:{port}", "Another app or Claumeet instance uses this port")
    add("Dashboard bind", host in ("127.0.0.1", "localhost"), host,
        "Loopback is recommended; LAN access needs a passphrase and HTTPS (docs/SECURITY.md)")
    add("Secret store", "fail" not in secrets.backend_name().lower(), secrets.backend_name(),
        "Windows Credential Manager should be available by default")
    add("Gemini API key", secrets.present(secrets.GEMINI_KEY), "stored" if secrets.present(secrets.GEMINI_KEY)
        else "not set", "Run Set-Key in the setup wizard or 'claude-agent set-key'")
    t0 = time.time()
    try:
        socket.create_connection(("generativelanguage.googleapis.com", 443), timeout=5).close()
        add("Network to Gemini", True, f"TCP connect {round((time.time() - t0) * 1000)} ms")
    except OSError as e:
        add("Network to Gemini", False, type(e).__name__, "Check internet/firewall")
    add("Free-only mode", bool(cfg.get("providers.free_only")), str(cfg.get("providers.free_only")),
        "Set providers.free_only: true")
    add("Profile folder", True, str(paths.browser_profile_dir()))
    if as_json:
        print(json.dumps(checks, indent=2))
    else:
        for c in checks:
            mark = "OK " if c["ok"] else "!! "
            print(f"{mark}{c['check']:<20} {c['detail']}" + (f"\n     -> {c['fix']}" if not c["ok"] and c["fix"] else ""))
    return 0 if all(c["ok"] for c in checks if c["check"] not in ("Gemini API key",)) else 1


async def _run(open_browser: bool) -> None:
    import uvicorn
    from .dashboard.app import create_app
    from .supervisor import Supervisor, single_instance_lock
    lock = single_instance_lock()
    cfg = Config.load()
    sup = Supervisor(cfg)
    host, port = cfg.get("dashboard.host", "127.0.0.1"), int(cfg.get("dashboard.port", 8765))
    app = create_app(sup, host, port)
    code = sup.owner.new_pairing_code()
    link = f"http://127.0.0.1:{port}/pair?code={code}"
    (paths.data_dir() / "agent.pid").write_text(str(os.getpid()))
    print("\n  Claumeet Control Center is starting.\n  Open this one-time link on THIS PC (valid 10 min):\n\n  "
          f"{link}\n", flush=True)
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="warning", access_log=False,
                                           ws_ping_interval=20))
    tasks = [asyncio.create_task(sup.scheduler_loop()), asyncio.create_task(sup.metrics_loop())]
    if open_browser:
        asyncio.get_running_loop().call_later(1.5, webbrowser.open, link)

    stop_file = paths.data_dir() / "stop.request"
    stop_file.unlink(missing_ok=True)

    async def watch_stop():
        while not server.should_exit:
            if stop_file.exists():
                stop_file.unlink(missing_ok=True)
                server.should_exit = True
            await asyncio.sleep(1)
    tasks.append(asyncio.create_task(watch_stop()))
    try:
        await server.serve()
    finally:
        await sup.shutdown()
        for t in tasks:
            t.cancel()
        sup.brain.close()
        (paths.data_dir() / "agent.pid").unlink(missing_ok=True)
        lock.close()


def request_stop() -> int:
    (paths.data_dir() / "stop.request").write_text("stop")
    pid_file = paths.data_dir() / "agent.pid"
    for _ in range(20):
        if not pid_file.exists():
            print("Claumeet stopped.")
            return 0
        time.sleep(0.5)
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text())
            import psutil
            p = psutil.Process(pid)
            if "python" in p.name().lower():
                os.kill(pid, signal.SIGTERM)
                print("Claumeet did not stop in time; sent terminate signal.")
        except Exception:
            pass
    return 0


GOOGLE_SIGNUP = "https://accounts.google.com/signup"
GEMINI_KEY_PAGE = "https://aistudio.google.com/apikey"


def store_key(key: str) -> int:
    """Validate a Gemini key with one free request, then keep it only in the OS credential store."""
    if not key:
        print("!! No key given.")
        return 2
    from .providers.gemini_text import probe
    res = asyncio.run(probe(key, "gemini-3.1-flash-lite", "text"))
    if res != "ok":
        print(f"!! Key validation failed: {res.split(':')[1] if ':' in res else res}")
        return 1
    secrets.put(secrets.GEMINI_KEY, key)
    print("Key validated and stored in the OS credential store.")
    return 0


def setup_wizard() -> int:
    """Terminal version of the setup checklist. Asks only for what is missing."""
    print(f"Claumeet {__version__} setup. Press Enter to accept the suggestion in [brackets].\n")
    st = setup_state.load()
    print("Step 1 of 3: a Google account for Claumeet")
    print("  Claumeet joins meetings with its OWN Google account, not yours. Name it like \"Claumeet (AI)\".")
    if st.get("google_signed_in"):
        print("  Done already.\n")
    else:
        if input("  Do you need to create that account now? [y/N] ").strip().lower().startswith("y"):
            webbrowser.open(GOOGLE_SIGNUP)
            print(f"  Opened {GOOGLE_SIGNUP}. Create the account, then come back here.")
            input("  Press Enter when the account exists... ")
        if input("  Open Claumeet's Chrome window to sign that account in? [Y/n] ").strip().lower() != "n":
            from .meet.browser import open_signin_window
            try:
                open_signin_window()
                input("  Sign in there (Google's normal page), close that window, then press Enter... ")
                setup_state.save(google_signed_in=True)
            except Exception as e:
                print(f"  !! {e}")
        print()
    print("Step 2 of 3: a free Gemini API key")
    if secrets.present(secrets.GEMINI_KEY):
        print("  A key is already stored.\n")
    else:
        print(f"  1. Open {GEMINI_KEY_PAGE} and sign in with any Google account.")
        print("  2. Click 'Create API key'. Leave billing OFF. Claumeet only uses free-tier models.")
        print("  3. Copy the key and paste it below (it stays hidden and goes only to the OS credential store).")
        if input("  Open that page now? [Y/n] ").strip().lower() != "n":
            webbrowser.open(GEMINI_KEY_PAGE)
        for _ in range(3):
            if store_key(getpass.getpass("  Paste key (hidden, Enter to skip): ").strip()) == 0:
                break
            if input("  Try again? [Y/n] ").strip().lower() == "n":
                break
        print()
    print("Step 3 of 3: test the free models")
    if not secrets.present(secrets.GEMINI_KEY):
        print("  Skipped: no key yet. Run this setup again later.")
        return 1
    from .supervisor import Supervisor
    rows = asyncio.run(Supervisor(Config.load()).probe_providers())
    ok = [r for r in rows if r["result"] == "ok"]
    for row in rows:
        print(f"  {row['kind']:<5} {row['model']:<50} {row['result']}")
    if ok and not any(r["kind"] == "live" for r in ok):
        print("\n!! Chat works, but no voice (Live) model answered, so Claumeet can't speak yet. Try again later.")
        return 1
    if ok:
        setup_state.save(probe_ok=True)
        print("\nAll set. Start Claumeet with Start-Claumeet (Windows) or 'python -m claude_agent run'.")
        return 0
    print("\n!! No free model answered. Check the key and try again later (free quotas reset daily).")
    return 1


def cli(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="claude-agent", description="Claumeet " + __version__)
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run")
    r.add_argument("--no-browser", action="store_true")
    d = sub.add_parser("doctor")
    d.add_argument("--json", action="store_true")
    sub.add_parser("signin")
    k = sub.add_parser("set-key")
    k.add_argument("--from-env", metavar="VAR", help="read the key from this environment variable (used by the installer)")
    sm = sub.add_parser("setup-mark")
    sm.add_argument("step", choices=["google_signed_in"])
    sub.add_parser("setup")
    sub.add_parser("probe")
    sub.add_parser("stop")
    sub.add_parser("version")
    a = ap.parse_args(argv)
    if a.cmd in (None, "run"):
        obslog.setup()
        try:
            asyncio.run(_run(not getattr(a, "no_browser", False)))
        except RuntimeError as e:
            print(f"!! {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            pass
    elif a.cmd == "doctor":
        sys.exit(doctor(a.json))
    elif a.cmd == "signin":
        from .meet.browser import open_signin_window
        open_signin_window()
        print("A normal Chrome window opened with Claumeet's dedicated profile. Sign in the AI-labeled Google account, "
              "then close the window.")
    elif a.cmd == "set-key":
        if a.from_env:
            key = os.environ.pop(a.from_env, "").strip()
        else:
            key = getpass.getpass("Paste Gemini API key (input hidden): ").strip()
        sys.exit(store_key(key))
    elif a.cmd == "setup-mark":
        setup_state.save(**{a.step: True})
    elif a.cmd == "setup":
        sys.exit(setup_wizard())
    elif a.cmd == "probe":
        from .supervisor import Supervisor
        sup = Supervisor(Config.load())
        for row in asyncio.run(sup.probe_providers()):
            print(f"{row['kind']:<5} {row['model']:<50} {row['result']}")
    elif a.cmd == "stop":
        sys.exit(request_stop())
    elif a.cmd == "version":
        print(__version__)


if __name__ == "__main__":
    cli()
