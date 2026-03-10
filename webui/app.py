from flask import Flask, render_template, redirect, url_for, request, jsonify
import shutil
from pathlib import Path
import subprocess
import sys
from pathlib import Path
import subprocess
import socket
import sys
import json
import os
import time
import importlib.util
import logging
from datetime import datetime

# Workaround for broken NumPy builds on some Windows/Python setups.
# pydicom is used in tests and can run without NumPy for these flows.
if os.environ.get('FLOWWORKLIST_DISABLE_NUMPY', '1') == '1':
    sys.modules.setdefault('numpy', None)

# Ensure project root on sys.path before importing local modules
ROOT = Path(__file__).parent.parent  # Parent of webui/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flow as manager

app = Flask(__name__, template_folder='templates', static_folder='static')

# Ensure project root is on sys.path so service_manager and other modules resolve
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ensure venv site-packages is in sys.path for proper module imports
_lib_path = ROOT / 'Lib' / 'site-packages'
if _lib_path.exists() and str(_lib_path) not in sys.path:
    sys.path.insert(0, str(_lib_path))

# Application logging (app logs)
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_file), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
app_logger = logging.getLogger('flowworklist.app')
DCMTK_MANUAL_URL = "https://dicom.offis.de/en/dcmtk/dcmtk-tools/"

def log_action(action, details="", user_ip=None):
    """Log user actions in the application."""
    try:
        if user_ip is None:
            user_ip = request.remote_addr if request else "system"
    except RuntimeError:
        # Outside request context
        user_ip = "system"
    app_logger.info(f"[{user_ip}] {action} | {details}")


def _to_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def _to_int(value, default):
    try:
        return int(value)
    except Exception:
        return default


def _to_float(value, default):
    try:
        return float(value)
    except Exception:
        return default


def default_printer_config():
    base = ROOT / "dicom-printer"
    return {
        "enabled": False,
        "receiver": {
            "aet": "VPRINTSCP",
            "profile": "FLOWWORKLIST_PRINTER",
            "port": 4100,
            "target_host": "127.0.0.1",
            "dcmtk_bin": r"C:\dcmtk\bin",
        },
        "worker": {
            "database_dir": str(base / "database"),
            "spool_dir": str(base / "spool"),
            "out_dir": str(base / "out"),
            "sumatra_path": r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
            "printer_name": "",
            "paper_size": "A3",
            "print_settings": "fit",
            "delete_after_success": False,
            "sp_time_window_seconds": 120,
            "poll_interval_seconds": 1.0,
        },
    }


def merge_printer_config(cfg):
    base = default_printer_config()
    incoming = cfg if isinstance(cfg, dict) else {}
    receiver = incoming.get("receiver", {}) if isinstance(incoming.get("receiver"), dict) else {}
    worker = incoming.get("worker", {}) if isinstance(incoming.get("worker"), dict) else {}

    base["enabled"] = _to_bool(incoming.get("enabled"), base["enabled"])
    base["receiver"].update(receiver)
    base["worker"].update(worker)
    return base


def _load_module_from_venv(module_name):
    """Load a module from venv site-packages, ensuring it comes from the right location."""
    _lib_path = ROOT / 'Lib' / 'site-packages'
    module_path = _lib_path / (module_name + '.py')
    
    # For packages, look for __init__.py
    if not module_path.exists():
        module_path = _lib_path / module_name / '__init__.py'
    
    if module_path.exists():
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    
    # Fallback to normal import
    return __import__(module_name)


def _venv_python_and_pip():
    """Return venv python and pip executables if available."""
    scripts = ROOT / 'Scripts'
    py = scripts / 'python.exe'
    pip = scripts / 'pip.exe'
    py_path = str(py if py.exists() else sys.executable)
    pip_path = str(pip if pip.exists() else (shutil.which('pip') or pip))
    return py_path, pip_path


def install_db_driver(db_type: str):
    pkg_map = {
        'oracle': ['cx_Oracle'],
        'postgres': ['psycopg2-binary'],
        'postgresql': ['psycopg2-binary'],
        'mysql': ['PyMySQL'],
        'pynetdicom': ['pynetdicom'],
    }
    packages = pkg_map.get((db_type or '').lower())
    if not packages:
        return False, f"Unknown DB type: {db_type}"
    _py, pip_exe = _venv_python_and_pip()
    try:
        for pkg in packages:
            subprocess.run([pip_exe, 'install', pkg], check=True)
        return True, f"Installed: {', '.join(packages)}"
    except subprocess.CalledProcessError as e:
        return False, f"Install failed: {e}"


def is_db_plugin_installed(db_type: str) -> bool:
    """Check plugin installed using pip show for reliability (handles loaded modules cache)."""
    dt = (db_type or '').lower()
    pkg_map = {
        'oracle': 'cx_Oracle',
        'postgres': 'psycopg2-binary',
        'postgresql': 'psycopg2-binary',
        'mysql': 'PyMySQL',
    }
    pkg = pkg_map.get(dt)
    if not pkg:
        return False
    _py, pip_exe = _venv_python_and_pip()
    try:
        res = subprocess.run([pip_exe, 'show', pkg], capture_output=True, text=True)
        return res.returncode == 0 and bool(res.stdout.strip())
    except Exception:
        return False


def plugins_status():
    plugins = [
        {'id': 'oracle', 'label': 'Oracle (cx_Oracle)', 'module': 'cx_Oracle', 'package': 'cx_Oracle'},
        {'id': 'postgres', 'label': 'PostgreSQL (psycopg2)', 'module': 'psycopg2', 'package': 'psycopg2-binary'},
        {'id': 'mysql', 'label': 'MySQL (PyMySQL)', 'module': 'pymysql', 'package': 'PyMySQL'},
        {'id': 'pynetdicom', 'label': 'DICOM Worklist Support (pynetdicom)', 'module': 'pynetdicom', 'package': 'pynetdicom'},
        {'id': 'dcmtk', 'label': 'DCMTK (System Tool)', 'module': 'dcmprscp/dcm2img', 'package': 'DCMTK.DCMTK', 'source': 'system'},
        {'id': 'sumatra', 'label': 'SumatraPDF (System Tool)', 'module': 'SumatraPDF.exe', 'package': 'SumatraPDF.SumatraPDF', 'source': 'system'},
    ]
    _py, pip_exe = _venv_python_and_pip()
    for p in plugins:
        if p.get('source') == 'system':
            p['installed'] = is_system_tool_installed(p['id'])
            continue
        try:
            res = subprocess.run([pip_exe, 'show', p['package']], capture_output=True, text=True)
            p['installed'] = (res.returncode == 0 and bool(res.stdout.strip()))
        except Exception:
            p['installed'] = False
    # Current configured type
    cfg_path = ROOT / "config.json"
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    db_type = (cfg.get('database', {}).get('type') or '').lower()
    return plugins, db_type


