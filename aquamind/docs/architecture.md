# AquaMind Architecture Documentation

## Overview

AquaMind is a comprehensive aquaculture management system built on Django 4.2.11 with Python 3.11. The system follows a modular architecture organized around key functional domains of aquaculture management, with TimescaleDB integration for efficient time-series data handling.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Applications                     │
│  (Web Browsers, Mobile Apps, External System Integrations)  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       API Layer                             │
│         Django REST Framework + JWT Authentication          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                         │
│                                                             │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  Core   │  │   Users  │  │Infrastructure│ Batch Mgmt  │  │
│  └─────────┘  └──────────┘  └──────────┘  └──────────────┘  │
│                                                             │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │Environmental│ Inventory │  │  Health  │  │ Operational │  │
│  └─────────┘  └──────────┘  └──────────┘  └──────────────┘  │
│                                                             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Data Layer                              │
│      PostgreSQL + TimescaleDB (Time-Series Extension)       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               Asynchronous Processing Layer                 │
│         Redis (Message Broker) + Celery (Task Queue)        │
│     Background tasks, event-driven recomputation, jobs      │
└─────────────────────────────────────────────────────────────┘
```

### Architecture Principles

1. **Modular Design**: The system is divided into domain-specific apps, each responsible for a distinct functional area.
2. **Django MTV Architecture**: Strict adherence to Django's Model-Template-View pattern.
3. **RESTful API Design**: All client interactions occur through a well-defined REST API.
4. **Role-Based Access Control**: Security is enforced at multiple levels based on user roles.
5. **Time-Series Optimization**: Environmental and monitoring data leverages TimescaleDB for efficient storage and retrieval.
6. **Event-Driven Processing**: Asynchronous task queue (Celery) enables background processing and real-time recomputation without blocking user requests.

## Component Architecture

### Core Apps and Their Responsibilities

#### 1. Core App (`core`)
- Shared utilities and base classes used across the system
- Common middleware and custom Django extensions
- System-wide constants and configuration

#### 2. Users App (`users`)
- User authentication and authorization
- Role-based access control
- User profiles with geography and subsidiary filtering
- Audit logging of user actions

#### 3. Infrastructure App (`infrastructure`)
- Management of physical assets (geographies, areas, stations)
- Container management (halls, tanks, pens)
- Sensor configuration and management
- Hierarchical organization of physical infrastructure

#### 4. Batch App (`batch`)
- Fish batch lifecycle management
- Growth tracking and sampling
- Lifecycle stage transitions
- Container assignments and transfers
- Mortality tracking

#### 5. Environmental App (`environmental`)
- Time-series environmental data collection and storage
- Sensor data integration (via WonderWare)
- Weather data integration (via OpenWeatherMap)
- Environmental parameter thresholds and alerts

#### 6. Inventory App (`inventory`)
- Feed management and tracking
- Stock level monitoring
- Feeding events and feed conversion ratio calculations
- Inventory alerts and reordering

#### 7. Health App (`health`)
- Health monitoring and journaling
- Disease tracking and treatment records
- Mortality cause analysis
- Sampling and lab results

#### 8. Operational App (`operational`)
- Daily task scheduling and management
- Resource allocation
- Operational dashboards
- Planning and forecasting

#### 9. Scenario App (`scenario`)
- Growth projections and scenario modeling
- TGC (Thermal Growth Coefficient) models
- Mortality models and biological constraints
- What-if analysis for production planning

### Asynchronous Processing Layer

**Redis + Celery** 

AquaMind uses **Redis** as a message broker and **Celery** as an asynchronous task queue to enable background processing without blocking user requests.

**Primary Use Case: Growth Assimilation (Batch Management)**

When operational events occur (growth samples, transfers, treatments, mortality), the system must recompute daily "actual" states for affected batches. This computation:
- Can take 1-5 seconds for large date ranges
- Must reflect real measurements (not just projections)
- Should not block the user who recorded the event

**Architecture Flow:**

```
Operational Event (e.g., Growth Sample recorded)
         ↓
Django Signal Handler (lightweight - just enqueues task)
         ↓
Redis Message Broker (stores task with parameters)
         ↓
Celery Worker (background process - executes computation)
         ↓
Growth Assimilation Engine (TGC-based daily state calculation)
         ↓
