"""Helpers for setting django-simple-history metadata in migration scripts."""

from __future__ import annotations

from typing import Any

from simple_history.utils import update_change_reason


def save_with_history(
    instance: Any, *, user: Any | None, reason: str | None
) -> None:
    if user is not None:
        instance._history_user = user
    instance.save()
    if reason and hasattr(instance, "history"):
        update_change_reason(instance, reason)


def get_or_create_with_history(
    model: Any,
    *,
    lookup: dict,
    defaults: dict,
    user: Any | None,
    reason: str | None,
    using: str | None = None,
):
    from django.db import IntegrityError, transaction
    
    qs = model.objects.using(using) if using else model.objects
    
    # First try to get existing
    obj = qs.filter(**lookup).first()
    if obj:
        return obj, False
    
    # Try to create - use transaction to handle race conditions
    payload = {**lookup, **defaults}
    obj = model(**payload)
    if user is not None:
        obj._history_user = user
    
    try:
        with transaction.atomic(using=using):
            obj.save(using=using)
    except IntegrityError:
        # Another worker created it first - fetch the existing one
        obj = qs.filter(**lookup).first()
        if obj:
            return obj, False
        # If still not found, re-raise
        raise
    
    # Update change reason - handle multi-database scenario
    if reason and hasattr(obj, "history"):
        try:
            history_qs = obj.history.using(using) if using else obj.history
            record = history_qs.first()
            if record:
                record.history_change_reason = reason
                record.save(using=using)
        except Exception:
            pass  # Silently ignore if history update fails
    return obj, True
