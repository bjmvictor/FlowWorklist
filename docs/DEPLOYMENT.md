# Production deployment

This is the canonical production guide. For a local first run, use the [README](../README.md). For packaging, use the [Build Guide](BUILD_GUIDE.md).

## Deployment model

Run one supervised management process. When `runtime.autostart_services` is enabled, that process starts and monitors MWL and, when configured, MPPS. Do not simultaneously configure separate supervisors for the same child services.

```text
Process supervisor
  |
  +-- FlowWorklist management app (127.0.0.1:5000)
        |
        +-- MWL SCP (configured server host/port)
        +-- MPPS SCP (when enabled and start_with_worklist=true)
```

## Production configuration

Create `config.json` from `config.example.json`. Use the web interface to edit it or manage it as a protected deployment file.

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
    "autostart_services": true,
    "ui_host": "127.0.0.1",
    "ui_port": 5000,
    "debug": false
  },
  "mpps": {
    "enabled": true,
    "start_with_worklist": true
  },
  "dicom_printer": { "enabled": false }
}
```

Keep the UI on localhost unless an authenticated TLS reverse proxy is required. Restrict database privileges to the MWL query and to the exact statements required by enabled MPPS SQL actions.

## Windows release installer

Use `FlowWorklist-Setup-VERSION-Windows-x64.exe` for normal production installation. It installs immutable binaries under `C:\Program Files\FlowWorklist`, stores writable site data under `C:\ProgramData\FlowWorklist`, and registers the automatically started `FlowWorklist` Windows service through the bundled WinSW wrapper.

The service runs the management interface through Waitress and sets `FLOWWORKLIST_AUTOSTART_SERVICES=1`, allowing the management process to supervise MWL and MPPS. Use the Start menu shortcut to open `http://127.0.0.1:5000`.

Release packages include the Oracle Thin, PostgreSQL, and MySQL Python drivers. Do not install or remove packages inside an installed release.

## Windows source deployment

Use a dedicated service account with read access to the application, execute access to Python, modify access to runtime/log directories, and only the required database/network permissions.

```powershell
nssm install FlowWorklist "C:\FlowWorklist\.venv\Scripts\python.exe" "C:\FlowWorklist\webui\app.py"
nssm set FlowWorklist AppDirectory "C:\FlowWorklist"
nssm set FlowWorklist Start SERVICE_AUTO_START
nssm set FlowWorklist AppExit Default Restart
nssm set FlowWorklist AppRestartDelay 5000
nssm set FlowWorklist AppStdout "C:\FlowWorklist\service_logs\nssm-stdout.log"
nssm set FlowWorklist AppStderr "C:\FlowWorklist\service_logs\nssm-stderr.log"
nssm start FlowWorklist
nssm status FlowWorklist
```

Do not point NSSM directly at `mwl_service.py` when the management app owns automatic service startup.

## Linux release with systemd

Extract the Linux portable archive and run `sudo ./install-service.sh`. The installer copies the bundle to `/opt/flowworklist`, creates the non-login `flowworklist` account, stores writable data under `/var/lib/flowworklist`, and enables `flowworklist.service`.

## Linux source deployment with systemd

Create a dedicated user and install the application under a controlled directory such as `/opt/flowworklist`.

```ini
[Unit]
Description=FlowWorklist
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=flowworklist
Group=flowworklist
WorkingDirectory=/opt/flowworklist
ExecStart=/opt/flowworklist/.venv/bin/python /opt/flowworklist/webui/app.py
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now flowworklist
sudo systemctl status flowworklist
```

Validate database drivers and DICOM networking on the target Linux distribution before production use.

## Network policy

Allow only the connections required by the deployment:

| Source | Destination | Purpose |
|---|---|---|
| approved modalities | MWL host and configured port | C-ECHO and C-FIND |
| approved modalities | MPPS host and configured port | N-CREATE and N-SET |
| FlowWorklist host | database DSN | MWL query and configured MPPS SQL actions |
| FlowWorklist host | approved API endpoints | configured MPPS API actions |
| administrators or reverse proxy | UI localhost port | management |

Do not expose the Flask development server directly to untrusted networks. If remote administration is required, place it behind an authenticated TLS reverse proxy and host firewall.

## MPPS action safety

MPPS actions can modify downstream systems.

1. Start with MPPS enabled and no actions to verify receipt.
2. Use the test payload and debug output only in a controlled test environment.
3. Add explicit event filters for N-CREATE or N-SET.
4. Add explicit status filters where appropriate.
5. Test API and SQL actions against non-production targets.
6. Confirm idempotency because modalities may retry DICOM messages.
7. Disable debug payload logging before go-live if it may contain patient data.

## Validation

Before go-live:

- load every management page and verify there are no server or browser errors;
- confirm the selected database driver and database test;
- validate all 17 query columns with production-like data;
- run C-ECHO and C-FIND from an approved modality;
- verify MWL filtering by patient, accession number, date, and modality as applicable;
- send MPPS N-CREATE and N-SET and verify DICOM success responses;
- prove that unmatched MPPS actions are skipped and matched actions run once as designed;
- restart the process and reboot the host;
- confirm log rotation, monitoring, backup, and restore procedures.

## Monitoring and logs

- `logs/`: management application logs;
- `service_logs/`: MWL, MPPS, print, and supervisor output;
- `.\flow.ps1 status` or `python flow.py status`: current process state;
- `http://127.0.0.1:5000/status`: management status endpoint.

Alert on repeated process restarts, database failures, DICOM association failures, MPPS action failures, and disk growth.

## Backup and recovery

Back up:

- `config.json`;
- `mpps-actions/`;
- any local print configuration needed by the site;
- supervisor configuration and service-account documentation.

Exclude credentials and clinical data from general-purpose source repositories. Test restoration on a non-production host.

## Upgrade procedure

1. Back up configuration and action definitions.
2. Review `CHANGELOG.md`.
3. Stop the supervisor.
4. For an installed release, run the newer installer over the existing version. For a source deployment, deploy the new code and update the virtual environment with `pip install -r requirements.txt`.
5. Run syntax, database, and DICOM tests.
6. Start the supervisor and verify MWL and MPPS state.
7. Keep a tested rollback package until acceptance is complete.

## Troubleshooting

Use [Operations and Troubleshooting](wiki/Operations-and-Troubleshooting.md) for common failures. For production incidents, preserve the relevant logs and configuration metadata without copying credentials or patient data into tickets.
