import argparse
import os
import sys
import subprocess
import time
import json
import datetime
from pathlib import Path

ROOT = Path(__file__).parent
APP_PID = ROOT / "app.pid"
SERVICE_PID = ROOT / "service.pid"
SERVICE_STATE = ROOT / "service_state.json"
SERVICE_LOG_DIR = ROOT / "service_logs"

SERVICE_LOG_DIR.mkdir(exist_ok=True)


def _venv_python():
    if os.name == 'nt':
        p = ROOT / "Scripts" / "python.exe"
    else:
        p = ROOT / "Scripts" / "python"
    return str(p) if p.exists() else sys.executable


def startapp():
    """Start the management App (web UI) in background without extra launcher files."""
    app_script = ROOT / "webui" / "app.py"
    if not app_script.exists():
        print("App entrypoint not found: webui/app.py")
        return

    python_path = _venv_python()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    creationflags = 0
    if os.name == 'nt' and hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW

    proc = subprocess.Popen(
        [python_path, str(app_script)],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags
    )

    try:
        APP_PID.write_text(str(proc.pid))
        print(f"App started with PID {proc.pid}. PID saved to app.pid.")
    except Exception:
        print("App started, but could not write app.pid.")
    
    # Wait for app to be ready
    print("Waiting for app to start...")
    time.sleep(3)
    
    # Open browser
    import webbrowser
    url = "http://127.0.0.1:5000"
    try:
        webbrowser.open(url)
        print(f"Browser opened at {url}")
    except Exception:
        print(f"Could not open browser automatically. Please visit: {url}")
    
    print("App is running in background. Use 'flow stopapp' to stop.")


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
    """Start MWL service in background."""
    if SERVICE_PID.exists():
        pid = int(SERVICE_PID.read_text().strip())
        if _is_process_running(pid):
            msg = f"Service already running (PID {pid})"
            print(msg)
            return {"ok": False, "msg": msg, "pid": pid}
        else:
            SERVICE_PID.unlink(missing_ok=True)
    
    # Clean obsolete lock file
    lock_file = ROOT / "mwl_server.lock"
    if lock_file.exists():
        try:
            with open(lock_file, "r") as f:
                old_pid = f.read().strip()
            if old_pid and old_pid.isdigit() and _is_process_running(int(old_pid)):
                msg = f"Service already running (lock PID {old_pid})"
                print(msg)
                return {"ok": False, "msg": msg, "pid": int(old_pid)}
            else:
                lock_file.unlink(missing_ok=True)
        except Exception:
            lock_file.unlink(missing_ok=True)
    
    # Determine Python executable
    python_path = _venv_python()
    script = ROOT / "mwl_service.py"
    if not script.exists():
        msg = "mwl_service.py not found"
        print(msg)
        return {"ok": False, "msg": msg}
    
    # Prepare log file
    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    log_path = SERVICE_LOG_DIR / f"mwls_{ts}.log"
    
    # Start detached process
    with open(log_path, "ab") as out:
        args = [python_path, str(script)]
        if config_path:
            args += ["--config", config_path]
        
        creationflags = 0
        startupinfo = None
        if os.name == 'nt':
            creationflags = 0x08000000  # CREATE_NO_WINDOW: hides the console window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
        
        proc = subprocess.Popen(
            args,
            stdout=out,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
            startupinfo=startupinfo
        )
    
    SERVICE_PID.write_text(str(proc.pid))
    state = {"pid": proc.pid, "log": str(log_path), "started_at": datetime.datetime.now().isoformat()}
    SERVICE_STATE.write_text(json.dumps(state))
    msg = f"Service started (PID {proc.pid}). Log: {log_path}"
    print(msg)
    return {"ok": True, **state, "msg": msg}


def stopservice():
    """Stop MWL service."""
    if not SERVICE_PID.exists():
        msg = "No PID file; service not running?"
        print(msg)
        return {"ok": False, "msg": msg}
    
    pid = int(SERVICE_PID.read_text().strip())
    if not _is_process_running(pid):
        SERVICE_PID.unlink(missing_ok=True)
        lock_file = ROOT / "mwl_server.lock"
        lock_file.unlink(missing_ok=True) if lock_file.exists() else None
        msg = f"Process {pid} not running"
        print(msg)
        return {"ok": False, "msg": msg, "pid": pid}
    
    try:
        if os.name == 'nt':
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            os.kill(pid, 15)
        time.sleep(0.5)
        SERVICE_PID.unlink(missing_ok=True)
        lock_file = ROOT / "mwl_server.lock"
        lock_file.unlink(missing_ok=True) if lock_file.exists() else None
        msg = f"Stopped service (PID {pid})"
        print(msg)
        return {"ok": True, "msg": msg, "pid": pid}
    except Exception as e:
        msg = f"Failed to stop service: {e}"
        print(msg)
        return {"ok": False, "msg": msg}


