import subprocess
import time
import webbrowser
from pathlib import Path

# Paths to workspace and UI app
work_dir = Path(__file__).parent
app_script = work_dir / "webui" / "app.py"
pid_file = work_dir / "app.pid"

# Launch the App as a detached subprocess
import os
import sys

# Configurar variáveis de ambiente
env = os.environ.copy()
env['PYTHONUNBUFFERED'] = '1'

# Start App in background without a visible console
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
    print(f"App started with PID: {process.pid}")
else:
    process = subprocess.Popen(
        [sys.executable, str(app_script)],
        cwd=str(work_dir),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print(f"App started with PID: {process.pid}")

# Write App PID to file for safe stopping later
try:
    pid_file.write_text(str(process.pid))
except Exception:
    pass

# Wait a moment for the App to be ready
time.sleep(3)

# Open browser
try:
    webbrowser.open("http://127.0.0.1:5000")
    print("Browser opened at http://127.0.0.1:5000")
except:
    print("Could not open the browser automatically")
    print("Please visit http://127.0.0.1:5000 manually")

print("App is running in background")
print("To stop safely: use 'flow stopapp' or kill PID from app.pid")
