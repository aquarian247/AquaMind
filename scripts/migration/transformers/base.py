"""Base transformer utilities used by replay pipelines."""

from __future__ import annotations

from scripts.migration.lib import transform_utils as utils


class BaseTransformer:
    utils = utils

    def normalize_timestamp(self, value):
        return utils.ensure_timezone(value)

    def kg_to_grams(self, value):
        return utils.kg_to_grams(value)
