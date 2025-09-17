# AquaMind Test Deployment Checklist

## 📋 Deployment Overview

This checklist guides the infrastructure team through deploying AquaMind on Ubuntu servers. The application consists of:

- **Frontend**: React SPA served by Nginx (Docker container)
- **Backend**: Django REST API (Docker container)
- **Database**: TimescaleDB PostgreSQL (Docker container)
- **HTTPS**: Let's Encrypt SSL certificates with automated renewal

### 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend VM   │    │   Backend VM    │    │ Database VM     │
│                 │    │                 │    │                 │
│ • Nginx         │◄──►│ • Django API    │◄──►│ • TimescaleDB   │
│ • React SPA     │    │ • Gunicorn      │    │ • PostgreSQL    │
│ • SSL/TLS       │    │ • Docker        │    │ • Docker        │
│ • Docker        │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 Prerequisites

### System Requirements
- **Ubuntu Server**: 22.04 LTS or 24.04 LTS
- **RAM**: Minimum 4GB per server (8GB recommended)
- **CPU**: 2+ cores per server
- **Storage**: 50GB+ free space per server
- **Network**: Static IP addresses for all servers

### Access Requirements
- **SSH Access**: Root or sudo access to all servers
- **DNS**: Domain name pointing to frontend server
- **Firewall**: UFW or iptables configured
- **Security Groups**: Open ports 80, 443, 22

## 🚀 Deployment Checklist

### Phase 1: Server Preparation

#### [ ] 1.1 Server Setup (All Servers)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y curl wget git htop ufw fail2ban unattended-upgrades

# Configure firewall
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw --force enable

# Create application user
sudo useradd -m -s /bin/bash aquamind
sudo usermod -aG docker aquamind

# Configure SSH security
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

#### [ ] 1.2 Docker Installation (All Servers)
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo systemctl enable docker
sudo systemctl start docker

# Install Docker Compose
sudo apt install docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

#### [ ] 1.3 Directory Structure (All Servers)
```bash
# Create application directories
sudo mkdir -p /opt/aquamind
sudo chown aquamind:aquamind /opt/aquamind

# Create data directories
sudo mkdir -p /opt/aquamind/data
sudo mkdir -p /opt/aquamind/logs
sudo mkdir -p /opt/aquamind/ssl
sudo chown -R aquamind:aquamind /opt/aquamind
```

### Phase 2: Database Server Setup

#### [ ] 2.1 Database Server Configuration
```bash
# Switch to aquamind user
su - aquamind

# Create docker-compose.yml for database
cat > /opt/aquamind/docker-compose.yml << 'EOF'
version: '3.8'
services:
  timescale-db:
    image: timescale/timescaledb:latest-pg14
    container_name: aquamind-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=aquamind_db
      - POSTGRES_USER=aquamind
      - POSTGRES_PASSWORD=YOUR_STRONG_DB_PASSWORD_HERE
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
      - ./logs/postgres:/var/log/postgresql
    ports:
      - "127.0.0.1:5432:5432"  # Only accessible locally
    networks:
      - aquamind-net

networks:
  aquamind-net:
    driver: bridge

volumes:
  postgres_data:
EOF
```

#### [ ] 2.2 Database Security Configuration
```bash
# Create PostgreSQL configuration
sudo tee /etc/postgresql/14/main/conf.d/aquamind.conf > /dev/null <<EOF
# AquaMind PostgreSQL Configuration
listen_addresses = 'localhost'
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 5242kB
min_wal_size = 1GB
max_wal_size = 4GB
EOF

# Restart PostgreSQL
sudo systemctl restart postgresql
```

#### [ ] 2.3 Database Backup Configuration
```bash
# Create backup script
cat > /opt/aquamind/backup-db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/aquamind/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/aquamind_$DATE.sql"

mkdir -p $BACKUP_DIR

docker exec aquamind-db pg_dump -U aquamind aquamind_db > $BACKUP_FILE

# Keep only last 7 days
find $BACKUP_DIR -name "aquamind_*.sql" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
EOF

chmod +x /opt/aquamind/backup-db.sh

# Add to crontab for daily backups
echo "0 2 * * * /opt/aquamind/backup-db.sh" | crontab -
```

### Phase 3: Backend Server Setup

#### [ ] 3.1 Backend Deployment
```bash
# Switch to aquamind user
su - aquamind

# Clone backend repository (or copy files)
cd /opt/aquamind
git clone https://github.com/aquarian247/AquaMind.git backend
cd backend

# Create environment configuration
cat > .env.test << 'EOF'
# Django Configuration
DEBUG=False
SECRET_KEY=your-super-secret-key-here-change-this
ALLOWED_HOSTS=backend.yourdomain.com,localhost,127.0.0.1

# Database Configuration
DATABASE_URL=postgresql://aquamind:YOUR_STRONG_DB_PASSWORD_HERE@database-server-ip:5432/aquamind_db

# Security
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True

# CORS Configuration
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CORS_ALLOW_CREDENTIALS=True

# Email Configuration (optional)
EMAIL_HOST=smtp.bakkafrost.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@bakkafrost.com
EMAIL_HOST_PASSWORD=your-app-password
EOF
```

