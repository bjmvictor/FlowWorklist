# Quick operational reference

This page is a command and verification reference. Installation details belong in the [README](../README.md); production service configuration belongs in [DEPLOYMENT.md](DEPLOYMENT.md).

## Start and stop

```powershell
.\flow.ps1 start app
.\flow.ps1 start service
.\flow.ps1 start all
.\flow.ps1 status
.\flow.ps1 restart service
.\flow.ps1 stop all
```

On other platforms, replace `.\flow.ps1` with `python flow.py`.

## Management interface

Default URL: `http://127.0.0.1:5000`

| Page | Purpose |
|---|---|
| Home | Service state, lifecycle controls, and recent logs |
| Config | MWL server, database, and query settings |
| Tests | Database, C-ECHO, C-FIND, and integration checks |
| MPPS | Listener settings, test payload, and action definitions |
| DICOM Printer | Optional receiver and print worker |
| Logs | Application and service diagnostics |

## Default endpoints

| Component | Default |
|---|---|
| Management UI | `127.0.0.1:5000` |
| MWL SCP | `0.0.0.0:11112`, AE `FLOWMWL` |
| MPPS SCP | `0.0.0.0:4101`, AE `FLOWMPPS` |

Confirm the actual values in `config.json` before testing.

## Expected workflow

1. The modality queries the MWL AE with C-FIND.
2. FlowWorklist executes the configured read-only query.
3. FlowWorklist returns scheduled procedures to the modality.
4. The modality sends MPPS N-CREATE when a procedure starts.
5. The modality sends MPPS N-SET as status changes, commonly to `COMPLETED` or `DISCONTINUED`.
6. Matching enabled MPPS actions call an API, execute SQL, perform both, or do nothing when no action is configured.

## Go-live checks

- database test succeeds with the production account;
- the query returns exactly 17 columns in the required order;
- C-ECHO and C-FIND succeed from an approved modality network;
- modality AE titles and firewall rules are restricted as intended;
- MPPS N-CREATE and N-SET are received when MPPS is enabled;
- each MPPS action runs only for its configured events and statuses;
- service restart and host reboot recovery succeed;
- logs contain no credentials or unexpected patient data;
- configuration and action definitions are backed up.

## First diagnostics

```powershell
.\flow.ps1 status
.\flow.ps1 logs
```

Then check `logs/`, `service_logs/`, bind ports, AE titles, DSN reachability, and query output. Release packages already contain all supported database drivers. See [Operations and Troubleshooting](wiki/Operations-and-Troubleshooting.md).
