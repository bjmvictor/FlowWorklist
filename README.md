![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![DICOM](https://img.shields.io/badge/DICOM-MWL-green)

# FlowWorklist

A lightweight, vendor-neutral **DICOM Modality Worklist (MWL)** server with a user-friendly web interface for management.

- 🏥 Connects to hospital databases (Oracle, PostgreSQL, MySQL)
- 🧾 Serves pending exams as C-FIND worklists to imaging modalities
- 🌐 Web dashboard to manage, configure, test, and monitor the system

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ installed
- Git installed
- Database access (Oracle, PostgreSQL, or MySQL)
  - Install the specific database driver from **Plugins** in the web UI (drivers are optional and not bundled by default)

Pick your platform and run the commands:

### Windows (PowerShell)
```
git clone https://github.com/bjmvictor/FlowWorklist.git
cd FlowWorklist
python -m venv .
.\Scripts\Activate.ps1
pip install -r requirements.txt
python .\flow.py install
.\flow start app

```

### Windows (CMD)
```
git clone https://github.com/bjmvictor/FlowWorklist.git
cd FlowWorklist
python -m venv .
.\Scripts\activate.bat
pip install -r requirements.txt
python flow.py install
flow start app

```

### Linux/macOS
```
git clone https://github.com/bjmvictor/FlowWorklist.git
cd FlowWorklist
python3 -m venv .
source bin/activate
pip install -r requirements.txt
python flow.py start app

```

## ⚙️ Configure Before Starting the Service

1. Open your browser: **`http://localhost:5000`** → Go to **Configuration**
2. **⚠️ IMPORTANT**: Before starting the DICOM service, go to the **Configuration** tab and:
   - Configure the database connection (Oracle / PostgreSQL / MySQL)
   - Set the DICOM server parameters (AET, port)
   - Paste your SQL query returning **17 columns** (see Column Mapping Guide)  
     *Or use a dummy query for testing*
3. Go to **Tests** and click **“Test Database Connection”** and **“Test Worklist”**

Only after the configuration is valid, start the DICOM service.

### Start the Service
- **Web UI**: Click **Start Service**
- **PowerShell**: `./flow start service`
- **CMD**: `flow start service`
- **Linux/macOS**: `python flow.py start service`

---

## 🧰 Useful Commands

- `flow start all` → Start both app and service
- `flow start app` → Start the dashboard (port 5000)
- `flow start service [--config path]` → Start MWL DICOM server (port 11112)
- `flow stop all` → Stop both
- `flow stop app` / `flow stop service` → Stop dashboard or service
- `flow restart all|app|service [--config path]` → Restart targets
- `flow status` → Show App + Service status
- `flow install [--add-to-path]` → Generate wrappers; optionally add to PATH (admin for system PATH)
- `flow uninstall` → Remove generated wrappers from this folder

Optional (Windows, System PATH): run terminal as Administrator then `python flow.py install --add-to-path` to use `flow` from any directory.
> ⚠️ **Note**: Administrator privileges are required to modify System PATH. If you don't have admin access, you can add the FlowWorklist directory to your User PATH manually through System Environment Variables.

---

## 📚 Docs

- Column mapping reference → [COLUMN_MAPPING_GUIDE.md](docs/COLUMN_MAPPING_GUIDE.md)
- Deployment guide → [DEPLOYMENT.md](docs/DEPLOYMENT.md)
- Quick reference card → [QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)
- Build executable (Windows) → [BUILD_GUIDE.md](docs/BUILD_GUIDE.md)

---

## ✅ What “Works” Looks Like

- Dashboard loads at http://localhost:5000
- Database tests pass
- DICOM service responds to C-FIND on port 11112
- Worklist items show expected patient data

---

## 🔒 Notes

- Do not commit real credentials; use placeholders in `config.json`
- Keep dependencies updated (`pip install -r requirements.txt`)

## Features

### 🎯 Core DICOM Features

- **DICOM Modality Worklist (MWL)** - C-FIND Service Class Provider
- **Flexible Query Support** - PatientName, PatientID, Modality, Date, Time filters
- **Complete Dataset Serialization** - All DICOM tags properly mapped and formatted
- **ScheduledProcedureStep Sequences** - Full support for procedure codes and scheduling info
- **Multiple Modality Support** - CR (Radiography), CT, MR, US, RF, NM, PT, etc.
- **International Character Support** - ISO IR 192 (UTF-8) for international patient names

### 💼 Management Dashboard

- **Service Control** - Start, stop, restart MWLSCP server with one click
- **Real-time Monitoring** - View service status, PID, memory usage
- **Configuration UI** - Edit database connections and server settings
- **Log Viewer** - Browse application and service logs in real-time
- **Plugin System** - Install/uninstall optional database drivers and tools (Oracle, PostgreSQL, MySQL, pynetdicom)
- **Worklist Testing** - Built-in C-FIND test endpoint for validation
- **Database Connection Test** - Verify database connectivity before deployment

### 🌍 Internationalization (i18n)

Fully translated into 10 languages with automatic language detection:
- Portuguese (Português) 🇧🇷
- English en
- Spanish (Español) 🇪🇸
- French (Français) 🇫🇷
- Chinese (中文) 🇨🇳
- Russian (Русский) 🇷🇺
- Japanese (日本語) 🇯🇵
- Italian (Italiano) 🇮🇹
- Turkish (Türkçe) 🇹🇷
- Filipino (Pilipino) 🇵🇭

---

## Architecture

The system is composed of two main components:

1. **MWLSCP Server**
   - Implements the DICOM Modality Worklist Information Model
   - Handles C-FIND requests from imaging modalities
   - Queries the hospital database in real time

2. **Management Dashboard**
   - Web-based UI for configuration and monitoring
   - Controls the lifecycle of the MWL service
   - Provides built-in testing and diagnostics

Dashboard URL: (http://localhost:5000)

---

### Available Flow Commands

| Command | Purpose |
|---------|---------|
| `flow install [--add-to-path]` | Initialize CLI wrappers; optionally add to system PATH |
| `flow uninstall` | Remove generated wrappers from the current folder |
| `flow start all` | Start both App and Service together (recommended) |
| `flow start app` | Start management dashboard (port 5000) |
| `flow start service [--config path]` | Start DICOM MWL server (port 11112) |
| `flow stop all` | Stop both Service and App gracefully (recommended) |
| `flow stop app` | Stop management dashboard gracefully |
| `flow stop service` | Stop DICOM MWL server |
| `flow restart all|app|service [--config path]` | Restart targets |
| `flow status` | Show App and Service status |

### Alternative: Windows Executable
For easier deployment on Windows without Python installation:

```powershell
# Build standalone executable (UI)
pyinstaller --name=FlowWorklist --onefile --windowed --add-data="webui;webui" --add-data="config.json;." webui/app.py

# Service-only build
pyinstaller --name=FlowWorklist-Service --onefile --console --add-data="config.json;." mwl_service.py

# Deploy and run
.\dist\FlowWorklist.exe
```

📖 **Complete guide**: [BUILD_GUIDE.md](docs/BUILD_GUIDE.md)

**Benefits**:
- ✅ No Python installation required
- ✅ Single .exe file (~80-120 MB)
- ✅ Easy service installation with NSSM
- ✅ Portable across Windows systems

---

## Configuration

### config.json Reference (Remove comments to use)

> ⚠️ JSON does not support comments. Remove all comments before using this file in production.
```json
{
  "server": {
    "aet": "FlowMWL",              // DICOM Application Entity Title (identifier for the server)
    "port": 11112,                 // DICOM listening port (standard MWL port)
    "host": "0.0.0.0",            // Network interface to bind to
    "client_aet": "Console"        // Expected client AET for filtering
  },
  "database": {
    "type": "oracle",              // Database type: oracle, postgresql, mysql
    "user": "db_user",             // Database username
    "password": "db_password",     // Database password
    "dsn": "host:1521/database",   // Connection string
    "query": "SELECT ..."          // SQL query returning 17 columns (see Column Mapping)
  },
  "ui": {
    "language": "en"               // Default UI language (pt, en, es, fr, zh, ru, ja, it, tr, fil)
  }
}
```

---

## Database Integration

### Column Mapping Guide

Your SQL query **must return exactly 17 columns** in the following order. Column names don't matter—**only position matters**.

#### Database Column → DICOM Field Mapping

| Pos | Database Column | DICOM Field | Description | Format | Example |
|-----|---|---|---|---|---|
| 1 | `col_patient_name` | **PatientName** | The full name of the patient | Text (use ^ for name parts) | `SMITH^JOHN^M` |
| 2 | `col_patient_id` | **PatientID** | Unique patient identifier in the hospital system | Text or numeric | `12345678` |
| 3 | `col_birth_date` | **PatientBirthDate** | Patient's date of birth for demographics | YYYYMMDD | `19751025` |
| 4 | `col_patient_sex` | **PatientSex** | Biological sex of the patient | M/F/O | `M` |
| 5 | `col_exam_description` | **RequestedProcedureDescription** | Free-text description of the requested procedure | Text | `RX TORAX PA E LATERAL` |
| 6 | `col_accession_number` | **AccessionNumber / RequestedProcedureID** | Unique order identifier | Text or numeric | `P102025` |
| 7 | `col_exam_date` | **ScheduledProcedureStepStartDate** | Scheduled or requested date for the exam | YYYYMMDD | `20251216` |
| 8 | `col_exam_time` | **ScheduledProcedureStepStartTime** | Scheduled or requested time for the exam | HHMMSS (24-hour) | `143000` |
| 9 | `col_physician_name` | **ScheduledPerformingPhysicianName** | Name of physician responsible for ordering/referring exam | Text (use ^ for name parts) | `JONES^MARY` |
| 10 | `col_modality` | **Modality** | Type of imaging equipment (CR, CT, MR, US, RF, NM, PT) | 2-letter DICOM code | `CR` |
| 11 | `col_priority` | **Priority Flag** | Priority level based on triage classification | Text | `HIGH`, `MEDIUM`, `LOW` |
| 12 | `col_encounter_type` | **Encounter Type** | Type of hospital visit or encounter | Text | `URGENCY`, `INTERNAL`, `AMBULATORY` |
| 13 | `col_encounter_id` | **Encounter ID** | Unique identifier for the patient encounter/admission | Text or numeric | `456789` |
| 14 | `col_unit_name` | **Location / Service Area** | Hospital unit or sector where request originated | Text | `EMERGENCY ROOM`, `X-RAY` |
| 15 | `col_procedure_code` | **ScheduledProcedureStepID (Procedure Code)** | Coded value identifying the specific procedure | Text (alphanumeric) | `FCR0101-0000` |
| 16 | `col_code_meaning` | **Code Meaning / Description** | Descriptive meaning of the procedure code | Text | `CHEST X-RAY` |
| 17 | `col_code_scheme` | **Code Scheme Designator** | Coding system used (CBR, SNOMED, DCM, etc.) Or Local using 99<UNIT TAG> | Text | `99UNIT` |

### Example of a Real-World Oracle SQL Query Used in Production

```sql
SELECT
    paciente.nm_paciente,                                    -- 1. Patient Name
    paciente.cd_paciente,                                    -- 2. Patient ID
    TO_CHAR(paciente.dt_nascimento, 'YYYYMMDD'),            -- 3. Birth Date
    paciente.tp_sexo,                                        -- 4. Patient Sex
    exa_rx.ds_exa_rx,                                        -- 5. Exam Description
    ped_rx.cd_ped_rx,                                        -- 6. Accession Number
    TO_CHAR(ped_rx.dt_pedido, 'YYYYMMDD'),                  -- 7. Exam Date
    TO_CHAR(ped_rx.hr_pedido, 'HH24MISS'),                  -- 8. Exam Time
    prestador.nm_prestador,                                  -- 9. Physician Name
    CASE WHEN exa_rx.ds_exa_rx LIKE '%RX%' THEN 'CR' ELSE 'CT' END,  -- 10. Modality
    CASE WHEN sacr_classificacao.ds_sigla = 'PI' THEN 'HIGH'
         WHEN sacr_classificacao.ds_sigla = 'PII' THEN 'MEDIUM'
         ELSE 'LOW' END,                                     -- 11. Priority
    decode(atendime.tp_atendimento, 'U', 'URGENCIA', 'I', 'INTERNACAO', 'A', 'AMBULATORIO'),  -- 12. Encounter Type
    atendime.cd_atendimento,                                 -- 13. Encounter ID
    setor.nm_setor,                                          -- 14. Unit Name
    'FCR'||wk.procedure_code_value,                          -- 15. Procedure Code Like: FCR0000-0000 For FCR Prima Console
    wk.code_meaning,                                         -- 16. Code Meaning
    wk.code_scheme_designator                                -- 17. Code Scheme
FROM dbamv.ped_rx
JOIN dbamv.atendime ON ped_rx.cd_atendimento = atendime.cd_atendimento
JOIN dbamv.paciente ON atendime.cd_paciente = paciente.cd_paciente
JOIN dbamv.itped_rx itped ON itped.cd_ped_rx = ped_rx.cd_ped_rx
JOIN dbamv.exa_rx ON itped.cd_exa_rx = exa_rx.cd_exa_rx
LEFT JOIN dbamv.de_para_worklist_rx wk ON to_char(wk.cd_exa_rx) = to_char(itped.cd_exa_rx)
LEFT JOIN dbamv.setor ON ped_rx.cd_setor = setor.cd_setor
LEFT JOIN dbamv.prestador ON prestador.cd_prestador = ped_rx.cd_prestador
LEFT JOIN dbamv.triagem_atendimento triagem ON atendime.cd_atendimento = triagem.cd_atendimento
LEFT JOIN dbamv.sacr_classificacao ON triagem.cd_cor_referencia = sacr_classificacao.cd_cor_referencia
WHERE ped_rx.cd_ped_rx IN (SELECT cd_ped_rx FROM dbamv.itped_rx WHERE sn_realizado = 'N')
  AND ped_rx.cd_set_exa IN ('4','39');
```

ℹ️The auxiliary de/para table (de_para_worklist_rx) acts as a semantic bridge between internal hospital exam identifiers and DICOM-compliant procedure codes and meanings, ensuring that the exam requested in the HIS is correctly mapped to the modality’s exposure menu on the workstation.

### Quick Reference: Key Field Mappings

```
Database Fields → DICOM Worklist Fields

cd_paciente          → PatientID
nm_paciente          → PatientName
tp_sexo              → PatientSex (M/F)
nascimento           → PatientBirthDate (YYYYMMDD)
modalidade           → Modality (CR/CT/MR/...)
exame_id             → AccessionNumber / RequestedProcedureID
exame_data           → ScheduledProcedureStepStartDate (YYYYMMDD)
exame_hora           → ScheduledProcedureStepStartTime (HHMMSS)
exame_descricao      → RequestedProcedureDescription
medico_responsavel   → ScheduledPerformingPhysicianName
procedure_code_value → ScheduledProcedureStepID (Procedure Code)
code_scheme_designator → Code Scheme Designator
code_meaning         → Code Meaning / Description
```

### Important Notes

- ✅ **Always return 17 columns** in the specified order
- ✅ **Format dates as YYYYMMDD** (8 digits)
- ✅ **Format times as HH24MISS** (6 digits in 24-hour format)
- ✅ **Use standard DICOM modality codes** (CR, CT, MR, US, RF, etc.)
- ❌ **Don't reorder columns** - position is what matters, not names
- ❌ **Don't skip columns** - always return exactly 17

For detailed customization examples, see [COLUMN_MAPPING_GUIDE.md](docs/COLUMN_MAPPING_GUIDE.md)

---

## Deployment

### Local Testing (Development)

```powershell
# Windows (single terminal, Flow CLI)
.\flow startservice     # MWL DICOM Server
.\flow startapp         # Management App (UI)
# Then open http://127.0.0.1:5000

# Linux/macOS
python flow.py startservice
python flow.py startapp
```

### Production Deployment

#### Windows Service Installation

```powershell
# Option 1: Using NSSM (Non-Sucking Service Manager)
nssm install FlowMWL "C:\path\to\FlowWorklist\Scripts\python.exe" "C:\path\to\FlowWorklist\mwl_service.py"
nssm set FlowMWL AppDirectory "C:\path\to\FlowWorklist"
nssm start FlowMWL
```

#### Linux/Docker Deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

EXPOSE 11112 5000
CMD ["python", "mwl_service.py"]
```

```bash
docker build -t flowworklist .
docker run -d -p 11112:11112 -p 5000:5000 -v /path/to/config.json:/app/config.json flowworklist
```

#### Systemd Service (Linux)

```ini
# /etc/systemd/system/flowmwl.service
[Unit]
Description=FlowWorklist DICOM MWL Server
After=network.target

[Service]
Type=simple
User=dicom
WorkingDirectory=/opt/FlowWorklist
ExecStart=/opt/FlowWorklist/venv/bin/python mwl_service.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable flowmwl
sudo systemctl start flowmwl
```

---

## API Reference

### Management Dashboard

#### Endpoints

| Endpoint | Method | Description |
|----------|--------|---|
| `/` | GET | Main dashboard |
| `/api/service/status` | GET | Get service status (running/stopped) |
| `/api/service/start` | POST | Start MWLSCP service |
| `/api/service/stop` | POST | Stop MWLSCP service |
| `/api/service/restart` | POST | Restart MWLSCP service |
| `/api/logs` | GET | Fetch recent logs |
| `/api/config` | GET, POST | Get/update configuration |
| `/test/database` | POST | Test database connection |
| `/test/worklist` | POST | Test DICOM C-FIND query |
| `/plugin/status/{plugin}` | GET | Check if plugin is installed |
| `/plugin/install/{plugin}` | POST | Install optional plugin |
| `/plugin/uninstall/{plugin}` | POST | Uninstall optional plugin |
| `/set-language` | POST | Set UI language preference |

#### Test Worklist Endpoint

```bash
curl -X POST http://localhost:5000/test/worklist
```

Response:
```json
{
  "status": "success",
  "count": 2,
  "host": "192.168.1.3",
  "port": 11112,
  "aet": "FlowMWL",
  "details": {
    "items": [
      {
        "PatientName": "SMITH^JOHN",
        "PatientID": "12345678",
        "PatientBirthDate": "19751025",
        "PatientSex": "M",
        "Modality": "CR",
        "AccessionNumber": "P102025",
        "RequestedProcedureDescription": "RX TORAX PA E LATERAL",
        "ScheduledProcedureStepSequence": [...]
      }
    ]
  }
}
```

### DICOM C-FIND Service

The MWLSCP server listens on port 11112 and implements the DICOM Modality Worklist Information Model (DICOM PS 3)

#### Supported Query Tags

- **PatientName** - Wildcard or exact match
- **PatientID** - Exact match
- **PatientBirthDate** - Exact match (YYYYMMDD)
- **PatientSex** - Exact match (M/F/O)
- **Modality** - Exact match (CR, CT, MR, US, etc.)
- **ScheduledProcedureStepStartDate** - Exact match (YYYYMMDD)
- **ScheduledProcedureStepStartTime** - Exact match (HHMMSS)
- **AccessionNumber** - Exact match or wildcard

#### Example using DCMTK: findscu Query

```bash
# Query all pending orders
findscu -aec FlowMWL -aet Client <IP/HOST> 11112

# Query specific patient
findscu -k PatientName="SMITH*" -k PatientID="12345678" -aec FlowMWL -aet Client <IP/HOST> 11112
```

---

## Troubleshooting

### MWLSCP Service Won't Start

**Problem**: Service fails to start or crashes immediately

**Solutions**:
1. Check `logs/mwl_server.log` for error messages
2. Verify database connection in `config.json`
3. Ensure all 17 columns are returned by your SQL query
4. Verify date/time formats (YYYYMMDD / HHMMSS)

### Connection Refused on Port 11112

**Problem**: DICOM clients cannot connect to the server

**Solutions**:
1. Verify mwl_service.py is running: `tasklist | findstr python`
2. Check firewall rules allow port 11112
3. Verify `host: 0.0.0.0` in config.json
4. Check server logs: `type logs\mwl_server.log`

### Database Connection Error

**Problem**: "SQL execution error" in logs

**Solutions**:
1. Test query manually in your database client
2. Verify credentials in `config.json`
3. Check network connectivity to database server
4. Use `/test/database` endpoint in dashboard to diagnose
5. Ensure all required database client libraries are installed in `/plugins`

### DICOM Client Receives Empty Worklist

**Problem**: C-FIND returns no results even though data exists

**Solutions**:
1. Verify SQL query returns results: `select count(*) from (...)`
2. Check query WHERE conditions are not too restrictive
3. Verify column order matches documentation (17 columns exactly - see [COLUMN_MAPPING_GUIDE.md](docs/COLUMN_MAPPING_GUIDE.md))
4. Check data formatting (dates, times, modality codes)
5. Review SQL query in config.json or via web interface

### Plugin Installation Fails

**Problem**: Cannot install Oracle, PostgreSQL, or MySQL drivers

**Solutions**:
1. Install pip update (On venv): `pip install --upgrade pip`
2. Check internet connectivity
3. Verify Python version (3.8+)
4. Try manual installation: `pip install cx_Oracle psycopg2-binary PyMySQL`

---

## Project Structure

```
FlowWorklist/
├── mwl_service.py             # DICOM MWL Server (core application)
├── flow.py                    # Flow CLI helper (app/service commands)
├── config.json                # Database and server configuration
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── COLUMN_MAPPING_GUIDE.md    # Detailed column mapping documentation
│
├── webui/                     # Flask management dashboard
│   ├── app.py                 # Flask application and endpoints
│   ├── static/
│   │   ├── style.css          # Dashboard styling (Tailwind CSS)
│   │   └── brand/             # Logo and branding assets
│   └── templates/
│       ├── base.html          # Master template with i18n translations
│       ├── index.html         # Dashboard home
│       ├── config.html        # Configuration editor
│       ├── logs.html          # Log viewer
│       ├── tests.html         # Test interface (C-ECHO, C-FIND, Worklist)
│       ├── plugins.html       # Plugin manager
│       └── view_log.html      # Individual log viewer
│
├── logs/                      # MWLSCP server logs (auto-generated)
├── service_logs/              # Management dashboard logs (auto-generated)
└── Include/, Lib/, Scripts/   # Virtual environment (created by venv)
```

---

## Requirements

### System Requirements

- **CPU**: 2+ cores
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 100MB for application + logs
- **Network**: Dedicated connection to database, port 11112 open for DICOM clients

### Python Dependencies

See `requirements.txt`:

```
Flask==3.1.2
pynetdicom==3.0.4
pydicom==3.0.1
cx_Oracle==8.3.0
psycopg2-binary==2.9.9
PyMySQL==1.1.2
Werkzeug==3.1.4
unidecode==1.4.0
```

---

## License

This project is intended for free use in hospitals and medical institutions.
Commercial resale or proprietary redistribution is not permitted.

See the LICENSE file for full terms and conditions.

## Regulatory Notice

This software does not replace certified RIS/PACS systems and must be validated
by the institution before clinical use, according to local regulations.

---

## Security Considerations

- Restrict MWL access by AET Title
- Deploy behind hospital firewall
- Do not expose port 11112 to public networks
- Use **read-only** database credentials

---

## Support & Documentation

- **Column Mapping**: See [COLUMN_MAPPING_GUIDE.md](docs/COLUMN_MAPPING_GUIDE.md)
- **Logs**: Check `logs/mwl_server.log` for detailed diagnostics
- **Dashboard**: Access http://localhost:5000 for real-time monitoring
- **Test Tools**: Use the built-in `/test/worklist` and `/test/database` endpoints

---

## Roadmap

- [ ] Multi-instance deployment support
- [ ] Advanced filtering and caching
- [ ] RESTful API for external integrations
- [ ] Audit logging and compliance reporting
- [ ] High-availability (HA) configuration
- [ ] Performance metrics and analytics dashboard

---

**Last Updated**: December 2025  
**Version**: 1.1.0
