"""Finance dimension models."""

from django.db import models

from apps.infrastructure.models.geography import Geography
from apps.users.models import Subsidiary


class DimCompany(models.Model):
    """Finance dimension for legal entities by geography and subsidiary."""

    company_id = models.BigAutoField(primary_key=True)
    geography = models.ForeignKey(
        Geography,
        on_delete=models.PROTECT,
        related_name="finance_companies",
    )
    subsidiary = models.CharField(max_length=3, choices=Subsidiary.choices)
    display_name = models.CharField(max_length=150)
    currency = models.CharField(max_length=3, blank=True, null=True)
    nav_company_code = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["geography", "subsidiary"],
                name="dim_company_geography_subsidiary_uniq",
            )
        ]
        ordering = ("geography__name", "subsidiary")
        verbose_name = "Finance Company"
        verbose_name_plural = "Finance Companies"

    def __str__(self) -> str:
        return self.display_name


class DimSite(models.Model):
    """Finance dimension for operational sites mapped to companies."""

    class SourceModel(models.TextChoices):
        STATION = "station", "Freshwater Station"
        AREA = "area", "Area"

    site_id = models.BigAutoField(primary_key=True)
    source_model = models.CharField(max_length=16, choices=SourceModel.choices)
    source_pk = models.PositiveIntegerField()
    company = models.ForeignKey(
        DimCompany,
        on_delete=models.PROTECT,
        related_name="sites",
    )
    site_name = models.CharField(max_length=150)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_model", "source_pk"],
                name="dim_site_source_model_pk_uniq",
            )
        ]
        ordering = ("site_name",)
        verbose_name = "Finance Site"
        verbose_name_plural = "Finance Sites"

    def __str__(self) -> str:
        return self.site_name
