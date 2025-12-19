# FlowWorklist - Windows Executable Build Guide

This guide explains how to create a standalone Windows executable (.exe) of FlowWorklist to simplify deployment without requiring a local Python installation.

## 📋 Prerequisites

- Python 3.8 or newer installed
- Virtual environment created and activated
- Project dependencies installed (`pip install -r requirements.txt`)

> Note (Development): When running from source (no executable), prefer the Flow CLI for initialization:
> 
> ```powershell
> # Windows PowerShell
> & .\Scripts\Activate.ps1
> pip install -r requirements.txt
> python .\flow.py install
> .\flow start app       # UI at http://127.0.0.1:5000
> .\flow start service   # DICOM MWL at port 11112
> ```

## 🚀 Build Process

### Option 1: Manual Build

#### Full Build (Dashboard + DICOM)

```powershell
 # Install PyInstaller
 pip install pyinstaller

# Gerar executável
pyinstaller --name=FlowWorklist ^
  --onefile ^
  --windowed ^
  --add-data="webui;webui" ^
  --add-data="config.json;." ^
  --hidden-import=pynetdicom ^
  --hidden-import=pydicom ^
  --hidden-import=flask ^
  --collect-all=pynetdicom ^
  --collect-all=pydicom ^
  --collect-all=flask ^
  webui/app.py
```

#### DICOM Service Build (CLI)

```powershell
pyinstaller --name=FlowWorklist-Service ^
  --onefile ^
  --console ^
  --add-data="config.json;." ^
  --hidden-import=pynetdicom ^
  --hidden-import=pydicom ^
  --collect-all=pynetdicom ^
  --collect-all=pydicom ^
  mwl_service.py

> If your deployment needs a specific database driver inside the executable, add `--hidden-import=<driver>` for it (e.g., `oracledb`, `pymysql`, or `psycopg`). By default, DB drivers are not bundled; install them via Plugins in the web UI when running from source.
```

## 📦 Generated Artifacts

After building, you'll find:

```
FlowWorklist/
├── dist/
│   ├── FlowWorklist.exe          # Executável completo (~80-120 MB)
│   └── FlowWorklist-Service.exe  # Serviço DICOM apenas (~60-80 MB)
├── build/                         # Arquivos temporários (pode deletar)
└── FlowWorklist.spec             # Configuração PyInstaller (pode deletar)
```

## 🔧 Executable Deployment

### Step 1: Prepare Files

Copy to the production server:

```
C:\FlowWorklist\
├── FlowWorklist.exe        # Executável principal
├── config.json             # Configuração (EDITE com credenciais reais!)
└── logs\                   # Pasta de logs (será criada automaticamente)
```

### Step 2: Configure config.json

**⚠️ IMPORTANT**: The `config.json` packaged during build may contain sample data. You MUST create a real `config.json` for production:

```json
{
  "server": {
    "aet": "FlowMWL",
    "port": 11112,
    "host": "0.0.0.0"
  },
  "database": {
    "type": "oracle",
    "user": "SEU_USUARIO",
    "password": "SUA_SENHA",
    "dsn": "IP:PORTA/SID",
    "query": "SELECT ... (sua query com 17 colunas)"
  },
  "ui": {
    "language": "pt"
  }
}
```

### Step 3: Run

#### Manual Mode

```powershell
# Run directly
\.\FlowWorklist.exe

# Open the dashboard
Start-Process "http://127.0.0.1:5000"
```

#### Service Mode (Recommended)

##### Using NSSM (Easiest)

