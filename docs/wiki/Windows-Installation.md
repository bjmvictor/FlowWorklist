# Windows Installation

Requirements: supported Windows, 64-bit Python 3.10+, database/modality network access, and the native database client when required.

```powershell
git clone https://github.com/bjmvictor/FlowWorklist.git
cd FlowWorklist
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item config.example.json config.json
.\.venv\Scripts\python.exe webui\app.py
```

Open `http://127.0.0.1:5000`. Validate the database, C-ECHO, and C-FIND from **Tests** before production deployment.

Before updating, back up `config.json` and MPPS actions, stop the service, update the code, and refresh dependencies. Git ignores the local configuration.
