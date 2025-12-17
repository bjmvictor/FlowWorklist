@echo off
SETLOCAL
set ROOT=%~dp0
if exist "%ROOT%Scripts\activate.bat" call "%ROOT%Scripts\activate.bat"
python "%ROOT%flow.py" %*
ENDLOCAL
