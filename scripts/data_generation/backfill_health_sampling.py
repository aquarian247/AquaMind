#!/usr/bin/env python3
"""
Backfill health sampling events for existing generated data.

All events are created on BatchContainerAssignment records.

Modes:
- assignment (default): ensure a target total per assignment
- batch-stage: ensure a target total per (batch, lifecycle stage), then
  place each planned event on a matching assignment in that stage
"""

import argparse
import os
import random
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import django
import numpy as np

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
django.setup()

from django.contrib.auth import get_user_model

from apps.batch.models import Batch, BatchContainerAssignment, LifeCycleStage
from apps.health.models import (
    FishParameterScore,
    HealthParameter,
    HealthSamplingEvent,
    IndividualFishObservation,
)


def compute_candidate_dates(
    start_date: date,
    end_date: date,
    existing_dates: set[date],
    target_total: int,
) -> list[date]:
    """Return missing sampling dates to reach target_total events."""
    missing = max(target_total - len(existing_dates), 0)
    if missing <= 0:
        return []

    span_days = max((end_date - start_date).days, 0)
    candidates: list[date] = []

    if target_total <= 1:
        proposed_offsets = [0]
    else:
        proposed_offsets = [
            round(i * span_days / (target_total - 1))
            for i in range(target_total)
        ]

    for offset in proposed_offsets:
        d = start_date + timedelta(days=max(min(offset, span_days), 0))
        if d not in existing_dates and d not in candidates:
            candidates.append(d)

    if len(candidates) < missing:
        scan_day = start_date
        while scan_day <= end_date and len(candidates) < missing:
            if scan_day not in existing_dates and scan_day not in candidates:
                candidates.append(scan_day)
            scan_day += timedelta(days=1)

    return candidates[:missing]


def score_for_parameter(parameter: HealthParameter, rng: random.Random) -> int:
    """Generate a realistic score with healthy bias."""
    min_score = int(parameter.min_score)
    max_score = int(parameter.max_score)
    values = list(range(min_score, max_score + 1))

    if values == [0, 1, 2, 3]:
        return rng.choices([0, 1, 2, 3], weights=[60, 30, 8, 2], k=1)[0]

    weights = list(reversed(range(1, len(values) + 1)))
    return rng.choices(values, weights=weights, k=1)[0]


def create_sampling_event(
    assignment: BatchContainerAssignment,
    sampling_date: date,
    sample_size: int,
    health_params: list[HealthParameter],
    sampled_by,
    rng: random.Random,
) -> tuple[int, int]:
    """
    Create one HealthSamplingEvent with observations and scores.

    Returns:
        Tuple (fish_observation_count, parameter_score_count)
    """
    avg_weight = float(assignment.avg_weight_g or 50.0)
    avg_weight = max(avg_weight, 5.0)
    avg_length = ((avg_weight * 1000.0) ** (1 / 3)) * 1.5

    event = HealthSamplingEvent.objects.create(
        assignment=assignment,
        sampling_date=sampling_date,
        number_of_fish_sampled=sample_size,
        sampled_by=sampled_by,
        notes=f"Backfilled health assessment - {assignment.lifecycle_stage.name}",
    )

    all_weights: list[float] = []
    all_lengths: list[float] = []
    fish_rows = []

    for fish_num in range(1, sample_size + 1):
        fish_weight = rng.gauss(avg_weight, avg_weight * 0.15)
        fish_weight = max(avg_weight * 0.5, min(avg_weight * 1.5, fish_weight))

        fish_length = rng.gauss(avg_length, avg_length * 0.10)
        fish_length = max(avg_length * 0.7, min(avg_length * 1.3, fish_length))

        all_weights.append(fish_weight)
        all_lengths.append(fish_length)

        fish_rows.append(
            IndividualFishObservation(
                sampling_event=event,
                fish_identifier=f"F{fish_num:03d}",
                weight_g=Decimal(str(round(fish_weight, 2))),
                length_cm=Decimal(str(round(fish_length, 2))),
            )
        )

    created_fish = IndividualFishObservation.objects.bulk_create(fish_rows, batch_size=200)

    score_rows = []
    for fish_obs in created_fish:
        for param in health_params:
            score_rows.append(
                FishParameterScore(
                    individual_fish_observation=fish_obs,
                    parameter=param,
                    score=score_for_parameter(param, rng),
                )
            )

    FishParameterScore.objects.bulk_create(score_rows, batch_size=500)

    event.avg_weight_g = Decimal(str(round(sum(all_weights) / len(all_weights), 2)))
    event.avg_length_cm = Decimal(str(round(sum(all_lengths) / len(all_lengths), 2)))
    event.std_dev_weight_g = Decimal(str(round(np.std(all_weights), 2)))
    event.std_dev_length_cm = Decimal(str(round(np.std(all_lengths), 2)))
    event.min_weight_g = Decimal(str(round(min(all_weights), 2)))
    event.max_weight_g = Decimal(str(round(max(all_weights), 2)))
    event.min_length_cm = Decimal(str(round(min(all_lengths), 2)))
    event.max_length_cm = Decimal(str(round(max(all_lengths), 2)))
    event.calculated_sample_size = sample_size

    k_factors = [
        100.0 * (w / (l**3)) for w, l in zip(all_weights, all_lengths) if l > 0
    ]
    if k_factors:
        event.avg_k_factor = Decimal(str(round(sum(k_factors) / len(k_factors), 4)))
    event.save()

    return len(created_fish), len(score_rows)


