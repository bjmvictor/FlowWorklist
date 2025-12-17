@echo off
REM MWLSCP Service Manager - App (Web UI) Launcher
REM Launch the App using Flow CLI wrappers

cd /d "C:\Users\benjamin.vieira\Documents\FlowWorklist"

REM Ativar venv
call Scripts\activate.bat

REM Start App via Flow CLI
python flow.py startapp

REM Keep window
pause
