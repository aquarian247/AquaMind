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
):
    obj = model.objects.filter(**lookup).first()
    if obj:
        return obj, False
    payload = {**lookup, **defaults}
    obj = model(**payload)
    if user is not None:
        obj._history_user = user
    obj.save()
    if reason and hasattr(obj, "history"):
        update_change_reason(obj, reason)
    return obj, True
