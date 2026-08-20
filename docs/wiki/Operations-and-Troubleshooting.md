# Operations and Troubleshooting

Monitor `/status`, free disk space, and logs. Retest after HIS/RIS, database, network, or modality changes. Back up `config.json` and `mpps-actions/` securely and update through staging first.

## Common issues

**Dashboard works but MWL does not start:** inspect `service_logs/`, JSON, ports, dependencies, NSSM `AppDirectory`, and the configured Python executable.

**Database failure:** verify DNS, route, port, DSN, credentials, and native client. Run the query with the same account. For Oracle, check 64-bit compatibility and `oracle_client_lib_dir`.

**Empty or incorrect worklist:** compare request filters, SQL output, and column order. Validate `YYYYMMDD`, `HHMMSS`, AE titles, and modality codes.

**Slow interface:** verify access to the Tailwind and Font Awesome CDNs. The Tests page uses in-process package metadata and the dashboard uses a short status cache.

Locks are stored in `%LOCALAPPDATA%\FlowWorklist\instances`. Only terminate orphan processes after confirming that no valid installation owns them.
