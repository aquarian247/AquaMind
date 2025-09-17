# 🔐 AquaMind Secrets Management Guide

This guide outlines secure secrets management practices for AquaMind deployments, specifically designed for Bakkafrost test environments and local network infrastructure.

## 📋 Overview

Secrets management is critical for maintaining security across development, test, and production environments. This guide covers:

- GitHub Actions secrets configuration
- Environment-specific secrets handling
- Database credential management
- SSL certificate management
- SSH key management for deployments

## 🔑 GitHub Actions Secrets Setup

### Required Repository Secrets

Navigate to: **Repository → Settings → Secrets and variables → Actions**

#### SSH Access Secrets (Required for Deployment)
```bash
# SSH private key for server access
TEST_SSH_PRIVATE_KEY
# Format: Full private key content (starts with -----BEGIN OPENSSH PRIVATE KEY-----)

# SSH username for test server
TEST_SSH_USER=ubuntu
# Or: TEST_SSH_USER=aquamind

# Test server hostname/IP
TEST_SERVER_HOST=192.168.1.100
# Or: TEST_SERVER_HOST=test.aquamind.local
```

#### Database Secrets
```bash
# Database credentials
TEST_DB_USER=aquamind_test
TEST_DB_PASSWORD=your_secure_database_password_here

# Database connection details
TEST_DB_HOST=your-database-server.bakkafrost.local
TEST_DB_PORT=5432
TEST_DB_NAME=aquamind_test_db
```

#### Django Application Secrets
```bash
# Django secret key (generate new one for each environment)
TEST_DJANGO_SECRET_KEY=your-generated-django-secret-key-here

# Environment configuration
TEST_DJANGO_DEBUG=false
TEST_ALLOWED_HOSTS=test.aquamind.local,192.168.1.100
```

#### SSL Certificate Secrets (Optional)
```bash
# For automated SSL certificate management
TEST_SSL_CERT_DOMAIN=test.aquamind.local
TEST_SSL_CERT_EMAIL=it@bakkafrost.fo
```

#### Notification Secrets (Optional)
```bash
# Slack notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

# Discord notifications
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR/DISCORD/WEBHOOK
```

### Environment Variables Mapping

The GitHub Actions workflows map these secrets to environment variables used by Docker Compose:

```yaml
# .github/workflows/deploy-full-test.yml
env:
  DJANGO_SECRET_KEY: ${{ secrets.TEST_DJANGO_SECRET_KEY }}
  DB_USER: ${{ secrets.TEST_DB_USER }}
  DB_PASSWORD: ${{ secrets.TEST_DB_PASSWORD }}
  DB_HOST: ${{ secrets.TEST_DB_HOST }}
  ALLOWED_HOSTS: ${{ secrets.TEST_ALLOWED_HOSTS }}
  CORS_ALLOWED_ORIGINS: ${{ secrets.TEST_CORS_ALLOWED_ORIGINS }}
  CSRF_TRUSTED_ORIGINS: ${{ secrets.TEST_CSRF_TRUSTED_ORIGINS }}
```

## 🏗️ Environment-Specific Configuration

### Development Environment (.env.development)
```bash
# Development environment - less restrictive
DJANGO_DEBUG=true
CORS_ALLOW_ALL_ORIGINS=true
DB_PASSWORD=dev_password_123
DJANGO_SECRET_KEY=dev-secret-key-for-local-development-only
```

### Test Environment (.env.test)
```bash
# Test environment - production-like settings
DJANGO_DEBUG=false
CORS_ALLOW_ALL_ORIGINS=false
DB_PASSWORD=${TEST_DB_PASSWORD}  # From GitHub secret
DJANGO_SECRET_KEY=${TEST_DJANGO_SECRET_KEY}  # From GitHub secret
ALLOWED_HOSTS=test.aquamind.local,192.168.1.100
```

### Production Environment (.env.production)
```bash
# Production environment - strict security
DJANGO_DEBUG=false
CORS_ALLOW_ALL_ORIGINS=false
DB_PASSWORD=${PROD_DB_PASSWORD}  # From secure vault
DJANGO_SECRET_KEY=${PROD_DJANGO_SECRET_KEY}  # From secure vault
SECURE_SSL_REDIRECT=true
```

