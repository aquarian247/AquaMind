#!/usr/bin/env python3
"""Pilot migrate FishTalk treatments for one stitched population component.

Source (FishTalk): dbo.Treatment keyed by ActionID.
  - Treatment.ActionID -> Action.PopulationID (+ OperationID -> Operations.StartTime)
  - Treatment.VaccineType -> VaccineTypes.VaccineTypeID (VaccineName)
  - Treatment.MedicamentID -> Medicaments.MedicamentID (MedicamentName)
  - Treatment.ReasonForTreatment -> TreatmentReasons.TreatmentReasonsID (DefaultText)

Target (AquaMind): apps.health.models.Treatment

Writes only to aquamind_db_migr_dev.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
os.environ.setdefault("SKIP_CELERY_SIGNALS", "1")

from scripts.migration.safety import configure_migration_environment, assert_default_db_is_migration_db

configure_migration_environment()

import django

django.setup()
assert_default_db_is_migration_db()

from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from scripts.migration.history import save_with_history

from apps.batch.models import Batch
from apps.batch.models.assignment import BatchContainerAssignment
from apps.health.models import Treatment, VaccinationType
from apps.migration_support.models import ExternalIdMap
from scripts.migration.extractors.base import BaseExtractor, ExtractionContext


User = get_user_model()

REPORT_DIR_DEFAULT = PROJECT_ROOT / "scripts" / "migration" / "output" / "population_stitching"


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None

    cleaned = value.strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def ensure_aware(dt: datetime) -> datetime:
    if timezone.is_aware(dt):
        return dt
    return timezone.make_aware(dt, timezone.utc)


def to_decimal(value: object, *, places: str) -> Decimal | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return Decimal(raw).quantize(Decimal(places))
    except Exception:
        return None


def get_external_map(source_model: str, source_identifier: str) -> ExternalIdMap | None:
    return ExternalIdMap.objects.filter(
        source_system="FishTalk", source_model=source_model, source_identifier=str(source_identifier)
    ).first()


@dataclass(frozen=True)
class ComponentMember:
    population_id: str
    start_time: datetime
    end_time: datetime | None


def load_members_from_report(report_dir: Path, *, component_id: int | None, component_key: str | None) -> list[ComponentMember]:
    import csv

    path = report_dir / "population_members.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing report file: {path}")

    members: list[ComponentMember] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if component_id is not None and row.get("component_id") != str(component_id):
                continue
            if component_key is not None and row.get("component_key") != component_key:
                continue
            start = parse_dt(row.get("start_time", ""))
            if start is None:
                continue
            end = parse_dt(row.get("end_time", ""))
            members.append(
                ComponentMember(
                    population_id=row.get("population_id", ""),
                    start_time=start,
                    end_time=end,
                )
            )

    members.sort(key=lambda m: m.start_time)
    return members


def resolve_component_key(report_dir: Path, *, component_id: int | None, component_key: str | None) -> str:
    if component_key:
        return component_key
    if component_id is None:
        raise ValueError("Provide --component-id or --component-key")

    import csv

    path = report_dir / "population_members.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("component_id") == str(component_id) and row.get("component_key"):
                return row["component_key"]

    raise ValueError("Unable to resolve component_key from report")


def infer_treatment_type(row: dict[str, str]) -> str:
    # FishTalk: VaccineType (int), MedicamentID (int), NonMedicalTreatmentMethod (int)
    if (row.get("VaccineType") or "").strip():
        return "vaccination"
    if (row.get("MedicamentID") or "").strip() or (row.get("AmountKg") or "").strip() or (row.get("AmountLitres") or "").strip():
        return "medication"
    if (row.get("NonMedicalTreatmentMethod") or "").strip():
        return "physical"
    return "other"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pilot migrate treatments for a stitched FishTalk component")
    parser.add_argument("--component-id", type=int, help="Component id from components.csv")
    parser.add_argument("--component-key", help="Stable component_key from components.csv")
    parser.add_argument("--report-dir", default=str(REPORT_DIR_DEFAULT), help="Directory containing population_members.csv")
    parser.add_argument("--sql-profile", default="fishtalk_readonly", help="FishTalk SQL Server profile")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report_dir = Path(args.report_dir)
    component_key = resolve_component_key(report_dir, component_id=args.component_id, component_key=args.component_key)
    members = load_members_from_report(report_dir, component_id=args.component_id, component_key=component_key)
    if not members:
        raise SystemExit("No members found for the selected component")

    batch_map = get_external_map("PopulationComponent", component_key)
    if not batch_map:
        raise SystemExit(
            f"Missing ExternalIdMap for PopulationComponent {component_key}. "
            "Run scripts/migration/tools/pilot_migrate_component.py first."
        )
    batch = Batch.objects.get(pk=batch_map.target_object_id)

    user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not user:
        raise SystemExit("No users exist in AquaMind DB; cannot create Treatment.user")

    population_ids = sorted({m.population_id for m in members if m.population_id})
    window_start = min(m.start_time for m in members)
    window_end = max((m.end_time or datetime.now()) for m in members)

    extractor = BaseExtractor(ExtractionContext(profile=args.sql_profile))
    in_clause = ",".join(f"'{pid}'" for pid in population_ids)
    start_str = window_start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = window_end.strftime("%Y-%m-%d %H:%M:%S")

    rows = extractor._run_sqlcmd(
        query=(
            "SELECT CONVERT(varchar(36), t.ActionID) AS ActionID, "
            "CONVERT(varchar(36), a.PopulationID) AS PopulationID, "
            "CONVERT(varchar(19), o.StartTime, 120) AS OperationStartTime, "
            "CONVERT(varchar(19), t.StartTime, 120) AS TreatmentStartTime, "
            "CONVERT(varchar(19), t.EndTime, 120) AS TreatmentEndTime, "
            "CONVERT(varchar(19), t.VaccinationDate, 120) AS VaccinationDate, "
            "CONVERT(varchar(32), t.TreatmentCount) AS TreatmentCount, "
            "CONVERT(varchar(64), t.AmountKg) AS AmountKg, "
            "CONVERT(varchar(64), t.AmountLitres) AS AmountLitres, "
            "CONVERT(varchar(32), t.ReasonForTreatment) AS ReasonForTreatment, "
            "ISNULL(tr.DefaultText, '') AS ReasonText, "
            "CONVERT(varchar(32), t.VaccineType) AS VaccineType, "
            "ISNULL(vt.VaccineName, '') AS VaccineName, "
            "CONVERT(varchar(32), t.MedicamentID) AS MedicamentID, "
            "ISNULL(med.MedicamentName, '') AS MedicamentName, "
            "CONVERT(varchar(32), t.TreatmentCategory) AS TreatmentCategory, "
            "CONVERT(varchar(32), t.TreatmentMethod) AS TreatmentMethod, "
            "CONVERT(varchar(32), t.NonMedicalTreatmentMethod) AS NonMedicalTreatmentMethod, "
            "ISNULL(t.Comment, '') AS Comment "
            "FROM dbo.Treatment t "
            "JOIN dbo.Action a ON a.ActionID = t.ActionID "
            "JOIN dbo.Operations o ON o.OperationID = a.OperationID "
            "LEFT JOIN dbo.TreatmentReasons tr ON tr.TreatmentReasonsID = t.ReasonForTreatment "
            "LEFT JOIN dbo.VaccineTypes vt ON vt.VaccineTypeID = t.VaccineType "
            "LEFT JOIN dbo.Medicaments med ON med.MedicamentID = t.MedicamentID "
            f"WHERE a.PopulationID IN ({in_clause}) "
            f"AND o.StartTime >= '{start_str}' AND o.StartTime <= '{end_str}' "
            "ORDER BY o.StartTime ASC"
        ),
        headers=[
            "ActionID",
            "PopulationID",
            "OperationStartTime",
            "TreatmentStartTime",
            "TreatmentEndTime",
            "VaccinationDate",
            "TreatmentCount",
            "AmountKg",
            "AmountLitres",
            "ReasonForTreatment",
            "ReasonText",
            "VaccineType",
            "VaccineName",
            "MedicamentID",
            "MedicamentName",
            "TreatmentCategory",
            "TreatmentMethod",
            "NonMedicalTreatmentMethod",
            "Comment",
        ],
    )

    if args.dry_run:
        print(f"[dry-run] Would migrate {len(rows)} FishTalk treatments into batch={batch.batch_number}")
        return 0

    assignment_by_pop: dict[str, BatchContainerAssignment] = {}
    for pid in population_ids:
        mapped = get_external_map("Populations", pid)
        if mapped:
            assignment_by_pop[pid] = BatchContainerAssignment.objects.get(pk=mapped.target_object_id)

    created = updated = skipped = 0

    with transaction.atomic():
        history_reason = f"FishTalk migration: treatments for component {component_key}"
        for row in rows:
            action_id = (row.get("ActionID") or "").strip()
            population_id = (row.get("PopulationID") or "").strip()
            if not action_id or not population_id:
                skipped += 1
                continue

            when = (
                parse_dt(row.get("TreatmentStartTime") or "")
                or parse_dt(row.get("VaccinationDate") or "")
                or parse_dt(row.get("OperationStartTime") or "")
            )
            if when is None:
                skipped += 1
                continue
            when = ensure_aware(when)

            end = parse_dt(row.get("TreatmentEndTime") or "")
            duration_days = 0
            if end is not None:
                end_aware = ensure_aware(end)
                duration_days = max(0, (end_aware.date() - when.date()).days)

            treatment_type = infer_treatment_type(row)
            vaccine_type_id = (row.get("VaccineType") or "").strip()
            vaccine_name = (row.get("VaccineName") or "").strip()
            medicament_id = (row.get("MedicamentID") or "").strip()
            medicament_name = (row.get("MedicamentName") or "").strip()

            vaccination_type = None
            if treatment_type == "vaccination":
                vt_label = vaccine_name or (f"VaccineTypeID={vaccine_type_id}" if vaccine_type_id else "FishTalk Vaccination")
                vaccination_type, _ = VaccinationType.objects.get_or_create(name=vt_label[:100])

            amount_kg = to_decimal(row.get("AmountKg"), places="0.001")
            amount_l = to_decimal(row.get("AmountLitres"), places="0.001")
            dosage_parts: list[str] = []
            if amount_kg is not None:
                dosage_parts.append(f"{amount_kg} kg")
            if amount_l is not None:
                dosage_parts.append(f"{amount_l} L")
            dosage = ", ".join(dosage_parts)[:100]

            reason_id = (row.get("ReasonForTreatment") or "").strip()
            reason_text = (row.get("ReasonText") or "").strip()
            comment = (row.get("Comment") or "").strip()
            count_raw = (row.get("TreatmentCount") or "").strip()

            desc_parts: list[str] = ["FishTalk treatment"]
            if treatment_type == "vaccination":
                desc_parts.append("vaccination")
                if vaccine_name:
                    desc_parts.append(vaccine_name)
                if vaccine_type_id:
                    desc_parts.append(f"VaccineTypeID={vaccine_type_id}")
            elif treatment_type == "medication":
                desc_parts.append("medication")
                if medicament_name:
                    desc_parts.append(medicament_name)
                if medicament_id:
                    desc_parts.append(f"MedicamentID={medicament_id}")
            elif treatment_type == "physical":
                desc_parts.append("physical")
                nm = (row.get("NonMedicalTreatmentMethod") or "").strip()
                if nm:
                    desc_parts.append(f"NonMedicalTreatmentMethod={nm}")
            else:
                desc_parts.append(treatment_type)

            if count_raw:
                desc_parts.append(f"treated_count={count_raw}")
            if dosage:
                desc_parts.append(f"dose={dosage}")
            if reason_text:
                desc_parts.append(f"reason={reason_text}")
            if reason_id and not reason_text:
                desc_parts.append(f"ReasonForTreatment={reason_id}")
            if comment:
                desc_parts.append(comment)

            assignment = assignment_by_pop.get(population_id)
            container = assignment.container if assignment else None

            defaults = {
                "batch": batch,
                "container": container,
                "batch_assignment": assignment,
                "user": user,
                "treatment_date": when,
                "treatment_type": treatment_type,
                "vaccination_type": vaccination_type,
                "description": "; ".join(desc_parts)[:2000],
                "dosage": dosage,
                "duration_days": duration_days,
                "withholding_period_days": 0,
                "outcome": "pending",
                "includes_weighing": False,
            }

            mapped = get_external_map("Treatment", action_id)
            if mapped:
                obj = Treatment.objects.get(pk=mapped.target_object_id)
                for k, v in defaults.items():
                    setattr(obj, k, v)
                save_with_history(obj, user=user, reason=history_reason)
                updated += 1
            else:
                obj = Treatment(**defaults)
                save_with_history(obj, user=user, reason=history_reason)
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="Treatment",
                    source_identifier=str(action_id),
                    defaults={
                        "target_app_label": obj._meta.app_label,
                        "target_model": obj._meta.model_name,
                        "target_object_id": obj.pk,
                        "metadata": {
                            "population_id": population_id,
                            "treatment_type": treatment_type,
                            "vaccine_type_id": vaccine_type_id,
                            "medicament_id": medicament_id,
                        },
                    },
                )
                created += 1

    print(
        f"Migrated treatments for component_key={component_key} into batch={batch.batch_number} "
        f"(created={created}, updated={updated}, skipped={skipped}, rows={len(rows)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
