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

- JWT (JSON Web Token) based authentication
- Token refresh mechanism for extended sessions
- Secure token storage and transmission

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