#### [ ] 3.2 Backend Docker Configuration
```bash
# Create test docker-compose.yml
cat > docker-compose.test.yml << 'EOF'
version: '3.8'
services:
  web:
    build:
      context: .
      dockerfile: Dockerfile.test
    container_name: aquamind-backend
    restart: unless-stopped
    environment:
      - DATABASE_HOST=database-server-ip
      - DJANGO_SETTINGS_MODULE=aquamind.settings.test
    env_file:
      - .env.test
    volumes:
      - ./static:/app/static
      - ./media:/app/media
      - ./logs:/app/logs
    ports:
      - "127.0.0.1:8000:8000"
    depends_on:
      - timescale-db
    networks:
      - aquamind-net
    command: gunicorn aquamind.wsgi:application --bind 0.0.0.0:8000 --workers 4

  timescale-db:
    image: timescale/timescaledb:latest-pg14
    container_name: aquamind-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=aquamind_db
      - POSTGRES_USER=aquamind
      - POSTGRES_PASSWORD=YOUR_STRONG_DB_PASSWORD_HERE
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5432:5432"
    networks:
      - aquamind-net

networks:
  aquamind-net:
    driver: bridge
EOF
```

#### [ ] 3.3 Backend Test Dockerfile
```bash
# Create test Dockerfile
cat > Dockerfile.test << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health-check/ || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "aquamind.wsgi:application"]
EOF
```

### Phase 4: Frontend Server Setup

#### [ ] 4.1 Frontend Deployment
```bash
# Switch to aquamind user
su - aquamind

# Clone frontend repository
cd /opt/aquamind
git clone https://github.com/aquarian247/AquaMind-Frontend.git frontend
cd frontend

# Build test configuration
cat > .env.test << 'EOF'
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_ENVIRONMENT=test
VITE_DEBUG_MODE=false
EOF
```

#### [ ] 4.2 Frontend Docker Configuration
```bash
# Create test docker-compose.yml
cat > docker-compose.test.yml << 'EOF'
version: '3.8'
services:
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.test
    container_name: aquamind-frontend
    restart: unless-stopped
    environment:
      - NGINX_ENVSUBST_TEMPLATE_DIR=/etc/nginx/templates
    ports:
      - "127.0.0.1:80:80"
      - "127.0.0.1:443:443"
    volumes:
      - ./ssl:/etc/ssl/certs
      - ./logs/nginx:/var/log/nginx
    networks:
      - aquamind-net

networks:
  aquamind-net:
    driver: bridge
EOF
```

#### [ ] 4.3 Frontend Test Dockerfile
```bash
# Create test Dockerfile
cat > Dockerfile.test << 'EOF'
FROM node:24-slim AS builder
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Test env nginx stage
FROM nginx:alpine

# Install certbot for SSL
RUN apk add --no-cache certbot certbot-nginx

# Copy built application
COPY --from=builder /app/dist/public /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf
COPY default.conf /etc/nginx/conf.d/default.conf

# Create SSL directory
RUN mkdir -p /etc/ssl/certs /var/www/certbot

# Expose ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
EOF
```

#### [ ] 4.4 Nginx Configuration for Frontend
```bash
# Create nginx configuration
cat > nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log;

    # Performance
    sendfile        on;
    tcp_nopush      on;
    tcp_nodelay     on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 100M;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # Include server configuration
    include /etc/nginx/conf.d/*.conf;
}
EOF

# Create default server configuration
cat > default.conf << 'EOF'
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL configuration
    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/certs/privkey.pem;

    # SSL security settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Root directory and index
    root /usr/share/nginx/html;
    index index.html index.htm;

    # Handle client-side routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy to backend
    location /api/ {
        proxy_pass http://backend-server-ip:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static assets with caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Health check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF
```

### Phase 5: HTTPS Setup with Let's Encrypt

#### [ ] 5.1 SSL Certificate Installation
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com

# Verify certificate renewal
sudo certbot renew --dry-run
```

#### [ ] 5.2 SSL Certificate Automation
```bash
# Create renewal hook script
cat > /etc/letsencrypt/renewal-hooks/post/nginx-reload.sh << 'EOF'
#!/bin/bash
docker restart aquamind-frontend
EOF

chmod +x /etc/letsencrypt/renewal-hooks/post/nginx-reload.sh

# Add to crontab for automatic renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

#### [ ] 5.3 SSL Configuration Verification
```bash
# Test SSL configuration
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Check certificate expiry
openssl x509 -in /etc/letsencrypt/live/yourdomain.com/cert.pem -text -noout | grep -A2 "Validity"

# Verify HTTPS redirect
curl -I http://yourdomain.com
```

### Phase 6: Networking and Security