ActualDailyAssignmentState (TimescaleDB hypertable - stores results)
```

**Components:**

1. **Redis**
   - Message broker for Celery task queue
   - Cache backend for Django (session storage, deduplication)
   - Deployment: Containerized (Docker) or native service
   - Port: 6379 (default)

2. **Celery Workers**
   - Background processes that execute queued tasks
   - Concurrency: 2-4 workers (dev), 4-8 workers (production)
   - Tasks: Growth assimilation recomputation, scheduled jobs
   - Monitoring: `celery -A aquamind inspect active`

3. **Celery Beat** (optional, for scheduled tasks)
   - Scheduler for periodic tasks (e.g., nightly catch-up jobs)
   - Alternative: Cron jobs calling Django management commands

**Key Tasks:**

- `recompute_assignment_window`: Recompute daily states for one assignment (triggered by anchors: samples, transfers, treatments)
- `recompute_batch_window`: Recompute daily states for entire batch (triggered by batch-level events: mortality)
- Deduplication: Multiple events on same day → single recompute task (via Redis SET with TTL)

**Integration Points:**

| Event | Signal | Task | Window |
|-------|--------|------|--------|
| Growth sample recorded | `on_growth_sample_saved` | `recompute_assignment_window` | ±2 days |
| Transfer with measured weight | `on_transfer_completed` | `recompute_assignment_window` | ±2 days |
| Treatment with weighing | `on_treatment_with_weighing` | `recompute_assignment_window` | ±2 days |
| Mortality event | `on_mortality_event` | `recompute_batch_window` | ±1 day |

**Benefits:**

- **Non-blocking**: User requests return immediately; computation happens in background
- **Durability**: Tasks survive server restarts (stored in Redis)
- **Retry logic**: Automatic retry on failure (max 3 retries with exponential backoff)
- **Scalability**: Add more Celery workers to handle load
- **Transparency**: Full provenance tracking (which data sources were used, confidence scores)

**Nightly Catch-up Job:**

A management command (`recompute_recent_daily_states`) runs nightly to catch any missed events:
```bash
# Via cron (production)
python manage.py recompute_recent_daily_states --days 14

