# FlowWorklist

FlowWorklist is a DICOM Modality Worklist server with a web dashboard for configuration, operation, and diagnostics. It queries a HIS/RIS database and answers modality C-FIND requests. MPPS and DICOM Print are optional.

## Start here

1. [Architecture](Architecture.md)
2. [Windows installation](Windows-Installation.md)
3. [Production with NSSM](Production-NSSM.md)
4. [Configuration](Configuration.md)
5. [Validation](Validation.md)
6. [Operations and troubleshooting](Operations-and-Troubleshooting.md)
7. [Security and backup](Security.md)

| Component | Default port | Recommended exposure |
|---|---:|---|
| Web dashboard | 5000 | Localhost or management network |
| MWL SCP | 11112 | Modality network |
| MPPS SCP | 4101 | Modality network |
| Print SCP | 4100 | Modality network |

> The institution must validate the system before clinical use. It does not replace a certified RIS/PACS.

Copy these files to the `<project>.wiki.git` repository to publish them as a GitHub Wiki. They also work directly under `docs/`.
