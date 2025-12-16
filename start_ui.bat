@echo off
REM MWLSCP Service Manager - Flask Web UI Launcher
REM Executa em modo oculto sem janela de terminal visível

cd /d "C:\Users\benjamin.vieira\Documents\FlowWorklist"

REM Ativar venv
call Scripts\activate.bat

REM Iniciar Flask em background
set FLASK_APP=webui/app.py
set FLASK_ENV=development
python -m flask run --host=127.0.0.1 --port=5000

REM Não fechar a janela
pause
