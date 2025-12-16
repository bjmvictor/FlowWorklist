import os
import sys
import json
import subprocess
import datetime
from pathlib import Path

ROOT = Path(__file__).parent
PID_FILE = ROOT / "service.pid"
STATE_FILE = ROOT / "service_state.json"
LOG_DIR = ROOT / "service_logs"
CONFIG_FILE = ROOT / "service_config.json"

LOG_DIR.mkdir(exist_ok=True)

def _log_path():
    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    return LOG_DIR / f"mwls_{ts}.log"

def start_service(config_path: str = None):
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
        if is_running(pid):
            return {"ok": False, "msg": f"Service already running (pid={pid})"}
        else:
            # PID file obsoleto, remover
            try:
                PID_FILE.unlink(missing_ok=True)
            except Exception:
                pass
    
    # Limpar lock file obsoleto do MWLSCP se existir
    lock_file = ROOT / "mwl_server.lock"
    if lock_file.exists():
        try:
            with open(lock_file, "r") as f:
                old_pid = f.read().strip()
            if old_pid and is_running(int(old_pid)):
                return {"ok": False, "msg": f"Service already running (lock pid={old_pid})"}
            else:
                # Lock file obsoleto, remover
                lock_file.unlink(missing_ok=True)
        except Exception:
            try:
                lock_file.unlink(missing_ok=True)
            except:
                pass
    
    # Prefer pythonw.exe (no console) on Windows, else fall back to python
    python_path = None
    if os.name == 'nt':
        venv_pythonw = ROOT / "Scripts" / "pythonw.exe"
        venv_python = ROOT / "Scripts" / "python.exe"
        if venv_pythonw.exists():
            python_path = str(venv_pythonw)
        elif venv_python.exists():
            python_path = str(venv_python)
        else:
            python_path = sys.executable
    else:
        venv_python = ROOT / "Scripts" / "python"
        python_path = str(venv_python) if venv_python.exists() else sys.executable
    
    script = ROOT / "MWLSCP.py"
    if not script.exists():
        return {"ok": False, "msg": "MWLSCP.py not found in project root"}

    logp = _log_path()
    # Open log file for append and start process
    out = open(logp, "ab")
    args = [python_path, str(script)]
    if config_path:
        args += ["--config", config_path]
    # Start detached process on Windows using creationflags
    creationflags = 0
    startupinfo = None
    if os.name == 'nt':
        # CREATE_NO_WINDOW | DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        creationflags = 0x08000000 | 0x00000008 | 0x00000200
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE
    p = subprocess.Popen(
        args,
        stdout=out,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
        startupinfo=startupinfo
    )
    PID_FILE.write_text(str(p.pid))
    state = {"pid": p.pid, "log": str(logp), "started_at": datetime.datetime.now().isoformat()}
    STATE_FILE.write_text(json.dumps(state))
    return {"ok": True, "pid": p.pid, "log": str(logp)}

def stop_service():
    if not PID_FILE.exists():
        return {"ok": False, "msg": "No PID file; service not running?"}
    pid = int(PID_FILE.read_text().strip())
    if not is_running(pid):
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        # Limpar lock file do MWLSCP mesmo se o processo não está rodando
        lock_file = ROOT / "mwl_server.lock"
        try:
            if lock_file.exists():
                lock_file.unlink(missing_ok=True)
        except Exception:
            pass
        return {"ok": False, "msg": f"Process {pid} not running"}
    try:
        if os.name == 'nt':
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            os.kill(pid, 15)
        # Aguardar um pouco para garantir que o processo foi finalizado
        import time
        time.sleep(0.5)
        
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        
        # Limpar lock file do MWLSCP
        lock_file = ROOT / "mwl_server.lock"
        try:
            if lock_file.exists():
                lock_file.unlink(missing_ok=True)
        except Exception:
            pass
        
        return {"ok": True, "msg": f"Stopped {pid}"}
    except Exception as e:
        return {"ok": False, "msg": str(e)}

def restart_service(config_path: str = None):
    stop_service()
    return start_service(config_path=config_path)

def is_running(pid: int) -> bool:
    try:
        if os.name == 'nt':
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return str(pid) in out.stdout
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False

def status():
    if not PID_FILE.exists():
        return {"running": False}
    pid = int(PID_FILE.read_text().strip())
    running = is_running(pid)
    state = {"running": running, "pid": pid}
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text())
            state.update(data)
        except Exception:
            pass
    return state

def list_logs(limit=20):
    files = sorted(LOG_DIR.glob('*.log'), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for p in files[:limit]:
        out.append({"name": p.name, "path": str(p), "size": p.stat().st_size, "mtime": p.stat().st_mtime})
    return out

def tail_log(path: str, lines: int = 200):
    p = Path(path)
    if not p.exists():
        return ""
    # Read last N lines efficiently
    with p.open('rb') as f:
        try:
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
        except Exception:
            f.seek(0)
            return f.read().decode(errors='replace')

def read_config():
    if not CONFIG_FILE.exists():
        default = {
            "oracle_dsn": "",
            "oracle_user": "",
            "oracle_password": "",
            "poll_interval_seconds": 30
        }
        CONFIG_FILE.write_text(json.dumps(default, indent=2))
        return default
    try:
        return json.loads(CONFIG_FILE.read_text())
    except Exception:
        return {}

def write_config(data: dict):
    CONFIG_FILE.write_text(json.dumps(data, indent=2))
    return True

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start','stop','restart','status','logs','tail','config'])
    parser.add_argument('--config', help='Path to config file', default=None)
    parser.add_argument('--log', help='Log path for tail', default=None)
    args = parser.parse_args()
    if args.action == 'start':
        print(start_service(config_path=args.config))
    elif args.action == 'stop':
        print(stop_service())
    elif args.action == 'restart':
        print(restart_service(config_path=args.config))
    elif args.action == 'status':
        print(status())
    elif args.action == 'logs':
        print(list_logs())
    elif args.action == 'tail':
        if args.log:
            print(tail_log(args.log))
        else:
            print('no log specified')
    elif args.action == 'config':
        print(read_config())
