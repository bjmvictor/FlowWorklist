# Configuration

Create `config.json` from `config.example.json`. The real file is local, contains environment credentials, and must not be committed.

| Section | Purpose |
|---|---|
| `server` | MWL AE title, bind address, port, and expected calling AE |
| `database` | engine, credentials, DSN, optional Oracle client, and 17-column SQL query |
| `ui` | interface language |
| `runtime` | UI bind settings, debug mode, and child-service autostart |
| `mpps` | optional MPPS listener and startup behavior |
| `dicom_printer` | optional DICOM Print receiver and worker |

Use the **Config** page for MWL and database settings, **MPPS** for listener/action settings, and **DICOM Printer** for print settings. Install optional drivers from **Config** or **Plugins**.

The worklist query is positional and must return exactly 17 columns. Use the [SQL Query Guide](../SQL_QUERY_GUIDE.md) as the contract and the [Column Mapping Guide](../COLUMN_MAPPING_GUIDE.md) for detailed behavior.

MPPS actions are stored separately under `mpps-actions/`. Each action can filter N-CREATE/N-SET events and MPPS statuses, then call an API, execute SQL, or perform both. No downstream action runs when no enabled action matches.

Use a read-only account for MWL. If MPPS SQL actions require writes, grant only the exact statements/tables required and validate the action filters.

Production-safe defaults:

- `runtime.debug: false`;
- `runtime.ui_host: "127.0.0.1"`;
- explicit modality AE and firewall rules;
- `mpps.debug_output: false` after validation;
- secrets and internal addresses excluded from source control and support bundles.

The complete example and first-run sequence are maintained in the [README](../../README.md).
