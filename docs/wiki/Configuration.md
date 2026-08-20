# Configuration

Copy `config.example.json` to `config.json`. The real file is local and ignored by Git.

- `server`: MWL AE title, bind address, port, and calling AE policy.
- `database`: type, credentials, DSN, native client, and SQL.
- `runtime`: automatic startup, UI address/port, and debug mode.
- `mpps`: optional MPPS listener and actions.
- `dicom_printer`: optional receiver and print worker.

Use a dedicated read-only database account. The query must return columns in the documented order; see the [SQL guide](../SQL_QUERY_GUIDE.md) and [DICOM mapping](../COLUMN_MAPPING_GUIDE.md).

Never commit configuration, environment files, logs, dumps, patient data, internal addresses, or runtime state. Keep the UI bound to localhost unless it is protected by an authenticated TLS proxy and firewall.
