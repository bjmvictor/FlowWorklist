# Architecture

- `webui/app.py`: Flask dashboard for configuration, tests, logs, and lifecycle control.
- `mwl_service.py`: DICOM MWL SCP and database-to-DICOM mapping.
- `mpps_service.py`: optional MPPS listener.
- `dicom_printer_service.py`: optional DICOM Print pipeline.
- `flow.py`: process, lock, state, and CLI manager.
- `config.json`: untracked local configuration containing environment credentials.

In development, start services from the dashboard or CLI. In production, run one operating-system service for the dashboard and enable `runtime.autostart_services` when it should start MWL/MPPS.

Runtime state is stored under `%LOCALAPPDATA%\FlowWorklist\instances\<instance-id>`, preventing conflicts between installations.

## MWL request flow

1. The modality opens a DICOM association.
2. It sends a C-FIND request.
3. FlowWorklist runs the configured query with a read-only account.
4. Each row is mapped according to the [column guide](../COLUMN_MAPPING_GUIDE.md).
5. Matching DICOM responses are returned.
