import argparse
import os
import sys
import subprocess
import time
import json
import datetime
import psutil
import hashlib
from pathlib import Path

ROOT = Path(__file__).parent
# Default paths (will be overridden after instance dir is computed)
APP_PID = ROOT / "app.pid"
APP_LOCK = ROOT / "app.lock"
SERVICE_PID = ROOT / "service.pid"
SERVICE_LOCK = ROOT / "service.lock"
SERVICE_STATE = ROOT / "service_state.json"
MPPS_PID = ROOT / "mpps.pid"
MPPS_LOCK = ROOT / "mpps.lock"
MPPS_STATE = ROOT / "mpps_state.json"
PRINTER_PID = ROOT / "printer.pid"
PRINTER_LOCK = ROOT / "printer.lock"
PRINTER_STATE = ROOT / "printer_state.json"
SERVICE_LOG_DIR = ROOT / "service_logs"

SERVICE_LOG_DIR.mkdir(exist_ok=True)


def _venv_python():
    if os.name == 'nt':
        p = ROOT / "Scripts" / "python.exe"
    else:
        p = ROOT / "Scripts" / "python"
    return str(p) if p.exists() else sys.executable


def _read_lock_file(lock_path: Path) -> dict | None:
    """Read and parse lock file, return None if invalid or missing."""
    if not lock_path.exists():
        return None
    try:
        data = json.loads(lock_path.read_text())
        if 'pid' in data and 'timestamp' in data:
            return data
    except Exception:
        pass
    return None


def _write_lock_file(lock_path: Path, pid: int, extra: dict = None):
    """Write lock file with PID and timestamp."""
    data = {
        'pid': pid,
        'timestamp': datetime.datetime.now().isoformat(),
        'hostname': os.environ.get('COMPUTERNAME', os.environ.get('HOSTNAME', 'unknown'))
    }
    if extra:
        data.update(extra)
    lock_path.write_text(json.dumps(data, indent=2))


def _instance_id() -> str:
    """Return a deterministic instance ID for this workspace.

    - Uses FLOWWORKLIST_INSTANCE_ID env var if set
    - Otherwise derives a short hash from the absolute ROOT path
    """
    iid = os.environ.get('FLOWWORKLIST_INSTANCE_ID')
    if iid and iid.strip():
        return iid.strip()
    h = hashlib.sha1(str(ROOT).lower().encode('utf-8')).hexdigest()[:8]
    return f"FWL-{h}"


def _instance_dir(iid: str) -> Path:
    """Compute storage directory for lock/state files for a given instance id."""
    # Allow override
    base_override = os.environ.get('FLOWWORKLIST_LOCK_DIR')
    if base_override and base_override.strip():
        p = Path(base_override).expanduser().resolve() / iid
        p.mkdir(parents=True, exist_ok=True)
        return p
    if os.name == 'nt':
        local = os.environ.get('LOCALAPPDATA') or os.environ.get('APPDATA')
        if local:
            p = Path(local) / 'FlowWorklist' / 'instances' / iid
            p.mkdir(parents=True, exist_ok=True)
            return p
    # Fallback (Linux/macOS or missing env): use ~/.local/share
    p = Path.home() / '.local' / 'share' / 'FlowWorklist' / 'instances' / iid
    p.mkdir(parents=True, exist_ok=True)
    return p

# Compute instance paths and override default lock/state files
INSTANCE_ID = _instance_id()
INSTANCE_DIR = _instance_dir(INSTANCE_ID)

APP_PID = INSTANCE_DIR / "app.pid"
APP_LOCK = INSTANCE_DIR / "app.lock"
SERVICE_PID = INSTANCE_DIR / "service.pid"
SERVICE_LOCK = INSTANCE_DIR / "service.lock"
SERVICE_STATE = INSTANCE_DIR / "service_state.json"
MPPS_PID = INSTANCE_DIR / "mpps.pid"
MPPS_LOCK = INSTANCE_DIR / "mpps.lock"
MPPS_STATE = INSTANCE_DIR / "mpps_state.json"
PRINTER_PID = INSTANCE_DIR / "printer.pid"
PRINTER_LOCK = INSTANCE_DIR / "printer.lock"
PRINTER_STATE = INSTANCE_DIR / "printer_state.json"


def _find_pids_by_id(script_name: str, instance_id: str) -> list[int]:
    """Find PIDs of processes running given script tagged with instance-id.

    We match by presence of script name and the token '--instance-id' and the
    instance_id anywhere in the command line.
    """
    pids: list[int] = []
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline_list = proc.info.get('cmdline') or []
                cmd = ' '.join(cmdline_list).lower()
                if script_name.lower() in cmd and 'python' in cmd and '--instance-id' in cmd and instance_id.lower() in cmd:
                    pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass
    return pids


def _is_process_alive(pid: int, cmdline_match: str = None) -> bool:
    """Robust check if process is alive using psutil.
    
    Args:
        pid: Process ID to check
        cmdline_match: Optional string that should appear in process command line
    
    Returns:
        True if process exists and optionally matches command line
    """
    try:
        proc = psutil.Process(pid)
        if not proc.is_running():
            return False
        
        # Additional validation: check command line if specified
        if cmdline_match:
            try:
                cmdline = ' '.join(proc.cmdline()).lower()
                if cmdline_match.lower() not in cmdline:
                    return False
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                # If we can't access cmdline but process exists, assume it's valid
                pass
        
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, ProcessLookupError):
        return False


def _cleanup_stale_lock(lock_path: Path, pid_path: Path = None, cmdline_match: str = None):
    """Remove lock file if process is not running."""
    lock_data = _read_lock_file(lock_path)
    if lock_data:
        pid = lock_data.get('pid')
        if pid and not _is_process_alive(pid, cmdline_match):
            lock_path.unlink(missing_ok=True)
            if pid_path:
                pid_path.unlink(missing_ok=True)
            return True
    elif lock_path.exists():
        # Invalid lock file, remove it
        lock_path.unlink(missing_ok=True)
        if pid_path:
            pid_path.unlink(missing_ok=True)
        return True
    return False