```powershell
# Download NSSM: https://nssm.cc/download

# Install service
nssm install FlowWorklist "C:\FlowWorklist\FlowWorklist.exe"
nssm set FlowWorklist AppDirectory "C:\FlowWorklist"
nssm set FlowWorklist DisplayName "FlowWorklist DICOM MWL Server"
nssm set FlowWorklist Description "DICOM Modality Worklist Service with Web Dashboard"
nssm set FlowWorklist Start SERVICE_AUTO_START

# Configurar restart automático
nssm set FlowWorklist AppThrottle 1500
nssm set FlowWorklist AppExit Default Restart
nssm set FlowWorklist AppRestartDelay 5000

 # Start service
 nssm start FlowWorklist

 # Check status
 nssm status FlowWorklist

# Gerenciar
nssm stop FlowWorklist
nssm restart FlowWorklist
nssm remove FlowWorklist confirm
```

##### Using sc.exe (Windows native)

```powershell
# Create service
sc.exe create FlowWorklist binPath= "C:\FlowWorklist\FlowWorklist.exe" start= auto
sc.exe description FlowWorklist "DICOM Modality Worklist Service"

 # Start
 sc.exe start FlowWorklist

 # Manage
 sc.exe stop FlowWorklist
 sc.exe delete FlowWorklist
```

## 🔍 Verification

### Test the Dashboard

```powershell
Start-Process "http://127.0.0.1:5000"
```

### Test the DICOM Port

```powershell
Test-NetConnection -ComputerName localhost -Port 11112
```

### Check Logs

```powershell
Get-Content C:\FlowWorklist\logs\mwl_server.log -Tail 50 -Wait
```

## 📊 Comparison: Executable vs Python

| Aspecto | Executável (.exe) | Python |
|---------|-------------------|--------|
| **Size** | 80-120 MB | ~5 MB |
| **Dependencies** | None (bundled) | Python + pip packages |
| **Installation** | Copy and run | Install Python + venv + deps |
| **Startup** | ~5-10 seconds | ~2-3 seconds |
| **Updates** | Replace .exe | `git pull` + `pip install` |
| **Portability** | ✅ Any Windows | ❌ Requires Python |
| **Disk footprint** | ~120 MB | ~220 MB (with venv) |

## ⚡ Optimizations

### Reduce Executable Size

```powershell
 # Use UPX to compress (~30-40% reduction)
 # Download: https://upx.github.io/

 pyinstaller --onefile --upx-dir=C:\upx webui/app.py
```

### Production-Optimized Build

```powershell
 # Remove debug symbols and optimize
 pyinstaller --onefile ^
  --optimize=2 ^
  --strip ^
  --clean ^
  --noconfirm ^
  webui/app.py
```

## 🐛 Troubleshooting

### Error: "Failed to execute script"

**Cause**: Missing dependencies or modules not found.

**Solution**: Add missing modules:

```powershell
pyinstaller --onefile `
  --hidden-import=MODULO_FALTANTE `
  webui/app.py
```

### Error: "config.json not found"

**Cause**: Executable cannot find the configuration file.

**Solution**: Place `config.json` next to the .exe or use an absolute path.

### Executable starts very slowly

**Cause**: PyInstaller extracts temp files every run.

**Solution**: Use `--onedir` instead of `--onefile`.

### Antivirus blocks the executable

**Cause**: Common false positive with PyInstaller.

**Solution**: 
1. Add AV exception
2. Digitally sign the .exe
3. Use `--onedir` build which is less suspicious

## 📝 Important Notes

1. **Security**: Keep `config.json` with credentials secured
2. **Firewall**: Open port 11112 (DICOM) and 5000 (Dashboard)
3. **Updates**: Replace only the .exe during updates (keep `config.json`)
4. **Logs**: Review logs at `C:\FlowWorklist\logs\` regularly
5. **Backup**: Backup `config.json` before updates

## 🔗 Additional Resources

- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [NSSM Documentation](https://nssm.cc/usage)
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
- [README.md](README.md) - Main documentation

## 📞 Support

For build or executable issues:

1. Check logs in `logs/`
2. Run with `--debug all` for more info
3. See [GitHub Issues](https://github.com/bjmvictor/FlowWorklist/issues)

---

**Last Updated**: December 2025  
**Version**: 1.0.0
