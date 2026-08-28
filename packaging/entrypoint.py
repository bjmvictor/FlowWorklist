"""Frozen entry point for the UI and companion DICOM processes."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


executable_name = Path(sys.executable).stem.lower()
role = "app"
if "--role" in sys.argv:
    role_index = sys.argv.index("--role")
    if role_index + 1 < len(sys.argv):
        role = sys.argv[role_index + 1].lower()
        del sys.argv[role_index:role_index + 2]
elif executable_name.endswith("-mwl"):
    role = "mwl"
elif executable_name.endswith("-mpps"):
    role = "mpps"

if role == "diagnostics":
    import cryptography.hazmat.primitives.kdf  # noqa: F401
    import oracledb  # noqa: F401
    import psycopg2  # noqa: F401
    import pymysql  # noqa: F401
    import pydicom  # noqa: F401
    import pynetdicom  # noqa: F401
    import waitress  # noqa: F401

    print("FlowWorklist packaged runtime diagnostics: OK")
elif role == "mwl":
    runpy.run_module("mwl_service", run_name="__main__")
elif role == "mpps":
    runpy.run_module("mpps_service", run_name="__main__")
else:
    runpy.run_module("webui.app", run_name="__main__")
