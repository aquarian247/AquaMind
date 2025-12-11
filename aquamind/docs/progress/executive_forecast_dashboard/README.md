# Executive Forecast Dashboard

**Status**: Planning  
**Priority**: High (CFO Request)  
**Estimated Effort**: 4-5 days

## Overview

Portfolio-level forecasting for executives to visualize:
- **Harvest forecasts**: When will batches reach target weight?
- **Sea-transfer forecasts**: When will freshwater batches be smolt-ready?

## Key Documents

- [Implementation Plan](./executive_forecast_dashboard_plan.md) - Full technical specification

## Prerequisites

This feature builds directly on:
- ✅ Batch Growth Assimilation (Phase 8/8.5)
- ✅ Production Planner with scenario projections
- ✅ Activity templates with weight/stage triggers

## Quick Start (When Implementing)

1. Create `apps/dashboard/` Django app
2. Implement aggregation endpoints
3. Build frontend dashboard cards
4. Add to navigation (executives only)

## CFO Value Proposition

> "How many harvests in Q2? Which sea-transfers are delayed? What's our projected biomass?"

All answerable with existing data—this is a read-only aggregation layer.


