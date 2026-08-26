# Security and Backup

- Use a dedicated least-privilege database account. Keep it read-only for MWL-only deployments; grant only the exact write operations required by enabled MPPS SQL actions.
- Restrict DICOM ports by firewall, source, and AE title.
- Keep the dashboard on localhost or behind an authenticated TLS reverse proxy; never expose the Flask development server directly to the internet.
- Restrict MPPS API actions to approved HTTPS destinations and protect their authentication headers.
- Make MPPS actions idempotent because modalities may retry N-CREATE or N-SET messages.
- Protect configuration, backups, and logs with filesystem ACLs.
- Never commit secrets, real DICOM data, databases, logs, locks, or spool files.
- Rotate any secret exposed through Git, issues, chat, or uncontrolled logs.
- Apply dependency and operating-system updates after staging validation.

Encrypt backups of `config.json` and `mpps-actions/`. PID, lock, state, log, spool, and temporary files do not require backup. Test restoration regularly.

Disable `runtime.debug` and `mpps.debug_output` in production unless temporary diagnostic logging has been explicitly approved; MPPS payloads and rendered action data may contain clinical identifiers.

During an incident, stop the service when clinical workflow is at risk, preserve evidence according to policy, revoke exposed credentials, and validate before resuming.
