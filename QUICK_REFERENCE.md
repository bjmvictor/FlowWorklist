# FlowWorklist - Quick Reference Card

## 🎯 Project Overview

**FlowWorklist** is a production-grade DICOM Modality Worklist server with management dashboard.

- **DICOM Server**: Listens on port 11112
- **Management UI**: Runs on port 5000
- **Languages**: 10 languages supported
- **Databases**: Oracle, PostgreSQL, MySQL
- **Features**: C-FIND, logging, plugins, i18n

---

## 📊 Database Column Mapping (17 Fields)

Required SQL query must return exactly 17 columns in this order:

```
1. nm_paciente         → PatientName
2. cd_paciente         → PatientID
3. nascimento          → PatientBirthDate (YYYYMMDD)
4. tp_sexo             → PatientSex (M/F/O)
5. exame_descricao     → RequestedProcedureDescription
6. exame_id            → AccessionNumber
7. exame_data          → ScheduledProcedureStepStartDate (YYYYMMDD)
8. exame_hora          → ScheduledProcedureStepStartTime (HHMMSS)
9. medico_responsavel  → ScheduledPerformingPhysicianName
10. modalidade         → Modality (CR/CT/MR/US/RF/etc.)
11. prioridade         → Priority Flag (HIGH/MEDIUM/LOW)
12. tp_atendimento     → Encounter Type
13. cd_atendimento     → StudyInstanceUID / Encounter ID
14. unidade            → Location / Unit Name
15. procedure_code     → ScheduledProcedureStepID
16. code_meaning       → Code Meaning
17. code_scheme        → Code Scheme Designator
```

**Critical**: Column POSITION matters, not names!

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Activate Virtual Environment
```powershell
& .\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Database
Edit `config.json`:
```json
{
  "database": {
    "type": "oracle",
    "user": "your_user",
    "password": "your_password",
    "dsn": "host:1521/database",
    "query": "SELECT ... (17 columns)"
  }
}
```

### Step 4: Use Flow CLI (Windows PowerShell)
```powershell
.\u200bflow install    # one-time wrappers
.\u200bflow startapp   # start the management App
.\u200bflow startservice  # start MWL service
.\u200bflow status     # show App + Service status
```

### Step 5: Open Browser
```
http://127.0.0.1:5000
```

---

## 📁 File Guide

| File | Purpose | Edit? |
|------|---------|-------|
| `mwl_service.py` | DICOM server | Usually not |
| `flow.py` | Command line helper | **YES** |
| `flow.bat` / `flow.ps1` | CLI wrappers | **YES** |
| `config.json` | Database config | **YES** |
| `webui/app.py` | Dashboard code | Usually not |
| `requirements.txt` | Dependencies | If adding packages |
| `README.md` | Documentation | Reference only |

---

## 🔧 Common Configuration Tasks

### Change DICOM Port
In `config.json`:
```json
{
  "server": {
    "port": 11112
  }
}
```

### Change Dashboard Port
In `webui/app.py`, search for `app.run()`:
```python
app.run(host='0.0.0.0', port=5000)
```

### Add New Language
1. Add translations in `webui/templates/base.html`
2. Select language in dashboard

### Change SQL Query
Edit `config.json` → `database.query` field

---

## 🐛 Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| Port already in use | Change port in config/app.py |
| Database connection failed | Check credentials and network connectivity |
| Empty worklist | Verify SQL query returns 17 columns |
| "PatientName" missing | Check database field exists |
| Firewall blocking | Allow port 11112 in firewall |
| Plugin won't install | Run `pip install --upgrade pip` |

---

## 📚 Documentation Map

```
START HERE
    ↓
README.md
├── Overview & Features
├── Installation
├── Configuration → config.json
└── Column Mapping → COLUMN_MAPPING_GUIDE.md
    ├── 17-field reference
    ├── SQL examples
    └── Customization tips

DEPLOYMENT
↓
DEPLOYMENT.md
├── Windows setup
├── Linux setup
├── Docker
├── Kubernetes
└── Security best practices

VERSION CONTROL
↓
GIT_QUICKSTART.md
├── Git initialization
├── Commit & push
└── Remote setup

HISTORY & ROADMAP
↓
CHANGELOG.md
├── v1.0.0 features
└── Future plans
```

---

## 🎨 Dashboard Navigation

```
Dashboard (http://localhost:5000)
├── Home / Status
│   └── Service status, quick actions
├── Configuration
│   └── Database settings, server AET
├── Logs
│   └── View MWLSCP and service logs
├── Tests
│   ├── Database connection test
│   ├── DICOM echo test
│   └── Worklist C-FIND test
├── Plugins
│   ├── Oracle driver status
│   ├── PostgreSQL driver status
│   └── MySQL driver status
└── Language Selector
    └── Switch between 10 languages
```

---

## 🏥 Real-World Example

### Typical Setup
```
Hospital Database
        ↓
SQL Query (17 columns)
        ↓
MWLSCP Server (port 11112)
        ↓
DICOM Equipment
(CT, MRI, X-Ray machines)
        ↓
Management Dashboard (port 5000)
```

### Test the Setup
1. Open dashboard: `http://localhost:5000`
2. Go to "Tests" tab
3. Click "Test Database Connection"
4. Click "Test Worklist"
5. Verify results show patient data

---

## 🔐 Security Checklist

- [ ] Update database credentials in `config.json`
- [ ] Use strong passwords
- [ ] Restrict DICOM port (11112) firewall access
- [ ] Use HTTPS for dashboard (reverse proxy)
- [ ] Enable authentication for dashboard
- [ ] Regular log reviews
- [ ] Backup configuration files
- [ ] Update Python packages regularly

---

## 📊 Performance Tips

| Task | Solution |
|------|----------|
| Slow database queries | Add indexes to join columns |
| High memory usage | Increase virtual memory, monitor with `tasklist` |
| Many worklist items | Implement pagination in dashboard |
| Network latency | Use dedicated network, reduce query complexity |

---

## 🚢 Deployment Checklist

- [ ] Test locally first
- [ ] Verify SQL query with real database
- [ ] Update firewall rules (port 11112)
- [ ] Configure log rotation
- [ ] Set up monitoring/alerting
- [ ] Document custom modifications
- [ ] Backup configuration
- [ ] Test with real DICOM equipment
- [ ] Train users
- [ ] Monitor logs daily

---

## 📞 Support Resources

- **Local**: `logs/mwl_server.log` (DICOM server logs)
- **Dashboard**: `service_logs/*.log` (UI logs)
- **Documentation**: README.md, COLUMN_MAPPING_GUIDE.md, DEPLOYMENT.md
- **Git Help**: GIT_QUICKSTART.md

---

## 🎯 Success Metrics

✅ All systems running:
- DICOM server responding to C-FIND queries
- Dashboard accessible and responsive
- Logs showing no errors
- Database queries returning expected results
- DICOM equipment able to fetch worklist items

---

**Last Updated**: December 16, 2025  
**Version**: 1.0.0
