"""Pagination utilities for finance APIs."""

from aquamind.utils.pagination import ValidatedPageNumberPagination


class FinancePagination(ValidatedPageNumberPagination):
    """Pagination tuned for finance endpoints."""

    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500