def _run_assignment_mode(
    args: argparse.Namespace,
    health_params: list[HealthParameter],
    sampled_by,
    rng: random.Random,
) -> tuple[int, int, int, int, int]:
    """
    Backfill events by assignment.

    Returns:
        Tuple:
            (assignments_inspected, events_planned, events_created, fish_created, scores_created)
    """
    assignments = BatchContainerAssignment.objects.select_related(
        "batch",
        "lifecycle_stage",
        "container",
    ).filter(
        lifecycle_stage__order__gte=args.stage_min_order
    ).order_by("batch_id", "assignment_date", "id")

    if args.batch_id:
        assignments = assignments.filter(batch_id=args.batch_id)

    total_assignments = assignments.count()
    print(
        f"Assignments in scope: {total_assignments} "
        f"(stage_order >= {args.stage_min_order}, batch_id={args.batch_id or 'ALL'})"
    )

    today = date.today()
    planned_events = 0
    created_events = 0
    created_fish = 0
    created_scores = 0

    for idx, assignment in enumerate(assignments, start=1):
        start_date = assignment.assignment_date
        end_date = assignment.departure_date or assignment.batch.actual_end_date or today
        if end_date < start_date:
            end_date = start_date

        existing_dates = set(
            assignment.health_sampling_events.values_list("sampling_date", flat=True)
        )
        new_dates = compute_candidate_dates(
            start_date=start_date,
            end_date=end_date,
            existing_dates=existing_dates,
            target_total=args.target_events_per_assignment,
        )

        planned_events += len(new_dates)
        if not new_dates or args.dry_run:
            continue

        for sampling_date in new_dates:
            fish_count, score_count = create_sampling_event(
                assignment=assignment,
                sampling_date=sampling_date,
                sample_size=args.sample_size,
                health_params=health_params,
                sampled_by=sampled_by,
                rng=rng,
            )
            created_events += 1
            created_fish += fish_count
            created_scores += score_count

        if idx % 25 == 0:
            print(
                f"Processed {idx}/{total_assignments} assignments | "
                f"events created so far: {created_events}"
            )

    return total_assignments, planned_events, created_events, created_fish, created_scores


def _assignment_end_date(assignment: BatchContainerAssignment, batch: Batch, today: date) -> date:
    return assignment.departure_date or batch.actual_end_date or today


