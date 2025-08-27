# Archived Data Generation Files

This folder contains archived files from the data generation development process.

## Contents

### Databases
- **`data_generation_db.sqlite3`** - Temporary SQLite database used during initial data generation testing

### Backup Files
- **`backup_session1_pre_session2.json`** - Checkpoint backup from Session 1 completion

### Investigation Documents
- **`backend-fcr-investigation-issue.md`** - Investigation notes on FCR (Feed Conversion Ratio) implementation issues

## Note

These files are kept for historical reference but are not needed for the current data generation system. The production system uses:
- TimescaleDB (not SQLite)
- Checkpoint files in the `checkpoints/` directory
- Comprehensive documentation in the parent directory

---
*Archived: January 2025*
