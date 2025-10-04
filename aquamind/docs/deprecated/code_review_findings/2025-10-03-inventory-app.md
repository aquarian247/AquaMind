# Inventory App Code Review Findings

## Overview
- Scope focused on models, serializers, viewsets, and services under `apps.inventory` plus supporting utilities and tests.
- Goal was to surface correctness, data integrity, and API contract issues that block reliable inventory tracking.

## Critical Defects & Mitigations

### 1. `BatchFeedingSummary.generate_for_batch` writes invalid fields
- **Impact:** `update_or_create` passes `average_biomass_kg`, `growth_kg`, and `average_biomass` which are not real columns, triggering `FieldError`; summaries never persist.
- **Mitigation:** Align defaults with actual model fields (`total_starting_biomass_kg`, `total_growth_kg`, etc.). Add regression test around `generate_for_batch` to catch mismatches.

### 2. FIFO cost calculation never succeeds in serializer
- **Impact:** `FeedingEventSerializer.create` calls `FIFOInventoryService.consume_feed_fifo` with unsupported keyword arguments, so it always raises, leading to the fallback path that double-subtracts stock and fabricates costs.
- **Mitigation:** Fix call signature (`consume_feed_fifo(feed_container=..., quantity_kg=..., feeding_event=...)`) and remove the fallback mutation once FIFO succeeds. Cover with unit tests exercising serializer create flow.

### 3. Feed stock adjustments are not atomic or update-safe
- **Impact:** `FeedingEvent.save` expects `_original_amount_kg` (never set) so updates subtract twice; creations can push stock negative without validation, corrupting quantities.
- **Mitigation:** Track original amount via `__init__`/`refresh_from_db`, perform stock validation before commit, and wrap adjustments in `transaction.atomic`. Add concurrency-aware tests to ensure quantities never dip below zero.

### 4. Reliance on absent `Batch.biomass_kg`
- **Impact:** `calculate_feeding_percentage` assumes batches expose `biomass_kg`; many models do not, causing `AttributeError` during save.
- **Mitigation:** Prefer the `batch_biomass_kg` field captured on the event; only hit batch attributes when present. Add defensive fallbacks and tests for batches lacking live biomass metrics.

## High-Priority Observations
- `FeedStockViewSet` declares `ordering_fields=['current_quantity_kg', 'last_updated']`, but the model uses `updated_at`, yielding API 400s. Update the field name and add a smoke test for ordering.
- FIFO fallback in serializer subtracts from `feed_stock` before model `save` performs its own decrement, doubling the deduction if both execute. Once the serializer call is fixed, ensure only one path mutates stock.
- No validation links `feed_stock.feed` or `feed_stock.feed_container` back to the submitted event, so mismatched combinations can slip through. Add cross-field validation.
- `summary` action caches responses for 30 seconds without keying on query params, returning wrong aggregates for different requests. Vary cache by arguments or drop caching until pagination strategy is defined.

## Testing & Coverage Gaps
- Viewset tests patch out `FeedStock.save`, hiding the broken stock logic and bad FIFO call. Rework tests to exercise real model behavior and assert on stock balances.
- No test covers `BatchFeedingSummary.generate_for_batch`; add one to verify persistence and output fields.
- Missing API tests for `FeedContainerStockViewSet` custom actions (`add_to_container`, `fifo_order`, etc.) and for `FeedingEventViewSet.summary` scenarios (single date vs. range validation).

## Suggested Next Steps
1. Patch model/service defects above, starting with serializer FIFO invocation and stock accounting to stabilize inventory numbers.
2. Extend automated tests to protect the corrected flows and prevent regression (serializer create, summary generation, FIFO endpoints).
3. Revisit caching/ordering configs after correctness fixes land.
4. Consider adding monitoring around feed stock deltas to detect future drift once fixes deploy.
