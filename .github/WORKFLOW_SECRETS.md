# GitHub Actions Secrets Configuration

This document outlines the required secrets for deploying AquaMind to test environments using GitHub Actions.

## Required Secrets

### For Test Environment Deployment

Add these secrets to your GitHub repository settings under **Settings > Secrets and variables > Actions**:

#### SSH Access Secrets
```
TEST_SSH_PRIVATE_KEY
- Description: Private SSH key for accessing the test server
- Type: SSH private key (starts with -----BEGIN OPENSSH PRIVATE KEY-----)
- Generation: Run `ssh-keygen -t ed25519 -C "github-actions@yourorg.com"` on your local machine
- Copy the private key content (NOT the .pub file)

TEST_SSH_USER
- Description: SSH username for the test server
- Example: ubuntu, ec2-user, or your custom user
- Default: ubuntu (for Ubuntu servers)

TEST_SERVER_HOST
- Description: Public IP or hostname of your test server
- Example: test.yourdomain.com or 1.2.3.4
```

#### Optional: Notification Secrets
```
SLACK_WEBHOOK_URL
- Description: Slack webhook URL for deployment notifications
- Format: https://hooks.slack.com/services/...

DISCORD_WEBHOOK_URL
- Description: Discord webhook URL for deployment notifications
- Format: https://discord.com/api/webhooks/...
```

## SSH Key Setup

### 1. Generate SSH Key Pair
```bash
# On your local machine
ssh-keygen -t ed25519 -C "github-actions@yourorg.com" -f ~/.ssh/github-actions

# This creates:
# ~/.ssh/github-actions (private key)
# ~/.ssh/github-actions.pub (public key)
```

### 2. Copy Public Key to Test Server
```bash
# Copy the public key to your test server
ssh-copy-id -i ~/.ssh/github-actions.pub user@test-server-ip

# Or manually append to ~/.ssh/authorized_keys on the test server
cat ~/.ssh/github-actions.pub | ssh user@test-server-ip "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### 3. Test SSH Connection
```bash
# Test the connection
ssh -i ~/.ssh/github-actions user@test-server-ip "echo 'SSH connection successful'"
```

### 4. Add Private Key to GitHub Secrets
```bash
# Copy the entire private key content
cat ~/.ssh/github-actions

# Paste into GitHub secret: TEST_SSH_PRIVATE_KEY
# Make sure to include the BEGIN and END lines
```

## Test Server Preparation

### 1. Initial Server Setup
```bash
# On your test server
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-plugin

# Create aquamind user
sudo useradd -m -s /bin/bash aquamind
sudo usermod -aG docker aquamind

# Set up SSH access
sudo mkdir -p /home/aquamind/.ssh
sudo chown aquamind:aquamind /home/aquamind/.ssh
# Add the public key to /home/aquamind/.ssh/authorized_keys
```

### 2. Create Application Directory
```bash
# As aquamind user
mkdir -p ~/aquamind-test
cd ~/aquamind-test

# Create initial docker-compose.yml (will be updated by deployment)
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  # This will be updated by the deployment workflow
  placeholder: {}
EOF
```

## Workflow Usage

### Automatic Deployment
- Push to `test` branch → Automatic deployment
- Push to `main` branch → Production deployment (when configured)

### Manual Deployment
1. Go to **Actions** tab in GitHub
2. Select **Deploy to Test Environment**
3. Click **Run workflow**
4. Choose environment (test/staging)

### Manual Updates
1. Go to **Actions** tab
2. Select **Update Test Environment**
3. Choose action:
   - **restart**: Restart all services
   - **update-config**: Update docker-compose.yml
   - **backup-db**: Create database backup
   - **logs**: View service logs

## Security Best Practices

### SSH Key Management
- Use dedicated SSH key for GitHub Actions
- Never reuse personal SSH keys
- Rotate keys regularly (every 90 days)
- Remove old keys from `authorized_keys`

### Server Security
- Disable password authentication: `sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config`
- Use fail2ban for brute force protection
- Keep server updated: `sudo apt update && sudo apt upgrade`
- Configure UFW firewall

### Secret Management
- Never commit secrets to code
- Use GitHub's secret management
- Rotate secrets regularly
- Limit secret access to necessary workflows

## Troubleshooting

### SSH Connection Issues
```bash
# Test SSH connection manually
ssh -i ~/.ssh/github-actions -o StrictHostKeyChecking=no user@server "echo 'Connection successful'"

# Check SSH service status
sudo systemctl status ssh

# Check firewall rules
sudo ufw status
```

### Docker Issues
```bash
# Check Docker service
sudo systemctl status docker

# Check Docker logs
sudo journalctl -u docker -f

# Test Docker access
docker run hello-world
```

### Workflow Failures
- Check **Actions** tab for detailed logs
- Verify secrets are configured correctly
- Ensure SSH key has proper permissions (600)
- Check server disk space: `df -h`

## Monitoring

### Deployment Status
- GitHub Actions provides real-time deployment status
- Check server logs: `docker-compose logs -f`
- Monitor resource usage: `docker stats`

### Health Checks
The deployment workflow includes automatic health checks:
- Container status verification
- API endpoint testing
- Database connectivity validation

## Support

For issues with:
- **SSH Setup**: Check SSH key format and server permissions
- **Docker Issues**: Verify Docker installation and user permissions
- **Workflow Failures**: Review GitHub Actions logs and server logs
- **Secrets**: Ensure all required secrets are configured

---

**Last Updated**: September 16, 2025
**Version**: 1.0.0