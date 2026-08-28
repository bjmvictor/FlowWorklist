# Build and release guide

FlowWorklist releases are complete, offline application bundles. Python, the DICOM libraries, Waitress, and the Oracle, PostgreSQL, and MySQL drivers are included. Runtime package installation is not supported.

## Release artifacts

| Artifact | Purpose |
|---|---|
| `FlowWorklist-Setup-VERSION-Windows-x64.exe` | Windows installation with an automatically managed service |
| `FlowWorklist-Portable-VERSION-Windows-x64.zip` | Windows portable execution without installation |
| `FlowWorklist-Portable-VERSION-Linux-x64.tar.gz` | Linux portable execution with an optional systemd installer |
| `SHA256SUMS.txt` | Release integrity checksums |

Installed binaries are immutable. Configuration, actions, logs, and print data are stored separately so upgrades do not overwrite site data.

## Build requirements

- Python 3.13 x64;
- dependencies from `requirements.txt`;
- PyInstaller;
- Inno Setup for the Windows installer (the build script installs it for the current user through `winget` when missing);
- internet access during the Windows build to retrieve the pinned WinSW service wrapper.

Build on the target operating system. PyInstaller does not cross-compile Windows binaries on Linux or Linux binaries on Windows.

## Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
.\packaging\build-windows.ps1 -Version 1.0.0
```

Use `-SkipInstaller` when only the portable ZIP is required. The script creates one PyInstaller `onedir` runtime whose internal roles launch the UI, MWL, and MPPS processes, then creates the portable archive and Inno Setup installer.

Before packaging, the build runs an embedded runtime diagnostic that imports every bundled database driver, the DICOM stack, Waitress, and the cryptography modules required by Oracle Thin mode. A missing runtime module stops the build instead of producing a defective installer.

If GitHub downloads are restricted in the build environment, download WinSW x64 v2.12.0 separately and provide it without disabling checksum verification:

```powershell
.\packaging\build-windows.ps1 -Version 1.0.0 -WinSWBinary C:\Downloads\WinSW-x64.exe
```

## Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
bash packaging/build-linux.sh 1.0.0
```

Extract the generated archive and run `./FlowWorklist`. To install it under `/opt/flowworklist` with a dedicated account and systemd, run `sudo ./install-service.sh` from the extracted directory.

## Automated releases

The `Build release packages` GitHub Actions workflow builds both platforms. A manual run stores build artifacts. Pushing a signed or annotated `vX.Y.Z` tag additionally creates a GitHub Release and publishes checksums.

```bash
git tag -a v1.0.0 -m "FlowWorklist 1.0.0"
git push origin v1.0.0
```

## Required validation

Test every release on clean Windows and Linux x64 machines:

1. verify the SHA-256 checksum;
2. confirm first-run creation of a blank configuration;
3. load every management page;
4. test Oracle Thin, PostgreSQL, and MySQL connectivity;
5. run C-ECHO and C-FIND;
6. validate MPPS N-CREATE and N-SET;
7. restart the service and reboot the host;
8. upgrade over an existing installation and confirm configuration preservation;
9. uninstall the application and confirm that operational data remains available for recovery.

DICOM Print requires platform tools in addition to the bundled Python drivers. Windows uses DCMTK and SumatraPDF. Linux deployments require DCMTK and a CUPS-compatible printing path.