def is_system_tool_installed(tool_name: str) -> bool:
    name = (tool_name or '').strip().lower()
    if os.name != 'nt':
        return False

    if name in ('sumatra', 'sumatrapdf'):
        return detect_sumatra_path() is not None

    # Fast path by common installation locations
    if name == 'dcmtk':
        known = [
            Path(r"C:\dcmtk\bin\dcmprscp.exe"),
            Path(r"C:\Program Files\dcmtk\bin\dcmprscp.exe"),
            Path(r"C:\Program Files\DCMTK\bin\dcmprscp.exe"),
        ]
        if any(p.exists() for p in known):
            return True

    # Fallback to winget list
    winget_ids = {
        'dcmtk': ['DCMTK.DCMTK', 'OFFIS.DCMTK'],
        'sumatra': ['SumatraPDF.SumatraPDF'],
        'sumatrapdf': ['SumatraPDF.SumatraPDF'],
    }.get(name)
    if not winget_ids:
        return False
    for winget_id in winget_ids:
        try:
            res = subprocess.run(
                ['winget', 'list', '--id', winget_id, '--exact', '--accept-source-agreements'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60
            )
            out = ((res.stdout or '') + '\n' + (res.stderr or '')).lower()
            if (res.returncode == 0 and winget_id.lower() in out) or ('no installed package found' not in out and 'not installed' not in out and winget_id.lower() in out):
                return True
        except Exception:
            continue
    return False


def detect_sumatra_path() -> str | None:
    """Return detected SumatraPDF executable path, if available."""
    candidates = [
        Path(r"C:\Program Files\SumatraPDF\SumatraPDF.exe"),
        Path(r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe"),
        Path.home() / "AppData" / "Local" / "SumatraPDF" / "SumatraPDF.exe",
        ROOT / "SumatraPDF" / "SumatraPDF.exe",
    ]

    # Prefer configured path when valid
    try:
        cfg_path = ROOT / "config.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text())
            configured = (cfg.get('dicom_printer') or {}).get('worker', {}).get('sumatra_path')
            if configured:
                p = Path(str(configured))
                if p.exists():
                    return str(p)
    except Exception:
        pass

    for p in candidates:
        try:
            if p.exists():
                return str(p)
        except Exception:
            pass

    try:
        found = shutil.which('SumatraPDF.exe')
        if found:
            return str(Path(found))
    except Exception:
        pass
    return None


def _discover_winget_ids(query: str) -> list:
    """Best-effort discovery of winget package IDs from `winget search` output."""
    if os.name != 'nt':
        return []
    import re
    try:
        res = subprocess.run(
            ['winget', 'search', '--query', query, '--source', 'winget', '--accept-source-agreements'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=90
        )
        text = (res.stdout or '') + '\n' + (res.stderr or '')
        candidates = []
        seen = set()
        for m in re.finditer(r'\b([A-Za-z0-9][A-Za-z0-9_.-]*\.[A-Za-z0-9_.-]+)\b', text):
            pkg_id = m.group(1)
            key = pkg_id.lower()
            if key not in seen:
                seen.add(key)
                candidates.append(pkg_id)
        return candidates
    except Exception:
        return []


def install_system_tool(tool_name: str):
    name = (tool_name or '').strip().lower()
    if os.name != 'nt':
        return False, 'Automatic tool install is only supported on Windows'

    tools = {
        'dcmtk': {'ids': ['DCMTK.DCMTK', 'OFFIS.DCMTK'], 'label': 'DCMTK'},
        'sumatra': {'ids': ['SumatraPDF.SumatraPDF'], 'label': 'SumatraPDF'},
        'sumatrapdf': {'ids': ['SumatraPDF.SumatraPDF'], 'label': 'SumatraPDF'},
    }
    tool = tools.get(name)
    if not tool:
        return False, f'Unknown tool: {tool_name}'

    def _compact_reason(text: str) -> str:
        if not text:
            return ""
        lines = [ln.strip() for ln in text.splitlines() if ln and ln.strip()]
        skip_tokens = ("name ", "id ", "version ", "source ", "-----", "found ", "installing ")
        useful = []
        for ln in lines:
            low = ln.lower()
            if any(tok in low for tok in skip_tokens):
                continue
            useful.append(ln)
        if not useful:
            useful = lines
        reason = " | ".join(useful[:3]).strip()
        return reason[:260]

    last_code = None
    last_reason = ""
    candidate_ids = list(tool['ids'])
    if name == 'dcmtk':
        for discovered in _discover_winget_ids('dcmtk'):
            if discovered.lower() not in [x.lower() for x in candidate_ids]:
                candidate_ids.append(discovered)

    for winget_id in candidate_ids:
        cmd = [
            'winget',
            'install',
            '--id', winget_id,
            '--exact',
            '--source', 'winget',
            '--disable-interactivity',
            '--silent',
            '--accept-package-agreements',
            '--accept-source-agreements',
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900)
            output = ((res.stdout or '') + '\n' + (res.stderr or '')).lower()
            last_code = res.returncode
            if res.returncode == 0:
                return True, f"{tool['label']} installed successfully via winget"
            if 'already installed' in output or 'no applicable update found' in output:
                return True, f"{tool['label']} is already installed"
            if 'no package found' in output or 'no package matched' in output or 'no package found matching input criteria' in output:
                last_reason = _compact_reason(output)
                continue
            last_reason = _compact_reason(output)
            # Unknown failure with this id: keep trying next id if any
        except FileNotFoundError:
            return False, 'winget not found. Install App Installer from Microsoft Store'
        except subprocess.TimeoutExpired:
            return False, f"Timeout installing {tool['label']} via winget"
        except Exception as e:
            return False, f"Install error for {tool['label']}: {e}"

    try:
        if is_system_tool_installed(name):
            return True, f"{tool['label']} is already installed"
    except Exception:
        pass
    if name == 'dcmtk' and (last_code == 2316632084 or 'nenhum pacote encontrou os critérios de entrada correspondentes' in (last_reason or '').lower()):
        return False, "Failed to install DCMTK: package not found in winget source on this machine. Update sources (`winget source update`) or install DCMTK manually."
    reason_txt = f" Reason: {last_reason}" if last_reason else ""
    return False, f"Failed to install {tool['label']} (winget code {last_code}).{reason_txt}"


def uninstall_system_tool(tool_name: str):
    name = (tool_name or '').strip().lower()
    if os.name != 'nt':
        return False, 'Automatic tool uninstall is only supported on Windows'

    tools = {
        'dcmtk': {'ids': ['DCMTK.DCMTK', 'OFFIS.DCMTK'], 'label': 'DCMTK'},
        'sumatra': {'ids': ['SumatraPDF.SumatraPDF'], 'label': 'SumatraPDF'},
        'sumatrapdf': {'ids': ['SumatraPDF.SumatraPDF'], 'label': 'SumatraPDF'},
    }
    tool = tools.get(name)
    if not tool:
        return False, f'Unknown tool: {tool_name}'

    def _compact_reason(text: str) -> str:
        if not text:
            return ""
        lines = [ln.strip() for ln in text.splitlines() if ln and ln.strip()]
        skip_tokens = ("name ", "id ", "version ", "source ", "-----", "found ", "uninstalling ")
        useful = []
        for ln in lines:
            low = ln.lower()
            if any(tok in low for tok in skip_tokens):
                continue
            useful.append(ln)
        if not useful:
            useful = lines
        reason = " | ".join(useful[:3]).strip()
        return reason[:260]

    last_code = None
    last_reason = ""
    found_any = False
    for winget_id in tool['ids']:
        try:
            check = subprocess.run(
                ['winget', 'list', '--id', winget_id, '--exact', '--accept-source-agreements'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60
            )
            check_out = ((check.stdout or '') + '\n' + (check.stderr or '')).lower()
            if winget_id.lower() not in check_out:
                continue
            found_any = True

            cmd = [
                'winget',
                'uninstall',
                '--id', winget_id,
                '--exact',
                '--silent',
                '--accept-source-agreements',
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900)
            out = ((res.stdout or '') + '\n' + (res.stderr or '')).lower()
            last_code = res.returncode
            if res.returncode == 0:
                return True, f"{tool['label']} uninstalled successfully via winget"
            if 'no installed package found' in out or 'not installed' in out:
                last_reason = _compact_reason(out)
                continue
            last_reason = _compact_reason(out)
        except FileNotFoundError:
            return False, 'winget not found. Install App Installer from Microsoft Store'
        except subprocess.TimeoutExpired:
            return False, f"Timeout uninstalling {tool['label']} via winget"
        except Exception as e:
            return False, f"Uninstall error for {tool['label']}: {e}"

    if not found_any:
        if not is_system_tool_installed(name):
            return True, f"{tool['label']} is already uninstalled"
    reason_txt = f" Reason: {last_reason}" if last_reason else ""
    return False, f"Failed to uninstall {tool['label']} (winget code {last_code}).{reason_txt}"


@app.route('/')
def index():
    st = manager.status()
    # Don't wait for logs on initial page load - load them async
    # logs = manager.logs(limit=10)
    # Pass only service status to template to match expected keys
    service_status = (st.get('service') or {})
    return render_template('index.html', status=service_status, logs=[])


def _validate_config():
    """Validate config.json exists and has basic structure."""
    cfg_path = ROOT / "config.json"
    if not cfg_path.exists():
        return False, "Configuration file (config.json) not found"
    
    try:
        cfg = json.loads(cfg_path.read_text())
        if not isinstance(cfg, dict):
            return False, "Configuration must be a JSON object"
        
        # Check for critical sections
        if not cfg.get("server") and not cfg.get("database"):
            return False, "Configuration is incomplete (missing server and database sections)"

        # Detect unresolved placeholders that would break startup/runtime tests
        placeholder_tokens = ["<DB_HOST>", "<DB_USER>", "<DB_PASSWORD>", "<DB_NAME>", "<DB_DSN>"]
        text = json.dumps(cfg)
        if any(tok in text for tok in placeholder_tokens):
            return False, "Configuration contains placeholders (e.g., <DB_HOST>, <DB_USER>, <DB_PASSWORD>). Replace them with real values"
        
        return True, "Configuration valid"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in config.json: {e.msg} (line {e.lineno})"
    except Exception as e:
        return False, f"Error reading config: {str(e)}"


@app.route('/action/<cmd>', methods=['POST'])
def action(cmd):
    log_action(f"Service action: {cmd}", f"User requested {cmd} service")
    cfg = str(ROOT / "config.json")
    
    # Validate config before attempting to start
    if cmd in ['start', 'restart']:
        valid, msg = _validate_config()
        if not valid:
            log_action(f"Service {cmd} failed", f"Config validation error: {msg}")
            return jsonify({
                'ok': False,
                'msg': f"Configuration Error: {msg}. Please check config.json",
                'error_type': 'config_error',
                'error_detail': msg
            }), 400
    
    try:
        if cmd == 'start':
            r = manager.startservice(config_path=cfg)
            log_action("Service started", f"Result: {r.get('ok', False)}")
        elif cmd == 'stop':
            r = manager.stopservice()
            log_action("Service stopped", f"Result: {r.get('ok', False)}")
        elif cmd == 'restart':
            r = manager.restartservice(config_path=cfg)
            log_action("Service restarted", f"Result: {r.get('ok', False)}")
        else:
            r = {"ok": False, "msg": 'unknown command', "error_type": "unknown_command"}
        
        # Ensure response always has error_type and error_detail for better debugging
        if not r.get('ok'):
            if 'error_type' not in r:
                r['error_type'] = 'execution_error'
            if 'error_detail' not in r and 'msg' in r:
                r['error_detail'] = r['msg']
        
        return jsonify(r)
    
    except Exception as e:
        # Catch any unexpected errors
        error_msg = str(e)
        return jsonify({
            'ok': False,
            'msg': f'Unexpected error: {error_msg}',
            'error_type': 'server_error',
            'error_detail': error_msg
        }), 500


@app.route('/status')
def status():
    # Provide backward-compatible, simplified status payload with detailed info
    st = manager.status()
    svc = st.get('service') or {}
    app_status = st.get('app') or {}
    return jsonify({
        'running': bool(svc.get('running')),
        'pid': svc.get('pid'),
        'timestamp': svc.get('timestamp'),
        'log': svc.get('log'),
        'instance_id': svc.get('instance_id') or app_status.get('instance_id'),
        'service': svc,
        'app': app_status,
        'message': 'Service is running' if svc.get('running') else 'Service is stopped'
    })


@app.route('/api/logs')
def get_logs_api():
    """Get recent logs as JSON for async loading"""
    try:
        limit = request.args.get('limit', default=10, type=int)
        logs_data = manager.logs(limit=limit)
        # Combine both service and app logs for homepage display
        all_logs = logs_data.get('service', []) + logs_data.get('app', [])
        # Sort by mtime (most recent first)
        all_logs.sort(key=lambda x: x.get('mtime', 0), reverse=True)
        return jsonify({'logs': all_logs[:limit]})
    except Exception as e:
        return jsonify({'logs': [], 'error': str(e)}), 500


@app.route('/logs')
def logs():
    logs_data = manager.logs(limit=50)
    notice = request.args.get('notice')
    status = request.args.get('status')
    return render_template('logs.html', logs=logs_data, notice=notice, status=status)


@app.route('/logs/view')
def view_log():
    path = request.args.get('path')
    lines = int(request.args.get('lines', 500))
    if not path:
        return 'no log specified', 400
    content = manager.tail(path, lines=lines)
    return render_template('view_log.html', content=content, path=path)


@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        log_action("Config update", "User updated configuration file")
        # Read current config file to preserve structure
        cfg_path = ROOT / "config.json"
        if cfg_path.exists():
            try:
                config_data = json.loads(cfg_path.read_text())
            except:
                config_data = {"server": {}, "database": {}}
        else:
            config_data = {"server": {}, "database": {}}
        
        # Update server section
        config_data["server"]["aet"] = request.form.get('server_aet', 'MWLSCP')
        config_data["server"]["host"] = request.form.get('server_host', '0.0.0.0')
        config_data["server"]["port"] = int(request.form.get('server_port', 11112))
        config_data["server"]["client_aet"] = request.form.get('server_client_aet', 'Prima')
        
        # Update database section
        config_data["database"]["type"] = request.form.get('database_type', 'oracle')
        config_data["database"]["user"] = request.form.get('database_user', '')
        config_data["database"]["password"] = request.form.get('database_password', '')
        config_data["database"]["dsn"] = request.form.get('database_dsn', '')
        config_data["database"]["query"] = request.form.get('database_query', '')
        
        # Remove column_mapping if present (moved to code)
        if "column_mapping" in config_data.get("database", {}):
            del config_data["database"]["column_mapping"]
        
        # Save to config.json
        try:
            cfg_path.write_text(json.dumps(config_data, indent=2))
            log_action("Config saved", f"Successfully saved configuration: server={config_data.get('server', {}).get('aet')}, db_type={config_data.get('database', {}).get('type')}")
            return redirect(url_for('config', notice='config_saved', status='success'))
        except Exception as e:
            log_action("Config save failed", f"Error: {str(e)}")
            return redirect(url_for('config', notice=f'config_save_error: {str(e)}', status='error'))
    else:
        # Read config.json
        cfg_path = ROOT / "config.json"
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text())
            except:
                cfg = {"server": {}, "database": {}}
        else:
            cfg = {"server": {}, "database": {}}
        
        # Get notification parameters
        notice = request.args.get('notice')
        status = request.args.get('status')
        return render_template('config.html', cfg=cfg, notice=notice, status=status)


@app.route('/printer-config', methods=['GET', 'POST'])
def printer_config():
    cfg_path = ROOT / "config.json"

    if request.method == 'POST':
        log_action("Virtual printer config update", "User updated virtual DICOM printer configuration")
        if cfg_path.exists():
            try:
                config_data = json.loads(cfg_path.read_text())
            except Exception:
                config_data = {"server": {}, "database": {}}
        else:
            config_data = {"server": {}, "database": {}}

        config_data["dicom_printer"] = {
            "enabled": bool(request.form.get("enabled")),
            "receiver": {
                "aet": request.form.get("receiver_aet", "VPRINTSCP").strip() or "VPRINTSCP",
                "profile": request.form.get("receiver_profile", "FLOWWORKLIST_PRINTER").strip() or "FLOWWORKLIST_PRINTER",
                "port": _to_int(request.form.get("receiver_port"), 4100),
                "target_host": request.form.get("receiver_target_host", "127.0.0.1").strip() or "127.0.0.1",
                "dcmtk_bin": request.form.get("receiver_dcmtk_bin", r"C:\dcmtk\bin").strip() or r"C:\dcmtk\bin",
            },
            "worker": {
                "database_dir": request.form.get("worker_database_dir", str(ROOT / "dicom-printer" / "database")).strip(),
                "spool_dir": request.form.get("worker_spool_dir", str(ROOT / "dicom-printer" / "spool")).strip(),
                "out_dir": request.form.get("worker_out_dir", str(ROOT / "dicom-printer" / "out")).strip(),
                "sumatra_path": request.form.get("worker_sumatra_path", r"C:\Program Files\SumatraPDF\SumatraPDF.exe").strip() or r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
                "printer_name": request.form.get("worker_printer_name", "").strip(),
                "paper_size": request.form.get("worker_paper_size", "A3").strip().upper() or "A3",
                "print_settings": request.form.get("worker_print_settings", "fit").strip() or "fit",
                "delete_after_success": bool(request.form.get("worker_delete_after_success")),
                "sp_time_window_seconds": _to_int(request.form.get("worker_sp_time_window_seconds"), 120),
                "poll_interval_seconds": _to_float(request.form.get("worker_poll_interval_seconds"), 1.0),
            },
        }

        try:
            cfg_path.write_text(json.dumps(config_data, indent=2))
            log_action("Virtual printer config saved", "Virtual DICOM printer settings saved successfully")
            return redirect(url_for('printer_config', notice='config_saved', status='success'))
        except Exception as e:
            log_action("Virtual printer config save failed", str(e))
            return redirect(url_for('printer_config', notice=f'config_save_error: {str(e)}', status='error'))

    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
        except Exception:
            cfg = {"server": {}, "database": {}}
    else:
        cfg = {"server": {}, "database": {}}

    printer_cfg = merge_printer_config(cfg.get("dicom_printer"))
    detected_sumatra = detect_sumatra_path()
    if detected_sumatra:
        worker_cfg = printer_cfg.get("worker") or {}
        current_sumatra = str(worker_cfg.get("sumatra_path") or "").strip()
        if not current_sumatra or not Path(current_sumatra).exists():
            worker_cfg["sumatra_path"] = detected_sumatra
            printer_cfg["worker"] = worker_cfg
    notice = request.args.get('notice')
    status = request.args.get('status')
    dcmtk_installed = is_system_tool_installed('dcmtk')
    sumatra_installed = is_system_tool_installed('sumatra')
    return render_template(
        'printer_config.html',
        cfg=cfg,
        printer_cfg=printer_cfg,
        notice=notice,
        status=status,
        dcmtk_installed=dcmtk_installed,
        sumatra_installed=sumatra_installed
    )


@app.route('/tests')
def tests():
    notice = request.args.get('notice')
    status = request.args.get('status')
    # Determine selected DB and whether plugin is installed
    cfg_path = ROOT / "config.json"
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    db_type = (cfg.get('database', {}).get('type') or 'oracle').lower()
    plugin_installed = is_db_plugin_installed(db_type)
    printer_enabled = bool((cfg.get('dicom_printer') or {}).get('enabled'))
    return render_template('tests.html', notice=notice, status=status, db_type=db_type, plugin_installed=plugin_installed, printer_enabled=printer_enabled)


@app.route('/plugins')
def plugins_page():
    items, current = plugins_status()
    notice = request.args.get('notice')
    status = request.args.get('status')
    manual_url = request.args.get('manual_url')
    return render_template('plugins.html', plugins=items, current=current, notice=notice, status=status, manual_url=manual_url)


@app.route('/plugin/install/<name>', methods=['POST'])
def plugin_install(name):
    name = (name or '').lower()
    mapping = {
        'oracle': 'cx_Oracle',
        'postgres': 'psycopg2-binary',
        'postgresql': 'psycopg2-binary',
        'mysql': 'PyMySQL',
        'pynetdicom': 'pynetdicom',
    }
    pkg = mapping.get(name)
    if not pkg:
        return redirect(url_for('plugins_page', notice=f'Unknown plugin {name}', status='error'))
    _py, pip_exe = _venv_python_and_pip()
    try:
        subprocess.run([pip_exe, 'install', pkg], check=True)
        return redirect(url_for('plugins_page', notice=f'Installed {pkg}', status='success'))
    except subprocess.CalledProcessError as e:
        return redirect(url_for('plugins_page', notice=f'Install failed: {e}', status='error'))


@app.route('/printer-config/install-tool/<name>', methods=['POST'])
def install_printer_tool(name):
    log_action("Printer tool install", f"Requested install for tool={name}")
    ok, msg = install_system_tool(name)
    if not ok and (name or '').lower() == 'dcmtk':
        return redirect(url_for('plugins_page', notice=msg, status='error', manual_url=DCMTK_MANUAL_URL))
    if ok and (name or '').lower() in ('sumatra', 'sumatrapdf'):
        detected_sumatra = detect_sumatra_path()
        if detected_sumatra:
            cfg_path = ROOT / "config.json"
            try:
                cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
            except Exception:
                cfg = {}
            dp = cfg.get('dicom_printer') or {}
            worker = dp.get('worker') or {}
            worker['sumatra_path'] = detected_sumatra
            dp['worker'] = worker
            cfg['dicom_printer'] = dp
            try:
                cfg_path.write_text(json.dumps(cfg, indent=2))
            except Exception:
                pass
    return redirect(url_for('plugins_page', notice=msg, status='success' if ok else 'error'))


@app.route('/printer-config/uninstall-tool/<name>', methods=['POST'])
def uninstall_printer_tool(name):
    log_action("Printer tool uninstall", f"Requested uninstall for tool={name}")
    ok, msg = uninstall_system_tool(name)
    return redirect(url_for('plugins_page', notice=msg, status='success' if ok else 'error'))


@app.route('/plugin/uninstall/<name>', methods=['POST'])
def plugin_uninstall(name):
    name = (name or '').lower()
    mapping = {
        'oracle': 'cx_Oracle',
        'postgres': 'psycopg2-binary',
        'postgresql': 'psycopg2-binary',
        'mysql': 'PyMySQL',
        'pynetdicom': 'pynetdicom',
    }
    pkg = mapping.get(name)
    if not pkg:
        return redirect(url_for('plugins_page', notice=f'Unknown plugin {name}', status='error'))
    _py, pip_exe = _venv_python_and_pip()
    try:
        subprocess.run([pip_exe, 'uninstall', '-y', pkg], check=True)
        return redirect(url_for('plugins_page', notice=f'Uninstalled {pkg}', status='success'))
    except subprocess.CalledProcessError as e:
        return redirect(url_for('plugins_page', notice=f'Uninstall failed: {e}', status='error'))


@app.route('/test/status', methods=['POST'])
def test_status():
    """Test service availability"""
    log_action("Test: Status", "Running service status test")
    try:
        # Use threading timeout for cross-platform support (SIGALRM doesn't exist on Windows)
        import threading
        st = [None]
        error = [None]
        
        def check_status():
            try:
                st[0] = manager.status()
            except Exception as e:
                error[0] = e
        
        # Run status check in thread with timeout
        thread = threading.Thread(target=check_status, daemon=True)
        thread.start()
        thread.join(timeout=5)  # 5-second timeout
        
        if error[0]:
            raise error[0]
        
        if thread.is_alive():
            # Thread still running after timeout
            return jsonify({'ok': False, 'message': 'Status check timed out'})
        
        if st[0]:
            running = bool((st[0].get('service') or {}).get('running'))
            if running:
                log_action("Test: Status passed", f"Service is running (PID: {st[0].get('service', {}).get('pid')})")
                return jsonify({
                    'ok': True, 
                    'message': 'Service is running',
                    'details': {'pid': (st[0].get('service') or {}).get('pid'), 'running': running}
                })
            else:
                log_action("Test: Status failed", "Service is not running")
                return jsonify({
                    'ok': False,
                    'message': 'Service is not running'
                })
        else:
            return jsonify({'ok': False, 'message': 'Unable to check service status'})
    except Exception as e:
        return jsonify({
            'ok': False,
            'message': f'Error checking service: {str(e)}',
            'error': str(e)
        })


@app.route('/test/db', methods=['POST'])
def test_db():
    """Test database connectivity"""
    log_action("Test: Database", "Running database connectivity test")
    try:
        # Read config.json directly
        cfg_path = ROOT / "config.json"
        if not cfg_path.exists():
            return jsonify({
                'ok': False,
                'message': 'Configuration file not found',
                'error': 'config.json missing'
            })
        
        try:
            cfg = json.loads(cfg_path.read_text())
        except:
            cfg = {}
        
        db_cfg = cfg.get('database', {})
        dsn = db_cfg.get('dsn', '')
        user = db_cfg.get('user', '')
        pwd = db_cfg.get('password', '')
        db_type = (db_cfg.get('type') or 'oracle').lower()
        
        if not all([dsn, user, pwd]):
            return jsonify({
                'ok': False,
                'message': 'Database credentials not configured in config.json',
                'error': f'Missing: {"DSN" if not dsn else ""} {"USER" if not user else ""} {"PASSWORD" if not pwd else ""}'.strip()
            })
        
        # Helpers to parse DSN in format IP:PORT/DB
        def parse_dsn_ip_port_db(dsn_str):
            try:
                host_part, dbname = dsn_str.split('/', 1)
                host, port = host_part.split(':', 1)
                return host.strip(), int(port), dbname.strip()
            except Exception:
                return None, None, None

        # Attempt connection based on database type
        try:
            if db_type == 'oracle':
                # Use cx_Oracle driver
                try:
                    import cx_Oracle
                except ImportError:
                    return jsonify({
                        'ok': False,
                        'message': 'No Oracle driver available',
                        'error': 'cx_Oracle is not installed'
                    })

                # Set connection timeout to avoid long waits
                conn = cx_Oracle.connect(user=user, password=pwd, dsn=dsn, timeout=10)
                driver_name = 'cx_Oracle'
                test_sql = "SELECT 1 FROM dual"

            elif db_type == 'postgres':
                try:
                    import psycopg2
                except ImportError:
                    return jsonify({
                        'ok': False,
                        'message': 'PostgreSQL driver not installed',
                        'error': 'Install psycopg2 or psycopg2-binary'
                    })
                host, port, dbname = parse_dsn_ip_port_db(dsn)
                if not host:
                    return jsonify({'ok': False, 'message': 'Invalid DSN format for PostgreSQL. Expected IP:PORT/DB'})
                # Set connection timeout
                conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=pwd, connect_timeout=10)
                driver_name = 'psycopg2'
                test_sql = "SELECT 1"

            elif db_type == 'mysql':
                try:
                    import pymysql
                except ImportError:
                    return jsonify({
                        'ok': False,
                        'message': 'MySQL driver not installed',
                        'error': 'Install PyMySQL or mysqlclient',
                        'canInstall': True
                    }), 400
                host, port, dbname = parse_dsn_ip_port_db(dsn)
                if not host:
                    return jsonify({'ok': False, 'message': 'Invalid DSN format for MySQL. Expected IP:PORT/DB'})
                # Set connection timeout
                conn = pymysql.connect(host=host, port=port, user=user, password=pwd, database=dbname, connect_timeout=10)
                driver_name = 'PyMySQL'
                test_sql = "SELECT 1"

            else:
                return jsonify({'ok': False, 'message': f'Unsupported database type: {db_type}'})

            # Execute a simple test query
            cursor = conn.cursor()
            cursor.execute(test_sql)
            _ = cursor.fetchone()
            cursor.close()
            conn.close()

            log_action("Test: DB passed", f"Connected to {db_type} database using {driver_name}")
            return jsonify({
                'ok': True,
                'message': f'Database connection successful using {driver_name}',
                'details': {'driver': driver_name, 'dsn': dsn, 'user': user, 'type': db_type}
            })
        except Exception as conn_err:
            log_action("Test: DB failed", f"Connection error: {str(conn_err)}")
            return jsonify({
                'ok': False,
                'message': f'Database connection failed: {str(conn_err)}',
                'error': str(conn_err)
            })
    except Exception as e:
        return jsonify({
            'ok': False,
            'message': f'Error testing database: {str(e)}',
            'error': str(e)
        })


@app.route('/install-driver', methods=['POST'])
def install_driver_route():
    """Install the database driver for the current config."""
    log_action("Plugin: Install driver", "User requested database driver installation")
    try:
        cfg_path = ROOT / "config.json"
        cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        db_type = cfg.get('database', {}).get('type', 'oracle')
        ok, msg = install_db_driver(db_type)
        log_action("Plugin: Install driver result", f"Driver={db_type}, Success={ok}, Message={msg}")
        status = 'success' if ok else 'error'
        return redirect(url_for('tests', notice=msg, status=status))
    except Exception as e:
        return redirect(url_for('tests', notice=f'Install error: {e}', status='error'))


@app.route('/logs/clear', methods=['POST'])
def clear_logs():
    """Clear log files under service_logs/ and logs/ directories."""
    log_action("Logs: Clear", "User requested to clear all log files")
    removed = []
    errors = []
    for folder in ['service_logs', 'logs']:
        p = ROOT / folder
        if p.exists() and p.is_dir():
            for f in p.glob('*'):
                if f.is_file():
                    try:
                        f.unlink()
                        removed.append(f.name)
                    except Exception as e:
                        errors.append(f"{f.name}: {e}")
        log_action("Logs: Clear result", f"Removed {len(removed)} files, Errors: {len(errors)}")
    status = 'success' if not errors else 'error'
    msg = 'Logs cleared' if status == 'success' else f"Partial clear; errors: {', '.join(errors)}"
    return redirect(url_for('logs', notice=msg, status=status))


@app.route('/test/echo', methods=['POST'])
def test_echo():
    """Test DICOM C-ECHO with fast timeouts (fail fast)."""
    log_action("Test: DICOM C-ECHO", "Running DICOM C-ECHO test")
    try:
        cfg_path = ROOT / 'config.json'
        cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        server_cfg = cfg.get('server', {})
        host = server_cfg.get('host', '127.0.0.1') or '127.0.0.1'
        port = server_cfg.get('port', 11112) or 11112
        remote_aet = server_cfg.get('aet', 'MWLSCP') or 'MWLSCP'
        client_aet = server_cfg.get('client_aet', 'TEST') or 'TEST'

        if host == '0.0.0.0':
            host = '127.0.0.1'

        # Prefer a real DICOM C-ECHO via pynetdicom with short timeouts
        try:
            import pynetdicom
            from pynetdicom.sop_class import Verification

            ae = pynetdicom.AE()
            ae.add_requested_context(Verification)
            # Fail fast: short timeouts
            try:
                ae.acse_timeout = 3
                ae.network_timeout = 3
                ae.dimse_timeout = 3
            except Exception:
                # Older versions may not expose all timeouts; proceed with defaults
                pass

            # Try association with provided AETs; support older signature
            try:
                assoc = ae.associate(host, port, ae_title=client_aet, remote_ae=remote_aet)
            except TypeError:
                assoc = ae.associate(host, port)

            if assoc and assoc.is_established:
                try:
                    status = assoc.send_c_echo()
                    assoc.release()
                    if status and getattr(status, 'Status', None) == 0x0000:
                        return jsonify({
                            'ok': True,
                            'message': f'C-ECHO (Verification) successful with {remote_aet}',
                            'details': {'host': host, 'port': port, 'aet': remote_aet}
                        })
                    else:
                        return jsonify({
                            'ok': False,
                            'message': 'C-ECHO failed',
                            'error': f'Status: {getattr(status, "Status", "unknown")}'
                        })
                except Exception as e:
                    try:
                        assoc.release()
                    except Exception:
                        pass
                    return jsonify({'ok': False, 'message': 'C-ECHO send failed', 'error': str(e)})
            else:
                return jsonify({
                    'ok': False,
                    'message': 'Cannot establish verification association',
                    'error': 'Association failed or service not running'
                })
        except ImportError:
            # Fallback: TCP connect check with 2s timeout
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((host, port))
                sock.close()
                if result == 0:
                    return jsonify({
                        'ok': True,
                        'message': f'DICOM service is listening on {host}:{port}',
                        'details': {'host': host, 'port': port, 'accessible': True}
                    })
                else:
                    return jsonify({
                        'ok': False,
                        'message': f'Cannot connect to DICOM service on {host}:{port}',
                        'error': 'Connection refused or timeout'
                    })
            except Exception as e:
                return jsonify({'ok': False, 'message': 'Echo test failed', 'error': str(e)})
    except Exception as e:
        return jsonify({'ok': False, 'message': f'DICOM echo test failed: {str(e)}', 'error': str(e)})




@app.route('/test/worklist', methods=['POST'])
def test_worklist():
    """Test DICOM C-FIND Worklist Response"""
    log_action("Test: DICOM Worklist", "Running DICOM worklist response test")
    try:
        # Debug: Check sys.path and reload site-packages
        _lib_path = ROOT / 'Lib' / 'site-packages'
        if str(_lib_path) not in sys.path:
            sys.path.insert(0, str(_lib_path))
        
        # Read config.json directly
        cfg_path = ROOT / "config.json"
        if not cfg_path.exists():
            return jsonify({
                'ok': False,
                'message': 'Configuration file not found',
                'error': 'config.json missing'
            })
        
        try:
            cfg = json.loads(cfg_path.read_text())
        except:
            cfg = {}
        
        server_cfg = cfg.get('server', {})
        host = server_cfg.get('host', '127.0.0.1') or '127.0.0.1'
        port = server_cfg.get('port', 11112) or 11112
        aet = server_cfg.get('aet', 'MWLSCP') or 'MWLSCP'
        client_aet = server_cfg.get('client_aet', 'Prima') or 'Prima'
        
        if host == '0.0.0.0':
            host = '127.0.0.1'
        
        # Try pynetdicom for C-FIND worklist query
        try:
            import pynetdicom
            from pynetdicom.sop_class import ModalityWorklistInformationFind
            from pydicom.dataset import Dataset
            
            # Create AE and add requested context
            ae = pynetdicom.AE()
            ae.add_requested_context(ModalityWorklistInformationFind)
            ae.acse_timeout = 5
            ae.network_timeout = 5
            
            # Try to establish association
            try:
                assoc = ae.associate(host, port, ae_title=client_aet, remote_ae=aet)
            except TypeError:
                # Older pynetdicom version
                assoc = ae.associate(host, port)
            
            if not assoc or not assoc.is_established:
                return jsonify({
                    'ok': False,
                    'message': 'Cannot establish C-FIND association with worklist server',
                    'error': 'Association failed - ensure DICOM server is running'
                })
            
            # Create a MWL C-FIND query identifier (avoid implicit modality filtering)
            ds = Dataset()
            ds.PatientName = '*'
            ds.PatientID = ''
            ds.AccessionNumber = ''
            ds.Modality = ''
            sps = Dataset()
            sps.Modality = ''
            sps.ScheduledStationAETitle = ''
            ds.ScheduledProcedureStepSequence = [sps]
            
            # Send C-FIND request
            responses = assoc.send_c_find(ds, ModalityWorklistInformationFind)
            results = []
            
            # Collect responses - serialize Dataset to dict with all attributes
            for status, dataset in responses:
                if status.Status in (0x0000, 0xFF00, 0xFF01):  # Success or Pending
                    if dataset:
                        # Convert Dataset to dict recursively, handling nested sequences
                        def dataset_to_dict(ds):
                            result = {}
                            for elem in ds:
                                keyword = elem.keyword if elem.keyword else f"Tag_{elem.tag}"
                                value = elem.value
                                
                                # Handle different value types
                                if value is None:
                                    result[keyword] = None
                                elif keyword in ('PatientName', 'ScheduledPerformingPhysicianName', 'ReferringPhysicianName'):
                                    # Handle PersonName fields - convert to string
                                    result[keyword] = str(value) if value else ''
                                elif isinstance(value, Dataset):
                                    result[keyword] = dataset_to_dict(value)
                                elif hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
                                    # Handle sequences
                                    if hasattr(value, '__class__') and value.__class__.__name__ == 'Sequence':
                                        result[keyword] = [dataset_to_dict(item) if isinstance(item, Dataset) else str(item) for item in value]
                                    else:
                                        result[keyword] = [str(v) for v in value]
                                else:
                                    result[keyword] = str(value)
                            return result
                        
                        item_dict = dataset_to_dict(dataset)
                        results.append(item_dict)
            
            assoc.release()
            
            if results:
                # Build modality summary across all returned items.
                modality_counts = {}
                for item in results:
                    mod = item.get('Modality')
                    if not mod:
                        try:
                            sps = item.get('ScheduledProcedureStepSequence') or []
                            if sps and isinstance(sps[0], dict):
                                mod = sps[0].get('Modality')
                        except Exception:
                            mod = None
                    mod = (str(mod).strip().upper() if mod else 'UNKNOWN')
                    modality_counts[mod] = modality_counts.get(mod, 0) + 1

                return jsonify({
                    'ok': True,
                    'message': f'Received {len(results)} worklist item(s) from DICOM server',
                    'details': {
                        'count': len(results),
                        'modalities': modality_counts,
                        'items': results,
                        'host': host,
                        'port': port,
                        'aet': aet,
                        'query_profile': 'mwl_v2_full'
                    }
                })
            else:
                return jsonify({
                    'ok': True,
                    'message': 'Association successful but no worklist items found',
                    'details': {
                        'count': 0,
                        'host': host,
                        'port': port,
                        'aet': aet
                    }
                })
        
        except ImportError as e:
            return jsonify({
                'ok': False,
                'message': 'pynetdicom plugin not installed',
                'error': f'Cannot test worklist without pynetdicom: {str(e)}',
                'canInstall': True
            })
        except Exception as e:
            return jsonify({
                'ok': False,
                'message': f'Worklist test failed: {str(e)}',
                'error': str(e)
            })
    except Exception as e:
        return jsonify({
            'ok': False,
            'message': f'Error testing worklist: {str(e)}',
            'error': str(e)
        })


@app.route('/test/find', methods=['POST'])
def test_find():
    """Test DICOM C-FIND - Query worklist"""
    log_action("Test: DICOM C-FIND", "Running DICOM C-FIND query test")
    try:
        # Read config.json directly
        cfg_path = ROOT / "config.json"
        if not cfg_path.exists():
            return jsonify({
                'ok': False,
                'message': 'Configuration file not found',
                'error': 'config.json missing'
            })
        
        try:
            cfg = json.loads(cfg_path.read_text())
        except:
            cfg = {}
        
        server_cfg = cfg.get('server', {})
        host = server_cfg.get('host', '127.0.0.1') or '127.0.0.1'
        port = server_cfg.get('port', 11112) or 11112
        aet = server_cfg.get('aet', 'MWLSCP') or 'MWLSCP'
        
        if host == '0.0.0.0':
            host = '127.0.0.1'
        
        # Try pynetdicom and handle all failure cases gracefully
        try:
            import pynetdicom
            from pynetdicom.sop_class import ModalityWorklistInformationFind
            
            # Create association - use 'ae' parameter instead of 'remote_ae'
            ae = pynetdicom.AE()
            ae.add_requested_context(ModalityWorklistInformationFind)
            
            assoc = ae.associate(host, port, ae_title='TEST', remote_ae=aet)
            if assoc and assoc.is_established:
                assoc.release()
                return jsonify({
                    'ok': True,
                    'message': f'DICOM C-FIND association established with {aet}',
                    'details': {'host': host, 'port': port, 'aet': aet}
                })
            else:
                return jsonify({
                    'ok': False,
                    'message': f'Cannot establish association with {aet}',
                    'error': 'Association failed or service not running'
                })
        except TypeError:
            # Older version of pynetdicom - try without remote_ae
            try:
                import pynetdicom
                from pynetdicom.sop_class import ModalityWorklistInformationFind
                
                ae = pynetdicom.AE()
                ae.add_requested_context(ModalityWorklistInformationFind)
                ae.acse_timeout = 5
                ae.network_timeout = 5
                
                assoc = ae.associate(host, port)
                if assoc and assoc.is_established:
                    assoc.release()
                    return jsonify({
                        'ok': True,
                        'message': f'DICOM C-FIND association established',
                        'details': {'host': host, 'port': port, 'aet': aet}
                    })
                else:
                    return jsonify({
                        'ok': False,
                        'message': 'Cannot establish association',
                        'error': 'Association failed or service not running'
                    })
            except Exception as e:
                return jsonify({
                    'ok': False,
                    'message': f'Cannot establish association: {str(e)}',
                    'error': str(e)
                })
        except ImportError:
            return jsonify({
                'ok': False,
                'message': 'pynetdicom not installed',
                'error': 'Cannot test C-FIND without pynetdicom'
            })
        except Exception as e:
            return jsonify({
                'ok': False,
                'message': 'C-FIND test failed',
                'error': str(e)
            })
    except Exception as e:
        return jsonify({
            'ok': False,
            'message': f'DICOM C-FIND test failed: {str(e)}',
            'error': str(e)
        })


@app.route('/test/printer', methods=['POST'])
def test_printer():
    """Test virtual DICOM printer flow by sending sample DICOM files to configured database folder."""
    log_action("Test: Virtual DICOM Printer", "Running virtual printer pipeline test")
    try:
        cfg_path = ROOT / "config.json"
        cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        printer_cfg = cfg.get('dicom_printer') or {}
        if not printer_cfg.get('enabled'):
            return jsonify({
                'ok': False,
                'message': 'Virtual DICOM printer is disabled',
                'error': 'Enable dicom_printer.enabled in settings'
            })

        worker_cfg = printer_cfg.get('worker') or {}
        database_dir = Path(worker_cfg.get('database_dir') or (ROOT / 'dicom-printer' / 'database'))
        out_dir = Path(worker_cfg.get('out_dir') or (ROOT / 'dicom-printer' / 'out'))
        sample_dir = ROOT / 'dicom-printer' / 'test' / '5x7'

        if not sample_dir.exists():
            return jsonify({
                'ok': False,
                'message': 'Sample test folder not found',
                'error': f'Missing folder: {sample_dir}'
            })

        database_dir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)

        pre_out_times = {str(p): p.stat().st_mtime for p in out_dir.glob('*') if p.is_file()}
        ts = datetime.now().strftime('%Y%m%d%H%M%S%f')
        copied = []

        for src in sorted(sample_dir.glob('*.dcm')):
            name = src.name
            if name.upper().startswith('HG_'):
                dst_name = f'HG_TEST_{ts}_{src.stem}.dcm'
            elif name.upper().startswith('SP_'):
                dst_name = f'SP_TEST_{ts}_{src.stem}.dcm'
            else:
                dst_name = f'TEST_{ts}_{src.stem}.dcm'
            dst = database_dir / dst_name
            shutil.copy2(src, dst)
            copied.append(str(dst))

        if not copied:
            return jsonify({
                'ok': False,
                'message': 'No sample DICOM files found in test folder',
                'error': f'Folder is empty: {sample_dir}'
            })

        # Wait for worker to pick up files and generate output artifacts
        timeout_seconds = 30
        start = time.time()
        generated = []
        while time.time() - start < timeout_seconds:
            for p in out_dir.glob('*'):
                if not p.is_file():
                    continue
                old_mtime = pre_out_times.get(str(p))
                if old_mtime is None or p.stat().st_mtime > old_mtime:
                    generated.append(str(p))
            if generated:
                break
            time.sleep(1)

        if generated:
            return jsonify({
                'ok': True,
                'message': 'Virtual printer test triggered successfully. New converted output detected.',
                'details': {
                    'sample_folder': str(sample_dir),
                    'database_dir': str(database_dir),
                    'out_dir': str(out_dir),
                    'copied_files': copied,
                    'generated_files': generated[:10]
                }
            })

        return jsonify({
            'ok': False,
            'message': 'Test files copied, but no new converted output detected within timeout',
            'error': 'Check if service is running and virtual printer worker is active',
            'details': {
                'sample_folder': str(sample_dir),
                'database_dir': str(database_dir),
                'out_dir': str(out_dir),
                'copied_files': copied
            }
        })
    except Exception as e:
        return jsonify({
            'ok': False,
            'message': f'Virtual printer test failed: {str(e)}',
            'error': str(e)
        })


@app.route('/setlang/<lang>')
def setlang(lang):
    """Set language (kept for compatibility)"""
    return redirect(request.referrer or '/')


@app.route('/set-language', methods=['POST'])
def set_language():
    try:
        data = request.get_json(silent=True) or {}
        lang = (data.get('lang') or 'en').lower()[:2]
        log_action("Language changed", f"User changed language to: {lang}")
        if not lang:
            return jsonify({'ok': False, 'message': 'Missing lang'}), 400
        cfg_path = ROOT / 'config.json'
        cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        ui = cfg.get('ui') or {}
        ui['language'] = lang
        cfg['ui'] = ui
        cfg_path.write_text(json.dumps(cfg, indent=2))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)}), 500


# Health endpoint for action APIs
@app.route('/action/health', methods=['GET'])
def action_health():
    try:
        return jsonify({'ok': True, 'endpoints': ['start', 'stop', 'restart']})
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)}), 500


# Utilities to locate and kill stray service processes
@app.route('/service/scan-kill', methods=['POST'])
def service_scan_kill():
    try:
        res = manager.kill_orphan_services()
        ok = res.get('ok', False)
        status = 200 if ok else 500
        return jsonify(res), status
    except Exception as e:
        return jsonify({'ok': False, 'msg': f'Unhandled error: {e}'}), 500


# Kill other-instance processes (service and/or app)
@app.route('/service/scan-kill-others', methods=['POST'])
def service_scan_kill_others():
    try:
        # Kill service and app processes that belong to different instance-id
        res = manager.kill_other_instances('both')
        ok = res.get('ok', False)
        status = 200 if ok else 500
        return jsonify(res), status
    except Exception as e:
        return jsonify({'ok': False, 'msg': f'Unhandled error: {e}'}), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
