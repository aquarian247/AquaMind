# FW→Sea Transfer Report Candidate Scan (2026-02-04)

**Sources (external reports):**
- `transfers_analyses/FW→Sea Transfer Mapping Analysis.md`
- `transfers_analyses/Freshwater Report Analysis - 2026-05-FreshwaterFøroyar.pdf.md`
- `transfers_analyses/Sea Report Analysis - 2026Týsdagsrapportvika5.pdf.md`

**Candidate transfer (external evidence):** Hvannasund S transfer plan dated **2025-12-17**
- Source FW halls: **S03 (18A/18B)**, **S24 (H/I/J)**, **S16 (E2)**, **S08 (T/R)**
- Destination: **A11 / A21 Hvannasund S**
- Fish counts/weights listed in the report (not in FishTalk DB).

## 1) FW hall populations overlapping the transfer window (2025-11-15 → 2026-02-15)

| Site | Hall | Population segments | Earliest Start | Latest End |
|---|---|---:|---|---|
| S03 Norðtoftir | 18 Høll A | 6 | 2025-10-24 | 2026-01-21 |
| S03 Norðtoftir | 18 Høll B | 22 | 2025-09-04 | 2026-01-09 |
| S08 Gjógv | R-Høll | 38 | 2025-09-08 | 2026-01-14 |
| S08 Gjógv | T-Høll | 15 | 2025-08-12 | 2026-01-13 |
| S16 Glyvradalur | E2 Høll | 6 | 2025-10-02 | 2025-12-29 |
| S24 Strond | H Høll | 4 | 2025-10-23 |  |
| S24 Strond | I Høll | 19 | 2025-10-14 | 2026-01-21 |
| S24 Strond | J Høll | 29 | 2025-09-24 | 2025-12-30 |

**Sample population names (per hall):**
- S03 Norðtoftir / 18 Høll A: Stofnfiskur sept 24
- S03 Norðtoftir / 18 Høll B: Stofnfiskur Juni 24; Stofnfiskur sept 24; Stofnfiskur Des 24
- S08 Gjógv / R-Høll: BF mars 2025; StofnFiskur okt. 2024
- S08 Gjógv / T-Høll: StofnFiskur okt. 2024; BF mars 2025
- S16 Glyvradalur / E2 Høll: Stofnfiskur Aug 2024; Stofnfiskur Nov 2024
- S24 Strond / H Høll: Benchmark Gen. Desembur 2024
- S24 Strond / I Høll: Benchmark Gen. Septembur 2024; Benchmark Gen. Desembur 2024; Benchmark Gen. Mars 2025
- S24 Strond / J Høll: Benchmark Gen. Desembur 2024; Benchmark Gen. Septembur 2024

## 2) Sea populations at A11/A21 (by start-time window)

**Sep–Nov 2024 (deployment window in sea report):**
- A11 Hvannasund S: 01 S24 SF SEP 24 (JUN 23); 02 S24 SF SEP 24 (JUN 23); 03 S24 SF SEP 24 (JUN 23); 04 S24 SF SEP 24 (JUN 23)
- A21 Hvannasund S: 06 S24 SF SEP 24 (JUN 23)

**Dec 2025–Feb 2026 (near FW transfer plan date):**
- A11 Hvannasund S: 06 S03 SF DES 25 (SEP 24) (*MO); 05 S03 SF DES 25 (SEP 24) (*MO); 10 S24 SF JAN 26 (SEP 24); 08 S03 SF DES 25 (SEP 24); 09 S24 SF JAN 26 (SEP 24); 12 S24 SF JAN 26 (SEP 24); 03 S16 SF DES 25 (AUG 24) (*MO); 04 S03 SF DES 25 (SEP 24) (*MO); 04 S03 SF DES 25 (JUN/SEP 24) (*½MO)
- A21 Hvannasund S: 04 S03 SF DES 25 (JUN 24); 06 S24 SF DES 25 (SEP 24); 05 S16 SF DES 25 (AUG 24) (*MO); 01 S24 SF DES 25 (SEP 24); 03 S24 SF DES 25 (SEP 24); 02 S08 SF JAN 26 (OKT 24)

## 3) Deterministic linkage check (current extract)
- `SubTransfers` rows in 2025-12-01 → 2026-02-15: **0** (no FW→Sea edges in this window).
- `PublicTransfers` FW→Sea edges do not exist in 2023+ per prior scans; no canonical edges here.

## 4) Candidate linkage status
- **Status:** External-report–sourced candidate only (non-canonical).
- **Gap:** No DB-native transfer edge linking these FW hall populations to A11/A21 sea populations in this backup.
- **Next:** If we accept external reports as evidence, we can create provisional FW→Sea links with explicit provenance metadata.