<div align="center">
  <img src="webui/static/brand/logo-lockup-white.png" alt="FlowWorklist" width="460">
</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/DICOM-MWL-16A34A" alt="DICOM MWL">
  <img src="https://img.shields.io/badge/MPPS-Optional-4F46E5" alt="Optional MPPS">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-2563EB" alt="Windows and Linux">
  <img src="https://img.shields.io/badge/License-HNCL%201.1-F59E0B" alt="HNCL 1.1 License">
</p>

<p align="center">
  A lightweight, vendor-neutral <strong>DICOM Modality Worklist (MWL)</strong> server with a user-friendly web interface for management.
</p>

## What it does

- answers DICOM MWL C-FIND requests from imaging modalities;
- reads scheduled procedures from the hospital database;
- maps each database row to a DICOM worklist response;
- optionally receives MPPS N-CREATE and N-SET events;
- optionally runs API or SQL actions when MPPS events arrive(Study create/in_progress/completed/discontinued -> Do action API/SQL);
- provides configuration, driver installation, tests, logs, and service controls through the web interface.

## Runtime workflow

```text
  MODALITY WORKLIST (MWL)               MODALITY PERFORMED PROCEDURE STEP (MPPS)

  +--------------------+                      +------------------+
  | HIS / RIS Database |                      | Imaging Modality |
  +--------------------+                      +------------------+
            |                                           |
            | Read-only SQL query                       | N-CREATE / N-SET
            v                                           v
  +----------------------+                    +-----------------------+
  | FlowWorklist MWL SCP |                    | FlowWorklist MPPS SCP |
  +----------------------+                    +-----------------------+
         ^        |                                     |
         |        |                                     +--> No action
  C-FIND |        | Scheduled                           +--> HTTP API
  Request|        | procedures                          +--> SQL action
         |        |                                     +--> HTTP API + SQL
         |        v
    +------------------+
    | Imaging Modality |
    +------------------+
```

MWL and MPPS are related operationally but are separate DICOM services. MWL sends scheduled procedure data in response to a modality query. The modality later reports procedure progress or completion to the MPPS receiver. FlowWorklist only performs an MPPS action when that action is enabled and its event/status filters match.

## Install a release

Release packages include Python, Waitress, DICOM libraries, and all supported database drivers. The application does not download Python packages at runtime.

### Windows installer

Download `FlowWorklist-Setup-VERSION-Windows-x64.exe`, run it as an administrator, and open **FlowWorklist** from the Start menu. The installer registers an automatically restarted Windows service and keeps writable data under `%ProgramData%\FlowWorklist`.

### Windows portable

Extract `FlowWorklist-Portable-VERSION-Windows-x64.zip` into a writable directory and run `FlowWorklist.exe`. Portable configuration and logs are stored in the package's `data` directory.

### Linux portable or service

```bash
tar -xzf FlowWorklist-Portable-VERSION-Linux-x64.tar.gz
cd FlowWorklist
./FlowWorklist
```

For a system service, run `sudo ./install-service.sh`. This installs the application under `/opt/flowworklist`, stores data under `/var/lib/flowworklist`, and enables the `flowworklist.service` systemd unit.

Open `http://127.0.0.1:5000`, complete **Config**, and run the database and DICOM tests before starting MWL. Oracle, PostgreSQL, and MySQL drivers are already included.

## Run from source

### Requirements

- Python 3.10 or newer;
- network access to the database and modality;
- a database account restricted to the required operations;

### Windows

```cmd
py -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
.\flow start app
```

Open `http://127.0.0.1:5000`, complete **Config**, and run the database and DICOM tests before starting the MWL service.

```powershell
.\flow start service
.\flow status
```

### Linux or macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json
python flow.py start app
```

The DICOM services are intended primarily for controlled server environments. Validate platform-specific database drivers before deployment.

## Configuration

`config.json` is the local runtime configuration. Create it from `config.example.json`; do not commit credentials or patient data.

```json
{
  "server": {
    "aet": "FLOWMWL",
    "host": "0.0.0.0",
    "port": 11112,
    "client_aet": "MODALITY_AE"
  },
  "database": {
    "type": "postgres",
    "user": "<DB_USER>",
    "password": "<DB_PASSWORD>",
    "dsn": "<DB_HOST>:5432/<DB_NAME>",
    "oracle_client_lib_dir": "",
    "query": "SELECT ..."
  },
  "ui": { "language": "en" },
  "runtime": {
    "autostart_services": false,
    "ui_host": "127.0.0.1",
    "ui_port": 5000,
    "debug": false
  },
  "mpps": {
    "enabled": false,
    "start_with_worklist": false
  },
  "dicom_printer": { "enabled": false }
}
```

The worklist query must return exactly 17 columns in the documented order. See the [SQL Query Guide](docs/SQL_QUERY_GUIDE.md) and [Column Mapping Guide](docs/COLUMN_MAPPING_GUIDE.md).

Configure the optional MPPS listener and action files from **MPPS** in the web interface. Actions are stored under `mpps-actions/` and can react to N-CREATE, N-SET, or selected MPPS statuses.

## Common commands

```powershell
.\flow start all
.\flow stop all
.\flow restart service
.\flow status
.\flow logs
```

Use `python flow.py ...` on platforms where the PowerShell wrapper is not appropriate.

## Production

Production deployments should:

1. use a dedicated least-privilege operating-system account;
2. keep `runtime.debug` disabled;
3. bind the management UI to localhost unless it is protected by an authenticated TLS reverse proxy;
4. restrict MWL and MPPS ports to approved modality networks;
5. store `config.json` outside version control and restrict its file permissions;
6. use the service installed by the release package, or supervise source deployments with systemd or another process manager;
7. enable `runtime.autostart_services` only when the management process should own MWL/MPPS startup;
8. validate database connectivity, C-ECHO, C-FIND, MPPS, action filters, logs, restart behavior, and backup recovery before go-live.

See the canonical [Production Deployment Guide](docs/DEPLOYMENT.md).

## Documentation

- [Documentation index](docs/INDEX.md)
- [Quick operational reference](docs/QUICK_REFERENCE.md)
- [Production deployment](docs/DEPLOYMENT.md)
- [SQL query contract](docs/SQL_QUERY_GUIDE.md)
- [DICOM column mapping](docs/COLUMN_MAPPING_GUIDE.md)
- [Build and release guide](docs/BUILD_GUIDE.md)
- [Architecture](docs/wiki/Architecture.md)
- [Operations and troubleshooting](docs/wiki/Operations-and-Troubleshooting.md)
- [Security](docs/wiki/Security.md)

## Project layout

```text
flow.py                    Process manager and CLI
mwl_service.py             MWL C-FIND SCP
mpps_service.py            Optional MPPS N-CREATE/N-SET SCP
mpps_actions.py            MPPS filtering and API/SQL actions
dicom_printer_service.py   Optional DICOM Print pipeline
webui/                     Flask management interface
mpps-actions/              Local MPPS action definitions
docs/                      Operational and technical documentation
config.example.json        Safe configuration template
```

## Security and clinical use

FlowWorklist handles clinical identifiers and may trigger downstream updates. Use encrypted network boundaries, least-privilege accounts, controlled action filters, audit logs, backups, and site validation. It is not a substitute for local regulatory, privacy, cybersecurity, or clinical safety review.

## License

See [LICENSE.md](LICENSE.md).
