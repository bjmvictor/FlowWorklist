# -*- mode: python ; coding: utf-8 -*-

import os

from PyInstaller.utils.hooks import collect_submodules

PROJECT_ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

hiddenimports = [
    "webui.app",
    "mwl_service",
    "mpps_service",
    "dicom_printer_service",
    "flow",
    "mpps_actions",
    "oracledb",
    "psycopg2",
    "pymysql",
    "waitress",
]
hiddenimports += collect_submodules("cryptography.hazmat.primitives.kdf")

a = Analysis(
    [os.path.join(PROJECT_ROOT, "packaging", "entrypoint.py")],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        (os.path.join(PROJECT_ROOT, "webui", "templates"), "webui/templates"),
        (os.path.join(PROJECT_ROOT, "webui", "static"), "webui/static"),
        (os.path.join(PROJECT_ROOT, "config.initial.json"), "."),
        (os.path.join(PROJECT_ROOT, "config.example.json"), "."),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FlowWorklist",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FlowWorklist",
)
