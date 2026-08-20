# FlowWorklist - Documentation Index

## Guia operacional / GitHub Wiki

Start with [wiki/Home.md](wiki/Home.md). It covers architecture, Windows installation, NSSM production deployment, configuration, validation, troubleshooting, and security.

Complete guide to FlowWorklist documentation and setup.

## 📚 Documentation Files

### 🚀 Getting Started (Start Here!)

1. **[README.md](README.md)** - Main documentation
   - Project overview and features
   - Architecture and design
   - Installation step-by-step
   - Configuration guide
   - Complete troubleshooting

2. **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick lookup
   - 5-minute quick start
   - Column mapping reference
   - Common issues and fixes
   - File guide
   - Dashboard navigation

### 💾 Database Integration

3. **[COLUMN_MAPPING_GUIDE.md](COLUMN_MAPPING_GUIDE.md)** - Database mapping
   - 17-column reference table
   - Database to DICOM mapping
   - SQL query examples (Oracle)
   - Customization examples
   - Testing procedures

4. **[SQL_QUERY_GUIDE.md](SQL_QUERY_GUIDE.md)** - SQL query examples
   - Complete SQL templates
   - Oracle, PostgreSQL, MySQL examples
   - Query customization
   - Performance tips

### 🚢 Deployment & DevOps

5. **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment guide
   - Windows deployment (NSSM, Task Scheduler)
   - Linux deployment (Systemd)
   - Docker deployment (single, docker-compose)
   - Kubernetes deployment (full manifests)
   - Network configuration
   - Security best practices
   - Monitoring and troubleshooting

6. **[BUILD_GUIDE.md](BUILD_GUIDE.md)** - Windows Executable Build
    - Creating standalone .exe files
    - Build automation script
    - Deployment with executables
    - Service installation (NSSM)
    - Troubleshooting build issues
    - Size optimization

### 📦 Version Control

7. **[GIT_QUICKSTART.md](GIT_QUICKSTART.md)** - Git initialization
   - Repository setup
   - Commit and push procedures
   - Branch management
   - Remote configuration
   - Sensitive data protection
   - Troubleshooting

### 📋 Project Tracking

8. **[CHANGELOG.md](../CHANGELOG.md)** - Version history
   - Release notes and updates
   - Feature additions
   - Bug fixes
   - Features and technical details
   - Future roadmap
   - Contributing guidelines

### 🧹 Repository

10. **[CLEANUP_SUMMARY.md](CLEANUP_SUMMARY.md)** - Repository preparation
    - Changes made during setup
    - Files cleaned/removed
    - Git configuration
    - Pre-deployment checklist

---

## 🎯 Choose Your Path

### 👨‍💻 I'm a Developer

