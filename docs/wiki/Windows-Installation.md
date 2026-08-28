# Windows installation

For normal deployments, download `FlowWorklist-Setup-VERSION-Windows-x64.exe` from the GitHub Release and run it as an administrator. The package contains Python and every supported database driver, registers an automatically started service, stores writable data under `%ProgramData%\FlowWorklist`, and adds a shortcut for the management interface.

Use the portable ZIP when installation is not appropriate. Extract it into a writable directory and run `FlowWorklist.exe`; its configuration and logs stay under the local `data` directory.

See the [README](https://github.com/bjmvictor/FlowWorklist/blob/main/README.md) for first-run configuration and [Production Deployment](https://github.com/bjmvictor/FlowWorklist/blob/main/docs/DEPLOYMENT.md#windows-release-installer) for service, security, upgrade, and validation guidance.
