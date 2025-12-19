# FlowWorklist - Deployment Guide

Guide for deploying FlowWorklist in different environments.

## Quick Start

### Windows - Development

```powershell
# 1. Activate virtual environment
& .\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure database in config.json
# Edit the file with your database credentials

# 4. Start management App (Flow CLI)
python .\flow.py install
.\flow start app
# Open http://127.0.0.1:5000
```

### Windows - Service Installation

#### Using NSSM (Recommended)

```powershell
# Download NSSM from https://nssm.cc/download
# Extract and add to PATH

# Install service
nssm install FlowMWL "C:\FlowWorklist\Scripts\python.exe" "C:\FlowWorklist\mwl_service.py"
nssm set FlowMWL AppDirectory "C:\FlowWorklist"
nssm set FlowMWL AppStdout "C:\FlowWorklist\logs\service.log"
nssm set FlowMWL AppStderr "C:\FlowWorklist\logs\service.log"

# Start/Stop/Restart
nssm start FlowMWL
nssm stop FlowMWL
nssm restart FlowMWL

# Verify
nssm status FlowMWL
```

#### Using Task Scheduler

```powershell
# Create a scheduled task that runs MWLSCP.py at startup
$action = New-ScheduledTaskAction -Execute "C:\FlowWorklist\Scripts\python.exe" `
  -Argument "C:\FlowWorklist\MWLSCP.py"
$trigger = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "FlowMWL" `
  -Description "DICOM Modality Worklist Server" -RunLevel Highest
```

---

## Linux / macOS Deployment

### Systemd Service (Recommended)

```bash
# 1. Create user for the service
sudo useradd -r -s /bin/bash dicom

# 2. Copy application to /opt/
sudo cp -r FlowWorklist /opt/

# 3. Set permissions
sudo chown -R dicom:dicom /opt/FlowWorklist

# 4. Create systemd service file
sudo tee /etc/systemd/system/flowmwl.service > /dev/null << EOF
[Unit]
Description=FlowWorklist DICOM MWL Server
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=dicom
Group=dicom
WorkingDirectory=/opt/FlowWorklist
ExecStart=/opt/FlowWorklist/venv/bin/python /opt/FlowWorklist/mwl_service.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 5. Start service
sudo systemctl daemon-reload
sudo systemctl enable flowmwl
sudo systemctl start flowmwl

# 6. Check status
sudo systemctl status flowmwl
sudo journalctl -u flowmwl -f
```

### Standalone (Without Systemd)

```bash
# 1. Create shell script
cat > /opt/FlowWorklist/start.sh << 'EOF'
#!/bin/bash
cd /opt/FlowWorklist
source venv/bin/activate
python MWLSCP.py >> logs/mwl_server.log 2>&1 &
echo $! > /var/run/flowmwl.pid
EOF

chmod +x /opt/FlowWorklist/start.sh

# 2. Add to crontab
crontab -e
# Add: @reboot /opt/FlowWorklist/start.sh
```

---

## Docker Deployment

### Build and Run

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libaio1 \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose ports
EXPOSE 11112 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import socket; s = socket.socket(); s.connect(('localhost', 11112)); s.close()" || exit 1

# Run MWLSCP server
CMD ["python", "mwl_service.py"]
```

### Build and Run

```bash
# Build image
docker build -t flowworklist:latest .

# Run container
docker run -d \
  --name flowmwl \
  -p 11112:11112 \
  -p 5000:5000 \
  -v /path/to/config.json:/app/config.json:ro \
  -v /path/to/logs:/app/logs \
  flowworklist:latest

# Monitor
docker logs -f flowmwl
docker stats flowmwl
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  flowmwl:
    image: flowworklist:latest
    container_name: flowmwl
    ports:
      - "11112:11112"
      - "5000:5000"
    volumes:
      - ./config.json:/app/config.json:ro
      - ./logs:/app/logs
    restart: always
    healthcheck:
      test: ["CMD", "python", "-c", "import socket; s = socket.socket(); s.connect(('localhost', 11112))"]
      interval: 30s
      timeout: 10s
      retries: 3
```

```bash
docker-compose up -d
docker-compose logs -f
docker-compose down
```

---

## Kubernetes Deployment

```yaml
# kubernetes.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flowmwl
  labels:
    app: flowmwl
spec:
  replicas: 1
  selector:
    matchLabels:
      app: flowmwl
  template:
    metadata:
      labels:
        app: flowmwl
    spec:
      containers:
      - name: flowmwl
        image: flowworklist:latest
        ports:
        - containerPort: 11112
          name: dicom
        - containerPort: 5000
          name: dashboard
        volumeMounts:
        - name: config
          mountPath: /app/config.json
          subPath: config.json
          readOnly: true
        - name: logs
          mountPath: /app/logs
        livenessProbe:
          tcpSocket:
            port: 11112
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          tcpSocket:
            port: 11112
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config
        configMap:
          name: flowmwl-config
      - name: logs
        emptyDir: {}

---
apiVersion: v1
kind: Service
metadata:
  name: flowmwl-dicom
spec:
  type: LoadBalancer
  ports:
  - port: 11112
    targetPort: 11112
    protocol: TCP
    name: dicom
  selector:
    app: flowmwl