1. Read [README.md](README.md) - Overview
2. Read [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Quick start
3. Run locally and test
4. See [GIT_QUICKSTART.md](GIT_QUICKSTART.md) - Version control

### 🗄️ I'm Setting Up the Database

1. Read [COLUMN_MAPPING_GUIDE.md](COLUMN_MAPPING_GUIDE.md) - Column mapping
2. Prepare 17-column SQL query
3. Test with `/test/database` endpoint
4. Verify with `/test/worklist` endpoint

### 🚀 I'm Deploying to Production

1. Read [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
2. Choose environment (Windows/Linux/Docker/K8s)
3. Follow step-by-step instructions
4. Use [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Troubleshooting

### 👨‍💼 I'm Managing the Project

1. Read [README.md](README.md) - Overview
2. Read [CHANGELOG.md](CHANGELOG.md) - History
3. Review [CLEANUP_SUMMARY.md](CLEANUP_SUMMARY.md) - Setup details

---

## 📊 Documentation Overview

| Document | Audience | Length | Focus |
|----------|----------|--------|-------|
| README.md | Everyone | 1400+ lines | Complete overview |
| QUICK_REFERENCE.md | Developers | 300 lines | Quick lookup |
| COLUMN_MAPPING_GUIDE.md | DBA/DevOps | 200 lines | SQL mapping |
| DROPDOWN_MENU_IMPLEMENTATION.md | Frontend Devs | 150 lines | UI dropdown feature |
| SCAN_KILL_FEATURE.md | Full Stack | 100 lines | Process management |
| DEPLOYMENT.md | DevOps/SysAdmin | 400 lines | Deployment |
| BUILD_GUIDE.md | DevOps | 200 lines | .exe building |
| GIT_QUICKSTART.md | Developers | 250 lines | Version control |
| CHANGELOG.md | Everyone | 150 lines | History & plans |
| CLEANUP_SUMMARY.md | Project Managers | 250 lines | Setup details |

---

## 🔍 Find Information

### By Topic

**Installation**
- → [README.md#Installation](README.md)
- → [QUICK_REFERENCE.md#Quick Start](QUICK_REFERENCE.md)

**Configuration**
- → [README.md#Configuration](README.md)
- → [QUICK_REFERENCE.md#File Guide](QUICK_REFERENCE.md)

**Database Integration**
- → [COLUMN_MAPPING_GUIDE.md](COLUMN_MAPPING_GUIDE.md)
- → [README.md#Database Integration](README.md)

**Deployment**
- → [DEPLOYMENT.md](DEPLOYMENT.md)
- → [README.md#Deployment](README.md)

**Troubleshooting**
- → [README.md#Troubleshooting](README.md)
- → [QUICK_REFERENCE.md#Common Issues](QUICK_REFERENCE.md)

**Version Control**
- → [GIT_QUICKSTART.md](GIT_QUICKSTART.md)

**Column Mapping**
- → [COLUMN_MAPPING_GUIDE.md](COLUMN_MAPPING_GUIDE.md)
- → [QUICK_REFERENCE.md#Database Column Mapping](QUICK_REFERENCE.md)

---

## 🎓 Learning Path

### Beginner (0-1 hour)
1. Read QUICK_REFERENCE.md (overview and quick start)
2. Skim README.md (get familiar with structure)
3. Try local installation

### Intermediate (1-3 hours)
1. Read README.md thoroughly
2. Study COLUMN_MAPPING_GUIDE.md
3. Prepare database query
4. Test with dashboard

### Advanced (3+ hours)
1. Study DEPLOYMENT.md for your environment
2. Set up Git repository (GIT_QUICKSTART.md)
3. Deploy to production
4. Monitor and troubleshoot

### Expert (Ongoing)
1. Customize for your specific needs
2. Contribute to roadmap (CHANGELOG.md)
3. Maintain and monitor
4. Document custom changes

---

## 🚀 Quick Links

### Start Here
- [README.md](README.md) - Main documentation

### I Need...
- **Quick start** → [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **Database help** → [COLUMN_MAPPING_GUIDE.md](COLUMN_MAPPING_GUIDE.md)
- **UI dropdown feature** → [DROPDOWN_MENU_IMPLEMENTATION.md](DROPDOWN_MENU_IMPLEMENTATION.md)
- **Process cleanup** → [SCAN_KILL_FEATURE.md](SCAN_KILL_FEATURE.md)
- **Deployment guide** → [DEPLOYMENT.md](DEPLOYMENT.md)
- **Build .exe** → [BUILD_GUIDE.md](BUILD_GUIDE.md)
- **Git help** → [GIT_QUICKSTART.md](GIT_QUICKSTART.md)
- **History** → [CHANGELOG.md](CHANGELOG.md)

### File Locations
- Source code: `mwl_service.py`, `webui/`, `flow.py`
- Configuration: `config.json`
- Logs: `logs/`, `service_logs/`

### Key Directories
- **webui/** - Flask application (templates, static files)
- **logs/** - DICOM server logs
- **service_logs/** - Management dashboard logs

---

## ✅ Before Deployment

- [ ] Read README.md
- [ ] Review COLUMN_MAPPING_GUIDE.md
- [ ] Prepare database query (17 columns)
- [ ] Update config.json with credentials
- [ ] Test locally with QUICK_REFERENCE.md
- [ ] Plan deployment using DEPLOYMENT.md
- [ ] Set up Git (GIT_QUICKSTART.md)
- [ ] Configure firewall (port 11112, 5000)
- [ ] Set up monitoring/logging
- [ ] Document customizations
- [ ] Train users

---

## 🔗 Cross-References

Each document links to related documentation:

```
README.md
├── → QUICK_REFERENCE.md (troubleshooting)
├── → COLUMN_MAPPING_GUIDE.md (database)
├── → DEPLOYMENT.md (deployment)
└── → GIT_QUICKSTART.md (version control)

DEPLOYMENT.md
├── → README.md (overview)
├── → COLUMN_MAPPING_GUIDE.md (database config)
└── → QUICK_REFERENCE.md (troubleshooting)

COLUMN_MAPPING_GUIDE.md
├── → README.md (architecture)
├── → QUICK_REFERENCE.md (column reference)
└── → config.json (configuration)

GIT_QUICKSTART.md
├── → README.md (project overview)
├── → CLEANUP_SUMMARY.md (repository structure)
└── → .gitignore, .gitattributes (configuration)
```

---

## 📞 Support

### Having Issues?

1. Check [QUICK_REFERENCE.md#Common Issues](QUICK_REFERENCE.md)
2. Review [README.md#Troubleshooting](README.md)
3. Check logs in `logs/mwl_server.log`
4. Consult relevant guide:
   - Database: [COLUMN_MAPPING_GUIDE.md](COLUMN_MAPPING_GUIDE.md)
   - Deployment: [DEPLOYMENT.md](DEPLOYMENT.md)
   - Git: [GIT_QUICKSTART.md](GIT_QUICKSTART.md)

### Running Commands?

Use [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for quick syntax reference.

### Need Details?

See [README.md](README.md) for comprehensive documentation.

---

## 📈 Version Information

- **Current Version**: 1.0.0
- **Last Updated**: December 18, 2025
- **Status**: Production Ready
- **See**: [CHANGELOG.md](CHANGELOG.md) for history and roadmap

---

**Created**: December 16, 2025  
**Last Updated**: December 18, 2025  
**Status**: ✅ Ready for Production (Directory reorganized, tests/logs cleaned)
