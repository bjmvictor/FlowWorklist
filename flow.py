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
    # If process is already not running, clean up stale PID file
    already_stopped = False
    if os.name == 'nt':
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if str(pid) not in out.stdout:
            already_stopped = True
    else:
        try:
            os.kill(pid, 0)
        except Exception:
            already_stopped = True
    if already_stopped:
        print(f"App not running (stale PID {pid}); cleaning up app.pid.")
        try:
            APP_PID.unlink(missing_ok=True)
        except Exception:
            pass
        return
    if os.name == 'nt':
        # Force kill entire process tree to ensure Flask and all child processes are terminated
        try:
            # Use /F /T to forcefully kill entire tree (Flask often spawns child processes)
            result = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)], 
                check=False, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode == 0:
                print(f"Stopped App (PID {pid}) and all child processes.")
            else:
                # Process might already be gone
                print(f"App process (PID {pid}) terminated or not found.")
        except Exception as e:
            print(f"Warning: Exception while stopping App (PID {pid}): {e}")
        
        # Give processes time to terminate
        time.sleep(0.5)
        
        # Verify process is actually gone
        verify = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if str(pid) in verify.stdout:
            print(f"⚠️  Warning: Process {pid} may still be running. Try manually: taskkill /F /PID {pid}")
    else:
        try:
            os.kill(pid, 9)  # SIGKILL for immediate termination
            print(f"Stopped App (PID {pid}).")
        except Exception as e:
            print(f"Failed to stop App (PID {pid}): {e}")
    try:
        APP_PID.unlink(missing_ok=True)
    except Exception:
        pass


def startall(config_path: str | None = None):
    """Start both App and Service."""
    print("Starting App...")
    startapp()
    time.sleep(2)
    # Check if app started
    if APP_PID.exists():
        print("App started successfully. Starting Service...")
        startservice(config_path=config_path)
    else:
        print("App failed to start. Skipping Service startup.")


def stopall():
    """Stop both App and Service."""
    print("Stopping Service...")
    stopservice()
    time.sleep(1)
    print("Stopping App...")
    stopapp()


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


def _add_to_path_windows():
    """Add FlowWorklist directory to Windows PATH environment variable."""
    import winreg
    flow_dir = str(ROOT)
    
    try:
        # Open registry key for environment variables
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Environment',
            0,
            winreg.KEY_READ | winreg.KEY_WRITE
        )
        # Get current PATH
        try:
            current_path, _ = winreg.QueryValueEx(key, 'Path')
        except FileNotFoundError:
            current_path = ""
        
        # Check if already in PATH
        if flow_dir.lower() not in current_path.lower():
            # Append to PATH
            new_path = f"{current_path};{flow_dir}" if current_path else flow_dir
            winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, new_path)
            winreg.CloseKey(key)
            print(f"✓ Added to PATH: {flow_dir}")
            print("⚠️  Please restart PowerShell/CMD for PATH changes to take effect.")
            return True
        else:
            winreg.CloseKey(key)
            print(f"ℹ️  Already in PATH: {flow_dir}")
            return False
    except Exception as e:
        print(f"✗ Failed to add to PATH: {e}")
        print("  Try running PowerShell/CMD as Administrator and retry.")
        return False


def _add_to_path_unix():
    """Provide instructions for adding to PATH on Unix systems."""
    flow_dir = str(ROOT)
    shell_rc = os.path.expanduser("~/.bashrc")
    
    print(f"To add FlowWorklist to PATH on Linux/macOS, add this line to your shell profile:")
    print(f'  export PATH="{flow_dir}:$PATH"')
    print(f"\nOr manually add it to {shell_rc}:")
    print(f'  echo \'export PATH="{flow_dir}:$PATH"\' >> {shell_rc}')
    print(f"Then reload: source {shell_rc}")
    return False


def install(add_to_path: bool = False):
    """Install local wrappers and optionally add to PATH."""
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
    print("✓ Installed local wrappers: flow.bat and flow.ps1")
    
    # Offer to add to PATH
    if add_to_path:
        print("\nAdding to PATH...")
        if os.name == 'nt':
            _add_to_path_windows()
        else:
            _add_to_path_unix()
    else:
        print("\nTo use 'flow' from any directory, run:")
        if os.name == 'nt':
            print(f"  flow install --add-to-path")
        else:
            print(f"  python {ROOT}/flow.py install --add-to-path")
    
    print("\nAvailable commands:")
    print("  flow startapp      - Start management App")
    print("  flow stopapp       - Stop management App")
    print("  flow startservice  - Start DICOM MWL service")
    print("  flow stopservice   - Stop DICOM MWL service")
    print("  flow startall      - Start App and Service")
    print("  flow stopall       - Stop App and Service")
    print("  flow status        - Show status of App and Service")
    print("  flow logs [--limit N] - List N most recent logs")
    print("  flow tail <path> [--lines N] - Tail log file")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="flow", description="FlowWorklist command line helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("startapp")
    sub.add_parser("stopapp")
    sub.add_parser("startall")
    sub.add_parser("stopall")

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

    p_install = sub.add_parser("install")
    p_install.add_argument("--add-to-path", action="store_true", help="Add FlowWorklist to system PATH")

    args = parser.parse_args()

    if args.cmd == "startapp":
        startapp()
    elif args.cmd == "stopapp":
        stopapp()
    elif args.cmd == "startall":
        startall()
    elif args.cmd == "stopall":
        stopall()
    elif args.cmd == "startservice":
        startservice(config_path=args.config)
    elif args.cmd == "stopservice":
        stopservice()
    elif args.cmd == "restartservice":
        restartservice(config_path=args.config)
    elif args.cmd == "status":
        status()
    elif args.cmd == "logs":
        logs(limit=args.logs)
    elif args.cmd == "tail":
        tail(log_path=args.log, lines=args.lines)
    elif args.cmd == "install":
        install(add_to_path=args.add_to_path)
