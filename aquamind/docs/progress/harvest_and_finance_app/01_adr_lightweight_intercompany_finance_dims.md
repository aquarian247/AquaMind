# ADR 000X – Lightweight Inter-Company Handling & Finance Dimensions  

Date: 2025-09-11  
Status: Accepted  

## 1 Context  

AquaMind must support inter-company (IC) reporting without bloating the operational schema.  
Current state  
• No table representing legal companies/subsidiaries.  
• User segregation relies on `users.UserProfile.geography` and `users.UserProfile.subsidiary` (TextChoices).  
• Infrastructure models already carry geography:  
  – `FreshwaterStation.geography`  → **implies subsidiary Freshwater**  
  – `Area.geography` → **implies subsidiary Farming**  
• Harvest functionality (Issue 2) will add `dest_geography` FK and `dest_subsidiary` enum on `HarvestEvent`.  

Need  
1. Detect IC movements (source ≠ destination company).  
2. Feed Finance facts / NAV export without introducing cross-app FK churn.  
3. Keep RBAC and operations unchanged.  

## 2 Decision  

1. **No operational `Company` model** – operations stay agnostic (see [ADR 0001](../../adr/ADR_0001_lightweight_intercompany_finance_dims.md)).  
2. **Finance layer owns company mapping** via two new dimension tables:  

| Dim | Key | Populated from | Purpose |
|-----|-----|---------------|---------|
| `dim_company` | (`geography`, `subsidiary`) | TextChoices / seed script | single source for legal entity metadata (currency, NAV code) |
| `dim_site` | infra object PK + type | `FreshwaterStation` / `Area` | resolves to `dim_company_id` for facts |

3. **Company derivation rule**  
```text
source_company_key = (assignment.container → hall/station OR area).geography , inferred subsidiary  
dest_company_key   = (HarvestEvent.dest_geography , dest_subsidiary)
```
4. **Inter-company detection** happens in Finance projections: create `IntercompanyTransaction` when keys differ and a policy exists.  

## 3 Consequences  

Positives  
• Zero impact on existing apps & migrations.  
• RBAC continues to leverage geography/subsidiary enums.  
• Finance can evolve legal-entity structures privately (add rows, not FKs).  

Trade-offs  
• Operational queries needing “company” must replicate derivation logic.  
• Multiple legal entities per (geo, sub) would require a future `Company` table → prepared by nullable `legal_entity_code` column in `dim_company`.  

## 4 Alternatives Considered  

| Option | Why rejected |
|--------|--------------|
| Introduce `users.Company` + add FKs on infra & batch models | High migration cost; cross-app entanglement; context rot risk |
| Free-text company codes on Harvest events | Breaks referential integrity; invalidates RBAC filters |
| Use only `geography` and ignore subsidiary | Fails to distinguish Broodstock vs Farming within same geography |

## 5 Implementation Sketch  

1. **Models (Finance app)**  
```python
class DimCompany(models.Model):
    geography = models.ForeignKey('infrastructure.Geography', on_delete=models.PROTECT)
    subsidiary = models.CharField(max_length=3, choices=Subsidiary.choices)
    display_name = models.CharField(max_length=60)
    currency = models.CharField(max_length=3, null=True, blank=True)
    nav_company_code = models.CharField(max_length=20, null=True, blank=True)
```
`DimSite` links infra objects → `DimCompany`.

2. **HarvestEvent fields**  
```python
dest_geography = models.ForeignKey('infrastructure.Geography', null=True, blank=True)
dest_subsidiary = models.CharField(max_length=3, choices=Subsidiary.choices, null=True, blank=True)
```

3. **Projection logic**  
Derive keys, look-up `DimCompany`, build `FactHarvest`, evaluate IC.

4. **Design-spec alignment** – remove references to `users.Company` / `infrastructure.Site`, add Finance dims & keys.

## 6 Open Decisions / Defaults  

| Topic | Default | Change process |
|-------|---------|----------------|
| Pricing method | `market` unless policy overrides | Finance > IntercompanyPolicy |
| Grade taxonomy | Codes from `ProductGrade` table; mapping TBD | Ops + Finance agree list |
| NAV transport | Secure bucket CSV | revisit once NAV API matures |
| FX source | No FX (single currency) | future Issue when multi-currency required |

## 7 References (Context Pack)  

1. `docs/design/finance_harvest_design_spec.md`  
2. `docs/quality_assurance/api_standards.md`  
3. `docs/architecture.md`  
4. `docs/prd.md`  
5. `docs/personas.md`  
6. `docs/database/data_model.md`

## 8 Acceptance Checklist  

- [x] ADR merged at `docs/adr/ADR_0001_lightweight_intercompany_finance_dims.md`.  
- [x] Design spec updated: Finance dims, dest fields, terminology.  
- [x] Links to this ADR added in spec & implementation plan.  
- [ ] Routers/settings re-validated against API standards (no basename omissions) — not applicable for documentation-only Issue 1; confirm when APIs ship.  

