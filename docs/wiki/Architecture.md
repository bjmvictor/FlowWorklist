# Architecture

## Components

- `webui/app.py`: Flask management interface for configuration, plugins, tests, logs, and lifecycle control.
- `mwl_service.py`: DICOM MWL SCP and database-to-DICOM mapping.
- `mpps_service.py`: optional DICOM MPPS SCP.
- `mpps_actions.py`: MPPS event/status filtering and API/SQL actions.
- `dicom_printer_service.py`: optional DICOM Print receiver and worker.
- `flow.py`: CLI, process ownership, locks, and runtime state.
- `config.json`: local environment configuration.
- `mpps-actions/*.json`: local MPPS action definitions.

Runtime state is isolated per installation under the platform-specific FlowWorklist application-data directory to prevent process conflicts between copies.

## MWL and MPPS workflow

```text
HIS / RIS database
      |
      | 1. configured worklist query
      v
FlowWorklist MWL SCP
      ^                    Imaging modality
      | 2. C-FIND request         |
      +---------------------------+
      |
      +---- 3. scheduled procedure C-FIND responses ---->

Imaging modality
      |
      | 4. N-CREATE: procedure started
      | 5. N-SET: procedure status updated/completed
      v
FlowWorklist MPPS SCP
      |
      | 6. normalize DICOM payload
      | 7. evaluate enabled event and status filters
      v
Configured action
      +--> HTTP API
      +--> SQL statement
      +--> API and SQL
      +--> skipped when no action matches
```

The MWL response does not directly invoke MPPS. The modality consumes a scheduled procedure from MWL and later sends independent MPPS messages. Accession number, patient ID, requested procedure ID, and study identifiers can correlate the two workflows.

## Failure boundaries

- A database failure prevents MWL query responses but should not expose credentials to the modality.
- An MPPS action failure is logged after the MPPS event is received; action filters should be explicit and actions should be idempotent.
- The management UI supervises child services only when configured to do so.
- DICOM Print is optional and independent from MWL and MPPS.

See [Production Deployment](../DEPLOYMENT.md) for process ownership and network policy.
