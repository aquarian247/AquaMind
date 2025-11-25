"""Validation helpers for comparing FishTalk vs AquaMind datasets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ValidationResult:
    passed: bool
    details: str = ''


class BaseValidator:
    def validate(self) -> ValidationResult:
        return ValidationResult(True, 'No validation implemented yet')
