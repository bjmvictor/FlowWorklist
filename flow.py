import argparse
import os
import sys
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).parent
APP_PID = ROOT / "app.pid"
SERVICE_MANAGER = ROOT / "service_manager.py"
STARTAPP_SCRIPT = ROOT / "startapp.py"


def _venv_python():
    if os.name == 'nt':
        p = ROOT / "Scripts" / "python.exe"
    else:
        p = ROOT / "Scripts" / "python"
    return str(p) if p.exists() else sys.executable


def startapp():
    """Start the management App (web UI) in background using startapp.py."""
    # Delegate to startapp.py which writes app.pid
    python_path = _venv_python()
    proc = subprocess.Popen(
        [python_path, str(STARTAPP_SCRIPT)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    # Stream initial output for user feedback
    start = time.time()
    while time.time() - start < 5:
        line = proc.stdout.readline()
        if not line:
            break
        print(line.rstrip())
    print("App start command issued. PID stored in app.pid if successful.")


def stopapp():
    """Stop the management App using PID from app.pid."""
    if not APP_PID.exists():
        print("No app.pid file found. App may not be running.")
        return
    try:
        pid = int(APP_PID.read_text().strip())
    except Exception:
        print("Invalid app.pid. Unable to stop.")
        return
    if os.name == 'nt':
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Stopped App (PID {pid}).")
        except subprocess.CalledProcessError as e:
            print(f"Failed to stop App (PID {pid}): {e}")
    else:
        try:
            os.kill(pid, 15)
            print(f"Stopped App (PID {pid}).")
        except Exception as e:
            print(f"Failed to stop App (PID {pid}): {e}")
    try:
        APP_PID.unlink(missing_ok=True)
    except Exception:
        pass


def startservice(config_path: str | None = None):
    """Start MWL service via service_manager.start_service."""
    from service_manager import start_service
    result = start_service(config_path=config_path)
    print(result)


def stopservice():
    from service_manager import stop_service
    result = stop_service()
    print(result)


def restartservice(config_path: str | None = None):
    from service_manager import restart_service
    result = restart_service(config_path=config_path)
    print(result)


def status():
    """Show status for both App and Service."""
    app_status = {
        "running": False,
        "pid": None
    }
    if APP_PID.exists():
        try:
            pid = int(APP_PID.read_text().strip())
            app_status["pid"] = pid
            if os.name == 'nt':
                # Check if PID exists in tasklist
                out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                app_status["running"] = str(pid) in out.stdout
            else:
                try:
                    os.kill(pid, 0)
                    app_status["running"] = True
                except Exception:
                    app_status["running"] = False
        except Exception:
            pass
    from service_manager import status as svc_status
    service_status = svc_status()
    print({"app": app_status, "service": service_status})


def logs(limit: int = 20):
    from service_manager import list_logs
    print(list_logs(limit=limit))


def tail(log_path: str, lines: int = 200):
    from service_manager import tail_log
    print(tail_log(log_path, lines=lines))


def install():
    """Install local wrappers to run 'flow' commands easily."""
    # Create flow.bat and flow.ps1 in the project root
    bat_path = ROOT / "flow.bat"
    ps1_path = ROOT / "flow.ps1"
    bat_content = (
        "@echo off\n"
        "SETLOCAL\n"
        "set ROOT=%~dp0\n"
        "if exist \"%ROOT%Scripts\\activate.bat\" call \"%ROOT%Scripts\\activate.bat\"\n"
        "python \"%ROOT%flow.py\" %*\n"
        "ENDLOCAL\n"
    )
    ps1_content = (
        "$Root = Split-Path -Parent $MyInvocation.MyCommand.Path\n"
        "if (Test-Path \"$Root\\Scripts\\Activate.ps1\") { & \"$Root\\Scripts\\Activate.ps1\" }\n"
        "python \"$Root\\flow.py\" $args\n"
    )
    bat_path.write_text(bat_content, encoding='utf-8')
    ps1_path.write_text(ps1_content, encoding='utf-8')
    print("Installed local wrappers: flow.bat and flow.ps1.")
    print("Usage: .\\flow startapp | stopapp | startservice | stopservice | restartservice | status | logs | tail | install")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="flow", description="FlowWorklist command line helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("startapp")
    sub.add_parser("stopapp")

    p_startsvc = sub.add_parser("startservice")
    p_startsvc.add_argument("--config", default=None, help="Path to MWL config file")

    sub.add_parser("stopservice")

    p_restartsvc = sub.add_parser("restartservice")
    p_restartsvc.add_argument("--config", default=None, help="Path to MWL config file")

    sub.add_parser("status")

    p_logs = sub.add_parser("logs")
    p_logs.add_argument("--limit", type=int, default=20, help="Number of logs to list")

    p_tail = sub.add_parser("tail")
    p_tail.add_argument("log", help="Path to log file to tail")
    p_tail.add_argument("--lines", type=int, default=200)

    sub.add_parser("install")

    args = parser.parse_args()

    if args.cmd == "startapp":
        startapp()
    elif args.cmd == "stopapp":
        stopapp()
    elif args.cmd == "startservice":
        startservice(config_path=args.config)
    elif args.cmd == "stopservice":
        stopservice()
    elif args.cmd == "restartservice":
        restartservice(config_path=args.config)
    elif args.cmd == "status":
        status()
    elif args.cmd == "logs":
        logs(limit=args.limit)
    elif args.cmd == "tail":
        tail(log_path=args.log, lines=args.lines)
    elif args.cmd == "install":
        install()
