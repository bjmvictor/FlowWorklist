# FlowWorklist - DICOM Modality Worklist Server with Management UI

A professional-grade **DICOM Modality Worklist (MWL) Server** with an integrated **Flask-based management dashboard**. FlowWorklist bridges your hospital database to DICOM imaging equipment, enabling seamless patient worklist distribution.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Integration](#database-integration)
- [Deployment](#deployment)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)

---

## Overview

FlowWorklist is a complete DICOM Modality Worklist server solution designed for hospitals and imaging centers. It:

1. **Connects to your hospital database** (Oracle, PostgreSQL, MySQL) to fetch pending imaging orders
2. **Converts database records into DICOM format** following the DICOM Modality Worklist standard (ISO 12011-1)
3. **Serves worklist data to imaging equipment** via the DICOM C-FIND protocol
4. **Provides a management dashboard** for monitoring, configuration, and testing
5. **Supports multiple languages** (10 languages: Portuguese, English, Spanish, French, Chinese, Russian, Japanese, Italian, Turkish, Filipino)

### Use Cases

- **Hospital PACS Integration**: Automatically populate imaging modalities with pending orders
- **Imaging Equipment Worklist**: Reduce manual patient entry on CT, MRI, X-ray machines
- **Multi-facility Deployment**: Centralized worklist distribution across multiple units
- **Workflow Automation**: Integrate with existing HIS/RIS systems

---

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
- **Plugin System** - Install/uninstall optional database drivers (Oracle, PostgreSQL, MySQL, pynetdicom)
- **Worklist Testing** - Built-in C-FIND test endpoint for validation
- **Database Connection Test** - Verify database connectivity before deployment

### 🌍 Internationalization (i18n)

Fully translated into 10 languages with automatic language detection:
- Portuguese (Português) 🇧🇷
- English 🇬🇧
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

```
┌─────────────────────────────────────────────────┐
│   DICOM Imaging Equipment (CT, MRI, X-Ray)     │
│   (DICOM Client via C-FIND Protocol)           │
└────────────────────┬────────────────────────────┘
                     │
        DICOM Protocol (Port 11112)
                     │
     ┌───────────────▼───────────────┐
     │   MWLSCP.py (DICOM Server)   │
     │   ├─ C-FIND Service Class    │
     │   ├─ Dataset Builder         │
     │   └─ Filter Processing       │
     └────────────┬──────────────────┘
                  │
        SQL Query (Database)
                  │
     ┌───────────▼─────────────┐
     │  Hospital Database      │
     │  (Oracle/PostgreSQL/MySQL)
     │  ├─ Patients            │
     │  ├─ Orders              │
     │  └─ Procedures          │
     └─────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  Flask Management Dashboard (webui/app.py)              │
│  ├─ Service Control Panel                              │
│  ├─ Configuration Editor                               │
│  ├─ Real-time Monitoring                               │
│  ├─ Log Viewer                                          │
│  ├─ Plugin Manager                                      │
│  └─ Worklist Test Interface                             │
└──────────────────────────────────────────────────────────┘
   (http://localhost:5000)
```

---

## Installation

### Prerequisites

- **Python 3.8+** (3.10+ recommended)
- **Virtual Environment** (venv recommended)
- **Database Client Library** (cx_Oracle for Oracle, psycopg2 for PostgreSQL, PyMySQL for MySQL)
- **Windows PowerShell 5.1+** or **Linux/Mac shell**

### Step 1: Clone or Download

```bash
git clone https://github.com/yourusername/FlowWorklist.git
cd FlowWorklist
```

### Step 2: Create Virtual Environment

```powershell
# Windows PowerShell
python -m venv .
& .\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .
source bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Database Connection

Edit `config.json` with your database credentials:

```json
{
  "database": {
    "type": "oracle",
    "user": "your_db_user",
    "password": "your_db_password",
    "dsn": "your_host:1521/your_database"
  }
}
```

### Step 5: Start Services

```powershell
# Start Management Dashboard (Port 5000)
python launch_flask.py

# Or in a separate terminal, start MWLSCP directly (Port 11112)
python MWLSCP.py
```

---

## Configuration

### config.json Reference

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
    "language": "pt"               // Default UI language (pt, en, es, fr, zh, ru, ja, it, tr, fil)
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
| 12 | `col_encounter_type` | **Encounter Type** | Type of hospital visit or encounter | Text | `URGENCIA`, `INTERNACAO`, `AMBULATORIO` |
| 13 | `col_encounter_id` | **StudyInstanceUID / Encounter ID** | Unique identifier for the patient encounter/admission | Text or numeric | `456789` |
| 14 | `col_unit_name` | **Location / Service Area** | Hospital unit or sector where request originated | Text | `EMERGENCY ROOM`, `RAIO-X` |
| 15 | `col_procedure_code` | **ScheduledProcedureStepID (Procedure Code)** | Coded value identifying the specific procedure | Text (alphanumeric) | `FCR0101` |
| 16 | `col_code_meaning` | **Code Meaning / Description** | Descriptive meaning of the procedure code | Text | `CHEST X-RAY` |
| 17 | `col_code_scheme` | **Code Scheme Designator** | Coding system used (CBR, SNOMED, DCM, etc.) | Text | `CBR` |

### Example Oracle Query

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
    'FCR'||wk.procedure_code_value,                          -- 15. Procedure Code
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
- ✅ **Use ^ separator** in names (e.g., `SMITH^JOHN^M`)
- ✅ **Use standard DICOM modality codes** (CR, CT, MR, US, RF, etc.)
- ❌ **Don't reorder columns** - position is what matters, not names
- ❌ **Don't skip columns** - always return exactly 17

For detailed customization examples, see [COLUMN_MAPPING_GUIDE.md](COLUMN_MAPPING_GUIDE.md)

---

## Deployment

### Local Testing (Development)

```powershell
# Terminal 1: Start MWLSCP Server
python MWLSCP.py

# Terminal 2: Start Management Dashboard
python launch_flask.py
# Then open http://localhost:5000
```

### Production Deployment

#### Windows Service Installation

```powershell
# Option 1: Using NSSM (Non-Sucking Service Manager)
nssm install FlowMWL "C:\path\to\FlowWorklist\Scripts\python.exe" "C:\path\to\FlowWorklist\MWLSCP.py"
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
CMD ["python", "MWLSCP.py"]
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
ExecStart=/opt/FlowWorklist/venv/bin/python MWLSCP.py
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

### Management Dashboard (Flask)

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

The MWLSCP server listens on port 11112 and implements the DICOM Modality Worklist Information Model (UID 1.2.840.10008.5.1.4.31).

#### Supported Query Tags

- **PatientName** - Wildcard or exact match
- **PatientID** - Exact match
- **PatientBirthDate** - Exact match (YYYYMMDD)
- **PatientSex** - Exact match (M/F/O)
- **Modality** - Exact match (CR, CT, MR, US, etc.)
- **ScheduledProcedureStepStartDate** - Exact match (YYYYMMDD)
- **ScheduledProcedureStepStartTime** - Exact match (HHMMSS)
- **AccessionNumber** - Exact match or wildcard

#### Example: findscu Query

```bash
# Query all pending orders
findscu -aec FlowMWL -aet ConsoleApp 192.168.1.3 11112

# Query specific patient
findscu -aec FlowMWL -aet ConsoleApp 192.168.1.3 11112 \
  -k PatientName="SMITH*" \
  -k PatientID="12345678"
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
1. Verify MWLSCP.py is running: `tasklist | findstr python`
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
5. Ensure all required database client libraries are installed (`pip install cx_Oracle`)

### DICOM Client Receives Empty Worklist

**Problem**: C-FIND returns no results even though data exists

**Solutions**:
1. Verify SQL query returns results: `select count(*) from (...)`
2. Check query WHERE conditions are not too restrictive
3. Verify column order matches documentation (17 columns exactly)
4. Check data formatting (dates, times, modality codes)
5. Review column mapping in config.json

### Plugin Installation Fails

**Problem**: Cannot install Oracle, PostgreSQL, or MySQL drivers

**Solutions**:
1. Install pip update: `pip install --upgrade pip`
2. Check internet connectivity
3. Verify Python version (3.8+)
4. Try manual installation: `pip install cx_Oracle psycopg2-binary PyMySQL`

---

## Project Structure

```
FlowWorklist/
├── MWLSCP.py                  # DICOM MWL Server (core application)
├── launch_flask.py            # Entry point for management dashboard
├── config.json                # Database and server configuration
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── COLUMN_MAPPING_GUIDE.md   # Detailed column mapping documentation
│
├── webui/                     # Flask management dashboard
│   ├── app.py                # Flask application and endpoints
│   ├── static/
│   │   ├── style.css         # Dashboard styling (Tailwind CSS)
│   │   └── brand/            # Logo and branding assets
│   └── templates/
│       ├── base.html         # Master template with i18n translations
│       ├── index.html        # Dashboard home
│       ├── config.html       # Configuration editor
│       ├── logs.html         # Log viewer
│       ├── tests.html        # Test interface (C-ECHO, C-FIND, Worklist)
│       ├── plugins.html      # Plugin manager
│       └── view_log.html     # Individual log viewer
│
├── logs/                      # MWLSCP server logs (auto-generated)
├── service_logs/             # Management dashboard logs (auto-generated)
└── Include/, Lib/, Scripts/  # Virtual environment (created by venv)
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
oracledb==3.4.1
psycopg2-binary==2.9.9
PyMySQL==1.1.2
Werkzeug==3.1.4
unidecode==1.4.0
```

---

## License

This project is provided as-is for hospital and medical imaging use.

---

## Support & Documentation

- **Column Mapping**: See [COLUMN_MAPPING_GUIDE.md](COLUMN_MAPPING_GUIDE.md)
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
**Version**: 1.0.0
