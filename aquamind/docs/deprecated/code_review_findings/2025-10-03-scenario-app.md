# Scenario Module Code Review Findings (2024-10-03)

## Blocking Issues

1. **CSV import services incomplete**  
   *Symptom:* `DataEntryViewSet.validate_csv` calls `BulkDataImportService.import_fcr_data` and `import_mortality_data`, but only temperature handlers exist, yielding runtime `AttributeError` for FCR/mortality uploads.  
   *Mitigation:* Implement the missing import routines (mirroring temperature flow) or gate the viewset action by data type until parity is achieved.

2. **Projection run fails for scenarios without initial weight**  
   *Symptom:* `ProjectionEngine.run_projection` casts `scenario.initial_weight` to `float`; serializers allow null weights, so running projections raises a server error.  
   *Mitigation:* Enforce non-null initial weights before projection (serializer or precondition check) or supply a defensible default weight in the engine.

3. **Projections aggregation endpoint broken**  
   *Symptom:* Weekly/monthly branches rely on `day_number__mod`, an invalid Django lookup, and then convert to `.values()`, which the serializer cannot handle.  
   *Mitigation:* Replace with `ExpressionWrapper`/`Func` (e.g., `Mod`) or `TruncWeek/TruncMonth` aggregations while keeping queryset instances for serialization.

4. **Scenario creation from batch can violate FK constraints**  
   *Symptom:* `ScenarioViewSet.from_batch` omits mandatory model FKs when `use_current_models=False` or no default models exist; the ensuing create call fails.  
   *Mitigation:* Validate model availability before creation (return 400 with guidance) or derive fallback models from batch metadata.

5. **Model change scheduling allows pre-start application**  
   *Symptom:* `ScenarioModelChange.clean` permits `change_day=0`; the engine computes `start_date + timedelta(change_day - 1)`, applying changes before day 1. Serializer validation also skips on create.  
   *Mitigation:* Clamp `change_day` to `>=1` in both serializer and model validation and adjust scheduling math to use zero-based indexing consistently.

## High-Priority Improvements

1. **CSV profile naming rules inconsistent**  
   `CSVUploadSerializer` forbids duplicating profile names, yet `BulkDataImportService` purposely overwrites existing profiles. Align validation with service capabilities (e.g., add opt-in `overwrite` flag or relax validation).

2. **Date-range profile save lacks conflict handling**  
   `DateRangeInputService.save_as_temperature_profile` unconditionally `create()`s a profile. Re-using a name raises an integrity error. Wrap in `get_or_create` or surface a clean validation error.

3. **Scenario duplication ignores projection flag**  
   The duplicate serializer exposes `include_projections`, but the viewset never uses it, misleading clients. Either honor the flag (recompute or copy projections) or drop it from the contract.

4. **Projection engine query load**  
   Temperature and FCR lookups execute per-day database hits. For long durations this becomes O(n) queries. Preload readings/overrides into memory or annotate models to keep projections performant.

## Suggested Next Steps

1. Add unit coverage for CSV imports across temperature, FCR, and mortality paths to catch missing handlers.  
2. Introduce request validation tests around projection and duplication endpoints to confirm preconditions and response contracts.  
3. Profile projection runs with sample data to quantify query volume, then optimize data access paths based on measurements.  
4. Document any behavioral decisions (e.g., overwrite semantics) after fixes so other droids can iterate on UX or API design.