def _run_batch_stage_mode(
    args: argparse.Namespace,
    health_params: list[HealthParameter],
    sampled_by,
    rng: random.Random,
) -> tuple[int, int, int, int, int]:
    """
    Target coverage by (batch, lifecycle stage), while creating events on assignments.

    Returns:
        Tuple:
            (batch_stage_pairs_inspected, events_planned, events_created, fish_created, scores_created)
    """
    today = date.today()

    batches = Batch.objects.order_by("id")
    if args.batch_id:
        batches = batches.filter(id=args.batch_id)
    batches = list(batches)

    stages = list(
        LifeCycleStage.objects.filter(order__gte=args.stage_min_order).order_by("order", "id")
    )

    print(
        f"Batches in scope: {len(batches)} "
        f"(batch_id={args.batch_id or 'ALL'}, stage_order >= {args.stage_min_order})"
    )

    inspected_pairs = 0
    planned_events = 0
    created_events = 0
    created_fish = 0
    created_scores = 0

    for batch_idx, batch in enumerate(batches, start=1):
        for stage in stages:
            stage_assignments = list(
                BatchContainerAssignment.objects.filter(
                    batch=batch,
                    lifecycle_stage=stage,
                ).order_by("assignment_date", "id")
            )
            if not stage_assignments:
                continue

            inspected_pairs += 1
            stage_start = min(a.assignment_date for a in stage_assignments)
            stage_end = max(_assignment_end_date(a, batch, today) for a in stage_assignments)
            if stage_end < stage_start:
                stage_end = stage_start

            existing_dates = set(
                HealthSamplingEvent.objects.filter(
                    assignment__batch=batch,
                    assignment__lifecycle_stage=stage,
                ).values_list("sampling_date", flat=True)
            )

            target_total = rng.randint(
                args.target_events_per_stage_min,
                args.target_events_per_stage_max,
            )
            new_dates = compute_candidate_dates(
                start_date=stage_start,
                end_date=stage_end,
                existing_dates=existing_dates,
                target_total=target_total,
            )
            planned_events += len(new_dates)

            if not new_dates or args.dry_run:
                continue

            for sampling_date in new_dates:
                matching_assignments = [
                    a
                    for a in stage_assignments
                    if a.assignment_date <= sampling_date <= _assignment_end_date(a, batch, today)
                ]
                assignment = matching_assignments[0] if matching_assignments else stage_assignments[0]

                fish_count, score_count = create_sampling_event(
                    assignment=assignment,
                    sampling_date=sampling_date,
                    sample_size=args.sample_size,
                    health_params=health_params,
                    sampled_by=sampled_by,
                    rng=rng,
                )
                created_events += 1
                created_fish += fish_count
                created_scores += score_count

        if batch_idx % 10 == 0:
            print(
                f"Processed {batch_idx}/{len(batches)} batches | "
                f"events created so far: {created_events}"
            )

    return inspected_pairs, planned_events, created_events, created_fish, created_scores


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill health sampling events.")
    parser.add_argument("--batch-id", type=int, default=None, help="Optional batch ID scope.")
    parser.add_argument(
        "--mode",
        choices=["assignment", "batch-stage"],
        default="assignment",
        help=(
            "Backfill mode. "
            "'assignment' targets events per assignment, "
            "'batch-stage' targets coverage per lifecycle stage per batch "
            "while still creating events on assignments."
        ),
    )
    parser.add_argument(
        "--target-events-per-assignment",
        type=int,
        default=5,
        help="Desired total events per assignment after backfill.",
    )
    parser.add_argument(
        "--stage-min-order",
        type=int,
        default=2,
        help="Minimum lifecycle stage order to include. Default 2 skips Egg&Alevin.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=75,
        help="Number of fish per health sampling event.",
    )
    parser.add_argument(
        "--target-events-per-stage-min",
        type=int,
        default=2,
        help="Minimum total events per stage per batch in batch-stage mode.",
    )
    parser.add_argument(
        "--target-events-per-stage-max",
        type=int,
        default=3,
        help="Maximum total events per stage per batch in batch-stage mode.",
    )
    parser.add_argument("--seed", type=int, default=20260218, help="Random seed.")
    parser.add_argument("--dry-run", action="store_true", help="Plan only; write nothing.")
    args = parser.parse_args()

    if args.mode == "assignment" and args.target_events_per_assignment < 1:
        print("target-events-per-assignment must be >= 1")
        return 2

    if args.mode == "batch-stage":
        if args.target_events_per_stage_min < 1:
            print("target-events-per-stage-min must be >= 1")
            return 2
        if args.target_events_per_stage_max < args.target_events_per_stage_min:
            print("target-events-per-stage-max must be >= target-events-per-stage-min")
            return 2

    if args.sample_size < 1:
        print("sample-size must be >= 1")
        return 2

    User = get_user_model()
    sampled_by = User.objects.filter(is_active=True).order_by("id").first()
    if sampled_by is None:
        print("No active user found; cannot set sampled_by.")
        return 1

    health_params = list(HealthParameter.objects.filter(is_active=True).order_by("id"))
    if not health_params:
        print("No active health parameters found. Run 01_initialize_health_parameters.py first.")
        return 1

    rng = random.Random(args.seed)

    if args.mode == "assignment":
        inspected, planned_events, created_events, created_fish, created_scores = _run_assignment_mode(
            args=args,
            health_params=health_params,
            sampled_by=sampled_by,
            rng=rng,
        )
        inspected_label = "Assignments inspected"
    else:
        inspected, planned_events, created_events, created_fish, created_scores = _run_batch_stage_mode(
            args=args,
            health_params=health_params,
            sampled_by=sampled_by,
            rng=rng,
        )
        inspected_label = "Batch-stage pairs inspected"

    print("\nBackfill summary")
    print("-" * 40)
    print(f"Mode: {args.mode}")
    print(f"Dry run: {args.dry_run}")
    print(f"{inspected_label}: {inspected}")
    print(f"Events planned: {planned_events}")
    print(f"Events created: {created_events}")
    print(f"Fish observations created: {created_fish}")
    print(f"Parameter scores created: {created_scores}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