# Via Celery Beat (future)
CELERY_BEAT_SCHEDULE = {'nightly-catchup': {...}}
```

### Data Flow Architecture

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ External Data │     │  User Input   │     │ Scheduled     │
│ Sources       │     │  (Web/Mobile) │     │ Tasks         │
└───────┬───────┘     └───────┬───────┘     └───────┬───────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                       API Layer                             │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │ Data Ingestion  │  │ CRUD Operations │  │ Reporting   │  │
│  │ Endpoints       │  │ Endpoints       │  │ Endpoints   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
│                                                             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Business Logic Layer                      │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │ Data Validation │  │ Business Rules  │  │ Calculations│  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
│                                                             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Data Access Layer                       │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │ Django ORM      │  │ Raw SQL for     │  │ TimescaleDB │  │
│  │ Queries         │  │ Complex Queries │  │ Functions   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
│                                                             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Database Layer                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                PostgreSQL Database                  │    │
│  │                                                     │    │
│  │  ┌─────────────────┐       ┌─────────────────────┐  │    │
│  │  │ Regular Tables  │       │ TimescaleDB         │  │    │
│  │  │                 │       │ Hypertables         │  │    │
│  │  └─────────────────┘       └─────────────────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Key Interfaces and Integration Points

### External System Integrations

1. **WonderWare Integration**
   - Purpose: Collection of sensor data from physical infrastructure
   - Integration Method: API-based data ingestion
   - Data Flow: WonderWare → Environmental App → TimescaleDB hypertables

2. **OpenWeatherMap Integration**
   - Purpose: Collection of weather data for geographical areas
   - Integration Method: API client with scheduled data collection
   - Data Flow: OpenWeatherMap API → Environmental App → TimescaleDB hypertables

### API Contract Synchronization

| Pillar | Details |
|--------|---------|
| **Spec Generation** | `drf-spectacular ≥ 0.28` builds a **single OpenAPI 3.1** file (`api/openapi.yaml`) on every push. |
| **CI Artefact** | GitHub Actions uploads this schema as an artefact; workflow name `Generate & Validate API Spec`. |
| **Frontend Consumption** | Front-end repo downloads the artefact, then runs `openapi-typescript-codegen` to regenerate the typed client & hooks. |
| **Contract Testing** | Backend CI runs the Django API regression suite (`python manage.py test tests.api`) alongside OpenAPI validation to keep schema and implementation aligned. |
| **Cross-Repo Sync** | A Factory **Code Droid** watches for spec diffs; when detected, it opens coordinated PRs:<br>① Backend – spec change<br>② Frontend – regenerated TypeScript client.<br>Both PRs must pass contract tests before merge. |

**Why It Matters**  
This architecture guarantees that:  
1. Backend implementation ↔ OpenAPI spec stay in lock-step (OpenAPI validation workflow + API regression tests fail CI if they diverge).  
2. Frontend always compiles against the latest, type-safe client without manual steps.  
3. Documentation (Swagger / ReDoc) is auto-published and always accurate.  

### Internal Component Interfaces

1. **Batch-Infrastructure Interface**
   - Purpose: Assignment of batches to containers
   - Primary Models: `BatchContainerAssignment` links `Batch` to `Container`
   - Key Operations: Creation, transfer, and tracking of batch locations

2. **Batch-Health Interface**
   - Purpose: Tracking health events and mortality for batches
   - Primary Models: `JournalEntry`, `MortalityRecord` linked to `Batch`
   - Key Operations: Recording health observations, treatments, and mortality events

3. **Batch-Inventory Interface**
   - Purpose: Tracking feed consumption and feed conversion ratios
   - Primary Models: `FeedingEvent` links `Batch` to `Feed` and `FeedStock`
   - Key Operations: Recording feeding events, calculating FCR, updating biomass

4. **Environmental-Infrastructure Interface**
   - Purpose: Associating environmental readings with physical locations
   - Primary Models: `EnvironmentalReading` linked to `Sensor` and `Container`
   - Key Operations: Recording and retrieving time-series environmental data

## Security Architecture

### Authentication

> **Design Goal:** provide a single, consistent _frontend_ login flow using JWT
> authentication across all environments (local dev, testing, production).

The authentication stack uses **JWT authentication** as the primary mechanism:

| Purpose | URL prefix | Auth style | Response Format |
|---------|------------|-----------|-----------------|
| **Primary / All Environments** – React frontend, API clients | `/api/token/…` | **JWT** (*drf-simplejwt*) | `{"access":"...","refresh":"..."}` |
| **Development Only** – API testing, automation | `/api/auth/…`, `/api/v1/auth/…` | **DRF Token** + `dev-auth` helper | `{"token":"...","user_id":7,"username":"test"}` |

### 1. JWT Flow (`/api/token/…`)
*   Endpoints: `POST /api/token/` (obtain), `POST /api/token/refresh/` (refresh)
*   Returns standard JWT tokens with access/refresh pair
*   Backed by Django's `ModelBackend`
*   Token lifetimes: **12 h access / 7 d refresh**
*   Front-end stores the *access* token in `localStorage.auth_token`
*   Refresh handled transparently by TanStack Query hooks

### 2. DRF Token Flow (`/api/auth/…`, `/api/v1/auth/…`)
*   Endpoints:
    * `POST /api/auth/token/` and `POST /api/v1/auth/token/` (obtain DRF token)
    * `GET /api/v1/auth/dev-auth/` (fetch token for anonymous dev)
*   **Not enabled in production** – guarded by `settings.DEBUG`
*   Used heavily by API regression tests where a quick token without JWT decoding overhead speeds up repeated requests
*   Provides alternative token-based auth for development and testing scenarios

### 3. Multi-Environment Strategy
* **Local Dev / CI:** Uses JWT with local accounts. No AD/LDAP integration required.
* **Shared DEV / TEST:** Same as local but published on the Internet; testers use JWT.
* **Production:** JWT with local accounts (AD/LDAP integration can be added later if needed)

### 4. Security Considerations
* HTTPS enforced in all non-local environments.  
* Argon2 password hasher for local accounts.  
* Tokens transmitted only via `Authorization: Bearer …` header – _never_
  in query-string.  
* CSRF protection is maintained for session-based admin logins; API uses
  stateless auth.  
* All auth events are audit-logged with source (ldap / local) for forensics.

For a deep-dive see  
`/AquaMind_Authentication_Architecture_Strategy.md`.

### Authorization

1. **Role-Based Access Control**
   - User roles define base permissions
   - Roles include: Admin, Manager, Operator, Veterinarian, etc.

2. **Geography-Based Filtering**
   - Users are restricted to specific geographies (e.g., Faroe Islands, Scotland)
   - Data queries are automatically filtered based on user's geography access

3. **Subsidiary-Based Filtering**
   - Further restriction based on subsidiary (e.g., Broodstock, Freshwater, Farming)
   - Ensures users only see data relevant to their operational area

4. **Function-Based Access**
   - Horizontal access control for specialized roles (QA, Finance, Veterinarians)
   - Provides cross-cutting access to specific functionality regardless of geography

### Data Protection

- Encryption of sensitive data at rest
- Secure transmission via HTTPS
- Comprehensive audit logging of data access and modifications

## Deployment Architecture

AquaMind is designed to be deployed in various environments with different configurations:

### Development Environment

- Local Docker containers for development (or native services on M2 Max)
- PostgreSQL with TimescaleDB extension
- Redis for caching and Celery message broker
- Celery workers for background task processing
- Development-specific settings with DEBUG enabled

### Testing Environment

- Continuous Integration environment
- SQLite for standard tests (without TimescaleDB features)
- Dedicated PostgreSQL with TimescaleDB for specialized tests

### Production Environment

- Containerized deployment with Docker
- High-availability PostgreSQL with TimescaleDB
- Redis clustering for message broker HA
- Multiple Celery workers for horizontal scaling
- Load balancing for API endpoints
- Scheduled backups and monitoring
- Health checks for all services (Django, Celery, Redis, PostgreSQL)

## Future Architecture Considerations

1. **Microservices Evolution**
   - Potential to evolve certain components into microservices for better scaling
   - Candidates include: Environmental monitoring, Reporting engine

2. **Real-time Data Processing** ✅ **Partially Implemented (Phase 4)**
   - ✅ Celery + Redis message queue for background processing
   - ✅ Event-driven architecture for growth assimilation
   - Future: WebSocket support for real-time dashboard updates
   - Future: Stream processing for high-frequency sensor data

3. **AI and Machine Learning Integration**
   - Integration points for predictive models
   - Data pipeline for training and inference

4. **Mobile Application Architecture**
   - API extensions for mobile-specific requirements
   - Offline data synchronization capabilities

## Architecture Decision Records

For significant architectural decisions, refer to the Architecture Decision Records (ADRs) in the `/docs/adr` directory. These records document the context, decision, and consequences of important architectural choices made during the development of AquaMind.
