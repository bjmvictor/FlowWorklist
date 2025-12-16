import subprocess
import time
import webbrowser
from pathlib import Path

# Caminho para o diretório e app
work_dir = Path(__file__).parent
app_script = work_dir / "webui" / "app.py"

# Iniciar Flask como subprocess detachado
import os
import sys

# Configurar variáveis de ambiente
env = os.environ.copy()
env['PYTHONUNBUFFERED'] = '1'

# Iniciar Flask em background sem console visível
if sys.platform == 'win32':
    # Windows: use CREATE_NO_WINDOW
    CREATE_NO_WINDOW = 0x08000000
    process = subprocess.Popen(
        [str(work_dir / "Scripts" / "python.exe"), str(app_script)],
        cwd=str(work_dir),
        env=env,
        creationflags=CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print(f"Flask iniciado com PID: {process.pid}")
else:
    process = subprocess.Popen(
        [sys.executable, str(app_script)],
        cwd=str(work_dir),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print(f"Flask iniciado com PID: {process.pid}")

# Aguardar Flask ficar pronto
time.sleep(3)

# Abrir navegador
try:
    webbrowser.open("http://127.0.0.1:5000")
    print("Navegador aberto em http://127.0.0.1:5000")
except:
    print("Não foi possível abrir o navegador automaticamente")
    print("Acesse http://127.0.0.1:5000 manualmente")

print("Flask está rodando em background")
print("Para parar: taskkill /F /IM python.exe")