## 🔐 SSH Key Management

### 1. Generate SSH Key Pair for GitHub Actions
```bash
# On your local machine (NOT on the server)
ssh-keygen -t ed25519 -C "github-actions@aquamind" -f ~/.ssh/aquamind_github_actions

# This creates:
# - ~/.ssh/aquamind_github_actions (private key)
# - ~/.ssh/aquamind_github_actions.pub (public key)
```

### 2. Add Public Key to Test Server
```bash
# Copy public key to test server
ssh-copy-id -i ~/.ssh/aquamind_github_actions.pub aquamind@test.aquamind.local

# Or manually add to ~/.ssh/authorized_keys on the server
cat ~/.ssh/aquamind_github_actions.pub >> ~/.ssh/authorized_keys
```

### 3. Configure SSH for GitHub Actions
```bash
# Read the private key content
cat ~/.ssh/aquamind_github_actions

# Copy the entire output (including -----BEGIN and -----END lines)
# Paste into GitHub repository secret: TEST_SSH_PRIVATE_KEY
```

### 4. SSH Configuration for Security
```bash
# On the test server, create /home/aquamind/.ssh/config
Host *
    PasswordAuthentication no
    PubkeyAuthentication yes
    AuthorizedKeysFile .ssh/authorized_keys
    PermitRootLogin no
    X11Forwarding no
    AllowTcpForwarding no
```

## 🗄️ Database Secrets Management

### PostgreSQL User Creation
```sql
-- Connect as postgres superuser
psql -h your-db-server -U postgres

-- Create application user with restricted permissions
CREATE USER aquamind_test WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT CONNECT ON DATABASE aquamind_test_db TO aquamind_test;
GRANT USAGE ON SCHEMA public TO aquamind_test;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO aquamind_test;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO aquamind_test;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO aquamind_test;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO aquamind_test;
```

### Database Connection String
```bash
# Store as single secret
TEST_DATABASE_URL=postgresql://aquamind_test:your_secure_password@db-server.bakkafrost.local:5432/aquamind_test_db

# Or separate components
TEST_DB_USER=aquamind_test
TEST_DB_PASSWORD=your_secure_password
TEST_DB_HOST=db-server.bakkafrost.local
TEST_DB_PORT=5432
TEST_DB_NAME=aquamind_test_db
```

## 🔒 SSL Certificate Management

### Automated Certificate Management
```bash
# Install certbot on test server
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot certonly --standalone -d test.aquamind.local

# Configure auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Certificate Storage for Docker
```bash
# Create SSL directory
sudo mkdir -p /opt/aquamind/ssl

# Copy certificates
sudo cp /etc/letsencrypt/live/test.aquamind.local/fullchain.pem /opt/aquamind/ssl/test.crt
sudo cp /etc/letsencrypt/live/test.aquamind.local/privkey.pem /opt/aquamind/ssl/test.key

