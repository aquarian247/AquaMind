# BakkaMind Test Environment

## Goal

Run a production-style shared test environment on `/opt/bakkamind` using:

- immutable backend and frontend images built in GitHub Actions
- server-resident secrets and runtime configuration
- `docker compose pull` + `docker compose up -d` deployments
- no source bind mounts
- no on-server application builds

This is the recommended path for a stable test environment. It differs from the
local migration preview flow, which is optimized for developer iteration.

## Canonical GitHub Workflows

Use these workflows as the canonical test deployment path:

- `AquaMind/.github/workflows/django-tests.yml`
- `AquaMind/.github/workflows/docker-build-backend.yml`
- `AquaMind-Frontend/.github/workflows/frontend-ci.yml`
- `AquaMind-Frontend/.github/workflows/docker-build-frontend.yml`
- `AquaMind/.github/workflows/deploy-test.yml`

Treat these as legacy and plan to retire them once the new flow is adopted:

- `AquaMind/.github/workflows/deploy-full-test.yml`
- `AquaMind/.github/workflows/update-test.yml`

## Secrets and Configuration Boundaries

Application secrets should stay on the server:

- database password
- Django secret key
- runtime `.env`
- Caddyfile

The Caddyfile itself usually contains no secrets. It should contain:

- the public hostname, for example `test.bakkamind.com`
- proxy routes
- optionally a contact email for certificate issuance

TLS certificates are then handled automatically by Caddy.

Deployment secrets can live in GitHub Actions secrets:

- GHCR pull token
- GHCR username
- admin bootstrap credentials

Recommended backend repo secrets:

- `GHCR_USERNAME`
- `GHCR_PULL_TOKEN`
- `TEST_ADMIN_USERNAME`
- `TEST_ADMIN_EMAIL`
- `TEST_ADMIN_PASSWORD`

Recommended GitHub Actions variable:

- `TEST_PUBLIC_HOST=test.bakkamind.com`

## Recommended Server Layout

```text
/opt/bakkamind
  ├── docker-compose.yml
  ├── Caddyfile
  ├── .env
  └── (named Docker volumes only; no app source checkouts)
```

## Recommended `/opt/bakkamind/docker-compose.yml`

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
      - staticfiles:/srv/static:ro
      - media:/srv/media:ro
    depends_on:
      - frontend
      - web
    networks:
      - bakkamind-net

  timescale-db:
    image: timescale/timescaledb:latest-pg17
    restart: unless-stopped
    environment:
      POSTGRES_DB: aquamind_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - bakkamind-net

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
    networks:
      - bakkamind-net

  web:
    image: ${BAKKAMIND_BACKEND_IMAGE:-ghcr.io/aquarian247/aquamind/backend:main}
    restart: unless-stopped
    env_file: .env
    depends_on:
      - timescale-db
      - redis
    command: >
      gunicorn aquamind.wsgi:application
      --bind 0.0.0.0:8000
      --workers 3
      --timeout 120
    volumes:
      - staticfiles:/app/staticfiles
      - media:/app/media
    networks:
      - bakkamind-net

  celery-worker:
    image: ${BAKKAMIND_BACKEND_IMAGE:-ghcr.io/aquarian247/aquamind/backend:main}
    restart: unless-stopped
    env_file: .env
    depends_on:
      - web
      - redis
    command: celery -A aquamind worker -l info
    volumes:
      - media:/app/media
    networks:
      - bakkamind-net

  frontend:
    image: ${BAKKAMIND_FRONTEND_IMAGE:-ghcr.io/aquarian247/aquamind-frontend/frontend:main}
    restart: unless-stopped
    depends_on:
      - web
    networks:
      - bakkamind-net

networks:
  bakkamind-net:

volumes:
  postgres_data:
  redis_data:
  caddy_data:
  staticfiles:
  media:
```

## Recommended `/opt/bakkamind/Caddyfile`

```caddy
{
    email infra@bakkamind.com
}

