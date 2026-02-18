#!/usr/bin/env python3
"""Migration profile presets for cohort-shape specific behavior.

Profiles keep migration behavior centralized while allowing explicit, auditable
overrides for known cohort families (station/era/process variants).
"""

from __future__ import annotations

from dataclasses import dataclass


STAGE_SELECTION_FRONTIER = "frontier"
STAGE_SELECTION_LATEST_MEMBER = "latest_member"
STAGE_SELECTION_MODES = {
    STAGE_SELECTION_FRONTIER,
    STAGE_SELECTION_LATEST_MEMBER,
}


@dataclass(frozen=True)
class MigrationProfile:
    """Preset knobs for migration-time behavior only."""

    name: str
    description: str
    lifecycle_frontier_window_hours: int = 24
    same_stage_supersede_max_hours: int = 24
    stage_selection_mode: str = STAGE_SELECTION_FRONTIER
    enforce_latest_container_holder_consistency: bool = True
    suppress_orphan_zero_assignments: bool = True

    def validate(self) -> None:
        if self.lifecycle_frontier_window_hours < 1:
            raise ValueError(
                f"{self.name}: lifecycle_frontier_window_hours must be >= 1 "
                f"(got {self.lifecycle_frontier_window_hours})"
            )
        if self.same_stage_supersede_max_hours < 1:
            raise ValueError(
                f"{self.name}: same_stage_supersede_max_hours must be >= 1 "
                f"(got {self.same_stage_supersede_max_hours})"
            )
        if self.stage_selection_mode not in STAGE_SELECTION_MODES:
            raise ValueError(
                f"{self.name}: invalid "
                f"stage_selection_mode={self.stage_selection_mode!r}; "
                f"expected one of {sorted(STAGE_SELECTION_MODES)}"
            )


MIGRATION_PROFILES: dict[str, MigrationProfile] = {
    # Baseline profile (current hardened default for FW cohorts).
    "fw_default": MigrationProfile(
        name="fw_default",
        description=(
            "Default hardened FW profile: frontier stage selection, "
            "latest-holder consistency, orphan-zero suppression."
        ),
    ),
    # Useful for diagnostics/backtesting when container ownership boundaries
    # are uncertain and you need to compare against pre-hardening behavior.
    "fw_relaxed_holder": MigrationProfile(
        name="fw_relaxed_holder",
        description=(
            "Frontier stage selection but without latest-holder consistency "
            "or orphan-zero suppression (diagnostics/backtesting)."
        ),
        enforce_latest_container_holder_consistency=False,
        suppress_orphan_zero_assignments=False,
    ),
    # Legacy behavior anchor for troubleshooting historical runs.
    "legacy_latest_member": MigrationProfile(
        name="legacy_latest_member",
        description=(
            "Legacy-biased profile: latest-member stage selection and relaxed "
            "active-holder checks."
        ),
        stage_selection_mode=STAGE_SELECTION_LATEST_MEMBER,
        enforce_latest_container_holder_consistency=False,
        suppress_orphan_zero_assignments=False,
    ),
}


for _name, _profile in MIGRATION_PROFILES.items():
    _profile.validate()

MIGRATION_PROFILE_NAMES = tuple(sorted(MIGRATION_PROFILES))


def get_migration_profile(profile_name: str) -> MigrationProfile:
    """Resolve a migration profile by name."""
    name = (profile_name or "").strip()
    profile = MIGRATION_PROFILES.get(name)
    if profile is None:
        known = ", ".join(MIGRATION_PROFILE_NAMES)
        raise ValueError(
            f"Unknown migration profile: {profile_name!r}. "
            f"Known profiles: {known}"
        )
    return profile
