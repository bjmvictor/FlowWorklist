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
import importlib.util

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
    ]
    _py, pip_exe = _venv_python_and_pip()
    for p in plugins:
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
        
        return True, "Configuration valid"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in config.json: {e.msg} (line {e.lineno})"
    except Exception as e:
        return False, f"Error reading config: {str(e)}"


@app.route('/action/<cmd>', methods=['POST'])
def action(cmd):
    cfg = str(ROOT / "config.json")
    
    # Validate config before attempting to start
    if cmd in ['start', 'restart']:
        valid, msg = _validate_config()
        if not valid:
            return jsonify({
                'ok': False,
                'msg': f"Configuration Error: {msg}. Please check config.json",
                'error_type': 'config_error',
                'error_detail': msg
            }), 400
    
    try:
        if cmd == 'start':
            r = manager.startservice(config_path=cfg)
        elif cmd == 'stop':
            r = manager.stopservice()
        elif cmd == 'restart':
            r = manager.restartservice(config_path=cfg)
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
        logs = manager.logs(limit=limit)
        return jsonify({'logs': logs})
    except Exception as e:
        return jsonify({'logs': [], 'error': str(e)}), 500


@app.route('/logs')
def logs():
    logs = manager.logs(limit=50)
    notice = request.args.get('notice')
    status = request.args.get('status')
    return render_template('logs.html', logs=logs, notice=notice, status=status)


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
            return redirect(url_for('config', notice='config_saved', status='success'))
        except Exception as e:
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


@app.route('/tests')
def tests():
    notice = request.args.get('notice')
    status = request.args.get('status')
    # Determine selected DB and whether plugin is installed
    cfg_path = ROOT / "config.json"
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    db_type = (cfg.get('database', {}).get('type') or 'oracle').lower()
    plugin_installed = is_db_plugin_installed(db_type)
    return render_template('tests.html', notice=notice, status=status, db_type=db_type, plugin_installed=plugin_installed)


@app.route('/plugins')
def plugins_page():
    items, current = plugins_status()
    notice = request.args.get('notice')
    status = request.args.get('status')
    return render_template('plugins.html', plugins=items, current=current, notice=notice, status=status)


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
                return jsonify({
                    'ok': True, 
                    'message': 'Service is running',
                    'details': {'pid': (st[0].get('service') or {}).get('pid'), 'running': running}
                })
            else:
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

            return jsonify({
                'ok': True,
                'message': f'Database connection successful using {driver_name}',
                'details': {'driver': driver_name, 'dsn': dsn, 'user': user, 'type': db_type}
            })
        except Exception as conn_err:
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
    try:
        cfg_path = ROOT / "config.json"
        cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        db_type = cfg.get('database', {}).get('type', 'oracle')
        ok, msg = install_db_driver(db_type)
        status = 'success' if ok else 'error'
        return redirect(url_for('tests', notice=msg, status=status))
    except Exception as e:
        return redirect(url_for('tests', notice=f'Install error: {e}', status='error'))


@app.route('/logs/clear', methods=['POST'])
def clear_logs():
    """Clear log files under service_logs/ and logs/ directories."""
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
    status = 'success' if not errors else 'error'
    msg = 'Logs cleared' if status == 'success' else f"Partial clear; errors: {', '.join(errors)}"
    return redirect(url_for('logs', notice=msg, status=status))


@app.route('/test/echo', methods=['POST'])
def test_echo():
    """Test DICOM C-ECHO with fast timeouts (fail fast)."""
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
            
            # Create a simple C-FIND query for worklist
            ds = Dataset()
            ds.PatientName = '*'
            ds.PatientID = ''
            ds.QueryRetrieveLevel = 'PATIENT'
            
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
                return jsonify({
                    'ok': True,
                    'message': f'Received {len(results)} worklist item(s) from DICOM server',
                    'details': {
                        'count': len(results),
                        'items': results[:10],  # Show first 10
                        'host': host,
                        'port': port,
                        'aet': aet
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


@app.route('/setlang/<lang>')
def setlang(lang):
    """Set language (kept for compatibility)"""
    return redirect(request.referrer or '/')


@app.route('/set-language', methods=['POST'])
def set_language():
    try:
        data = request.get_json(silent=True) or {}
        lang = (data.get('lang') or '').lower()[:2]
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
