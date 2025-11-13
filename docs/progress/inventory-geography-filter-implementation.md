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
- Backend: run `python manage.py test apps.inventory.api` (or targeted modules) and any new tests.
- Frontend: `npm run test`.
- Manual QA: verify `/inventory` UI updates when selecting different regions/areas; confirm operations overview remains global.

### Risks & Mitigations
- **Incomplete backend filtering** – coordinate with backend to land API changes before frontend expects them.
- **Performance** – ensure new filters reuse existing indices; cache high-cost summaries as before.
- **UX Clarity** – clearly communicate when certain datasets remain global; add badges/tooltips where necessary.

### Deliverables
- Backend PR with updated endpoints, tests, and OpenAPI spec.
- Frontend PR updating filters, hooks, and page wiring.
- Updated documentation (`docs/progress` entry and README snippet if behavior changes).