def startapp():
    """Start the management App (web UI) in background without extra launcher files."""
    # Check for existing instance
    _cleanup_stale_lock(APP_LOCK, APP_PID, 'app.py')

    iid = _instance_id()
    # Prefer instance-id based check to avoid cross-repo conflicts
    existing_by_id = _find_pids_by_id('app.py', iid)
    if existing_by_id:
        pid = existing_by_id[0]
        print(f"App already running for {iid} (PID {pid})")
        print(f"Use 'flow stop app' to stop it first.")
        return
    
    lock_data = _read_lock_file(APP_LOCK)
    if lock_data:
        pid = lock_data.get('pid')
        if pid and _is_process_alive(pid, 'app.py'):
            print(f"App already running (PID {pid})")
            print(f"Started at: {lock_data.get('timestamp', 'unknown')}")
            print(f"Use 'flow stop app' to stop it first.")
            return
    
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
        [python_path, str(app_script), '--instance-id', iid],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags
    )

    # Write both PID file and lock file
    try:
        APP_PID.write_text(str(proc.pid))
        _write_lock_file(APP_LOCK, proc.pid, {'type': 'app', 'url': 'http://127.0.0.1:5000', 'instance_id': iid})
        print(f"[OK] App started successfully (PID {proc.pid})")
    except Exception as e:
        print(f"[WARNING] App started but could not write lock files: {e}")
    
    # Wait for app to be ready
    print("Waiting for app to start...")
    time.sleep(3)
    
    # Verify app is actually running
    if not _is_process_alive(proc.pid, 'app.py'):
        print("[ERROR] App failed to start (process died immediately)")
        APP_PID.unlink(missing_ok=True)
        APP_LOCK.unlink(missing_ok=True)
        return
    
    # Open browser
    import webbrowser
    url = "http://127.0.0.1:5000"
    try:
        webbrowser.open(url)
        print(f"[OK] Browser opened at {url}")
    except Exception:
        print(f"[INFO] Could not open browser automatically. Please visit: {url}")
    
    print("[OK] App is running. Use 'flow stop app' to stop.")


