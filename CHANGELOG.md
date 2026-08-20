# Changelog

All notable changes to FlowWorklist are documented here.

## Unreleased

- Added configuration-driven automatic MWL/MPPS startup for production services.
- Disabled Flask debug mode and the development reloader by default.
- Improved dashboard navigation and page-load performance.
- Added MPPS actions and optional DICOM Print support.
- Moved local configuration and runtime artifacts out of version control.
- Added an English operations wiki and NSSM deployment guide.

## 2.0 - 2025-12-18

- Added JSON lock files with PID, timestamp, hostname, and instance identity.
- Added stale-lock cleanup and duplicate-process prevention.
- Added grouped CLI lifecycle commands for the app and DICOM services.
- Improved shutdown, restart, status reporting, and orphan-process recovery.
- Added rotating logs and cross-platform process management through `psutil`.

## 1.1

- Added the web management dashboard, database diagnostics, DICOM tests, plugin management, and internationalization.
- Added Oracle, PostgreSQL, and MySQL support.

## 1.0

- Initial DICOM Modality Worklist SCP implementation.
