# FlowWorklist documentation

Each topic has one canonical document. Supporting wiki pages provide short operational entry points and link back to these sources instead of repeating setup instructions.

## Start here

1. [Project overview and first run](../README.md)
2. [Quick operational reference](QUICK_REFERENCE.md)
3. [Production deployment](DEPLOYMENT.md)

## Configuration and data mapping

- [Configuration](wiki/Configuration.md): configuration sections, secrets, and safe defaults.
- [SQL Query Guide](SQL_QUERY_GUIDE.md): the 17-column SQL contract and a query example.
- [Column Mapping Guide](COLUMN_MAPPING_GUIDE.md): detailed database-to-DICOM field behavior.

## Operations

- [Architecture](wiki/Architecture.md): components and the MWL-to-MPPS workflow.
- [Operations and troubleshooting](wiki/Operations-and-Troubleshooting.md): logs, health checks, and common failures.
- [Validation](wiki/Validation.md): pre-production acceptance checks.
- [Security](wiki/Security.md): credentials, network boundaries, and clinical data handling.

## Packaging and source control

- [Build Guide](BUILD_GUIDE.md): Windows executable packaging.
- [Git Quick Start](GIT_QUICKSTART.md): repository setup and release basics.

## Documentation ownership

| Information | Canonical document |
|---|---|
| First installation and basic configuration | `README.md` |
| Day-to-day commands | `QUICK_REFERENCE.md` |
| Production service, network, security, and recovery | `DEPLOYMENT.md` |
| Query output contract | `SQL_QUERY_GUIDE.md` |
| Detailed DICOM mapping | `COLUMN_MAPPING_GUIDE.md` |
| Component and event flow | `wiki/Architecture.md` |

When behavior changes, update the canonical document and keep cross-references concise.
