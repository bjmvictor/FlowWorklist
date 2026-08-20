# Validation

## Production checklist

- Valid JSON with no placeholders and a read-only database account.
- Correct query shape and column order.
- Successful C-ECHO and C-FIND between server and modality.
- Correct AE titles, ports, dates, times, modalities, and accession numbers.
- One dashboard/service instance after reboot.
- Firewall limited to required sources.
- Logs compliant with institutional policy.

From **Tests**, run database connectivity, status, C-ECHO, Worklist, and C-FIND in that order. Test MPPS and printing only when configured.

Record the date, commit, sanitized configuration, test modality, results, and evidence. Complete acceptance testing with non-clinical data first.