# Set permissions
sudo chown aquamind:aquamind /opt/aquamind/ssl/*
sudo chmod 600 /opt/aquamind/ssl/test.key
```

## 🔄 Secrets Rotation Strategy

### Regular Rotation Schedule
```bash
# Monthly rotation checklist:
# 1. Django SECRET_KEY
# 2. Database passwords
# 3. SSH keys
# 4. API tokens
# 5. SSL certificates
```

### Django Secret Key Rotation
```bash
# Generate new secret key
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Update in GitHub secrets
# Update TEST_DJANGO_SECRET_KEY

# Deploy new key (will require service restart)
# Old sessions will be invalidated
```

### Database Password Rotation
```sql
-- Update password in PostgreSQL
ALTER USER aquamind_test PASSWORD 'new_secure_password';

-- Update GitHub secret
# Update TEST_DB_PASSWORD

-- Deploy changes
# This will require a service restart to pick up new password
```

## 🛡️ Security Best Practices

### 1. Principle of Least Privilege
- Database users should only have necessary permissions
- SSH keys should be restricted to specific commands
- Environment variables should be validated before use

### 2. Secret Storage
- Never commit secrets to version control
- Use GitHub repository secrets for CI/CD
- Consider using Azure Key Vault or AWS Secrets Manager for enterprise deployments

### 3. Access Control
```bash
# Restrict access to secrets
# Only repository administrators should manage secrets
# Use branch protection rules for production deployments
```

### 4. Audit Logging
```bash
# Enable audit logging for secret access
# Monitor GitHub Actions logs for secret usage
# Log secret rotation events
```

## 🚨 Emergency Procedures

### Compromised Secret Response
1. **Immediate Actions:**
   - Rotate the compromised secret
   - Update all affected systems
   - Revoke compromised SSH keys
   - Change database passwords

2. **Investigation:**
   - Review access logs
   - Check for unauthorized access
   - Audit recent deployments

3. **Prevention:**
   - Implement stricter access controls
   - Regular security audits
   - Automated secret rotation

### Service Account Recovery
```bash
# If service account credentials are lost:
# 1. Generate new SSH key pair
# 2. Update GitHub Actions secrets
# 3. Update server authorized_keys
# 4. Test deployment pipeline
```

## 📊 Monitoring and Compliance

### Secret Usage Monitoring
```bash
# Monitor GitHub Actions for secret usage
# Set up alerts for failed deployments due to bad secrets
# Regular audit of secret access patterns
```

### Compliance Requirements
- **PCI DSS**: Encrypt sensitive data
- **GDPR**: Protect personal data
- **SOX**: Audit trail for financial data
- **Bakkafrost Internal**: Follow company security policies

### Audit Trail
```bash
# Log all secret operations
# Maintain records of:
# - Secret creation dates
# - Rotation history
# - Access patterns
# - Incident responses
```

## 🔧 Troubleshooting

### Common Issues

#### SSH Connection Failures
```bash
# Check SSH key format in GitHub secret
# Ensure public key is in authorized_keys
# Verify server firewall allows SSH
# Check SSH service status on server
```

#### Database Connection Issues
```bash
# Verify database credentials
# Check network connectivity
# Validate SSL certificate if required
# Test connection from deployment server
```

#### Certificate Problems
```bash
# Check certificate validity dates
# Verify certificate matches domain
# Ensure certificate files have correct permissions
# Test certificate with openssl commands
```

#### Environment Variable Issues
```bash
# Validate environment variable names match Docker Compose
# Check for typos in secret names
# Ensure secrets are not empty
# Verify environment variable parsing in Python
```

## 📞 Support and Escalation

### Internal Contacts
- **Security Team**: security@bakkafrost.fo
- **IT Operations**: it-ops@bakkafrost.fo
- **Development Team**: dev-team@bakkafrost.fo

### Emergency Contacts
- **24/7 Security Hotline**: +298 123 4567
- **IT Emergency**: +298 765 4321

### Escalation Procedures
1. **Low Impact**: Create GitHub issue with security label
2. **Medium Impact**: Contact IT operations team
3. **High Impact**: Contact security team immediately
4. **Critical**: Use emergency hotline

---

## 📋 Quick Reference

### Required Secrets Checklist
- [ ] `TEST_SSH_PRIVATE_KEY` - SSH private key
- [ ] `TEST_SSH_USER` - SSH username
- [ ] `TEST_SERVER_HOST` - Test server address
- [ ] `TEST_DB_USER` - Database username
- [ ] `TEST_DB_PASSWORD` - Database password
- [ ] `TEST_DJANGO_SECRET_KEY` - Django secret key
- [ ] `TEST_ALLOWED_HOSTS` - Allowed hostnames

### Secret Rotation Commands
```bash
# Generate new Django secret key
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Generate new SSH key pair
ssh-keygen -t ed25519 -C "github-actions@aquamind"

# Test SSH connection
ssh -i ~/.ssh/aquamind_github_actions aquamind@test.aquamind.local
```

### Validation Commands
```bash
# Test database connection
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d $TEST_DB_NAME

# Test SSH connection
ssh -T aquamind@test.aquamind.local

# Validate SSL certificate
openssl x509 -in /opt/aquamind/ssl/test.crt -text -noout
```

---

**Remember: Security is everyone's responsibility. Always follow the principle of least privilege and regularly rotate secrets.**
