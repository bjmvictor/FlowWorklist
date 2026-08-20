# Build Guide

This guide describes how to package FlowWorklist for Windows. A Python virtual-environment deployment is recommended when easy upgrades and diagnostics are more important than a single executable.

## Requirements

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pyinstaller
```

## Build the management application

```powershell
pyinstaller --name FlowWorklist --onefile --console `
  --add-data "webui;webui" `
  --add-data "config.example.json;." `
  webui\app.py
```

## Build the MWL service only

```powershell
pyinstaller --name FlowWorklist-Service --onefile --console `
  --add-data "config.example.json;." `
  mwl_service.py
```

Build output is written to `dist/`. Copy the required executable, create a local `config.json` from `config.example.json`, and keep credentials outside version control.

## Validation

Test the executable on a clean, supported Windows machine. Verify page loading, database connectivity, C-ECHO, C-FIND, log creation, graceful shutdown, and automatic restart before production use.

## NSSM

For the recommended production service configuration, recovery settings, working directory, and post-reboot checks, see [Production with NSSM](wiki/Production-NSSM.md).

## Troubleshooting

- If templates or static files are missing, check the `--add-data` paths.
- If Oracle cannot load its native library, verify architecture and `oracle_client_lib_dir`.
- If a process exits immediately, inspect `service_logs/` and NSSM stdout/stderr.
- Do not package a production `config.json` into a distributable executable.
