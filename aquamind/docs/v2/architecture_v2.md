# AquaMind Architecture Version 2

**Version**: 2.0  
**Date**: December 18, 2025  
**Status**: Visionary Blueprint (Target Implementation: H2 2026 – H1 2027)  
**Context**: Evolution to AI-Native Platform

## Overview

AquaMind V1's architecture—modular Django backend, RESTful APIs, PostgreSQL with TimescaleDB hypertables, Celery asynchronous processing, and React/TypeScript frontend—has proven robust for data integrity, regulatory compliance, and operational scalability.

Version 2 preserves this **durable substrate** as the unchanging system of record while introducing an **agentic intelligence layer** and **generative interface layer**. This aligns with the emerging paradigm of "product as durable substrate with pixels as throwaway": the core data model, business logic, and audit trails remain fixed and reliable, while user-facing experiences become ephemeral, context-aware renders generated on-demand by AI agents.

By mid-2026, convergence of massive-context multimodal models, mature agent orchestration frameworks, and generative UI tools will make this hybrid feasible at enterprise scale—delivering proactive, role-tailored intelligence without sacrificing compliance or data sovereignty.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Lightweight Client Shell                   │
│  (Mobile/Web Apps – Voice, Text, Minimal Durable UI)        │
│  Renders ephemeral views from agent outputs                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               Generative Interface Layer                    │
│  Agent-generated UI descriptions (JSON/SVG/Three.js/Markdown)│
│  Ephemeral visualizations, voice synthesis, camera overlays │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                Agentic Intelligence Layer                   │
│  Multimodal LLM agents (schema-aware, tool-calling)          │
│  Proactive monitoring, reasoning chains, guarded actions    │
│  Nightly/event-driven orchestration                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Durable Substrate (V1 Core)                │
│  Django REST APIs │ PostgreSQL/TimescaleDB │ Celery Tasks    │
│  Audit trails │ Signals │ Hypertable computations            │
└─────────────────────────────────────────────────────────────┘
```

### Architecture Principles

1. **Substrate Stability**: Core data model, APIs, and business rules (growth assimilation, live projections, EoM valuations, transfer workflows) remain unchanged—ensuring continuity, compliance, and backward compatibility.
2. **Agentic Proactivity**: Intelligence layer continuously observes data streams, reasons over full context, and initiates guarded workflows.
3. **Ephemeral Pixels**: No fixed dashboards; interfaces generated per interaction for maximal relevance.
4. **Human-in-the-Loop**: All state-changing actions require explicit user approval; overrides train the system.
5. **Data Sovereignty & Compliance**: Agents run in controlled environments (on-prem/private cloud) with row-level security inherited from substrate APIs.
6. **Hybrid Evolution**: Traditional React UI retained as fallback/"advanced mode" during transition.

## Component Layers

### 1. Durable Substrate (Unchanged Foundation)

- **Backend**: Django 4.x+ with DRF APIs – authoritative source for all data and logic.
- **Database**: PostgreSQL + TimescaleDB for hypertables (environmental readings, daily assimilation states, projections).
- **Async Processing**: Celery + Redis for background tasks (assimilation, live forward projection, EoM runs).
- **Integrations**: Wonderware/AVEVA sensors, OpenWeatherMap, NAV exports – remain direct or via signals.
- **Security**: JWT auth, row-level permissions (geography/subsidiary/role), django-simple-history audits.

This layer becomes the "truth engine" that agents query and act upon via tool-calling.

### 2. Agentic Intelligence Layer (New)

- **Core Technology (Projected Mid-2026)**:
  - Leading multimodal models (Grok 5, GPT-5 equivalents, or open weights like Llama 4) with 5–10M+ token contexts and native tool-calling.
  - Deployment: Hybrid – private cloud/API for speed, on-prem fine-tuned instances for sensitive reasoning.
  - Schema embedding: Full data model + recent state loaded into context or via advanced RAG.

- **Orchestration**:
  - Frameworks like LangGraph, CrewAI, or xAI agent stacks – production-mature by 2026.
  - Agents specialized by domain: Health Agent, Operations Agent, Finance Agent, Executive Agent.
  - Event triggers: Postgres LISTEN/NOTIFY on key changes; nightly proactive scans.

- **Capabilities**:
  - Continuous monitoring and anomaly detection.
  - Reasoning chains (e.g., env spike → growth impact → feeding adjustment → workflow draft).
  - Guarded execution: Propose → human review → API call with user token.
  - Learning: Overrides logged as fine-tuning data (anonymized).

### 3. Generative Interface Layer (New)

- **Core Technology (Projected Mid-2026)**:
  - Mature successors to v0.dev, Galileo, or similar – agent-to-UI description pipelines.
  - Structured outputs: JSON for layouts, SVG/Three.js for visualizations, Markdown with embedded media.

- **Rendering Patterns**:
  - Ephemeral views: Dynamic charts (biomass projections), camera overlays (tank/ring anomalies), 3D simulations (transfer routes).
  - Multimodal: Voice synthesis for briefs; vision analysis of uploaded photos/videos.
  - Convergence: Data-aware reasoning and UI generation handled by same agent chain.

- **Client Shell**:
  - Lightweight mobile/web app (React Native or Progressive Web App).
  - Responsibilities: Auth, voice/text input, real-time rendering of agent outputs, fallback to V1 grids.

### 4. Security & Compliance Overlay

- **Inherited Controls**: All agent actions via substrate APIs → full row-level security and audit trails.
- **Agent Guardrails**: Explicit approval gates for state changes; hallucination checks via substrate verification calls.
- **Privacy**: No exfiltration of sensitive data; on-prem options for broodstock genetics or health records.
- **Explainability**: All agent outputs reference source data (e.g., "Based on hypertable chunk X, reading_time Y").

## Technology Projections (6–12 Months)

- **LLMs/Agents**: Grok 5 or equivalents achieve reliable enterprise tool-calling; agent frameworks support production monitoring.
- **Generative UI**: Tools evolve to robust structured outputs; client libraries handle dynamic renders securely.
- **Voice/Multimodal**: Native in leading models; edge deployment viable for field use (Starlink-enabled ships).
- **Realistic Constraints**: Full "no substrate" UIs remain immature for compliance domains → hybrid model dominates.

## Migration Path

1. **V1.5 (Q1–Q2 2026)**: Add read-only co-pilot chat; agent prototypes on health/operations.
2. **V1.8 (Q3–Q4 2026)**: Proactive notifications; generative views for select flows.
3. **V2 (H1 2027)**: Agent-first default; traditional UI optional.

AquaMind V2 positions Bakkafrost at the forefront of AI-native enterprise systems—leveraging our exceptional data substrate to deliver intelligence that anticipates needs while preserving the reliability that defines our operations.