---
apiVersion: v1
kind: Service
metadata:
  name: flowmwl-dashboard
spec:
  type: LoadBalancer
  ports:
  - port: 5000
    targetPort: 5000
    protocol: TCP
    name: dashboard
  selector:
    app: flowmwl

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: flowmwl-config
data:
  config.json: |
    {
      "server": {
        "aet": "FlowMWL",
        "port": 11112,
        "host": "0.0.0.0",
        "client_aet": "Console"
      },
      "database": {
        "type": "oracle",
        "user": "YOUR_USER",
        "password": "YOUR_PASSWORD",
        "dsn": "YOUR_HOST:1521/YOUR_DB",
        "query": "SELECT ..."
      }
    }
```

```bash
# Deploy
kubectl apply -f kubernetes.yaml

# Monitor
kubectl get pods
kubectl logs -f deployment/flowmwl
kubectl port-forward svc/flowmwl-dashboard 5000:5000
```

---

## Network Configuration

### Firewall Rules

#### Windows Firewall
```powershell
# Allow DICOM port (11112)
New-NetFirewallRule -DisplayName "FlowMWL DICOM" `
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 11112

# Allow Dashboard port (5000)
New-NetFirewallRule -DisplayName "FlowMWL Dashboard" `
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5000
```

#### Linux (iptables)
```bash
# Allow DICOM port
sudo iptables -A INPUT -p tcp --dport 11112 -j ACCEPT

# Allow Dashboard port
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT

# Save rules
sudo netfilter-persistent save
```

#### Linux (firewalld)
```bash
sudo firewall-cmd --permanent --add-port=11112/tcp
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

---

## Reverse Proxy Configuration

### Nginx (For Dashboard)

```nginx
upstream flowmwl_dashboard {
    server localhost:5000;
}

server {
    listen 80;
    server_name worklist.hospital.com;

    location / {
        proxy_pass http://flowmwl_dashboard;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Apache (For Dashboard)

```apache
<VirtualHost *:80>
    ServerName worklist.hospital.com

    ProxyPreserveHost On
    ProxyPass / http://localhost:5000/
    ProxyPassReverse / http://localhost:5000/
</VirtualHost>
```

---

## Security Considerations

### 1. Configuration Security
- Store `config.json` outside of web-accessible directories
- Use environment variables for sensitive credentials
- Rotate database passwords regularly
- Implement file-level access controls

### 2. Network Security
- Use VPN or private network for database connections
- Restrict DICOM port (11112) to known imaging equipment IPs
- Use TLS/SSL for dashboard (reverse proxy with HTTPS)
- Implement rate limiting on API endpoints

### 3. Access Control
- Run service under dedicated non-privileged user account
- Restrict file permissions (config.json: 600)
- Implement authentication for dashboard (reverse proxy)
- Audit logs regularly

### Example: Secured Environment Variables
```bash
# .env file (keep secure!)
export DB_USER="hospital_user"
export DB_PASSWORD="secure_password_here"
export DB_DSN="prod-db.hospital.local:1521/PROD"
```

```python
# In app.py/MWLSCP.py
import os
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
```

---

## Monitoring and Troubleshooting

### Log Files
- **MWLSCP Server**: `logs/mwl_server.log`
- **Dashboard**: `service_logs/*.log`
- **System**: Check OS system logs

### Health Checks

```bash
# Check if DICOM port is listening
netstat -an | findstr 11112          # Windows
netstat -an | grep 11112            # Linux

# Test connection
(New-Object System.Net.Sockets.TcpClient).Connect("localhost", 11112)  # Windows

# Query logs
tail -f logs/mwl_server.log         # Linux
Get-Content logs\mwl_server.log     # Windows
```

### Performance Tuning
- Monitor CPU and memory usage
- Check database query performance
- Adjust DICOM timeout values if needed
- Consider caching for frequently-queried data

---

## Backup and Recovery

### Backup Configuration
```bash
# Backup config.json daily
0 0 * * * cp /opt/FlowWorklist/config.json /backup/config.json.$(date +\%Y\%m\%d)

# Keep 30 days of backups
find /backup/config.json.* -mtime +30 -delete
```

### Recovery
```bash
# Restore from backup
cp /backup/config.json.20251216 /opt/FlowWorklist/config.json

# Restart service
sudo systemctl restart flowmwl
```

---

## Version Management

### Git Workflow
```bash
# Clone repository
git clone https://github.com/yourusername/FlowWorklist.git
cd FlowWorklist

# Create deployment branch
git checkout -b deploy/production

# Update configuration for production
# (Don't commit sensitive data!)
git checkout -- config.json

# Tag version
git tag -a v1.0.0 -m "Production Release 1.0.0"
git push origin v1.0.0
```

---

## Support

For issues during deployment:
1. Check `logs/mwl_server.log` for error messages
2. Review [README.md](README.md) for configuration guide
3. Consult [COLUMN_MAPPING_GUIDE.md](COLUMN_MAPPING_GUIDE.md) for database queries
4. Test endpoints using dashboard at http://localhost:5000

---

**Last Updated**: December 2025  
**Version**: 1.0.0
