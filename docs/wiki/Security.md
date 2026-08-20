# Security and Backup

- Use a dedicated read-only database account with minimal grants.
- Restrict DICOM ports by firewall, source, and AE title.
- Never expose the dashboard directly to the internet.
- Protect configuration, backups, and logs with filesystem ACLs.
- Never commit secrets, real DICOM data, databases, logs, locks, or spool files.
- Rotate any secret exposed through Git, issues, chat, or uncontrolled logs.
- Apply dependency and operating-system updates after staging validation.

Encrypt backups of `config.json` and MPPS actions. PID, lock, state, log, and temporary files do not require backup. Test restoration regularly.

During an incident, stop the service when clinical workflow is at risk, preserve evidence according to policy, revoke exposed credentials, and validate before resuming.
