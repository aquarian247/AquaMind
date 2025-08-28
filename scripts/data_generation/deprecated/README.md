# Deprecated Data Generation Scripts

This folder contains deprecated scripts that were used during the initial development of the data generation system. These scripts have been replaced by the comprehensive orchestrator system in the parent directory.

## Archived Scripts

### Feed System Implementation (August 2025)
These scripts were used for initial feed system testing before Session 2 implementation:

- **`create_feed_infrastructure.py`** - Created feed containers and infrastructure
- **`create_feed_stock.py`** - Generated initial feed stock records
- **`create_feeding_events.py`** - Created feeding event records
- **`create_health_monitoring.py`** - Generated health monitoring data
- **`feed_analysis.py`** - Analyzed feed consumption patterns
- **`run_complete_feed_system.py`** - Orchestrated the above scripts

## Why Deprecated?

These scripts were superseded by the session-based orchestrator system which provides:
- Better memory management
- Checkpoint/resume capability
- Integrated data generation across all modules
- Proper temporal progression
- Production-scale data generation

## Current System

For current data generation, use:
```bash
python scripts/data_generation/run_generation.py --session=[1-4]
```

See the parent directory's README.md for full documentation.

---
*Archived: January 2025*
