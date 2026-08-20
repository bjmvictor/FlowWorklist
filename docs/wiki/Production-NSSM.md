# Production with NSSM

Use a least-privilege service account. Set this in the local `config.json`:

```json
"runtime": {
  "autostart_services": true,
  "ui_host": "127.0.0.1",
  "ui_port": 5000,
  "debug": false
}
```

MWL starts with the dashboard. MPPS also starts when both `mpps.enabled` and `mpps.start_with_worklist` are true. Existing processes are detected to prevent duplicates.

```powershell
nssm install FlowWorklist "C:\FlowWorklist\.venv\Scripts\python.exe" "C:\FlowWorklist\webui\app.py"
nssm set FlowWorklist AppDirectory "C:\FlowWorklist"
nssm set FlowWorklist Start SERVICE_AUTO_START
nssm set FlowWorklist AppExit Default Restart
nssm set FlowWorklist AppRestartDelay 5000
nssm set FlowWorklist AppStdout "C:\FlowWorklist\service_logs\nssm-stdout.log"
nssm set FlowWorklist AppStderr "C:\FlowWorklist\service_logs\nssm-stderr.log"
nssm start FlowWorklist
```

Alternatively, set `FLOWWORKLIST_AUTOSTART_SERVICES=1` in the NSSM environment.

After reboot, check `nssm status FlowWorklist`, `http://127.0.0.1:5000/status`, port 11112, and a real query from a test modality.
