"""
Read-model style lineage resolver for mixed batches.

This service builds an ancestry graph and compounded source-share breakdown
for a batch using container-scoped mix events. It falls back to BatchComposition
when no mix event is available for a mixed batch.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, List, Tuple

from apps.batch.models import Batch, BatchComposition, BatchMixEvent


class MixedLineageService:
    """
    Resolve mixed-batch ancestry into:
    - graph nodes/edges (batch + mix-event nodes)
    - compounded root source shares
    """

    ROOT_SHARE = Decimal("100")

    @classmethod
    def build_lineage(cls, batch: Batch, as_of_date: date | None = None) -> Dict:
        if as_of_date is None:
            as_of_date = date.today()

        state = {
            "batch_nodes": {},
            "mix_nodes": {},
            "edges": [],
            "root_shares": {},
            "unresolved_batches": set(),
            "max_depth": 0,
            "resolution_notes": set(),
        }

        cls._walk_batch(
            batch=batch,
            incoming_share=cls.ROOT_SHARE,
            depth=0,
            as_of_date=as_of_date,
            state=state,
            call_path=set(),
        )

        root_sources = sorted(
            [
                {
                    "batch_id": source_batch_id,
                    "batch_number": state["batch_nodes"].get(source_batch_id, {}).get(
                        "batch_number"
                    ),
                    "percentage": str(root_share.quantize(Decimal("0.01"))),
                }
                for source_batch_id, root_share in state["root_shares"].items()
            ],
            key=lambda item: Decimal(item["percentage"]),
            reverse=True,
        )

        return {
            "batch": {
                "id": batch.id,
                "batch_number": batch.batch_number,
                "batch_type": batch.batch_type,
            },
            "as_of_date": as_of_date.isoformat(),
            "mode": "container_scoped_mixing_lineage",
            "max_depth": state["max_depth"],
            "root_sources": root_sources,
            "unresolved_batches": sorted(state["unresolved_batches"]),
            "boundaries": {
                "flattening_strategy": "latest_mix_event_per_mixed_batch",
                "resolution_notes": sorted(state["resolution_notes"]),
            },
            "graph": {
                "batch_nodes": sorted(
                    state["batch_nodes"].values(), key=lambda item: item["batch_id"]
                ),
                "mix_nodes": sorted(
                    state["mix_nodes"].values(), key=lambda item: item["node_id"]
                ),
                "edges": state["edges"],
            },
        }

    @classmethod
    def _walk_batch(
        cls,
        *,
        batch: Batch,
        incoming_share: Decimal,
        depth: int,
        as_of_date: date,
        state: Dict,
        call_path: set[int],
    ) -> None:
        state["max_depth"] = max(state["max_depth"], depth)
        state["batch_nodes"].setdefault(
            batch.id,
            {
                "node_id": f"batch:{batch.id}",
                "batch_id": batch.id,
                "batch_number": batch.batch_number,
                "batch_type": batch.batch_type,
                "is_mixed": batch.batch_type == "MIXED",
            },
        )

        if batch.id in call_path:
            state["resolution_notes"].add(
                "Cycle detected in lineage graph; cycle node treated as unresolved terminal."
            )
            state["unresolved_batches"].add(batch.id)
            state["root_shares"][batch.id] = state["root_shares"].get(
                batch.id, Decimal("0")
            ) + incoming_share
            return

        if batch.batch_type != "MIXED":
            state["root_shares"][batch.id] = state["root_shares"].get(
                batch.id, Decimal("0")
            ) + incoming_share
            return

        resolution, mix_node, source_components = cls._resolve_components(
            batch=batch, as_of_date=as_of_date
        )
        state["resolution_notes"].add(resolution)

        if mix_node is not None:
            state["mix_nodes"].setdefault(mix_node["node_id"], mix_node)
            state["edges"].append(
                {
                    "from_node": f"batch:{batch.id}",
                    "to_node": mix_node["node_id"],
                    "edge_type": "resolved_by",
                }
            )

        if not source_components:
            state["unresolved_batches"].add(batch.id)
            state["root_shares"][batch.id] = state["root_shares"].get(
                batch.id, Decimal("0")
            ) + incoming_share
            return

        total_percentage = sum(
            (item["percentage"] for item in source_components), Decimal("0")
        )
        if total_percentage <= 0:
            state["unresolved_batches"].add(batch.id)
            state["root_shares"][batch.id] = state["root_shares"].get(
                batch.id, Decimal("0")
            ) + incoming_share
            return

        next_path = set(call_path)
        next_path.add(batch.id)

        for component in source_components:
            source_batch = component["source_batch"]
            source_share = (component["percentage"] / total_percentage) * incoming_share
            state["edges"].append(
                {
                    "from_node": mix_node["node_id"] if mix_node else f"batch:{batch.id}",
                    "to_node": f"batch:{source_batch.id}",
                    "edge_type": "component",
                    "percentage": str(component["percentage"].quantize(Decimal("0.01"))),
                    "population_count": component["population_count"],
                    "biomass_kg": str(component["biomass_kg"].quantize(Decimal("0.01"))),
                    "source_assignment_id": component.get("source_assignment_id"),
                    "is_transferred_in": component.get("is_transferred_in"),
                }
            )
            cls._walk_batch(
                batch=source_batch,
                incoming_share=source_share,
                depth=depth + 1,
                as_of_date=as_of_date,
                state=state,
                call_path=next_path,
            )

    @classmethod
    def _resolve_components(
        cls, *, batch: Batch, as_of_date: date
    ) -> Tuple[str, Dict | None, List[Dict]]:
        latest_mix_event = (
            BatchMixEvent.objects.filter(
                mixed_batch=batch,
                mixed_at__date__lte=as_of_date,
            )
            .prefetch_related("components__source_batch")
            .select_related("container", "workflow_action")
            .order_by("-mixed_at", "-id")
            .first()
        )

        if latest_mix_event:
            by_source_batch: Dict[int, Dict] = {}
            for component in latest_mix_event.components.all():
                aggregate = by_source_batch.setdefault(
                    component.source_batch_id,
                    {
                        "source_batch": component.source_batch,
                        "percentage": Decimal("0"),
                        "population_count": 0,
                        "biomass_kg": Decimal("0"),
                        "source_assignment_id": component.source_assignment_id,
                        "is_transferred_in": component.is_transferred_in,
                    },
                )
                aggregate["percentage"] += component.percentage
                aggregate["population_count"] += component.population_count
                aggregate["biomass_kg"] += component.biomass_kg

            return (
                "Resolved from latest BatchMixEvent.",
                {
                    "node_id": f"mix_event:{latest_mix_event.id}",
                    "event_id": latest_mix_event.id,
                    "mixed_batch_id": batch.id,
                    "container_id": latest_mix_event.container_id,
                    "workflow_action_id": latest_mix_event.workflow_action_id,
                    "mixed_at": latest_mix_event.mixed_at.isoformat(),
                    "resolution": "MIX_EVENT",
                },
                list(by_source_batch.values()),
            )

        compositions = list(
            BatchComposition.objects.filter(mixed_batch=batch).select_related("source_batch")
        )
        if not compositions:
            return (
                "No BatchMixEvent or BatchComposition available; lineage unresolved at this batch.",
                None,
                [],
            )

        fallback_components = [
            {
                "source_batch": comp.source_batch,
                "percentage": comp.percentage,
                "population_count": comp.population_count,
                "biomass_kg": comp.biomass_kg,
                "source_assignment_id": None,
                "is_transferred_in": None,
            }
            for comp in compositions
        ]
        return (
            "Resolved from BatchComposition fallback (no qualifying BatchMixEvent).",
            {
                "node_id": f"composition_fallback:{batch.id}",
                "event_id": None,
                "mixed_batch_id": batch.id,
                "container_id": None,
                "workflow_action_id": None,
                "mixed_at": None,
                "resolution": "BATCH_COMPOSITION_FALLBACK",
            },
            fallback_components,
        )
