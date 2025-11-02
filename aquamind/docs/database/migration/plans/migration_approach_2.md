# FishTalk to AquaMind Migration Approach

**Version:** 2.0  
**Date:** November 2, 2025  
**Audience:** IT Management & AVEVA System Owners  
**Status:** Proposal for Review

---

## Executive Summary

AquaMind is Bakkafrost's new aquaculture management system replacing FishTalk. This document outlines our data migration strategy focusing on **active batches** and operational data. We're requesting **local database copies** to enable a fast, safe, and controlled migration with zero impact on production systems.

**Key Request:** Database backups of FishTalk and AVEVA systems for local migration environment.

---

## Migration Scope

### What We're Migrating
✅ **All fish batches** (complete 6-7 year operational history)  
✅ **Complete inventory history** (feed stock, containers, FIFO records)  
✅ **Full health records** (medical journal, treatments, mortality)  
✅ **Environmental data** (sensor readings, 6-7 years)  
✅ **User accounts & permissions**  
✅ **Harvest records & financial data**  

### What We're NOT Migrating
❌ Deprecated/inactive infrastructure records  
❌ Legacy report configurations  
❌ System logs and debug data  

**Rationale:** Full historical data enables trend analysis, regulatory compliance (multi-year audits), and complete traceability from egg to harvest. However, we'll test migration approach with a **2-year subset first**, then expand to full 6-7 year dataset once validated.

---

## Why Local Database Copies?

### Our Approach: Local Development + Testing Environment

Instead of migrating directly from production systems via APIs, we will:

1. **Get full database backups** of FishTalk and AVEVA (complete 6-7 year history)
2. **Restore locally** on development MacBook (128GB RAM, M4 Max, 4TB storage)
3. **Develop migration scripts** against local copies
4. **Test with 2-year subset** first, then expand to full dataset
5. **Validate repeatedly** without affecting production
6. **Execute final migration** in controlled cutover window

### Benefits for Bakkafrost

| Benefit | Description |
|---------|-------------|
| **Zero Production Impact** | No load on FishTalk or AVEVA during development/testing |
| **Faster Development** | 60-100x faster than API queries (critical for 6-7 years of data) |
| **Repeatable Testing** | Test migration 10+ times before production cutover |
| **Full Validation** | Compare source vs. target data side-by-side across entire history |
| **Risk Reduction** | Identify data quality issues before go-live |
| **Flexible Timeline** | No dependency on production system availability |
| **Scalability Testing** | Validate performance with full data volume before go-live |

### Technical Note
Our development Mac can run FishTalk, AVEVA, and AquaMind databases simultaneously for rapid testing cycles. With 6-7 years of environmental sensor data (potentially 100M+ readings), **local database access is essential**—API-based migration would take months and risk production system overload.

---

## What We Need from IT & AVEVA Teams

### 1. FishTalk Database Backup
**From:** Bakkafrost IT  
**Format:** SQL Server full backup (.bak file) or equivalent  
**Scope:** Complete database with 6-7 years of operational history  
**Timeline:** ASAP to start development  

**Estimated Size:** TBD (please advise - likely 50-500GB depending on data)  
**Transfer Method:** 
- Preferred: Secure file share or OneDrive (if size permits)
- Alternative: Physical USB drive/external SSD for large backups

### 2. AVEVA Systems Database Access
**From:** AVEVA System Owner  
**Requirement:** Database backup(s) with 6-7 years of environmental/sensor data  

**Questions for AVEVA Team:**
- What database platform does AVEVA use? (SQL Server, Oracle, PostgreSQL, InSQL?)
- How many separate databases store sensor data?
- Can you provide full backups, or should we extract specific date ranges?
- **Estimated database size for 6-7 years of sensor readings?** (Critical for planning)
- Are there data retention policies or archival systems we should know about?

**Alternative:** If full backups are not feasible due to size, we can work with:
- Compressed/filtered backups (excluding debug/system tables)
- CSV exports for specific date ranges
- Staged delivery (2018-2020, 2020-2022, 2022-2025)

**Note:** With 6-7 years of high-frequency sensor data, API-based extraction is not practical. Local database access is essential for this migration approach.

### 3. Schema Documentation (Optional but Helpful)
- FishTalk entity-relationship diagrams or data dictionary
- AVEVA sensor tag naming conventions and container mappings
- Any existing migration guides or data export procedures

---

## Migration Timeline Overview

### Phase 1: Preparation & Initial Testing (3 weeks)
- Receive and restore database backups locally
- Analyze schemas and validate field mappings
- Develop extraction and transformation scripts
- **Test migration with 2-year subset** (5-10 batches, 2023-2025 data)

### Phase 2: Full Historical Migration Testing (3 weeks)
- Execute full 6-7 year test migration
- Validate data accuracy and completeness across entire history
- Performance testing with full data volume
- Refine scripts based on findings

