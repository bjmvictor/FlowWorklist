# Production with NSSM

The maintained NSSM configuration, process-ownership model, recovery settings, and validation checklist are in [Production Deployment](../DEPLOYMENT.md#windows-with-nssm).

Run one supervised management process and let it own MWL/MPPS startup when `runtime.autostart_services` is enabled. Do not supervise duplicate child services separately.