test.bakkamind.com {
    handle /api/* {
        reverse_proxy web:8000
    }

    handle /admin/* {
        reverse_proxy web:8000
    }

    handle /static/* {
        root * /srv
        file_server
    }

    handle /media/* {
        root * /srv
        file_server
    }

    handle {
        reverse_proxy frontend:80
    }
}
```

Notes:

- There are no app secrets in this file.
- Caddy will attempt to obtain Let's Encrypt certificates automatically.
- For that to work, `test.bakkamind.com` must resolve publicly to the server and
  inbound ports `80` and `443` must reach the host.
- If the environment is not publicly reachable, automatic Let's Encrypt HTTP-01
  validation will not work and you will need a different certificate strategy.

## Recommended `/opt/bakkamind/.env`

```dotenv
POSTGRES_PASSWORD=replace-with-real-password

DJANGO_SECRET_KEY=replace-with-long-random-string
DJANGO_DEBUG=false
DJANGO_SETTINGS_MODULE=aquamind.settings

DB_ENGINE=django.db.backends.postgresql
DB_NAME=aquamind_db
DB_USER=postgres
DB_PASSWORD=${POSTGRES_PASSWORD}
DB_HOST=timescale-db
DB_PORT=5432

ALLOWED_HOSTS=test.bakkamind.com,localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=https://test.bakkamind.com
CSRF_TRUSTED_ORIGINS=https://test.bakkamind.com

CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

Do not rely on `DATABASE_URL` alone for this project. The current Django
settings read `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`
directly, so those must be present in `.env`.

## Deployment Flow

### Build phase

1. Backend repo pushes trigger:
   - `django-tests.yml`
   - `docker-build-backend.yml`
2. Frontend repo pushes trigger:
   - `frontend-ci.yml`
   - `docker-build-frontend.yml`
3. Both images are published to GHCR with branch and SHA tags.

### Deploy phase

Use `AquaMind/.github/workflows/deploy-test.yml` as the canonical deploy entry
point. It performs:

1. The self-hosted GitHub runner executes directly on the test server.
2. `docker login ghcr.io`.
3. `docker compose pull web celery-worker frontend`.
4. `docker compose up -d timescale-db redis`.
5. `docker compose run --rm web python manage.py migrate`.
6. `docker compose run --rm web python manage.py collectstatic --noinput`.
7. `docker compose run --rm web python manage.py ensure_admin_user`.
8. `docker compose up -d web celery-worker frontend caddy`.
9. health-check the root site and a backend API endpoint through Caddy.

The admin bootstrap command is idempotent. It reads:

- `DJANGO_SUPERUSER_USERNAME`
- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD`

from the deploy workflow and creates or updates the admin account on every
deploy.

## What You Need To Configure

### 1. On the server

Create these files under `/opt/bakkamind`:

- `docker-compose.yml`
- `Caddyfile`
- `.env`

Install on the server:

- Docker Engine
- Docker Compose plugin

Open inbound ports:

- `80/tcp`
- `443/tcp`

### 2. In DNS

Create an `A` or `AAAA` record:

- `test.bakkamind.com -> <public IP of the test server>`

### 3. In GitHub repository secrets for `AquaMind`

- `GHCR_USERNAME`
- `GHCR_PULL_TOKEN`
- `TEST_ADMIN_USERNAME`
- `TEST_ADMIN_EMAIL`
- `TEST_ADMIN_PASSWORD`

Recommended values:

- `TEST_ADMIN_USERNAME`: the admin login name you want
- `TEST_ADMIN_EMAIL`: your email
- `TEST_ADMIN_PASSWORD`: a strong password

### 4. In GitHub repository variables for `AquaMind`

- `TEST_PUBLIC_HOST=test.bakkamind.com`

### 5. In GitHub repository variables for `AquaMind-Frontend`

Until the frontend is fully same-origin `/api` driven, set:

- `VITE_DJANGO_API_URL=https://test.bakkamind.com`

This makes the built frontend image target the public test domain correctly.

### 6. Self-hosted runner

The canonical deployment flow assumes a self-hosted GitHub Actions runner is
already registered on the test server with the standard labels:

- `self-hosted`
- `linux`
- `x64`

Because the runner executes locally on the target server, no SSH deploy secret
is required for the normal `deploy-test.yml` path.

### Rollback phase

Redeploy by re-running `deploy-test.yml` with older image tags:

- `backend_tag=<older-tag>`
- `frontend_tag=<older-tag>`

Because the environment is image-based, rollback is just a tag change and a
repeat deploy.

## Why This Is Better Than Building On The Server

- no giant source transfers during deploy
- no accidental inclusion of ETL/migration payloads
- no dependency on sibling repo layout
- reproducible images from CI
- faster and safer rollback
- secrets stay on the server

## Notes on Image Inputs

- Backend images now build from `AquaMind/Dockerfile` instead of `Dockerfile.dev`.
- Backend build context is aggressively trimmed by `.dockerignore`, excluding:
  - `scripts/`
  - `docs/`
  - `tests/`
  - logs, caches, local DB files, and dev artifacts
- Frontend builds also use `.dockerignore` so local `node_modules`, test
  artifacts, and docs do not bloat the build context.

## Remaining Improvement Opportunity

The frontend image still bakes `VITE_DJANGO_API_URL` at build time. For a single
test environment that is acceptable, but the next improvement would be moving
the frontend to same-origin `/api` semantics so the same image can be reused
across environments without rebuild-time host changes.
