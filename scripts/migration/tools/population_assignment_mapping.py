from __future__ import annotations

from collections.abc import Iterable

from apps.migration_support.models import ExternalIdMap


ASSIGNMENT_SCOPED_SOURCE_MODEL = "PopulationComponentPopulationAssignment"
LEGACY_ASSIGNMENT_SOURCE_MODEL = "Populations"


def build_component_population_identifier(
    component_key: str,
    population_id: str,
) -> str:
    return f"{str(component_key).strip()}:{str(population_id).strip()}"


def extract_population_id(source_model: str, source_identifier: str) -> str:
    raw_identifier = (source_identifier or "").strip()
    if (
        source_model == ASSIGNMENT_SCOPED_SOURCE_MODEL
        and ":" in raw_identifier
    ):
        return raw_identifier.split(":", 1)[1].strip()
    return raw_identifier


def get_assignment_external_map(
    population_id: str,
    *,
    component_key: str | None = None,
    allow_legacy_fallback: bool = True,
) -> ExternalIdMap | None:
    pop_id = str(population_id or "").strip()
    if not pop_id:
        return None

    if component_key:
        scoped_identifier = build_component_population_identifier(
            str(component_key),
            pop_id,
        )
        scoped_map = ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model=ASSIGNMENT_SCOPED_SOURCE_MODEL,
            source_identifier=scoped_identifier,
            target_app_label="batch",
            target_model="batchcontainerassignment",
        ).first()
        if scoped_map:
            return scoped_map

    if not allow_legacy_fallback:
        return None

    return ExternalIdMap.objects.filter(
        source_system="FishTalk",
        source_model=LEGACY_ASSIGNMENT_SOURCE_MODEL,
        source_identifier=pop_id,
        target_app_label="batch",
        target_model="batchcontainerassignment",
    ).first()


def upsert_assignment_external_maps(
    *,
    component_key: str,
    population_id: str,
    target_app_label: str,
    target_model: str,
    target_object_id: int,
    metadata: dict | None = None,
    update_legacy_map: bool = True,
) -> tuple[ExternalIdMap, ExternalIdMap | None]:
    pop_id = str(population_id or "").strip()
    if not pop_id:
        raise ValueError(
            "population_id must be non-empty for assignment mapping"
        )
    comp_key = str(component_key or "").strip()
    if not comp_key:
        raise ValueError(
            "component_key must be non-empty for assignment mapping"
        )

    map_metadata = dict(metadata or {})
    map_metadata.setdefault("component_key", comp_key)

    scoped_identifier = build_component_population_identifier(comp_key, pop_id)
    scoped_map, _ = ExternalIdMap.objects.update_or_create(
        source_system="FishTalk",
        source_model=ASSIGNMENT_SCOPED_SOURCE_MODEL,
        source_identifier=scoped_identifier,
        defaults={
            "target_app_label": target_app_label,
            "target_model": target_model,
            "target_object_id": target_object_id,
            "metadata": map_metadata,
        },
    )
    if update_legacy_map:
        legacy_map, _ = ExternalIdMap.objects.update_or_create(
            source_system="FishTalk",
            source_model=LEGACY_ASSIGNMENT_SOURCE_MODEL,
            source_identifier=pop_id,
            defaults={
                "target_app_label": target_app_label,
                "target_model": target_model,
                "target_object_id": target_object_id,
                "metadata": map_metadata,
            },
        )
    else:
        legacy_map = ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model=LEGACY_ASSIGNMENT_SOURCE_MODEL,
            source_identifier=pop_id,
            target_app_label=target_app_label,
            target_model=target_model,
            target_object_id=target_object_id,
        ).first()
    return scoped_map, legacy_map


def get_component_assignment_maps(component_key: str) -> list[ExternalIdMap]:
    comp_key = str(component_key or "").strip()
    if not comp_key:
        return []

    scoped_rows = list(
        ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model=ASSIGNMENT_SCOPED_SOURCE_MODEL,
            source_identifier__startswith=f"{comp_key}:",
            target_app_label="batch",
            target_model="batchcontainerassignment",
        )
    )
    if scoped_rows:
        return scoped_rows

    return list(
        ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model=LEGACY_ASSIGNMENT_SOURCE_MODEL,
            target_app_label="batch",
            target_model="batchcontainerassignment",
            metadata__component_key=comp_key,
        )
    )


def build_population_lookup_from_maps(
    mappings: Iterable[ExternalIdMap],
) -> dict[int, str]:
    pop_by_assignment_id: dict[int, str] = {}
    for mapping in mappings:
        metadata = mapping.metadata or {}
        if metadata.get("folded_culling_tail"):
            # Prefer the canonical non-folded population for assignment-level
            # validation and reporting when multiple FishTalk populations map to
            # the same AquaMind assignment.
            continue
        pop_id = extract_population_id(
            mapping.source_model,
            mapping.source_identifier,
        )
        if pop_id:
            pop_by_assignment_id[mapping.target_object_id] = pop_id
    return pop_by_assignment_id
