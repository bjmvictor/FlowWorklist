# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-12-16

### Added
- **DICOM Modality Worklist Server (MWLSCP)**
  - C-FIND Service Class Provider
  - Support for Oracle, PostgreSQL, and MySQL databases
  - Complete DICOM dataset serialization with all tags
  - ScheduledProcedureStep sequences with procedure codes
  - International character support (ISO IR 192 / UTF-8)

- **Management Dashboard (Flask)**
  - Service control (start/stop/restart)
  - Real-time monitoring (status, PID, memory)
  - Configuration editor with JSON validation
  - Log viewer with real-time updates
  - Plugin manager (optional database drivers)
  - DICOM worklist testing interface
  - Database connection tester

- **Internationalization (i18n)**
  - Support for 10 languages
  - Client-side translations with localStorage persistence
  - Dynamic language switching without page reload
  - Portuguese (pt), English (en), Spanish (es), French (fr), Chinese (zh)
  - Russian (ru), Japanese (ja), Italian (it), Turkish (tr), Filipino (fil)

- **Documentation**
  - README.md with comprehensive feature overview
  - COLUMN_MAPPING_GUIDE.md with detailed SQL mapping
  - DEPLOYMENT.md with setup instructions for Windows, Linux, Docker, Kubernetes
  - Architecture diagrams and deployment options

### Technical Details

#### Database Integration
- Position-based column mapping (17-column standard)
- Automatic patient name formatting with ^ delimiters
- Date/time format conversion (YYYYMMDD / HHMMSS)
- NULL value handling with sensible defaults
- Support for complex CASE statements and JOINs

#### DICOM Features
- Modality Worklist Information Model (UID 1.2.840.10008.5.1.4.31)
- Supported query tags: PatientName, PatientID, Modality, Date, Time, etc.
- Procedure code sequences with scheme designators
- Proper Person Name serialization (DICOM PN format)
- Study Instance UID and SOP Instance UID generation

#### Management Features
- Plugin installation system (pip-based)
- Service state persistence
- Detailed logging with rotating file handlers
- Lock file mechanism to prevent duplicate instances
- Process monitoring and recovery

### Architecture
- Modular design with separate DICOM server and Flask dashboard
- Event-driven DICOM protocol handling via pynetdicom
- Async-ready structure for future enhancements
- Clean separation of concerns (server, UI, database)

### File Structure
```
FlowWorklist/
├── MWLSCP.py              # DICOM MWL Server
├── launch_flask.py        # Dashboard launcher
├── webui/                 # Flask application
├── config.json            # Server configuration
├── requirements.txt       # Python dependencies
├── README.md              # Main documentation
├── COLUMN_MAPPING_GUIDE.md
├── DEPLOYMENT.md
└── CHANGELOG.md
```

### Deployment Options
- Windows (PowerShell, NSSM, Task Scheduler)
- Linux (Systemd, standalone)
- Docker (containerized deployment)
- Kubernetes (orchestrated deployment)
- Reverse proxy configuration (Nginx, Apache)

---

## Planned Features

### v1.1.0
- [ ] RESTful API for external integrations
- [ ] Advanced filtering and caching
- [ ] Performance metrics dashboard
- [ ] Audit logging for compliance

### v1.2.0
- [ ] Multi-instance deployment support
- [ ] Load balancing configuration
- [ ] Database connection pooling
- [ ] Enhanced error reporting

### v2.0.0
- [ ] High-availability (HA) setup
- [ ] Geo-redundancy support
- [ ] Advanced analytics and reporting
- [ ] Integration with popular PACS systems

---

## Known Issues

None currently reported. Please submit issues via GitHub or contact support.

---

## Contributors

- Benjamin Vieira - Initial development and architecture

---

## License

This project is provided as-is for hospital and medical imaging use.

---

## Support

- GitHub Issues: For bug reports and feature requests
- Documentation: See README.md, COLUMN_MAPPING_GUIDE.md, DEPLOYMENT.md
- Logs: Check logs/mwl_server.log for diagnostics

---

**Last Updated**: December 16, 2025
