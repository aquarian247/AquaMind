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
```

### Architecture Principles

1. **Modular Design**: The system is divided into domain-specific apps, each responsible for a distinct functional area.
2. **Django MTV Architecture**: Strict adherence to Django's Model-Template-View pattern.
3. **RESTful API Design**: All client interactions occur through a well-defined REST API.
4. **Role-Based Access Control**: Security is enforced at multiple levels based on user roles.
5. **Time-Series Optimization**: Environmental and monitoring data leverages TimescaleDB for efficient storage and retrieval.

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
| **Contract Testing** | Backend CI runs **Schemathesis** with `--hypothesis-max-examples=10`, using runtime hooks (`aquamind.utils.schemathesis_hooks`) for auth & SQLite integer clamping. |
| **Cross-Repo Sync** | A Factory **Code Droid** watches for spec diffs; when detected, it opens coordinated PRs:<br>① Backend – spec change<br>② Frontend – regenerated TypeScript client.<br>Both PRs must pass contract tests before merge. |

**Why It Matters**  
This architecture guarantees that:  
1. Backend implementation ↔ OpenAPI spec stay in lock-step (Schemathesis fails CI if they diverge).  
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

> **Design Goal:** provide a single, consistent _frontend_ login flow while
> allowing the backend to operate in three very different environments  
> (local‐dev, shared DEV / TEST in the cloud, and production behind the
> corporate firewall).

The authentication stack therefore exposes **two parallel mechanisms** that
share the same `auth_user` table but are mounted at different URL prefixes.

| Purpose | URL prefix | Auth style | Typical environment |
|---------|------------|-----------|----------------------|
| **Primary / Production** – React frontend, mobile clients | `/users/auth/…` | **JWT** (*drf-simplejwt*) | All environments |
| **Development / CI** – fast API scripting, Fixture loading, Schemathesis | `/auth/…` | **DRF Token** + `dev-auth` helper | Local & CI only |

### 1. JWT Flow (`/users/auth/…`)
*   Endpoints: `token/`, `token/refresh/`, user registration, profile, password
    change.  
*   Issued tokens include custom claims (`auth_source`, `full_name`).  
*   Backed by **multibackend** Django auth:  
    1. `django_auth_ldap.backend.LDAPBackend` (production)  
    2. `django.contrib.auth.backends.ModelBackend` (local fallback)  
*   Token lifetimes: **12 h access / 7 d refresh** (see `settings.py → SIMPLE_JWT`).  
*   Front-end stores the *access* token in `localStorage.aquamine_token`
    (configurable). Refresh handled transparently by TanStack Query hooks.

### 2. DRF Token Flow (`/auth/…`)
*   Endpoints: `token/` (obtain), `dev-auth/` (fetch token for anonymous dev).  
*   **Not enabled in production** – guarded by `settings.DEBUG`.  
*   Used heavily by unit tests and Schemathesis where a quick token without JWT
    decoding overhead speeds up thousands of requests.

### 3. Multi-Environment Strategy
* **Local Dev / CI:** Uses DRF Token *or* JWT with local accounts. LDAP
  libraries are not loaded.  
* **Shared DEV / TEST:** Same as local but published on the Internet; testers
  use JWT.  
* **Production:** LDAP is enabled via env flag `USE_LDAP_AUTH=true`. If AD is
  unavailable the chain silently falls back to local super-users (break-glass).

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

- Local Docker containers for development
- PostgreSQL with TimescaleDB extension
- Development-specific settings with DEBUG enabled

### Testing Environment

- Continuous Integration environment
- SQLite for standard tests (without TimescaleDB features)
- Dedicated PostgreSQL with TimescaleDB for specialized tests

### Production Environment

- Containerized deployment with Docker
- High-availability PostgreSQL with TimescaleDB
- Load balancing for API endpoints
- Scheduled backups and monitoring

## Future Architecture Considerations

1. **Microservices Evolution**
   - Potential to evolve certain components into microservices for better scaling
   - Candidates include: Environmental monitoring, Reporting engine

2. **Real-time Data Processing**
   - Addition of message queues for real-time data processing
   - Event-driven architecture for alerts and notifications

3. **AI and Machine Learning Integration**
   - Integration points for predictive models
   - Data pipeline for training and inference

4. **Mobile Application Architecture**
   - API extensions for mobile-specific requirements
   - Offline data synchronization capabilities

## Architecture Decision Records

For significant architectural decisions, refer to the Architecture Decision Records (ADRs) in the `/docs/adr` directory. These records document the context, decision, and consequences of important architectural choices made during the development of AquaMind.
