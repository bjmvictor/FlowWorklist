# Validation

## Production checklist

- Valid JSON with no placeholders and a least-privilege database account. Use read-only access unless an enabled MPPS SQL action explicitly requires constrained writes.
- Successful connection using the bundled driver for the selected database engine.
- Correct query shape and column order.
- Successful C-ECHO and C-FIND between server and modality.
- Correct AE titles, ports, dates, times, modalities, and accession numbers.
- One dashboard/service instance after reboot.
- Firewall limited to required sources.
- Logs compliant with institutional policy.
- MPPS N-CREATE/N-SET receipt, event/status filters, idempotency, and expected API/SQL side effects when MPPS is enabled.
- DCMTK, SumatraPDF, spool paths, paper format, and a test print when DICOM Print is enabled.

From **Tests**, run database connectivity, status, C-ECHO, Worklist, and C-FIND in that order. Test MPPS and printing only when configured. Confirm that unmatched MPPS actions are skipped and matched actions execute only for their configured events and statuses.

Record the date, commit, sanitized configuration, test modality, results, and evidence. Complete acceptance testing with non-clinical data first.