def stopapp():
    """Stop the management App using PID from app.pid."""
    iid = _instance_id()
    # First, try to find any running app.py processes
    found_pids = []
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline']).lower() if proc.info['cmdline'] else ''
                if 'app.py' in cmdline and 'python' in cmdline and '--instance-id' in cmdline and iid.lower() in cmdline:
                    found_pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass
    
    # Try to get PID from lock file first, fallback to PID file
    lock_data = _read_lock_file(APP_LOCK)
    pid = None
    
    if lock_data:
        pid = lock_data.get('pid')
    elif APP_PID.exists():
        try:
            pid = int(APP_PID.read_text().strip())
        except Exception:
            pass
    
    # If we found running app processes and stored PID doesn't match, use found process
    if found_pids and (not pid or pid not in found_pids):
        # Use the found PID
        pid = found_pids[0]
        print(f"[INFO] Found running app for {iid} (PID {pid}), stopping it...")
    
    if not pid:
        # No PID found either in files or in running processes
        if _cleanup_stale_lock(APP_LOCK, APP_PID, 'app.py'):
            print("[OK] Cleaned up stale app files.")
        else:
            print("[INFO] No app running or PID file found.")
        return
    
    # Check if process is actually running before trying to stop it
    if not _is_process_alive(pid, 'app.py'):
        # Process not running, just clean up files
        if found_pids:
            # But we found other running apps, recursively stop them
            print(f"[INFO] Stale PID {pid}. Looking for other running instances...")
            APP_PID.unlink(missing_ok=True)
            APP_LOCK.unlink(missing_ok=True)
            if len(found_pids) > 1:
                # More instances to stop
                for other_pid in found_pids[1:]:
                    try:
                        proc = psutil.Process(other_pid)
                        proc.terminate()
                        proc.wait(timeout=5)
                        print(f"[OK] Stopped app instance (PID {other_pid})")
                    except Exception as e:
                        print(f"[WARNING] Could not stop app (PID {other_pid}): {e}")
        else:
            print(f"[INFO] App not running (stale PID {pid}). Cleaning up...")
            APP_PID.unlink(missing_ok=True)
            APP_LOCK.unlink(missing_ok=True)
        return
    
    # Stop the process
    try:
        proc = psutil.Process(pid)
        
        # Get children BEFORE terminating parent (they won't be accessible after)
        children = proc.children(recursive=True)
        
        # Terminate gracefully first
        proc.terminate()
        
        # Wait up to 5 seconds for graceful shutdown
        try:
            proc.wait(timeout=5)
            print(f"[OK] App stopped gracefully (PID {pid})")
        except psutil.TimeoutExpired:
            # Force kill if still running
            print(f"[WARNING] Forcing App shutdown (PID {pid})...")
            proc.kill()
            proc.wait(timeout=3)
            print(f"[OK] App force-killed (PID {pid})")
        
        # Kill all children too
        for child in children:
            try:
                child.kill()
                print(f"[OK] Killed child process (PID {child.pid})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
    except psutil.NoSuchProcess:
        print(f"[INFO] Process {pid} already terminated.")
    except Exception as e:
        print(f"[ERROR] Error stopping App (PID {pid}): {e}")
    
    # Clean up files
    APP_PID.unlink(missing_ok=True)
    APP_LOCK.unlink(missing_ok=True)
    time.sleep(0.5)
    
    # Final verification
    if _is_process_alive(pid):
        print(f"[WARNING] Warning: Process {pid} may still be running.")
    else:
        print("[OK] App stopped successfully.")


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
    print("Stopping MPPS...")
    stop_mpps_service()
    time.sleep(1)
    print("Stopping App...")
    stopapp()


def _load_config_file(config_path: str | None = None) -> dict:
    cfg_file = Path(config_path) if config_path else (ROOT / "config.json")
    if not cfg_file.exists():
        return {}
    try:
        return json.loads(cfg_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _mpps_should_start_with_worklist(config_path: str | None = None) -> bool:
    cfg = _load_config_file(config_path)
    mpps = cfg.get("mpps") if isinstance(cfg.get("mpps"), dict) else {}
    enabled = bool(mpps.get("enabled"))
    start_with_worklist = bool(mpps.get("start_with_worklist", True))
    return enabled and start_with_worklist


def start_mpps_service(config_path: str | None = None):
    """Start MPPS service in background."""
    cfg = _load_config_file(config_path)
    mpps_cfg = cfg.get("mpps") if isinstance(cfg.get("mpps"), dict) else {}
    if not bool(mpps_cfg.get("enabled")):
        msg = "MPPS is disabled in config.json"
        print(f"[INFO] {msg}")
        return {"ok": False, "msg": msg, "error_type": "disabled"}

    _cleanup_stale_lock(MPPS_LOCK, MPPS_PID, 'mpps_service.py')
    iid = _instance_id()
    existing = _find_pids_by_id('mpps_service.py', iid)
    if existing:
        pid = existing[0]
        msg = f"MPPS already running for {iid} (PID {pid})"
        print(f"[INFO] {msg}")
        return {"ok": False, "msg": msg, "error_type": "already_running", "pid": pid}

    lock_data = _read_lock_file(MPPS_LOCK)
    if lock_data:
        pid = lock_data.get('pid')
        if pid and _is_process_alive(pid, 'mpps_service.py'):
            msg = f"MPPS already running (PID {pid})"
            print(f"[INFO] {msg}")
            return {"ok": False, "msg": msg, "error_type": "already_running", "pid": pid}

    script = ROOT / "mpps_service.py"
    if not script.exists():
        msg = f"MPPS script not found: {script}"
        print(f"[ERROR] {msg}")
        return {"ok": False, "msg": msg, "error_type": "script_not_found", "error_detail": msg}

    if config_path and not Path(config_path).exists():
        msg = f"Configuration file not found: {config_path}"
        print(f"[ERROR] {msg}")
        return {"ok": False, "msg": msg, "error_type": "config_not_found", "error_detail": msg}

    python_path = _venv_python()
    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    log_path = SERVICE_LOG_DIR / f"mpps_{ts}.log"
    try:
        with open(log_path, "ab") as out:
            args = [python_path, str(script), '--instance-id', iid]
            if config_path:
                args += ["--config", config_path]
            creationflags = 0
            startupinfo = None
            if os.name == 'nt':
                creationflags = 0x08000000
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
    except Exception as e:
        msg = f"Failed to start MPPS process: {e}"
        print(f"[ERROR] {msg}")
        return {"ok": False, "msg": msg, "error_type": "process_start_failed", "error_detail": str(e)}

    MPPS_PID.write_text(str(proc.pid))
    state = {"pid": proc.pid, "log": str(log_path), "started_at": datetime.datetime.now().isoformat()}
    MPPS_STATE.write_text(json.dumps(state, indent=2))
    _write_lock_file(MPPS_LOCK, proc.pid, {'type': 'mpps', 'log': str(log_path), 'instance_id': iid})

    time.sleep(1)
    if not _is_process_alive(proc.pid, 'mpps_service.py'):
        msg = f"MPPS process died immediately after start (PID {proc.pid})"
        print(f"[ERROR] {msg}")
        MPPS_PID.unlink(missing_ok=True)
        MPPS_LOCK.unlink(missing_ok=True)
        MPPS_STATE.unlink(missing_ok=True)
        return {"ok": False, "msg": msg, "error_type": "process_died", "log_path": str(log_path)}

    msg = f"[OK] MPPS started successfully (PID {proc.pid}). Log: {log_path}"
    print(msg)
    return {"ok": True, **state, "msg": msg}


def stop_mpps_service():
    """Stop MPPS service."""
    iid = _instance_id()
    found_pids = _find_pids_by_id('mpps_service.py', iid)
    lock_data = _read_lock_file(MPPS_LOCK)
    pid = None
    if lock_data:
        pid = lock_data.get('pid')
    elif MPPS_PID.exists():
        try:
            pid = int(MPPS_PID.read_text().strip())
        except Exception:
            pid = None

    if found_pids and (not pid or pid not in found_pids):
        pid = found_pids[0]

    if not pid:
        _cleanup_stale_lock(MPPS_LOCK, MPPS_PID, 'mpps_service.py')
        MPPS_STATE.unlink(missing_ok=True)
        return {"ok": False, "msg": "[INFO] No MPPS running or PID file found."}

    if not _is_process_alive(pid, 'mpps_service.py'):
        MPPS_PID.unlink(missing_ok=True)
        MPPS_LOCK.unlink(missing_ok=True)
        MPPS_STATE.unlink(missing_ok=True)
        return {"ok": False, "msg": f"[INFO] MPPS not running (stale PID {pid}).", "pid": pid}

    try:
        proc = psutil.Process(pid)
        children = proc.children(recursive=True)
        proc.terminate()
        try:
            proc.wait(timeout=5)
            msg = f"[OK] MPPS stopped gracefully (PID {pid})"
        except psutil.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
            msg = f"[OK] MPPS force-killed (PID {pid})"
        for child in children:
            try:
                child.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        MPPS_PID.unlink(missing_ok=True)
        MPPS_LOCK.unlink(missing_ok=True)
        MPPS_STATE.unlink(missing_ok=True)
        return {"ok": True, "msg": msg, "pid": pid}
    except psutil.NoSuchProcess:
        MPPS_PID.unlink(missing_ok=True)
        MPPS_LOCK.unlink(missing_ok=True)
        MPPS_STATE.unlink(missing_ok=True)
        return {"ok": True, "msg": f"[INFO] MPPS process {pid} already terminated.", "pid": pid}
    except Exception as e:
        return {"ok": False, "msg": f"[ERROR] Error stopping MPPS (PID {pid}): {e}"}


def restart_mpps_service(config_path: str | None = None):
    stop_res = stop_mpps_service()
    time.sleep(1)
    start_res = start_mpps_service(config_path=config_path)
    if start_res.get('ok'):
        return {"ok": True, "msg": f"[OK] MPPS restarted successfully (PID {start_res.get('pid')})", **start_res}
    return {"ok": False, "msg": start_res.get('msg', 'MPPS restart failed'), "stop": stop_res, **start_res}


def _normalize_printer_cfg(config_path: str | None = None) -> dict:
    cfg = _load_config_file(config_path)
    raw = cfg.get("dicom_printer") if isinstance(cfg.get("dicom_printer"), dict) else {}
    receiver = raw.get("receiver") if isinstance(raw.get("receiver"), dict) else {}
    worker = raw.get("worker") if isinstance(raw.get("worker"), dict) else {}
    base = ROOT / "dicom-printer"
    return {
        "enabled": bool(raw.get("enabled")),
        "receiver": {
            "aet": str(receiver.get("aet", "VPRINTSCP")).strip() or "VPRINTSCP",
            "profile": str(receiver.get("profile", "FLOWWORKLIST_PRINTER")).strip() or "FLOWWORKLIST_PRINTER",
            "target_host": str(receiver.get("target_host", "127.0.0.1")).strip() or "127.0.0.1",
            "port": int(receiver.get("port", 4100) or 4100),
            "dcmtk_bin": str(receiver.get("dcmtk_bin", r"C:\dcmtk\bin")).strip() or r"C:\dcmtk\bin",
            "spool_dir": str(worker.get("spool_dir", str(base / "spool"))).strip() or str(base / "spool"),
        },
        "worker": {
            "database_dir": str(worker.get("database_dir", str(base / "database"))).strip() or str(base / "database"),
        },
    }


def _write_printer_runtime_cfg(printer_cfg: dict) -> Path:
    receiver = printer_cfg["receiver"]
    worker = printer_cfg["worker"]
    runtime_cfg = ROOT / "dicom-printer" / "runtime_printer.cfg"
    runtime_cfg.parent.mkdir(parents=True, exist_ok=True)
    Path(receiver["spool_dir"]).mkdir(parents=True, exist_ok=True)
    Path(worker["database_dir"]).mkdir(parents=True, exist_ok=True)
    lines = [
        "# Auto-generated by FlowWorklist",
        "",
        "[[GENERAL]]",
        "",
        "[PRINT]",
        f"Directory = {receiver['spool_dir']}",
        "DetailedLog = true",
        "BinaryLog = false",
        "DeletePrintJobs = false",
        "",
        "[DATABASE]",
        f"Directory = {worker['database_dir']}",
        "",
        "[[COMMUNICATION]]",
        "",
        f"[{receiver['profile']}]",
        "type = LOCALPRINTER",
        f"hostname = {receiver['target_host']}",
        f"port = {receiver['port']}",
        f"aetitle = {receiver['aet']}",
        "description = FlowWorklist DICOM Print SCP",
        "DisplayFormat = 1,1\\1,2\\2,2\\2,3\\3,3\\3,4\\4,4",
        "FilmSizeID = 14INX17IN\\10INX12IN\\8INX10IN\\24CMX30CM\\A3\\A4",
        "MagnificationType = CUBIC\\BILINEAR\\REPLICATE\\NONE",
        "MediumType = BLUE FILM\\CLEAR FILM\\PAPER",
        "FilmDestination = PROCESSOR\\MAGAZINE\\BIN_1\\BIN_2",
        "Supports12Bit = true",
        "SupportsPresentationLUT = true",
        "PresentationLUTinFilmSession = false",
        "PresentationLUTMatchRequired = true",
        "SupportsTrim = true",
        "SupportsDecimateCrop = false",
        "SupportsImageSize = true",
        "MaxPDU = 32768",
        "ImplicitOnly = false",
        "DisableNewVRs = false",
    ]
    runtime_cfg.write_text("\n".join(lines), encoding="utf-8")
    return runtime_cfg


def start_printer_service(config_path: str | None = None):
    """Start virtual DICOM printer receiver (dcmprscp)."""
    printer_cfg = _normalize_printer_cfg(config_path)
    if not printer_cfg.get("enabled"):
        msg = "Virtual printer is disabled in config.json"
        return {"ok": False, "msg": msg, "error_type": "disabled"}

    existing = find_printer_receiver_pids()
    if existing:
        pid = existing[0]
        msg = f"Virtual printer receiver already running (PID {pid})"
        return {"ok": False, "msg": msg, "error_type": "already_running", "pid": pid}

    dcmprscp = Path(printer_cfg["receiver"]["dcmtk_bin"]) / "dcmprscp.exe"
    if not dcmprscp.exists():
        msg = f"dcmprscp.exe not found at: {dcmprscp}"
        return {"ok": False, "msg": msg, "error_type": "binary_not_found", "error_detail": msg}

    runtime_cfg = _write_printer_runtime_cfg(printer_cfg)
    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    log_path = SERVICE_LOG_DIR / f"printer_{ts}.log"
    try:
        with open(log_path, "ab") as out:
            args = [
                str(dcmprscp),
                "-c",
                str(runtime_cfg),
                "-p",
                str(printer_cfg["receiver"]["profile"]),
                "+d",
                "-v",
            ]
            creationflags = 0
            startupinfo = None
            if os.name == 'nt':
                creationflags = 0x08000000
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
            proc = subprocess.Popen(
                args,
                cwd=str((ROOT / "dicom-printer")),
                stdout=out,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
                startupinfo=startupinfo,
            )
    except Exception as e:
        return {
            "ok": False,
            "msg": f"Failed to start virtual printer receiver: {e}",
            "error_type": "process_start_failed",
            "error_detail": str(e),
        }

    PRINTER_PID.write_text(str(proc.pid))
    state = {"pid": proc.pid, "log": str(log_path), "started_at": datetime.datetime.now().isoformat()}
    PRINTER_STATE.write_text(json.dumps(state, indent=2))
    _write_lock_file(PRINTER_LOCK, proc.pid, {'type': 'printer_receiver', 'log': str(log_path), 'instance_id': INSTANCE_ID})
    time.sleep(1)
    if proc.poll() is not None:
        PRINTER_PID.unlink(missing_ok=True)
        PRINTER_LOCK.unlink(missing_ok=True)
        PRINTER_STATE.unlink(missing_ok=True)
        return {
            "ok": False,
            "msg": f"Virtual printer receiver process died immediately after start (PID {proc.pid})",
            "error_type": "process_died",
            "log_path": str(log_path),
        }
    return {"ok": True, **state, "msg": f"[OK] Virtual printer receiver started (PID {proc.pid})"}


def stop_printer_service():
    """Stop virtual DICOM printer receiver (dcmprscp)."""
    pids = set(find_printer_receiver_pids())
    lock_data = _read_lock_file(PRINTER_LOCK)
    if lock_data and lock_data.get("pid"):
        pids.add(int(lock_data.get("pid")))
    if PRINTER_PID.exists():
        try:
            pids.add(int(PRINTER_PID.read_text().strip()))
        except Exception:
            pass

    if not pids:
        PRINTER_PID.unlink(missing_ok=True)
        PRINTER_LOCK.unlink(missing_ok=True)
        PRINTER_STATE.unlink(missing_ok=True)
        return {"ok": False, "msg": "[INFO] No virtual printer receiver process found."}

    killed = []
    errors = []
    for pid in sorted(pids):
        try:
            if os.name == 'nt':
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], check=False,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:
                os.kill(pid, 9)
            killed.append(pid)
        except Exception as e:
            errors.append(f"{pid}: {e}")

    PRINTER_PID.unlink(missing_ok=True)
    PRINTER_LOCK.unlink(missing_ok=True)
    PRINTER_STATE.unlink(missing_ok=True)
    if errors and not killed:
        return {"ok": False, "msg": f"[ERROR] Failed stopping virtual printer receiver: {'; '.join(errors)}"}
    return {"ok": True, "msg": f"[OK] Virtual printer receiver stopped (PIDs: {', '.join(map(str, killed))})", "killed": killed, "errors": errors}


def restart_printer_service(config_path: str | None = None):
    stop_res = stop_printer_service()
    time.sleep(1)
    start_res = start_printer_service(config_path=config_path)
    if start_res.get("ok"):
        return {"ok": True, "msg": start_res.get("msg"), "stop": stop_res, **start_res}
    return {"ok": False, "msg": start_res.get("msg", "Virtual printer restart failed"), "stop": stop_res, **start_res}


def startservice(config_path: str | None = None):
    """Start MWL service in background."""
    # Check for existing instance using new lock system
    _cleanup_stale_lock(SERVICE_LOCK, SERVICE_PID, 'mwl_service.py')
    iid = _instance_id()
    existing_by_id = _find_pids_by_id('mwl_service.py', iid)
    if existing_by_id:
        pid = existing_by_id[0]
        msg = f"Service already running for {iid} (PID {pid})"
        print(f"[INFO] {msg}")
        return {"ok": False, "msg": msg, "error_type": "already_running", "pid": pid}
    
    lock_data = _read_lock_file(SERVICE_LOCK)
    if lock_data:
        pid = lock_data.get('pid')
        if pid and _is_process_alive(pid, 'mwl_service.py'):
            msg = f"Service already running (PID {pid})"
            print(f"[INFO] {msg}")
            print(f"Started at: {lock_data.get('timestamp', 'unknown')}")
            print(f"Use 'flow stopservice' to stop it first.")
            return {"ok": False, "msg": msg, "error_type": "already_running", "pid": pid}
    
    # Clean up old mwl_server.lock if exists
    old_lock = ROOT / "mwl_server.lock"
    old_lock.unlink(missing_ok=True)
    
    # Determine Python executable
    python_path = _venv_python()
    script = ROOT / "mwl_service.py"
    if not script.exists():
        msg = f"Service script not found: {script}"
        print(f"[ERROR] {msg}")
        return {"ok": False, "msg": msg, "error_type": "script_not_found", "error_detail": msg}
    
    # Check if config file exists when provided
    if config_path and not Path(config_path).exists():
        msg = f"Configuration file not found: {config_path}"
        print(f"[ERROR] {msg}")
        return {"ok": False, "msg": msg, "error_type": "config_not_found", "error_detail": msg}
    
    # Prepare log file
    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    log_path = SERVICE_LOG_DIR / f"mwls_{ts}.log"
    
    # Start detached process
    try:
        with open(log_path, "ab") as out:
            args = [python_path, str(script), '--instance-id', iid]
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
    except Exception as e:
        msg = f"Failed to start process: {str(e)}"
        print(f"[ERROR] {msg}")
        return {"ok": False, "msg": msg, "error_type": "process_start_failed", "error_detail": str(e)}
    
    # Write lock, PID, and state files
    SERVICE_PID.write_text(str(proc.pid))
    state = {"pid": proc.pid, "log": str(log_path), "started_at": datetime.datetime.now().isoformat()}
    SERVICE_STATE.write_text(json.dumps(state, indent=2))
    _write_lock_file(SERVICE_LOCK, proc.pid, {'type': 'service', 'log': str(log_path), 'instance_id': iid})
    
    # Wait a moment and verify process started
    time.sleep(1)
    if not _is_process_alive(proc.pid, 'mwl_service.py'):
        msg = f"Service process died immediately after start (PID {proc.pid})"
        print(f"[ERROR] {msg}")
        print(f"Check log file for details: {log_path}")
        SERVICE_PID.unlink(missing_ok=True)
        SERVICE_LOCK.unlink(missing_ok=True)
        SERVICE_STATE.unlink(missing_ok=True)
        
        # Try to read log for more info
        log_content = ""
        try:
            log_content = log_path.read_text()[-500:]  # Last 500 chars
        except:
            pass
        
        return {
            "ok": False, 
            "msg": msg, 
            "error_type": "process_died",
            "error_detail": f"{msg}. Log: {log_path}. Last output: {log_content}",
            "log_path": str(log_path)
        }
    
    msg = f"[OK] Service started successfully (PID {proc.pid}). Log: {log_path}"
    print(msg)
    result = {"ok": True, **state, "msg": msg}

    # Start MPPS together when configured, but never fail MWL startup because of MPPS.
    try:
        if _mpps_should_start_with_worklist(config_path=config_path):
            mpps_res = start_mpps_service(config_path=config_path)
            result["mpps"] = mpps_res
            if not mpps_res.get("ok"):
                result["warning"] = f"MWL started, but MPPS did not start: {mpps_res.get('msg')}"
    except Exception as e:
        result["mpps"] = {"ok": False, "msg": f"Unhandled MPPS start error: {e}"}
        result["warning"] = f"MWL started, but MPPS start raised exception: {e}"

    return result


def stopservice():
    """Stop MWL service."""
    # Always stop MPPS first to avoid auxiliary orphan processes.
    try:
        stop_mpps_service()
    except Exception:
        pass
    # Stop virtual printer receiver process as part of full service stop.
    try:
        stop_printer_service()
    except Exception:
        pass

    iid = _instance_id()
    # First, try to find any running mwl_service.py processes
    found_pids = []
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline']).lower() if proc.info['cmdline'] else ''
                if 'mwl_service.py' in cmdline and 'python' in cmdline and '--instance-id' in cmdline and iid.lower() in cmdline:
                    found_pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass
    
    # Try to get PID from lock file first, fallback to PID file
    lock_data = _read_lock_file(SERVICE_LOCK)
    pid = None
    
    if lock_data:
        pid = lock_data.get('pid')
    elif SERVICE_PID.exists():
        try:
            pid = int(SERVICE_PID.read_text().strip())
        except Exception:
            pass
    
    # If we found running service processes and stored PID doesn't match, use found process
    if found_pids and (not pid or pid not in found_pids):
        # Use the found PID
        pid = found_pids[0]
        print(f"[INFO] Found running service for {iid} (PID {pid}), stopping it...")
    
    if not pid:
        # No PID found either in files or in running processes
        if _cleanup_stale_lock(SERVICE_LOCK, SERVICE_PID, 'mwl_service.py'):
            msg = "[OK] Cleaned up stale service files."
            print(msg)
        else:
            msg = "[INFO] No service running or PID file found."
            print(msg)
        return {"ok": False, "msg": msg}
    
    # Check if process is actually running before trying to stop it
    if not _is_process_alive(pid, 'mwl_service.py'):
        # Process not running, just clean up files
        if found_pids:
            # But we found other running services, stop them
            print(f"[INFO] Stale PID {pid}. Stopping other instances...")
            SERVICE_PID.unlink(missing_ok=True)
            SERVICE_LOCK.unlink(missing_ok=True)
            if len(found_pids) > 1:
                for other_pid in found_pids[1:]:
                    try:
                        proc = psutil.Process(other_pid)
                        proc.terminate()
                        proc.wait(timeout=5)
                        print(f"[OK] Stopped service instance (PID {other_pid})")
                    except Exception as e:
                        print(f"[WARNING] Could not stop service (PID {other_pid}): {e}")
        else:
            msg = f"[INFO] Service not running (stale PID {pid}). Cleaning up..."
            print(msg)
            SERVICE_PID.unlink(missing_ok=True)
            SERVICE_LOCK.unlink(missing_ok=True)
        SERVICE_STATE.unlink(missing_ok=True)
        old_lock = ROOT / "mwl_server.lock"
        old_lock.unlink(missing_ok=True)
        return {"ok": False, "msg": msg, "pid": pid}

    
    # Stop the process
    try:
        proc = psutil.Process(pid)
        
        # Terminate gracefully first
        proc.terminate()
        
        # Wait up to 5 seconds for graceful shutdown
        try:
            proc.wait(timeout=5)
            msg = f"[OK] Service stopped gracefully (PID {pid})"
            print(msg)
        except psutil.TimeoutExpired:
            # Force kill if still running
            print(f"[WARNING] Forcing service shutdown (PID {pid})...")
            proc.kill()
            proc.wait(timeout=3)
            msg = f"[OK] Service force-killed (PID {pid})"
            print(msg)
        
        # Kill all children too
        for child in proc.children(recursive=True):
            try:
                child.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Clean up files
        SERVICE_PID.unlink(missing_ok=True)
        SERVICE_LOCK.unlink(missing_ok=True)
        SERVICE_STATE.unlink(missing_ok=True)
        old_lock = ROOT / "mwl_server.lock"
        old_lock.unlink(missing_ok=True)
        
        time.sleep(0.5)
        
        # Final verification
        if _is_process_alive(pid):
            msg = f"[WARNING] Warning: Process {pid} may still be running."
            print(msg)
            return {"ok": False, "msg": msg, "pid": pid}
        
        return {"ok": True, "msg": msg, "pid": pid}
        
    except psutil.NoSuchProcess:
        msg = f"[INFO] Process {pid} already terminated."
        print(msg)
        SERVICE_PID.unlink(missing_ok=True)
        SERVICE_LOCK.unlink(missing_ok=True)
        SERVICE_STATE.unlink(missing_ok=True)
        return {"ok": True, "msg": msg, "pid": pid}
    except Exception as e:
        msg = f"[ERROR] Error stopping service (PID {pid}): {e}"
        print(msg)
        return {"ok": False, "msg": msg}


def restartservice(config_path: str | None = None):
    """Restart MWL service with better error reporting."""
    stop_res = stopservice()
    time.sleep(1)
    start_res = startservice(config_path=config_path)
    
    # Combine results with better error messages for web UI
    result = {
        "ok": start_res.get('ok', False) if isinstance(start_res, dict) else False,
    }
    
    # Generate meaningful message
    if isinstance(start_res, dict):
        if start_res.get('ok'):
            result["msg"] = f"[OK] Service restarted successfully (PID {start_res.get('pid')})"
            result["pid"] = start_res.get('pid')
            result["log"] = start_res.get('log')
            result["started_at"] = start_res.get('started_at')
        else:
            # Extract error details from start_res for better web UI error display
            error_msg = start_res.get('msg', 'Unknown error during start')
            error_detail = start_res.get('error_detail', error_msg)
            result["msg"] = error_msg
            result["error_detail"] = error_detail
            result["error_type"] = start_res.get('error_type', 'restart_failed')
            # Include stop result for debugging
            if not stop_res.get('ok'):
                result["stop_error"] = stop_res.get('msg', 'Unknown stop error')
    
    return result


def status():
    """Show status for both App and Service using robust lock-based verification."""
    # Clean up any stale locks first
    _cleanup_stale_lock(APP_LOCK, APP_PID, 'app.py')
    _cleanup_stale_lock(SERVICE_LOCK, SERVICE_PID, 'mwl_service.py')
    _cleanup_stale_lock(MPPS_LOCK, MPPS_PID, 'mpps_service.py')
    _cleanup_stale_lock(PRINTER_LOCK, PRINTER_PID, 'dcmprscp')
    iid = _instance_id()
    
    # Check App status
    app_status = {
        "running": False,
        "pid": None,
        "timestamp": None,
        "url": None
    }
    
    # Prefer id-based detection
    app_pids = _find_pids_by_id('app.py', iid)
    if app_pids:
        pid = app_pids[0]
        app_status["running"] = True
        app_status["pid"] = pid
        app_status["timestamp"] = None
        app_status["url"] = 'http://127.0.0.1:5000'
    else:
        lock_data = _read_lock_file(APP_LOCK)
        if lock_data:
            pid = lock_data.get('pid')
            if pid and _is_process_alive(pid, 'app.py'):
                app_status["running"] = True
                app_status["pid"] = pid
                app_status["timestamp"] = lock_data.get('timestamp')
                app_status["url"] = lock_data.get('url', 'http://127.0.0.1:5000')
    
    # Check Service status
    service_status = {
        "running": False,
        "pid": None,
        "timestamp": None,
        "log": None
    }
    
    # Prefer id-based detection
    svc_pids = _find_pids_by_id('mwl_service.py', iid)
    if svc_pids:
        pid = svc_pids[0]
        service_status["running"] = True
        service_status["pid"] = pid
        service_status["timestamp"] = None
        # Try to read SERVICE_STATE for log
        if SERVICE_STATE.exists():
            try:
                state = json.loads(SERVICE_STATE.read_text())
                service_status["log"] = state.get('log')
                service_status["timestamp"] = state.get('started_at')
            except Exception:
                pass
    else:
        lock_data = _read_lock_file(SERVICE_LOCK)
        if lock_data:
            pid = lock_data.get('pid')
            if pid and _is_process_alive(pid, 'mwl_service.py'):
                service_status["running"] = True
                service_status["pid"] = pid
                service_status["timestamp"] = lock_data.get('timestamp')
                service_status["log"] = lock_data.get('log')
                
                # Also check SERVICE_STATE for additional info
                if SERVICE_STATE.exists():
                    try:
                        state = json.loads(SERVICE_STATE.read_text())
                        if not service_status["log"]:
                            service_status["log"] = state.get('log')
                        if not service_status["timestamp"]:
                            service_status["timestamp"] = state.get('started_at')
                    except Exception:
                        pass

    # Check MPPS status
    mpps_status = {
        "running": False,
        "pid": None,
        "timestamp": None,
        "log": None
    }
    mpps_pids = _find_pids_by_id('mpps_service.py', iid)
    if mpps_pids:
        pid = mpps_pids[0]
        mpps_status["running"] = True
        mpps_status["pid"] = pid
        if MPPS_STATE.exists():
            try:
                state = json.loads(MPPS_STATE.read_text())
                mpps_status["log"] = state.get('log')
                mpps_status["timestamp"] = state.get('started_at')
            except Exception:
                pass
    else:
        lock_data = _read_lock_file(MPPS_LOCK)
        if lock_data:
            pid = lock_data.get('pid')
            if pid and _is_process_alive(pid, 'mpps_service.py'):
                mpps_status["running"] = True
                mpps_status["pid"] = pid
                mpps_status["timestamp"] = lock_data.get('timestamp')
                mpps_status["log"] = lock_data.get('log')
                if MPPS_STATE.exists():
                    try:
                        state = json.loads(MPPS_STATE.read_text())
                        if not mpps_status["log"]:
                            mpps_status["log"] = state.get('log')
                        if not mpps_status["timestamp"]:
                            mpps_status["timestamp"] = state.get('started_at')
                    except Exception:
                        pass
    
    app_status["instance_id"] = iid
    service_status["instance_id"] = iid
    mpps_status["instance_id"] = iid
    printer_status = {
        "running": False,
        "pid": None,
        "timestamp": None,
        "log": None,
        "instance_id": iid,
    }
    printer_pids = find_printer_receiver_pids()
    if printer_pids:
        printer_status["running"] = True
        printer_status["pid"] = printer_pids[0]
    lock_data = _read_lock_file(PRINTER_LOCK)
    if lock_data:
        printer_status["timestamp"] = lock_data.get("timestamp")
        printer_status["log"] = lock_data.get("log")
        if not printer_status["pid"] and lock_data.get("pid"):
            printer_status["pid"] = lock_data.get("pid")
    if PRINTER_STATE.exists():
        try:
            state = json.loads(PRINTER_STATE.read_text())
            if not printer_status["log"]:
                printer_status["log"] = state.get("log")
            if not printer_status["timestamp"]:
                printer_status["timestamp"] = state.get("started_at")
        except Exception:
            pass
    return {"app": app_status, "service": service_status, "mpps": mpps_status, "printer": printer_status}


def _find_service_pids_windows() -> list[int]:
    """Find PIDs of running service processes on Windows by command line match."""
    pids: list[int] = []
    try:
        # Prefer CIM if available (more reliable than tasklist for command line)
        cmd = [
            'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*mwl_service.py*" } | Select-Object -ExpandProperty ProcessId'
        ]
        out = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in out.stdout.splitlines():
            try:
                pid = int(line.strip())
                if pid > 0:
                    pids.append(pid)
            except Exception:
                pass
        # Fallback to WMIC if CIM returned nothing
        if not pids:
            cmd = ['wmic', 'process', 'where', "CommandLine like '%mwl_service.py%'", 'get', 'ProcessId']
            out = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for tok in out.stdout.replace('\r', '').split():
                if tok.isdigit():
                    pids.append(int(tok))
    except Exception:
        pass
    return list(sorted(set(pids)))


def _find_service_pids_unix() -> list[int]:
    pids: list[int] = []
    try:
        out = subprocess.run(['sh', '-lc', "ps -eo pid,command | grep -v grep | grep mwl_service.py | awk '{print $1}'"],
                             check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in out.stdout.splitlines():
            try:
                pid = int(line.strip())
                if pid > 0:
                    pids.append(pid)
            except Exception:
                pass
    except Exception:
        pass
    return list(sorted(set(pids)))


def find_service_pids() -> list[int]:
    """Find all candidate service PIDs including from pid file and process list."""
    pids: set[int] = set()
    # Add PID from file if running
    if SERVICE_PID.exists():
        try:
            pid = int(SERVICE_PID.read_text().strip())
            if _is_process_alive(pid, 'mwl_service.py'):
                pids.add(pid)
        except Exception:
            pass
    # Add by scanning processes
    scan = _find_service_pids_windows() if os.name == 'nt' else _find_service_pids_unix()
    for pid in scan:
        if _is_process_alive(pid, 'mwl_service.py'):
            pids.add(pid)
    return list(sorted(pids))


def _find_mpps_pids_windows() -> list[int]:
    pids: list[int] = []
    try:
        cmd = [
            'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*mpps_service.py*" } | Select-Object -ExpandProperty ProcessId'
        ]
        out = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in out.stdout.splitlines():
            try:
                pid = int(line.strip())
                if pid > 0:
                    pids.append(pid)
            except Exception:
                pass
        if not pids:
            cmd = ['wmic', 'process', 'where', "CommandLine like '%mpps_service.py%'", 'get', 'ProcessId']
            out = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for tok in out.stdout.replace('\r', '').split():
                if tok.isdigit():
                    pids.append(int(tok))
    except Exception:
        pass
    return list(sorted(set(pids)))


def _find_mpps_pids_unix() -> list[int]:
    pids: list[int] = []
    try:
        out = subprocess.run(['sh', '-lc', "ps -eo pid,command | grep -v grep | grep mpps_service.py | awk '{print $1}'"],
                             check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in out.stdout.splitlines():
            try:
                pid = int(line.strip())
                if pid > 0:
                    pids.append(pid)
            except Exception:
                pass
    except Exception:
        pass
    return list(sorted(set(pids)))


def find_mpps_pids() -> list[int]:
    pids: set[int] = set()
    if MPPS_PID.exists():
        try:
            pid = int(MPPS_PID.read_text().strip())
            if _is_process_alive(pid, 'mpps_service.py'):
                pids.add(pid)
        except Exception:
            pass
    scan = _find_mpps_pids_windows() if os.name == 'nt' else _find_mpps_pids_unix()
    for pid in scan:
        if _is_process_alive(pid, 'mpps_service.py'):
            pids.add(pid)
    return list(sorted(pids))


def find_printer_receiver_pids() -> list[int]:
    """Find orphan dcmprscp processes started by FlowWorklist virtual printer."""
    pids: set[int] = set()
    marker = str((ROOT / "dicom-printer" / "runtime_printer.cfg")).lower().replace("\\", "/")
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline_list = proc.info.get('cmdline') or []
                cmd = ' '.join(cmdline_list).lower().replace("\\", "/")
                if ('dcmprscp' in cmd or 'dcmprscp.exe' in cmd) and (marker in cmd or 'flowworklist_printer' in cmd):
                    pids.add(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass
    return list(sorted(pids))


def kill_orphan_services():
    """Locate and kill any running mwl_service.py processes; cleanup pid/lock files.

    Returns a dict with ok, killed, errors.
    """
    killed: list[int] = []
    errors: list[str] = []
    candidates = find_service_pids() + find_mpps_pids() + find_printer_receiver_pids()
    for pid in candidates:
        try:
            if os.name == 'nt':
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], check=False,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:
                os.kill(pid, 9)
            killed.append(pid)
        except Exception as e:
            errors.append(f"{pid}: {e}")
    # Cleanup pid and lock files regardless
    try:
        SERVICE_PID.unlink(missing_ok=True)
    except Exception:
        pass
    try:
        MPPS_PID.unlink(missing_ok=True)
    except Exception:
        pass
    try:
        PRINTER_PID.unlink(missing_ok=True)
    except Exception:
        pass
    try:
        SERVICE_LOCK.unlink(missing_ok=True)
    except Exception:
        pass
    try:
        MPPS_LOCK.unlink(missing_ok=True)
    except Exception:
        pass
    try:
        PRINTER_LOCK.unlink(missing_ok=True)
    except Exception:
        pass
    try:
        SERVICE_STATE.unlink(missing_ok=True)
    except Exception:
        pass
    try:
        MPPS_STATE.unlink(missing_ok=True)
    except Exception:
        pass
    try:
        PRINTER_STATE.unlink(missing_ok=True)
    except Exception:
        pass
    lock_file = ROOT / "mwl_server.lock"
    try:
        lock_file.unlink(missing_ok=True)
    except Exception:
        pass
    mpps_lock = ROOT / "mpps_server.lock"
    try:
        mpps_lock.unlink(missing_ok=True)
    except Exception:
        pass
    ok = len(errors) == 0
    return {"ok": ok, "killed": killed, "errors": errors}


def _collect_other_instance_pids() -> dict:
    """Collect PIDs for app/service processes that belong to other instances.

    Returns a dict: { 'app': [pids], 'service': [pids], 'mpps': [pids] }
    """
    current_id = INSTANCE_ID.lower()
    root_str = str(ROOT).lower().replace('\\', '/')

    def is_other_instance(cmd: str) -> bool:
        c = cmd.lower().replace('\\', '/')
        if '--instance-id' in c:
            parts = c.split()
            for i, tok in enumerate(parts):
                if tok == '--instance-id' and i + 1 < len(parts):
                    if parts[i + 1].lower() != current_id:
                        return True
                    return False
            # '--instance-id' but couldn't read next token, treat as other
            return True
        # No instance-id: if command line doesn't include our repo root, consider it other
        return root_str not in c

    pids = {'app': [], 'service': [], 'mpps': []}
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline_list = proc.info.get('cmdline') or []
                cmd = ' '.join(cmdline_list)
                cl = cmd.lower()
                if 'python' not in cl:
                    continue
                if 'webui/app.py' in cl or 'app.py' in cl:
                    if is_other_instance(cmd):
                        pids['app'].append(proc.info['pid'])
                elif 'mwl_service.py' in cl:
                    if is_other_instance(cmd):
                        pids['service'].append(proc.info['pid'])
                elif 'mpps_service.py' in cl:
                    if is_other_instance(cmd):
                        pids['mpps'].append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass
    return pids


def kill_other_instances(target: str = 'both'):
    """Kill processes (app/service) that belong to other instance-ids.

    target: 'app' | 'service' | 'both'
    Returns dict with ok, killed, errors grouped by kind.
    """
    target = (target or 'both').lower()
    pids = _collect_other_instance_pids()
    to_kill = {
        'app': pids['app'] if target in ('app', 'both') else [],
        'service': pids['service'] if target in ('service', 'both') else [],
        'mpps': pids['mpps'] if target in ('service', 'both') else [],
    }
    killed = {'app': [], 'service': [], 'mpps': []}
    errors = []
    for kind in ('app', 'service', 'mpps'):
        for pid in to_kill[kind]:
            try:
                if os.name == 'nt':
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], check=False,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                else:
                    os.kill(pid, 9)
                killed[kind].append(pid)
            except Exception as e:
                errors.append(f"{kind}:{pid}: {e}")
    return {"ok": len(errors) == 0, "killed": killed, "errors": errors, "instance_id": INSTANCE_ID}


def logs(limit: int = 20):
    """List recent log files from both service_logs and logs directories."""
    # Service logs
    service_files = sorted(SERVICE_LOG_DIR.glob('*.log'), key=lambda p: p.stat().st_mtime, reverse=True)
    service_logs = []
    for p in service_files[:limit]:
        service_logs.append({
            "name": p.name, 
            "path": str(p), 
            "size": p.stat().st_size, 
            "mtime": p.stat().st_mtime,
            "type": "service"
        })
    
    # App logs (from logs/ directory)
    app_log_dir = ROOT / "logs"
    app_logs = []
    if app_log_dir.exists():
        app_files = sorted(app_log_dir.glob('*.log'), key=lambda p: p.stat().st_mtime, reverse=True)
        for p in app_files[:limit]:
            app_logs.append({
                "name": p.name,
                "path": str(p),
                "size": p.stat().st_size,
                "mtime": p.stat().st_mtime,
                "type": "app"
            })
    
    return {"service": service_logs, "app": app_logs}


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
    print("  flow start all                   - Start App and Service")
    print("  flow start app                   - Start management App")
    print("  flow start service [--config p]  - Start DICOM MWL service")
    print("  flow stop all                    - Stop App and Service")
    print("  flow stop app|service            - Stop targets")
    print("  flow restart all|app|service [--config p] - Restart targets")
    print("  flow status                      - Show status of App and Service")
    print("  flow logs [--limit N]            - List N most recent logs")
    print("  flow tail <path> [--lines N]     - Tail log file")
    print("  flow install [--add-to-path]     - Generate wrappers")
    print("  flow uninstall                   - Remove generated wrappers")


def uninstall():
    """Remove local wrappers created by install()."""
    removed = []
    for fname in ["flow.bat", "flow.ps1"]:
        p = ROOT / fname
        if p.exists():
            try:
                p.unlink()
                removed.append(fname)
            except Exception as e:
                print(f"Failed to remove {fname}: {e}")
    if removed:
        print(f"Removed: {', '.join(removed)}")
    else:
        print("No wrappers to remove.")


def print_status():
    """Print status in a user-friendly format."""
    st = status()
    
    print("\n" + "="*60)
    print("FlowWorklist Status")
    print("="*60)
    
    # App status
    app = st.get('app', {})
    print("\n📱 Management App (Web UI)")
    print("-" * 60)
    if app.get('running'):
        print(f"  Status:     ✓ Running")
        print(f"  PID:        {app.get('pid')}")
        print(f"  URL:        {app.get('url', 'http://127.0.0.1:5000')}")
        if app.get('timestamp'):
            print(f"  Started:    {app.get('timestamp')}")
    else:
        print(f"  Status:     ✗ Stopped")
    
    # Service status
    service = st.get('service', {})
    print("\n🔧 MWL Service (DICOM Worklist)")
    print("-" * 60)
    if service.get('running'):
        print(f"  Status:     ✓ Running")
        print(f"  PID:        {service.get('pid')}")
        if service.get('timestamp'):
            print(f"  Started:    {service.get('timestamp')}")
        if service.get('log'):
            print(f"  Log:        {service.get('log')}")
    else:
        print(f"  Status:     ✗ Stopped")

    # MPPS status
    mpps = st.get('mpps', {})
    print("\n🧾 MPPS Service")
    print("-" * 60)
    if mpps.get('running'):
        print(f"  Status:     ✓ Running")
        print(f"  PID:        {mpps.get('pid')}")
        if mpps.get('timestamp'):
            print(f"  Started:    {mpps.get('timestamp')}")
        if mpps.get('log'):
            print(f"  Log:        {mpps.get('log')}")
    else:
        print(f"  Status:     ✗ Stopped")
    
    print("\n" + "="*60)
    
    # Return the raw status for programmatic use
    return st


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="flow", description="FlowWorklist command line helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # New grouped commands (e.g., flow start all)
    p_start = sub.add_parser("start")
    p_start.add_argument("target", choices=["all", "app", "service"], help="What to start")
    p_start.add_argument("--config", default=None, help="Path to MWL config file (service only)")

    p_stop = sub.add_parser("stop")
    p_stop.add_argument("target", choices=["all", "app", "service"], help="What to stop")

    p_restart = sub.add_parser("restart")
    p_restart.add_argument("target", choices=["all", "app", "service"], help="What to restart")
    p_restart.add_argument("--config", default=None, help="Path to MWL config file (service only)")

    # Backward-compatible commands
    sub.add_parser("start app")
    sub.add_parser("stop app")
    sub.add_parser("start all")
    sub.add_parser("stop all")

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

    sub.add_parser("uninstall")

    args = parser.parse_args()

    # New grouped commands
    if args.cmd == "start":
        if args.target == "all":
            startall()
        elif args.target == "app":
            startapp()
        elif args.target == "service":
            res = startservice(config_path=args.config)
            if res is not None:
                print(res)
    elif args.cmd == "stop":
        if args.target == "all":
            stopall()
        elif args.target == "app":
            stopapp()
        elif args.target == "service":
            res = stopservice()
            if res is not None:
                print(res)
    elif args.cmd == "restart":
        if args.target == "all":
            stopall(); time.sleep(1); startall()
        elif args.target == "app":
            stopapp(); time.sleep(1); startapp()
        elif args.target == "service":
            res = restartservice(config_path=args.config)
            if res is not None:
                print(res)

    # Legacy commands remain supported
    elif args.cmd == "start app":
        startapp()
    elif args.cmd == "stop app":
        stopapp()
    elif args.cmd == "start all":
        startall()
    elif args.cmd == "stop all":
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
        print_status()
    elif args.cmd == "logs":
        print(logs(limit=args.limit))
    elif args.cmd == "tail":
        print(tail(args.log, lines=args.lines))
    elif args.cmd == "install":
        install(add_to_path=args.add_to_path)
    elif args.cmd == "uninstall":
        uninstall()
