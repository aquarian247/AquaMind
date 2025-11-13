## Inventory Geography Filtering Implementation Plan

### Summary
- Introduce real geography / area filters to the Inventory experience so tab content reflects the user’s selection.
- Keep the homepage KPI strip global until backend KPIs expose geography parameters; align tab-level KPIs and tables with filtered data.
- Extend existing Django aggregation endpoints instead of layering complex client-side filtering.

### Required Reading & References
- `client/src/pages/inventory.tsx`, `client/src/features/inventory/components/InventoryTabsContent.tsx`, `client/src/features/inventory/api.ts`
- Filter widget: `client/src/components/layout/hierarchical-filter.tsx`
- Executive dashboard pattern (geography-aware): `client/src/features/executive/pages/ExecutiveDashboardPage.tsx`, `client/src/features/executive/api/api.ts`
- Backend endpoints:
  - `apps/inventory/api/viewsets/feeding.py` (`summary`, `finance_report`, filter class)
  - `apps/inventory/api/viewsets/container_stock.py` (`summary`)
  - `apps/inventory/api/filters/feeding.py`
  - `apps/infrastructure/api/viewsets` for geography/area listings if needed
- OpenAPI spec (`api/openapi.yaml`) for parameter names and request shapes.

### Backend Enhancements
1. **Feeding Events Summary**
   - Accept optional `geography`, `area`, `hall`, `freshwater_station`, `container__in` query params.
   - Reuse `FeedingEventFilter` logic (or apply explicit joins) before aggregating counts.
   - Update OpenAPI annotations and regenerate client (`npm run sync:openapi`).
2. **Feed Container Stock Summary**
   - Accept the same geography/area/hall filters.
   - Join through `feed_container.area`/`hall` to scope queryset prior to aggregation.
   - Document defaults (global when no filters supplied).
3. **(Optional) Feed Purchases**
   - Evaluate data model; if purchases can be linked to area/container, add foreign keys and filters. Otherwise, note limitation in docs.
4. **Tests**
   - Extend existing API tests or add new ones covering geography filters, ensuring results narrow correctly.

### Frontend Enhancements
1. **Filter Widget**
   - Replace `SAMPLE_REGIONS` with dynamic data from `apiV1InfrastructureGeographiesList`.
   - On region select, fetch areas / halls for dependent dropdowns (lazy load or prefetch).
   - Persist selections as numeric IDs (`geographyId`, `areaIds`, `stationIds`, `hallIds`).
2. **Query Hooks**
   - Extend inventory hooks to accept optional filter DTO:
     - `useFeedContainerStockSummary`, `useFeedContainerStock`
     - `useFeedingEvents`, `useFeedingEventsSummaryLastDays`, `useFeedingEventsFinanceReport`
   - Pass query params only when IDs are defined to avoid breaking caches.
3. **Page Wiring**
   - Lift filter state into `inventory.tsx`.
   - Keep top KPI strip global; propagate filters to tabs via props.
   - Ensure tabs render consistent metrics (e.g., 7-day feed KPI matches filtered summary).
4. **Fallback Handling**
   - If backend filtering is unavailable (e.g., feed purchases), leave content global and surface tooltip / helper text.

### Testing & Verification
- Backend: run `python manage.py test apps.inventory.api` (or targeted modules) and any new tests, as well as the full ci run to make sure no breaking changes.
- Frontend: `npm run test`.
- Manual QA: verify `/inventory` UI updates when selecting different regions/areas; confirm operations overview remains global.

---

## Implementation Status (2025-11-13)

### ✅ Backend Completed

#### 1. Feed Container Stock Summary (`/api/v1/inventory/feed-container-stock/summary/`)
- **Geography filters added**: `geography`, `area`, `hall`, `freshwater_station`
- **Implementation**: Manual Q-based filtering for geography (marine areas + freshwater stations)
- **OpenAPI schema**: Updated with all geography filter parameters
- **Tests**: New test file `apps/inventory/tests/test_feed_container_stock_summary.py` (2 tests passing)

#### 2. Feeding Events Summary (`/api/v1/inventory/feeding-events/summary/`)
- **Geography filters added**: `geography`, `geography__in`, `area`, `area__in`, `hall`, `hall__in`, `freshwater_station`, `freshwater_station__in`
- **Implementation**: Uses `FeedingEventFilter.filter_queryset()` for consistent filtering
- **Filter class**: `apps/inventory/api/filters/feeding.py` with custom `filter_geography()` and `filter_geography_in()` methods
- **OpenAPI schema**: Comprehensive parameter documentation (lines 162-216)
- **Tests**: Extended test file `apps/inventory/tests/test_feeding_events_summary_range.py` with geography filter tests (11 tests passing)

#### 3. Filter Implementation Details
**FeedingEventFilter** (`apps/inventory/api/filters/feeding.py`):
- Geography filter uses Q-based OR logic: `Q(container__area__geography__id=value) | Q(container__hall__freshwater_station__geography__id=value)`
- Supports both marine containers (via `container → area → geography`) and freshwater containers (via `container → hall → station → geography`)
- Handles both single ID (`geography=1`) and multiple IDs (`geography__in=1,2`)

#### 4. Test Coverage
- **Feed container stock**: 2 new tests validating geography/area/hall/station filters
- **Feeding events**: 11 tests including geography filter combinations
- **Full inventory suite**: 201 tests passing (3 skipped)
- **Full project suite**: 1,214 tests passing (62 skipped)

#### 5. Key Fixes During Implementation
- **RBAC compatibility**: Tests create users with automatic ADMIN/ALL profile via signals
- **Cache handling**: Added `cache.clear()` in test setUp to prevent cross-test contamination
- **Geography filter semantics**: Fixed test expectations to account for OR logic (Scotland geography returns both area-based AND hall-based containers)

### ⏭️ Pending Backend Tasks
1. **Feed Purchases Summary**: Low priority, requires data model evaluation
2. **OpenAPI spec regeneration**: Run `python manage.py spectacular --file api/openapi.yaml --validate`
3. **Backend PR**: Create feature branch PR with comprehensive summary

### 🔜 Frontend Tasks (Not Started)
1. Replace `SAMPLE_REGIONS` with dynamic geography data
2. Extend inventory query hooks with geography filter parameters
3. Wire filter state into `inventory.tsx` page
4. Update tab components to pass filters through
5. Frontend testing with new filters
6. Frontend PR after backend contract is stable

### 📝 Notes
- Geography filter pattern (Q-based OR) matches existing patterns in batch and operational endpoints
- All filters are optional; omitting them returns global aggregates
- Cache decorators remain in place (`@cache_page(30)` for summary, `@cache_page(60)` for finance report)
- Filter implementation respects RBAC: operators with geography restrictions automatically see filtered results

### Risks & Mitigations
- **Incomplete backend filtering** – coordinate with backend to land API changes before frontend expects them.
- **Performance** – ensure new filters reuse existing indices; cache high-cost summaries as before.
- **UX Clarity** – clearly communicate when certain datasets remain global; add badges/tooltips where necessary.

### Deliverables
- Backend PR with updated endpoints, tests, and OpenAPI spec.
- Frontend PR updating filters, hooks, and page wiring.
- Updated documentation (if needed: docs/AGGREGATION_ENDPOINTS_CATALOG.md and aquamind/docs/quality_assurance/AGGREGATION_ENDPOINTS_CATALOG.md - they have the same content, but both repos need a copy for now).