#### [ ] 6.1 Internal Networking
```bash
# Configure firewall rules between servers
# On Backend Server:
sudo ufw allow from frontend-server-ip to any port 8000
sudo ufw allow from database-server-ip to any port 8000

# On Database Server:
sudo ufw allow from backend-server-ip to any port 5432

# On Frontend Server:
sudo ufw allow from backend-server-ip to any port 80
sudo ufw allow from backend-server-ip to any port 443
```

#### [ ] 6.2 DNS Configuration
```bash
# Update /etc/hosts on all servers
echo "frontend-server-ip frontend.yourdomain.com" | sudo tee -a /etc/hosts
echo "backend-server-ip backend.yourdomain.com" | sudo tee -a /etc/hosts
echo "database-server-ip database.yourdomain.com" | sudo tee -a /etc/hosts
```

### Phase 7: Monitoring and Maintenance

#### [ ] 7.1 Application Monitoring
```bash
# Install monitoring tools
sudo apt install -y prometheus-node-exporter

# Create health check script
cat > /opt/aquamind/health-check.sh << 'EOF'
#!/bin/bash

# Check frontend
if curl -f -k https://localhost/health > /dev/null 2>&1; then
    echo "Frontend: OK"
else
    echo "Frontend: FAILED"
fi

# Check backend
if curl -f http://localhost:8000/health-check/ > /dev/null 2>&1; then
    echo "Backend: OK"
else
    echo "Backend: FAILED"
fi

# Check database
if docker exec aquamind-db pg_isready -U aquamind -d aquamind_db > /dev/null 2>&1; then
    echo "Database: OK"
else
    echo "Database: FAILED"
fi
EOF

chmod +x /opt/aquamind/health-check.sh
```

#### [ ] 7.2 Log Rotation
```bash
# Configure logrotate for application logs
cat > /etc/logrotate.d/aquamind << 'EOF'
/opt/aquamind/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 aquamind aquamind
    postrotate
        docker restart aquamind-frontend aquamind-backend
    endscript
}
EOF
```

#### [ ] 7.3 Automated Updates
```bash
# Configure unattended upgrades
sudo dpkg-reconfigure unattended-upgrades

# Update Docker images weekly
cat > /opt/aquamind/update-containers.sh << 'EOF'
#!/bin/bash
docker pull timescale/timescaledb:latest-pg14
docker pull nginx:alpine
docker pull python:3.11-slim
docker pull node:24-slim

echo "Docker images updated. Restart containers if needed."
EOF

chmod +x /opt/aquamind/update-containers.sh

# Add to crontab
echo "0 3 * * 0 /opt/aquamind/update-containers.sh" | crontab -
```

### Phase 8: Testing and Verification

#### [ ] 8.1 Functional Testing
```bash
# Test HTTPS
curl -I https://yourdomain.com

# Test API endpoints
curl -k https://api.yourdomain.com/api/v1/infrastructure/geographies/

# Test authentication
curl -X POST https://api.yourdomain.com/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

#### [ ] 8.2 Performance Testing
```bash
# Install Apache Bench
sudo apt install -y apache2-utils

# Load testing
ab -n 1000 -c 10 https://yourdomain.com/

# Memory and CPU monitoring
docker stats aquamind-frontend aquamind-backend aquamind-db
```

#### [ ] 8.3 Backup Verification
```bash
# Test backup restoration
/opt/aquamind/backup-db.sh

# Verify backup file exists
ls -la /opt/aquamind/backups/
```

## 🚨 Emergency Procedures

### Database Recovery
```bash
# Stop application
docker-compose down

# Restore from backup
docker exec -i aquamind-db psql -U aquamind aquamind_db < /path/to/backup.sql

# Restart application
docker-compose up -d
```

### SSL Certificate Emergency Renewal
```bash
# Force certificate renewal
sudo certbot renew --force-renewal

# Reload nginx
docker restart aquamind-frontend
```

### Application Rollback
```bash
# Stop current version
docker-compose down

# Pull previous version
docker pull your-registry/aquamind-frontend:previous-tag
docker pull your-registry/aquamind-backend:previous-tag

# Start previous version
docker-compose up -d
```

## 📞 Support Contacts

- **Infrastructure Team**: teknisk-support@bakkafrost.com
- **Application Support**: janus.laearsson@bakkafrost.com
- **Security Issues**: hewa@bakkafrost.com

## ✅ Final Checklist

- [ ] All servers provisioned and configured
- [ ] Docker installed and configured
- [ ] Database initialized and secured
- [ ] Backend deployed and tested
- [ ] Frontend deployed and tested
- [ ] HTTPS certificates installed and configured
- [ ] Networking configured between servers
- [ ] Monitoring and logging configured
- [ ] Backup procedures tested
- [ ] Documentation updated
- [ ] UAT sign-off obtained

---

**Last Updated**: September 16, 2025
**Deployment Version**: v1.0.0
**Environment**: Test
