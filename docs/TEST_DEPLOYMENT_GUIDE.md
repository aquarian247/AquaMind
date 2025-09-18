# 🐟 AquaMind Test Environment Deployment Guide

This guide provides comprehensive instructions for deploying AquaMind to Bakkafrost test servers in local networks.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Preparation](#server-preparation)
3. [Environment Configuration](#environment-configuration)
4. [SSL Certificate Setup](#ssl-certificate-setup)
5. [Database Setup](#database-setup)
6. [Application Deployment](#application-deployment)
7. [Monitoring Setup](#monitoring-setup)
8. [Security Configuration](#security-configuration)
9. [Backup Configuration](#backup-configuration)
10. [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

### System Requirements
- **Ubuntu Server**: 22.04 LTS or 24.04 LTS
- **RAM**: Minimum 4GB, Recommended 8GB+
- **CPU**: 2+ cores
- **Storage**: 50GB+ free space
- **Network**: Static IP address

### Required Software
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    docker.io \
    docker-compose \
    nginx \
    certbot \
    postgresql-client \
    redis-tools \
    curl \
    wget \
    git \
    htop \
    ufw \
    fail2ban \
    logrotate \
    unattended-upgrades
```

### User Setup
```bash
# Create dedicated user for AquaMind
sudo useradd -m -s /bin/bash aquamind
sudo usermod -aG docker aquamind

# Create application directory
sudo mkdir -p /opt/aquamind
sudo chown aquamind:aquamind /opt/aquamind

# Switch to aquamind user
sudo -u aquamind bash
cd /opt/aquamind
```

## 🖥️ Server Preparation

### 1. Firewall Configuration
```bash
# Enable UFW
sudo ufw enable

# Allow SSH (change port if needed)
sudo ufw allow ssh
sudo ufw allow 22

# Allow HTTP and HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow AquaMind specific ports (if needed)
sudo ufw allow 8000  # Backend
sudo ufw allow 5433  # PostgreSQL (external)
sudo ufw allow 6380  # Redis (external)
sudo ufw allow 9090  # Prometheus (monitoring)

# Reload firewall
sudo ufw reload
```

### 2. Security Hardening
```bash
# Disable root login
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Use key-based authentication only
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# Restart SSH service
sudo systemctl restart sshd

# Install and configure fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 3. Docker Configuration
```bash
# Create Docker daemon configuration
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "5"
  },
  "storage-driver": "overlay2",
  "iptables": false
}
EOF

# Restart Docker
sudo systemctl restart docker

# Enable Docker service
sudo systemctl enable docker
```

### 4. Directory Structure Setup
```bash
# Create required directories
sudo mkdir -p /opt/aquamind/{app,backups,logs,ssl,monitoring}
sudo mkdir -p /var/log/aquamind
sudo mkdir -p /var/www/{static,media}

# Set proper permissions
sudo chown -R aquamind:aquamind /opt/aquamind
sudo chown -R aquamind:aquamind /var/log/aquamind
sudo chown -R aquamind:aquamind /var/www/{static,media}
```

## ⚙️ Environment Configuration

### 1. Clone Repository
```bash
cd /opt/aquamind/app
git clone https://github.com/aquarian247/AquaMind.git .
git checkout test  # Use test branch for deployments
```

### 2. Create Environment File
```bash
# Copy environment template
cp docs/env-test-example.txt .env

# Edit with your specific values
nano .env
```

**Required Environment Variables:**
```bash
# Generate Django secret key
DJANGO_SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

# Database credentials
DB_USER=aquamind_test
DB_PASSWORD=your_secure_db_password_here

# Server configuration
ALLOWED_HOSTS=your-test-server-ip,test.aquamind.local
CORS_ALLOWED_ORIGINS=http://test.aquamind.local,http://your-test-server-ip
CSRF_TRUSTED_ORIGINS=http://test.aquamind.local,http://your-test-server-ip

# Bakkafrost specific
BAKKAFROST_REGION=SCOTLAND  # or FAROE_ISLANDS
TEST_ENV_ID=BAKKAFROST_TEST_001
```

### 2.1 CI/CD Test Secrets (GitHub Actions)

Set these repository secrets in GitHub (Repository → Settings → Secrets and variables → Actions) for the backend repo to enable automated test deployments:

```
# SSH / Deployment
TEST_SSH_PRIVATE_KEY   # Full private key (BEGIN/END OPENSSH PRIVATE KEY)
TEST_SSH_USER          # e.g., aquamind
TEST_SERVER_HOST       # e.g., 192.168.1.100 or test.aquamind.local

# Django / App
TEST_DJANGO_SECRET_KEY # Generated with Django secret key util
TEST_ALLOWED_HOSTS     # Comma-separated, e.g., test.aquamind.local,192.168.1.100
TEST_CORS_ALLOWED_ORIGINS   # e.g., http://test.aquamind.local,http://192.168.1.100
TEST_CSRF_TRUSTED_ORIGINS   # e.g., http://test.aquamind.local,http://192.168.1.100

# Database
TEST_DB_USER           # e.g., aquamind_test
TEST_DB_PASSWORD       # strong password
TEST_DB_HOST           # database host/IP (if external DB)
TEST_DB_NAME           # e.g., aquamind_test_db
```

For detailed guidance and rotation procedures, see `docs/SECRETS_MANAGEMENT_GUIDE.md`.

### 3. Validate Environment Configuration
```bash
# Test environment file syntax
python3 -c "
import os
from pathlib import Path

# Load environment file
env_file = Path('.env')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    print(f'{key}: {\"SET\" if value else \"EMPTY\"}')
                else:
                    print(f'INVALID: {line}')
"

# Check for required variables
REQUIRED_VARS=('DJANGO_SECRET_KEY' 'DB_PASSWORD' 'ALLOWED_HOSTS')
for var in REQUIRED_VARS:
    if not os.getenv(var):
        echo "ERROR: $var is not set!"
        exit 1
    fi
done
echo "Environment configuration validated successfully"
```

## 🔒 SSL Certificate Setup

### 1. Obtain SSL Certificate
```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate (replace with your domain)
sudo certbot certonly --standalone -d test.aquamind.local

# Certificate files will be in:
/etc/letsencrypt/live/test.aquamind.local/
```

### 2. Configure Auto-Renewal
```bash
# Test renewal
sudo certbot renew --dry-run

# Add renewal to crontab
sudo crontab -e
# Add this line:
# 0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. Copy Certificates for Docker
```bash
# Copy certificates to application directory
sudo cp /etc/letsencrypt/live/test.aquamind.local/fullchain.pem /opt/aquamind/ssl/test.crt
sudo cp /etc/letsencrypt/live/test.aquamind.local/privkey.pem /opt/aquamind/ssl/test.key

# Set proper permissions
sudo chown aquamind:aquamind /opt/aquamind/ssl/*
sudo chmod 600 /opt/aquamind/ssl/test.key
```

## 🗄️ Database Setup

### 1. Create Database User and Database
```bash
# Connect to PostgreSQL (replace with your admin credentials)
psql -h your-db-server -U postgres

# Create database and user
CREATE DATABASE aquamind_test_db;
CREATE USER aquamind_test WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE aquamind_test_db TO aquamind_test;
ALTER USER aquamind_test CREATEDB;

# Enable TimescaleDB extension
\c aquamind_test_db
CREATE EXTENSION IF NOT EXISTS timescaledb;

\q
```

### 2. Test Database Connection
```bash
# Test connection from application server
psql -h your-db-server -U aquamind_test -d aquamind_test_db -c "SELECT version();"
```

## 🚀 Application Deployment

### 1. Initial Deployment
```bash
cd /opt/aquamind/app

# Build and start services
docker-compose -f docker-compose.test.yml up -d

# Check service status
docker-compose -f docker-compose.test.yml ps

# View logs
docker-compose -f docker-compose.test.yml logs -f
```

### 2. Database Migration
```bash
# Run migrations
docker-compose -f docker-compose.test.yml exec web python manage.py migrate

# Create superuser (interactive)
docker-compose -f docker-compose.test.yml exec web python manage.py createsuperuser

# Or create superuser non-interactively
docker-compose -f docker-compose.test.yml exec web python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@aquamind.local', 'admin123')
    print('Superuser created successfully')
else:
    print('Superuser already exists')
"
```

### 3. Static Files Collection
```bash
# Collect static files
docker-compose -f docker-compose.test.yml exec web python manage.py collectstatic --noinput
```

### 4. Health Check Verification
```bash
# Test backend health
curl -f http://localhost:8000/health/

# Test API endpoints
curl -f http://localhost:8000/api/v1/

# Test admin interface
curl -f http://localhost:8000/admin/
```

## 📊 Monitoring Setup

### 1. Prometheus Configuration
```bash
# Create Prometheus configuration directory
mkdir -p /opt/aquamind/monitoring

# Create prometheus.yml
cat > /opt/aquamind/monitoring/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'aquamind-backend'
    static_configs:
      - targets: ['web:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s

  - job_name: 'aquamind-database'
    static_configs:
      - targets: ['timescale-db:5432']
    scrape_interval: 30s

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:80']
    scrape_interval: 15s
EOF
```

### 2. Application Metrics
```bash
# Install Django Prometheus
docker-compose -f docker-compose.test.yml exec web pip install django-prometheus

# Add to INSTALLED_APPS in settings
echo "INSTALLED_APPS += ['django_prometheus']" >> aquamind/settings_test.py

# Restart services
docker-compose -f docker-compose.test.yml restart web
```

## 🔐 Security Configuration

### 1. Secrets Management
```bash
# Use Docker secrets for sensitive data
echo "your_secure_db_password" | docker secret create db_password -

# Or use environment file with restricted permissions
chmod 600 .env
```

### 2. Network Security
```bash
# Create Docker network with restricted access
docker network create --driver bridge --subnet 172.20.0.0/16 aquamind-test-net

# Use internal networking for service communication
# External access only through Nginx reverse proxy
```

### 3. Log Security
```bash
# Configure log rotation
cat > /etc/logrotate.d/aquamind << EOF
/var/log/aquamind/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 aquamind aquamind
    postrotate
        docker-compose -f /opt/aquamind/app/docker-compose.test.yml restart nginx
    endscript
}
EOF
```

## 💾 Backup Configuration

### 1. Database Backup Script
```bash
# Create backup script
cat > /opt/aquamind/scripts/backup.sh << 'EOF'
#!/bin/bash

# Database backup script for AquaMind test environment
BACKUP_DIR="/opt/aquamind/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/aquamind_test_${TIMESTAMP}.sql"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Perform backup
docker-compose -f /opt/aquamind/app/docker-compose.test.yml exec -T timescale-db pg_dump \
    -U aquamind_test \
    -d aquamind_test_db \
    --no-password \
    --format=custom \
    --compress=9 \
    --verbose > $BACKUP_FILE

# Verify backup
if [ $? -eq 0 ]; then
    echo "Backup completed successfully: $BACKUP_FILE"
    # Clean up old backups (keep last 30 days)
    find $BACKUP_DIR -name "aquamind_test_*.sql" -mtime +30 -delete
else
    echo "Backup failed!"
    exit 1
fi
EOF

# Make script executable
chmod +x /opt/aquamind/scripts/backup.sh
```

### 2. Automated Backup Schedule
```bash
# Add to crontab for daily backups at 2 AM
crontab -e
# Add this line:
# 0 2 * * * /opt/aquamind/scripts/backup.sh
```

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. Database Connection Issues
```bash
# Check database connectivity
docker-compose -f docker-compose.test.yml exec web python manage.py dbshell

# Test database from host
psql -h localhost -p 5433 -U aquamind_test -d aquamind_test_db

# Check database logs
docker-compose -f docker-compose.test.yml logs timescale-db
```

#### 2. Application Startup Issues
```bash
# Check application logs
docker-compose -f docker-compose.test.yml logs web

# Test Django configuration
docker-compose -f docker-compose.test.yml exec web python manage.py check

# Verify environment variables
docker-compose -f docker-compose.test.yml exec web env | grep -E "(DJANGO|DB_|CORS_)"
```

#### 3. Permission Issues
```bash
# Fix file permissions
sudo chown -R aquamind:aquamind /opt/aquamind
sudo chown -R aquamind:aquamind /var/log/aquamind
sudo chown -R aquamind:aquamind /var/www

# Check Docker permissions
sudo usermod -aG docker aquamind
sudo systemctl restart docker
```

#### 4. SSL Certificate Issues
```bash
# Check certificate validity
openssl x509 -in /opt/aquamind/ssl/test.crt -text -noout

# Renew certificates
sudo certbot renew

# Copy renewed certificates
sudo cp /etc/letsencrypt/live/test.aquamind.local/fullchain.pem /opt/aquamind/ssl/test.crt
sudo cp /etc/letsencrypt/live/test.aquamind.local/privkey.pem /opt/aquamind/ssl/test.key

# Restart Nginx
docker-compose -f docker-compose.test.yml restart nginx
```

#### 5. Memory Issues
```bash
# Check system resources
htop

# Check Docker container resources
docker stats

# Increase Docker memory limit if needed
sudo tee -a /etc/docker/daemon.json > /dev/null <<EOF
{
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Soft": 1024,
      "Hard": 2048
    }
  }
}
EOF
```

### Log Analysis
```bash
# View application logs
docker-compose -f docker-compose.test.yml logs -f web

# View Nginx access logs
docker-compose -f docker-compose.test.yml logs -f nginx

# Search for errors
docker-compose -f docker-compose.test.yml logs | grep -i error

# Monitor real-time logs
tail -f /var/log/aquamind/*.log
```

### Performance Monitoring
```bash
# Check application performance
curl -w "@curl-format.txt" -o /dev/null -s http://localhost/api/v1/

# Database query performance
docker-compose -f docker-compose.test.yml exec web python manage.py shell -c "
import django
django.setup()
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT * FROM pg_stat_activity;')
print(cursor.fetchall())
"

# System resource usage
docker system df
docker stats --no-stream
```

## 📞 Support and Maintenance

### Regular Maintenance Tasks
```bash
# Update system packages
sudo unattended-upgrades

# Update Docker images
docker-compose -f docker-compose.test.yml pull

# Restart services
docker-compose -f docker-compose.test.yml restart

# Clean up Docker
docker system prune -f
```

### Emergency Procedures
```bash
# Quick service restart
docker-compose -f docker-compose.test.yml restart

# Emergency database restore
# Stop services first
docker-compose -f docker-compose.test.yml down

# Restore from backup
docker-compose -f docker-compose.test.yml exec timescale-db pg_restore \
    -U aquamind_test \
    -d aquamind_test_db \
    /backups/latest_backup.sql

# Start services
docker-compose -f docker-compose.test.yml up -d
```

### Monitoring and Alerts
- Set up monitoring for critical services
- Configure alerts for:
  - Service downtime
  - High resource usage
  - Failed backups
  - SSL certificate expiration
  - Database connection issues

---

## 🎯 Quick Reference

### Service Management
```bash
# Start services
docker-compose -f docker-compose.test.yml up -d

# Stop services
docker-compose -f docker-compose.test.yml down

# View logs
docker-compose -f docker-compose.test.yml logs -f

# Restart specific service
docker-compose -f docker-compose.test.yml restart web
```

### Health Checks
```bash
# Backend health
curl http://localhost:8000/health/

# Database health
docker-compose -f docker-compose.test.yml exec timescale-db pg_isready

# Redis health
docker-compose -f docker-compose.test.yml exec redis redis-cli ping
```

### Backup Operations
```bash
# Manual backup
/opt/aquamind/scripts/backup.sh

# List backups
ls -la /opt/aquamind/backups/

# Restore from backup
# (Use pg_restore with appropriate backup file)
```

---

**For additional support, contact the Bakkafrost IT team or create an issue in the AquaMind repository.**