def _is_process_running(pid: int) -> bool:
    """Check if process with given PID is running."""
    try:
        if os.name == 'nt':
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return str(pid) in out.stdout
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False


def restartservice(config_path: str | None = None):
    """Restart MWL service."""
    stop_res = stopservice()
    time.sleep(1)
    start_res = startservice(config_path=config_path)
    return {"stop": stop_res, "start": start_res}


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
            app_status["running"] = _is_process_running(pid)
        except Exception:
            pass
    
    service_status = {
        "running": False,
        "pid": None
    }
    if SERVICE_PID.exists():
        try:
            pid = int(SERVICE_PID.read_text().strip())
            service_status["pid"] = pid
            service_status["running"] = _is_process_running(pid)
            if SERVICE_STATE.exists():
                try:
                    data = json.loads(SERVICE_STATE.read_text())
                    service_status.update(data)
                except Exception:
                    pass
        except Exception:
            pass
    
    return {"app": app_status, "service": service_status}


def logs(limit: int = 20):
    """List recent service log files."""
    files = sorted(SERVICE_LOG_DIR.glob('*.log'), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for p in files[:limit]:
        out.append({"name": p.name, "path": str(p), "size": p.stat().st_size, "mtime": p.stat().st_mtime})
    return out


def tail(log_path: str, lines: int = 200):
    """Tail a service log file."""
    p = Path(log_path)
    if not p.exists():
        return f"Log file not found: {log_path}"
    try:
        with p.open('rb') as f:
            f.seek(0, os.SEEK_END)
            end = f.tell()
            block_size = 1024
            data = b''
            while end > 0 and data.count(b'\n') <= lines:
                read_size = min(block_size, end)
                f.seek(end - read_size)
                data = f.read(read_size) + data
                end -= read_size
            text = data.decode(errors='replace')
            return '\n'.join(text.splitlines()[-lines:])
    except Exception as e:
        return f"Error reading log: {e}"


def _add_to_path_windows():
    """Add FlowWorklist directory to Windows System PATH (requires Administrator)."""
    import winreg
    import ctypes
    flow_dir = str(ROOT)
    
    # Check if running as administrator
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False
    
    if not is_admin:
        print("⚠️  Administrator privileges required to modify System PATH.")
        print("   Please run PowerShell or CMD as Administrator and try again.")
        print()
        print("   Alternative: Add to User PATH instead (no admin required):")
        print(f"   Add this to your User PATH manually: {flow_dir}")
        return False
    
    try:
        # Open registry key for SYSTEM environment variables (requires admin)
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
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
            
            # Broadcast WM_SETTINGCHANGE to notify system of environment change
            try:
                HWND_BROADCAST = 0xFFFF
                WM_SETTINGCHANGE = 0x1A
                SMTO_ABORTIFHUNG = 0x0002
                ctypes.windll.user32.SendMessageTimeoutW(
                    HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment",
                    SMTO_ABORTIFHUNG, 5000, None
                )
            except:
                pass  # Non-critical if broadcast fails
            
            print(f"✓ Added to System PATH: {flow_dir}")
            print("⚠️  Please restart PowerShell/CMD for PATH changes to take effect.")
            return True
        else:
            winreg.CloseKey(key)
            print(f"ℹ️  Already in System PATH: {flow_dir}")
            return False
    except PermissionError:
        print("✗ Permission denied. Run PowerShell/CMD as Administrator.")
        return False
    except Exception as e:
        print(f"✗ Failed to add to System PATH: {e}")
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
        res = startservice(config_path=args.config)
        if res is not None:
            print(res)
    elif args.cmd == "stopservice":
        res = stopservice()
        if res is not None:
            print(res)
    elif args.cmd == "restartservice":
        res = restartservice(config_path=args.config)
        if res is not None:
            print(res)
    elif args.cmd == "status":
        print(status())
    elif args.cmd == "logs":
        print(logs(limit=args.limit))
    elif args.cmd == "tail":
        print(tail(args.log, lines=args.lines))
    elif args.cmd == "install":
        install(add_to_path=args.add_to_path)
