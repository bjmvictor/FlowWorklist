# Production service on Windows

The release installer uses the bundled WinSW wrapper to register and automatically restart the `FlowWorklist` Windows service. Manual NSSM setup remains documented only for source deployments.

Run one supervised management process and let it own MWL/MPPS startup. Do not register duplicate child services separately. See [Production Deployment](https://github.com/bjmvictor/FlowWorklist/blob/main/docs/DEPLOYMENT.md#windows-release-installer) for the maintained installation, data paths, recovery settings, and validation checklist.