### Phase 3: User Acceptance (1-2 weeks)
- Business users review migrated data in test environment
- Validate historical trends and reports
- Document any discrepancies or issues
- Final script adjustments

### Phase 4: Production Cutover (1 weekend)
- Execute migration during planned maintenance window
- Run comprehensive validation reports
- Go-live on Monday with full support
- Monitor system performance with full data load

**Total Duration:** ~8-10 weeks from database backup receipt to production

**Incremental Approach:** Start with recent data (2023-2025) for faster validation cycles, then expand to full historical dataset (2018-2025) once approach is proven.

---

## Our Migration Strategy

### Chronological Data Replay

We've developed a proven approach that recreates batch lifecycles in **chronological order**, ensuring:

- ✅ Complete audit trails for regulatory compliance
- ✅ Accurate feed conversion ratios and growth calculations
- ✅ Proper container assignment history
- ✅ User attribution for all operational events

This approach mirrors how we generate test data for AquaMind, giving us high confidence in data integrity.

### Data Source Strategy

| Data Type | Primary Source | Historical Scope | Estimated Volume |
|-----------|---------------|------------------|------------------|
| Batch operations | FishTalk database | 6-7 years | ~200-500 batches |
| Feed & inventory | FishTalk database | 6-7 years | ~2-5M feeding events |
| Health records | FishTalk database | 6-7 years | ~50-100K journal entries |
| Environmental data | AVEVA database | 6-7 years | ~50-200M sensor readings |
| Harvest/financial | FishTalk database | 6-7 years | ~10-20K harvest events |

**Key Insight:** AVEVA likely has better quality sensor data than FishTalk's internal sensor tables, so we'll use AVEVA as primary source for environmental readings. With 6-7 years of high-frequency sensor data (potentially 100M+ readings), **local database access is not just preferred—it's essential** for successful migration.

---

## Data Security & Compliance

### Handling of Database Copies

- ✅ Stored on encrypted development machine only
- ✅ Not shared outside development team
- ✅ Deleted after successful production migration
- ✅ No production credentials stored in scripts
- ✅ All access logged for audit purposes

### Audit Trail Preservation

AquaMind maintains complete change history for all migrated records, including:
- Original FishTalk record IDs (for reference)
- Migration timestamp and user
- Source system identification

This ensures regulatory compliance and traceability from legacy to new system.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| **Database backups too large to transfer** | Staged delivery, compressed backups, or physical drive transfer |
| **Historical data quality issues** | Test with recent data first; gives time to resolve older data issues |
| **Schema differences from documentation** | Local copies let us analyze real structure before migration |
| **Migration takes longer than expected** | Incremental approach: validate 2-year subset first, then expand |
| **Performance issues with 6-7 years of data** | Local testing environment allows performance optimization before go-live |
| **AVEVA database size/complexity** | Can work with filtered exports if full backup not feasible |

---

## Success Criteria

✅ **100% of batches** (6-7 years) migrated with complete history  
✅ **Zero data loss** for financial and compliance records  
✅ **Complete environmental trends** available for analysis  
✅ **All users** can access historical and current operational data  
✅ **Audit trails** preserved for regulatory compliance (multi-year)  
✅ **System performance** meets or exceeds FishTalk with full data load  
✅ **Historical reporting** functional (YoY comparisons, trend analysis)

---

## Next Steps

### Immediate Actions (This Week)

1. **IT Team:** Assess FishTalk database backup feasibility and size
2. **AVEVA Team:** Identify database platform and backup procedures
3. **Development Team:** Prepare local environment and restore procedures
4. **All:** Schedule kickoff meeting to review technical details

### Questions for Discussion

- Preferred method for secure database transfer (given potentially large file sizes)?
- Any constraints on database backup timing or size?
- AVEVA database size and feasibility of full 6-7 year backup?
- Are there data archival/compression strategies already in place we should leverage?
- AVEVA maintenance windows or access restrictions?
- Contact persons for technical troubleshooting during migration?

---

## Contact & Support

**Migration Lead:** [Your Name]  
**Email:** [Your Email]  
**Phone:** [Your Phone]  

**Availability:** Daily for questions and coordination

---

## Appendix: Why This Approach Works

Our test data generation system already simulates complete salmon lifecycles (850+ days) with:
- 300,000+ events per batch
- Chronologically-correct stage transitions
- Realistic growth patterns and feed consumption
- Full audit trail generation

By adapting these proven scripts to read from FishTalk/AVEVA instead of generating synthetic data, we leverage a battle-tested framework that guarantees data integrity and regulatory compliance.

**This isn't a typical "export CSV and import" migration—it's a sophisticated chronological replay that recreates operational history exactly as it occurred.**

---

**End of Document**

*Questions? Contact the migration team for clarification on any aspect of this approach.*
