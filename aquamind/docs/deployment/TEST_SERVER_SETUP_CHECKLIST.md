# Test Server Setup Checklist - AquaMind (Bakkafrost Test Environment)

**Goal**: Clean, simple, solid, observable deployment on the test server using:
- GitHub Container Registry (GHCR) images
- Caddy as the **single reverse proxy** with Let’s Encrypt
- Minimal middleware (no duplicate Nginx layers)
- Health checks

Current location: `/opt/bakkamind/`

**Do this with the server/security person.**

### 1. Preparation & Cleanup (Existing App is Running)

```bash
cd /opt/bakkamind

# Stop everything
docker compose down --remove-orphans

# Backup current config
cp docker-compose.yml docker-compose.yml.bak 2>/dev/null || true
cp Caddyfile Caddyfile.bak 2>/dev/null || true
cp nginx.test.conf nginx.test.conf.bak 2>/dev/null || true

# Remove old containers/networks
docker rm -f $(docker ps -a -q -f name=aquamind) 2>/dev/null || true
docker network rm aquamind-net 2>/dev/null || true
```

### 2. Required Files

**File**: `/opt/bakkamind/docker-compose.yml` (updated simplified version)

```yaml
version: '3.9'

services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - static:/srv/static:ro
      - media:/srv/media:ro
    depends_on:
      - web
      - frontend
    networks:
      - aquamind-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  web:
    image: ghcr.io/YOUR-ORG/aquamind/backend:latest
    restart: unless-stopped
    env_file: .env
    volumes:
      - static:/app/staticfiles
      - media:/app/media
    depends_on:
      - timescale-db
      - redis
    networks:
      - aquamind-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    image: ghcr.io/YOUR-ORG/aquamind-frontend:latest
    restart: unless-stopped
    networks:
      - aquamind-net

  timescale-db:
    image: timescale/timescaledb:latest-pg14
    restart: unless-stopped
    env_file: .env
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - aquamind-net

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - aquamind-net

  celery-worker:
    image: ghcr.io/YOUR-ORG/aquamind/backend:latest
    restart: unless-stopped
    command: celery -A aquamind worker -l info --concurrency=3
    env_file: .env
    depends_on:
      - timescale-db
      - redis
    networks:
      - aquamind-net

networks:
  aquamind-net:

volumes:
  postgres_data:
  redis_data:
  caddy_data:
  static:
  media:
```

**File**: `/opt/bakkamind/Caddyfile`

```caddy
{
    email security@bakkafrost.com
}

test.bakkamind.com {
    handle /api/* {
        reverse_proxy web:8000
    }
    handle /admin/* {
        reverse_proxy web:8000
    }
    handle /static/* {
        root * /srv/static
        file_server
    }
    handle /media/* {
        root * /srv/media
        file_server
    }
    handle /health {
        reverse_proxy web:8000
    }
    handle {
        reverse_proxy frontend:80
    }
}
```

### 3. Deployment Steps

```bash
cd /opt/bakkamind

# Login to GHCR (use PAT)
echo $GHCR_PAT | docker login ghcr.io -u YOUR-GITHUB-USERNAME --password-stdin

docker compose pull
docker compose up -d

docker compose exec web python manage.py migrate
```

### 4. Final Verification

- Application available at **https://test.bakkamind.com**
- All services running: `docker compose ps`
- Health checks passing
- Let’s Encrypt certificate active (check in Caddy logs)

**Notes**:
- We removed the duplicate Nginx layer from `docker-compose.test.yml` and deprecated `nginx.test.conf`.
- Prometheus/Grafana not included yet — added later when needed.
- Update `YOUR-ORG` and image tags as appropriate.

---
**End of Checklist**
