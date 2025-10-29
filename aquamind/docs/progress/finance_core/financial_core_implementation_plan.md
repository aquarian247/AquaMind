# Financial Core Implementation Plan

**AquaMind Financial Planning & Budgeting Module**

**Version**: 1.0  
**Date**: October 28, 2025  
**Status**: Production-Ready Architecture

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Implementation Overview](#implementation-overview)
3. [Phase 1: Foundation (Weeks 1-3)](#phase-1-foundation)
4. [Phase 2: Core Features (Weeks 4-6)](#phase-2-core-features)
5. [Phase 3: Integration & Reporting (Weeks 7-9)](#phase-3-integration--reporting)
6. [Phase 4: Testing & Deployment (Weeks 10-12)](#phase-4-testing--deployment)
7. [Acceptance Criteria](#acceptance-criteria)
8. [Risk Mitigation](#risk-mitigation)

---

## Executive Summary

This implementation plan provides a complete, production-ready roadmap for building the **Financial Core** module in AquaMind. The module addresses the critical gap identified in the FishTalk feature analysis: the lack of a Chart of Accounts (CoA), Cost Center tracking, and Budgeting functionality.

### Key Objectives

1. **Enable Financial Planning**: Provide farming managers and finance teams with tools to create annual budgets, track cost centers, and project financial performance.
2. **Maintain Architectural Integrity**: Ensure clear separation from the existing `finance` app (operational reporting) while enabling powerful integration for Budget vs. Actuals analysis.
3. **Support Scenario-Based Budgeting**: Integrate with the `scenario` app to enable "what-if" financial projections.
4. **Deliver Production-Quality Code**: No temporary implementations—every component is designed for the final architecture.

### Implementation Timeline

- **Total Duration**: 12 weeks
- **Backend Development**: 8 weeks
- **Integration & Testing**: 4 weeks
- **Deployment**: Week 12

### Resource Requirements

- **Backend Developer**: 1 FTE (full-time equivalent) for 12 weeks
- **Database Administrator**: 0.25 FTE for schema design and migration support
- **QA Engineer**: 0.5 FTE for testing (Weeks 8-12)

---

## Implementation Overview

### Architectural Principles

1. **Separation of Concerns**:
   - `finance` app = Operational financial reporting (harvest facts, intercompany transactions, NAV export)
   - `finance_core` app = Financial planning and budgeting (CoA, cost centers, budgets)

2. **Integration Over Duplication**:
   - `finance_core` uses `DimCompany` from `finance` for company-level aggregation
   - Budget vs. Actuals reports integrate `finance_core` budgets with `finance` actuals

3. **Django Best Practices**:
   - Follow AquaMind's code organization guidelines (`apps/`, `api/`, `models.py`, `serializers/`, `viewsets/`)
   - Use DRF for REST API
   - Leverage TimescaleDB for time-series budget data

4. **API-First Design**:
   - All functionality exposed via REST API
   - Frontend consumes API exclusively (no direct database access)

### Technology Stack

- **Backend Framework**: Django 4.2+ with Django REST Framework
- **Database**: PostgreSQL 14+ with TimescaleDB extension
- **API Documentation**: drf-spectacular (OpenAPI 3.0)
- **Testing**: pytest with pytest-django
- **Migrations**: Django migrations with custom SQL for TimescaleDB

---

## Phase 1: Foundation (Weeks 1-3)

### Objective

Establish the foundational data model, app structure, and core models for the Financial Core module.

### Tasks

#### Week 1: App Scaffolding and Data Model Design

**Task 1.1: Create `finance_core` Django App**

```bash
# In aquamind/apps/
django-admin startapp finance_core
```

**Directory Structure**:
```
aquamind/apps/finance_core/
├── __init__.py
├── models.py
├── admin.py
├── apps.py
├── api/
│   ├── __init__.py
│   ├── serializers/
│   │   ├── __init__.py
│   │   ├── account_serializer.py
│   │   ├── cost_center_serializer.py
│   │   ├── budget_serializer.py
│   │   └── budget_entry_serializer.py
│   ├── viewsets/
│   │   ├── __init__.py
│   │   ├── account_viewset.py
│   │   ├── cost_center_viewset.py
│   │   ├── budget_viewset.py
│   │   └── budget_entry_viewset.py
│   └── routers/
│       ├── __init__.py
│       └── finance_core_router.py
├── migrations/
│   └── __init__.py
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_serializers.py
    └── test_viewsets.py
```

**Acceptance Criteria**:
- ✅ `finance_core` app created and registered in `INSTALLED_APPS`
- ✅ Directory structure matches AquaMind conventions
- ✅ Empty test files created

---

**Task 1.2: Implement Core Models**

**File**: `aquamind/apps/finance_core/models.py`

```python
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from aquamind.apps.finance.models import DimCompany  # Integration point


class AccountType(models.TextChoices):
    """Chart of Accounts account types following standard accounting principles."""
    ASSET = 'ASSET', 'Asset'
    LIABILITY = 'LIABILITY', 'Liability'
    EQUITY = 'EQUITY', 'Equity'
    REVENUE = 'REVENUE', 'Revenue'
    EXPENSE = 'EXPENSE', 'Expense'


class AccountGroup(models.Model):
    """
    Hierarchical grouping for Chart of Accounts.
    Enables multi-level rollups (e.g., Operating Expenses > Feed Costs > Smolt Feed).
    """
    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Unique group code (e.g., 'OPEX', 'FEED')"
    )
    name = models.CharField(
        max_length=200,
        help_text="Human-readable group name (e.g., 'Operating Expenses')"
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        help_text="Parent group for hierarchical rollups"
    )
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        help_text="Account type for all accounts in this group"
    )
    display_order = models.IntegerField(
        default=0,
        help_text="Sort order for UI display"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'finance_core_account_group'
        ordering = ['display_order', 'code']
        verbose_name = 'Account Group'
        verbose_name_plural = 'Account Groups'
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def clean(self):
        """Validate that parent group has the same account type."""
        if self.parent and self.parent.account_type != self.account_type:
            raise ValidationError(
                f"Parent group '{self.parent.code}' has type '{self.parent.account_type}', "
                f"but this group has type '{self.account_type}'. They must match."
            )
    
    def get_full_path(self):
        """Return the full hierarchical path (e.g., 'OPEX > FEED > SMOLT_FEED')."""
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.code}"
        return self.code


class Account(models.Model):
    """
    Chart of Accounts (CoA) for financial planning and budgeting.
    Separate from operational finance app (harvest facts, intercompany transactions).
    """
    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Unique account code (e.g., '5100', 'FEED-SMOLT')"
    )
    name = models.CharField(
        max_length=200,
        help_text="Human-readable account name (e.g., 'Smolt Feed Costs')"
    )
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        db_index=True,
        help_text="Account type for financial statement classification"
    )
    group = models.ForeignKey(
        AccountGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accounts',
        help_text="Optional grouping for rollup reporting"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of account purpose and usage"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Inactive accounts are hidden from budget entry but retain historical data"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'finance_core_account'
        ordering = ['code']
        verbose_name = 'Account'
        verbose_name_plural = 'Chart of Accounts'
        indexes = [
            models.Index(fields=['account_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def clean(self):
        """Validate that account type matches group type if group is set."""
        if self.group and self.group.account_type != self.account_type:
            raise ValidationError(
                f"Account type '{self.account_type}' does not match "
                f"group type '{self.group.account_type}' for group '{self.group.code}'."
            )


class CostCenter(models.Model):
    """
    Cost Center for allocating costs across operational dimensions.
    Examples: Farm locations, lifecycle stages, projects.
    """
    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Unique cost center code (e.g., 'FARM-01', 'HATCHERY')"
    )
    name = models.CharField(
        max_length=200,
        help_text="Human-readable cost center name (e.g., 'Faroe Islands - Farm 1')"
    )
    company = models.ForeignKey(
        DimCompany,
        on_delete=models.CASCADE,
        related_name='cost_centers',
        help_text="Company owning this cost center (integration with finance app)"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of cost center scope and purpose"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Inactive cost centers are hidden from budget entry but retain historical data"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'finance_core_cost_center'
        ordering = ['code']
        verbose_name = 'Cost Center'
        verbose_name_plural = 'Cost Centers'
        indexes = [
            models.Index(fields=['company', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class Budget(models.Model):
    """
    Annual budget header linking to a scenario (optional).
    Enables scenario-based budgeting for "what-if" analysis.
    """
    name = models.CharField(
        max_length=200,
        help_text="Budget name (e.g., '2025 Base Budget', '2025 Expansion Scenario')"
    )
    year = models.IntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(2100)],
        db_index=True,
        help_text="Fiscal year for this budget"
    )
    scenario = models.ForeignKey(
        'scenario.Scenario',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='budgets',
        help_text="Optional link to scenario for scenario-based budgeting"
    )
    company = models.ForeignKey(
        DimCompany,
        on_delete=models.CASCADE,
        related_name='budgets',
        help_text="Company owning this budget"
    )
    description = models.TextField(
        blank=True,
        help_text="Budget assumptions, methodology, and notes"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Only one budget per company/year can be active (used for reporting)"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_budgets'
    )
    
    class Meta:
        db_table = 'finance_core_budget'
        ordering = ['-year', 'name']
        verbose_name = 'Budget'
        verbose_name_plural = 'Budgets'
        unique_together = [('company', 'year', 'name')]
        indexes = [
            models.Index(fields=['company', 'year', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.year})"
    
    def clean(self):
        """Ensure only one active budget per company/year."""
        if self.is_active:
            existing_active = Budget.objects.filter(
                company=self.company,
                year=self.year,
                is_active=True
            ).exclude(pk=self.pk)
            
            if existing_active.exists():
                raise ValidationError(
                    f"An active budget already exists for {self.company.name} in {self.year}. "
                    f"Please deactivate it before activating this budget."
                )


class BudgetEntry(models.Model):
    """
    Monthly budget entry for a specific account and cost center.
    Granular data for budget vs. actuals reporting.
    """
    budget = models.ForeignKey(
        Budget,
        on_delete=models.CASCADE,
        related_name='entries',
        help_text="Parent budget header"
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='budget_entries',
        help_text="Chart of Accounts account"
    )
    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.PROTECT,
        related_name='budget_entries',
        help_text="Cost center for allocation"
    )
    month = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        db_index=True,
        help_text="Month (1-12)"
    )
    budgeted_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Budgeted amount for this month (in company currency)"
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional notes or assumptions for this entry"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'finance_core_budget_entry'
        ordering = ['budget', 'month', 'account__code']
        verbose_name = 'Budget Entry'
        verbose_name_plural = 'Budget Entries'
        unique_together = [('budget', 'account', 'cost_center', 'month')]
        indexes = [
            models.Index(fields=['budget', 'month']),
            models.Index(fields=['account', 'cost_center']),
        ]
    
    def __str__(self):
        return f"{self.budget.name} - {self.account.code} - Month {self.month}"
    
    def clean(self):
        """Validate that account and cost center belong to the same company as the budget."""
        if self.cost_center.company != self.budget.company:
            raise ValidationError(
                f"Cost center '{self.cost_center.code}' belongs to {self.cost_center.company.name}, "
                f"but budget '{self.budget.name}' belongs to {self.budget.company.name}."
            )
```

**Acceptance Criteria**:
- ✅ All 5 models implemented (`AccountGroup`, `Account`, `CostCenter`, `Budget`, `BudgetEntry`)
- ✅ Foreign key relationships correctly defined
- ✅ Validation logic implemented in `clean()` methods
- ✅ Database table names follow AquaMind conventions (`finance_core_*`)
- ✅ Indexes created for common query patterns

---

**Task 1.3: Create Initial Migrations**

```bash
python manage.py makemigrations finance_core
python manage.py migrate finance_core
```

**Acceptance Criteria**:
- ✅ Migration files created without errors
- ✅ Database tables created successfully
- ✅ Foreign key constraints verified

---

#### Week 2: Admin Interface and Basic CRUD

**Task 2.1: Implement Django Admin Interface**

**File**: `aquamind/apps/finance_core/admin.py`

```python
from django.contrib import admin
from django.utils.html import format_html
from .models import AccountGroup, Account, CostCenter, Budget, BudgetEntry


@admin.register(AccountGroup)
class AccountGroupAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'account_type', 'parent', 'display_order']
    list_filter = ['account_type']
    search_fields = ['code', 'name']
    ordering = ['display_order', 'code']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'account_type')
        }),
        ('Hierarchy', {
            'fields': ('parent', 'display_order')
        }),
    )


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'account_type', 'group', 'is_active_badge']
    list_filter = ['account_type', 'is_active', 'group']
    search_fields = ['code', 'name', 'description']
    ordering = ['code']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'account_type')
        }),
        ('Classification', {
            'fields': ('group', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">●</span> Active')
        return format_html('<span style="color: red;">●</span> Inactive')
    is_active_badge.short_description = 'Status'


@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'company', 'is_active_badge']
    list_filter = ['company', 'is_active']
    search_fields = ['code', 'name', 'description']
    ordering = ['code']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'company')
        }),
        ('Details', {
            'fields': ('description',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">●</span> Active')
        return format_html('<span style="color: red;">●</span> Inactive')
    is_active_badge.short_description = 'Status'


class BudgetEntryInline(admin.TabularInline):
    model = BudgetEntry
    extra = 0
    fields = ['account', 'cost_center', 'month', 'budgeted_amount', 'notes']
    autocomplete_fields = ['account', 'cost_center']


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'year', 'company', 'scenario', 'is_active_badge', 'created_at']
    list_filter = ['year', 'company', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['-year', 'name']
    inlines = [BudgetEntryInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'year', 'company')
        }),
        ('Scenario Integration', {
            'fields': ('scenario',),
            'description': 'Link to a scenario for scenario-based budgeting (optional)'
        }),
        ('Details', {
            'fields': ('description',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">●</span> Active')
        return format_html('<span style="color: red;">●</span> Inactive')
    is_active_badge.short_description = 'Status'


@admin.register(BudgetEntry)
class BudgetEntryAdmin(admin.ModelAdmin):
    list_display = ['budget', 'account', 'cost_center', 'month', 'budgeted_amount']
    list_filter = ['budget__year', 'month', 'account__account_type']
    search_fields = ['budget__name', 'account__code', 'cost_center__code']
    autocomplete_fields = ['budget', 'account', 'cost_center']
    ordering = ['budget', 'month', 'account__code']
    
    fieldsets = (
        ('Budget Entry', {
            'fields': ('budget', 'account', 'cost_center', 'month', 'budgeted_amount')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )
```

**Acceptance Criteria**:
- ✅ All models registered in Django admin
- ✅ List views configured with appropriate filters and search
- ✅ Inline editing enabled for `BudgetEntry` within `Budget` admin
- ✅ Admin interface tested with sample data

---

**Task 2.2: Create Seed Data Script**

**File**: `aquamind/apps/finance_core/management/commands/seed_finance_core.py`

```python
from django.core.management.base import BaseCommand
from aquamind.apps.finance.models import DimCompany
from aquamind.apps.finance_core.models import (
    AccountType, AccountGroup, Account, CostCenter, Budget, BudgetEntry
)


class Command(BaseCommand):
    help = 'Seed initial Chart of Accounts, Cost Centers, and sample budget data'
    
    def handle(self, *args, **options):
        self.stdout.write('Seeding Financial Core data...')
        
        # Get or create a company
        company, _ = DimCompany.objects.get_or_create(
            code='BAKKAFROST',
            defaults={'name': 'Bakkafrost P/F'}
        )
        
        # Create Account Groups
        opex_group = AccountGroup.objects.create(
            code='OPEX',
            name='Operating Expenses',
            account_type=AccountType.EXPENSE,
            display_order=1
        )
        
        feed_group = AccountGroup.objects.create(
            code='FEED',
            name='Feed Costs',
            account_type=AccountType.EXPENSE,
            parent=opex_group,
            display_order=1
        )
        
        labor_group = AccountGroup.objects.create(
            code='LABOR',
            name='Labor Costs',
            account_type=AccountType.EXPENSE,
            parent=opex_group,
            display_order=2
        )
        
        revenue_group = AccountGroup.objects.create(
            code='REVENUE',
            name='Sales Revenue',
            account_type=AccountType.REVENUE,
            display_order=1
        )
        
        # Create Accounts
        accounts = [
            Account(code='5100', name='Smolt Feed', account_type=AccountType.EXPENSE, group=feed_group),
            Account(code='5110', name='Parr Feed', account_type=AccountType.EXPENSE, group=feed_group),
            Account(code='5200', name='Farm Labor', account_type=AccountType.EXPENSE, group=labor_group),
            Account(code='5210', name='Hatchery Labor', account_type=AccountType.EXPENSE, group=labor_group),
            Account(code='4000', name='Harvest Revenue', account_type=AccountType.REVENUE, group=revenue_group),
        ]
        Account.objects.bulk_create(accounts)
        
        # Create Cost Centers
        cost_centers = [
            CostCenter(code='FARM-01', name='Faroe Islands - Farm 1', company=company),
            CostCenter(code='HATCHERY', name='Main Hatchery', company=company),
            CostCenter(code='SMOLT-HALL', name='Smolt Production Hall', company=company),
        ]
        CostCenter.objects.bulk_create(cost_centers)
        
        # Create a sample budget
        budget = Budget.objects.create(
            name='2025 Base Budget',
            year=2025,
            company=company,
            description='Base budget for 2025 fiscal year',
            is_active=True
        )
        
        # Create sample budget entries (Jan-Dec for one account/cost center)
        smolt_feed = Account.objects.get(code='5100')
        farm_01 = CostCenter.objects.get(code='FARM-01')
        
        entries = [
            BudgetEntry(
                budget=budget,
                account=smolt_feed,
                cost_center=farm_01,
                month=month,
                budgeted_amount=50000 + (month * 1000)  # Increasing monthly budget
            )
            for month in range(1, 13)
        ]
        BudgetEntry.objects.bulk_create(entries)
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded Financial Core data'))
```

**Run Command**:
```bash
python manage.py seed_finance_core
```

**Acceptance Criteria**:
- ✅ Seed script creates sample account groups, accounts, cost centers, and budget entries
- ✅ Data visible in Django admin
- ✅ No validation errors during seed data creation

---

#### Week 3: API Serializers

**Task 3.1: Implement Account Serializer**

**File**: `aquamind/apps/finance_core/api/serializers/account_serializer.py`

```python
from rest_framework import serializers
from aquamind.apps.finance_core.models import Account, AccountGroup


class AccountGroupSerializer(serializers.ModelSerializer):
    """Serializer for AccountGroup model."""
    
    parent_code = serializers.CharField(source='parent.code', read_only=True, allow_null=True)
    full_path = serializers.CharField(read_only=True)
    
    class Meta:
        model = AccountGroup
        fields = [
            'id', 'code', 'name', 'account_type', 'parent', 'parent_code',
            'full_path', 'display_order', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'parent_code', 'full_path']


class AccountSerializer(serializers.ModelSerializer):
    """Serializer for Account model (Chart of Accounts)."""
    
    group_code = serializers.CharField(source='group.code', read_only=True, allow_null=True)
    group_name = serializers.CharField(source='group.name', read_only=True, allow_null=True)
    
    class Meta:
        model = Account
        fields = [
            'id', 'code', 'name', 'account_type', 'group', 'group_code', 'group_name',
            'description', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'group_code', 'group_name']
    
    def validate_code(self, value):
        """Ensure account code is uppercase and alphanumeric."""
        if not value.replace('-', '').replace('_', '').isalnum():
            raise serializers.ValidationError("Account code must be alphanumeric (hyphens and underscores allowed)")
        return value.upper()
```

**Acceptance Criteria**:
- ✅ Serializers handle nested relationships (group_code, group_name)
- ✅ Read-only fields correctly marked
- ✅ Validation logic implemented

---

**Task 3.2: Implement CostCenter Serializer**

**File**: `aquamind/apps/finance_core/api/serializers/cost_center_serializer.py`

```python
from rest_framework import serializers
from aquamind.apps.finance_core.models import CostCenter


class CostCenterSerializer(serializers.ModelSerializer):
    """Serializer for CostCenter model."""
    
    company_code = serializers.CharField(source='company.code', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = CostCenter
        fields = [
            'id', 'code', 'name', 'company', 'company_code', 'company_name',
            'description', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'company_code', 'company_name']
    
    def validate_code(self, value):
        """Ensure cost center code is uppercase and alphanumeric."""
        if not value.replace('-', '').replace('_', '').isalnum():
            raise serializers.ValidationError("Cost center code must be alphanumeric (hyphens and underscores allowed)")
        return value.upper()
```

**Acceptance Criteria**:
- ✅ Company information included in serialized output
- ✅ Code validation implemented

---

**Task 3.3: Implement Budget Serializers**

**File**: `aquamind/apps/finance_core/api/serializers/budget_serializer.py`

```python
from rest_framework import serializers
from aquamind.apps.finance_core.models import Budget, BudgetEntry


class BudgetEntrySerializer(serializers.ModelSerializer):
    """Serializer for BudgetEntry model."""
    
    account_code = serializers.CharField(source='account.code', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    cost_center_code = serializers.CharField(source='cost_center.code', read_only=True)
    cost_center_name = serializers.CharField(source='cost_center.name', read_only=True)
    
    class Meta:
        model = BudgetEntry
        fields = [
            'id', 'budget', 'account', 'account_code', 'account_name',
            'cost_center', 'cost_center_code', 'cost_center_name',
            'month', 'budgeted_amount', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'account_code', 'account_name', 'cost_center_code', 'cost_center_name'
        ]
    
    def validate_month(self, value):
        """Ensure month is between 1 and 12."""
        if not 1 <= value <= 12:
            raise serializers.ValidationError("Month must be between 1 and 12")
        return value


class BudgetSerializer(serializers.ModelSerializer):
    """Serializer for Budget model."""
    
    company_code = serializers.CharField(source='company.code', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    scenario_name = serializers.CharField(source='scenario.name', read_only=True, allow_null=True)
    entry_count = serializers.IntegerField(source='entries.count', read_only=True)
    total_budgeted = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True,
        help_text="Sum of all budget entries for this budget"
    )
    
    class Meta:
        model = Budget
        fields = [
            'id', 'name', 'year', 'company', 'company_code', 'company_name',
            'scenario', 'scenario_name', 'description', 'is_active',
            'entry_count', 'total_budgeted', 'created_at', 'updated_at', 'created_by'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by',
            'company_code', 'company_name', 'scenario_name', 'entry_count', 'total_budgeted'
        ]
    
    def validate_year(self, value):
        """Ensure year is reasonable."""
        if not 2000 <= value <= 2100:
            raise serializers.ValidationError("Year must be between 2000 and 2100")
        return value


class BudgetDetailSerializer(BudgetSerializer):
    """Detailed serializer for Budget model including all entries."""
    
    entries = BudgetEntrySerializer(many=True, read_only=True)
    
    class Meta(BudgetSerializer.Meta):
        fields = BudgetSerializer.Meta.fields + ['entries']
```

**Acceptance Criteria**:
- ✅ Budget serializer includes aggregated data (entry_count, total_budgeted)
- ✅ Detail serializer includes nested entries
- ✅ Validation logic implemented

---

### Phase 1 Deliverables

- ✅ `finance_core` app created and configured
- ✅ 5 core models implemented with validation
- ✅ Database migrations applied
- ✅ Django admin interface configured
- ✅ Seed data script created and tested
- ✅ API serializers implemented for all models

---

## Phase 2: Core Features (Weeks 4-6)

### Objective

Implement REST API endpoints, custom actions, and business logic for the Financial Core module.

### Tasks

#### Week 4: ViewSets and Routers

**Task 4.1: Implement Account ViewSet**

**File**: `aquamind/apps/finance_core/api/viewsets/account_viewset.py`

```python
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from aquamind.apps.finance_core.models import Account, AccountGroup
from aquamind.apps.finance_core.api.serializers.account_serializer import (
    AccountSerializer, AccountGroupSerializer
)


class AccountGroupViewSet(viewsets.ModelViewSet):
    """ViewSet for AccountGroup CRUD operations."""
    
    queryset = AccountGroup.objects.all()
    serializer_class = AccountGroupSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['account_type', 'parent']
    search_fields = ['code', 'name']
    ordering_fields = ['code', 'display_order', 'created_at']
    ordering = ['display_order', 'code']


class AccountViewSet(viewsets.ModelViewSet):
    """ViewSet for Account (Chart of Accounts) CRUD operations."""
    
    queryset = Account.objects.select_related('group').all()
    serializer_class = AccountSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['account_type', 'group', 'is_active']
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['code', 'name', 'created_at']
    ordering = ['code']
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """
        Custom action: Get accounts grouped by account type.
        GET /api/v1/finance-core/accounts/by-type/
        """
        account_type = request.query_params.get('type')
        if not account_type:
            return Response({'error': 'type parameter is required'}, status=400)
        
        accounts = self.queryset.filter(account_type=account_type, is_active=True)
        serializer = self.get_serializer(accounts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Custom action: Get only active accounts.
        GET /api/v1/finance-core/accounts/active/
        """
        accounts = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(accounts, many=True)
        return Response(serializer.data)
```

**Acceptance Criteria**:
- ✅ CRUD operations work for Account and AccountGroup
- ✅ Filtering by account_type, group, is_active
- ✅ Search by code, name, description
- ✅ Custom actions (`by_type`, `active`) implemented

---

**Task 4.2: Implement CostCenter ViewSet**

**File**: `aquamind/apps/finance_core/api/viewsets/cost_center_viewset.py`

```python
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from aquamind.apps.finance_core.models import CostCenter
from aquamind.apps.finance_core.api.serializers.cost_center_serializer import CostCenterSerializer


class CostCenterViewSet(viewsets.ModelViewSet):
    """ViewSet for CostCenter CRUD operations."""
    
    queryset = CostCenter.objects.select_related('company').all()
    serializer_class = CostCenterSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['company', 'is_active']
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['code', 'name', 'created_at']
    ordering = ['code']
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Custom action: Get only active cost centers.
        GET /api/v1/finance-core/cost-centers/active/
        """
        cost_centers = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(cost_centers, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_company(self, request):
        """
        Custom action: Get cost centers for a specific company.
        GET /api/v1/finance-core/cost-centers/by-company/?company_id=1
        """
        company_id = request.query_params.get('company_id')
        if not company_id:
            return Response({'error': 'company_id parameter is required'}, status=400)
        
        cost_centers = self.queryset.filter(company_id=company_id, is_active=True)
        serializer = self.get_serializer(cost_centers, many=True)
        return Response(serializer.data)
```

**Acceptance Criteria**:
- ✅ CRUD operations work for CostCenter
- ✅ Filtering by company, is_active
- ✅ Custom actions (`active`, `by_company`) implemented

---

**Task 4.3: Implement Budget ViewSets**

**File**: `aquamind/apps/finance_core/api/viewsets/budget_viewset.py`

```python
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Q
from aquamind.apps.finance_core.models import Budget, BudgetEntry
from aquamind.apps.finance_core.api.serializers.budget_serializer import (
    BudgetSerializer, BudgetDetailSerializer, BudgetEntrySerializer
)


class BudgetViewSet(viewsets.ModelViewSet):
    """ViewSet for Budget CRUD operations."""
    
    queryset = Budget.objects.select_related('company', 'scenario', 'created_by').all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['year', 'company', 'scenario', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['year', 'name', 'created_at']
    ordering = ['-year', 'name']
    
    def get_serializer_class(self):
        """Use detailed serializer for retrieve action."""
        if self.action == 'retrieve':
            return BudgetDetailSerializer
        return BudgetSerializer
    
    def perform_create(self, serializer):
        """Set created_by to current user."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """
        Custom action: Get budget summary by account type.
        GET /api/v1/finance-core/budgets/{id}/summary/
        
        Returns:
        {
            "budget_id": 1,
            "budget_name": "2025 Base Budget",
            "year": 2025,
            "summary_by_type": [
                {"account_type": "REVENUE", "total": 1000000.00},
                {"account_type": "EXPENSE", "total": 800000.00}
            ],
            "net_income": 200000.00
        }
        """
        budget = self.get_object()
        
        # Aggregate by account type
        summary = BudgetEntry.objects.filter(budget=budget).values(
            'account__account_type'
        ).annotate(
            total=Sum('budgeted_amount')
        ).order_by('account__account_type')
        
        # Calculate net income (revenue - expenses)
        revenue = sum(
            item['total'] for item in summary
            if item['account__account_type'] == 'REVENUE'
        )
        expenses = sum(
            item['total'] for item in summary
            if item['account__account_type'] == 'EXPENSE'
        )
        net_income = revenue - expenses
        
        return Response({
            'budget_id': budget.id,
            'budget_name': budget.name,
            'year': budget.year,
            'summary_by_type': [
                {'account_type': item['account__account_type'], 'total': item['total']}
                for item in summary
            ],
            'net_income': net_income
        })
    
    @action(detail=True, methods=['post'])
    def copy(self, request, pk=None):
        """
        Custom action: Copy budget to a new year.
        POST /api/v1/finance-core/budgets/{id}/copy/
        Body: {"new_year": 2026, "new_name": "2026 Base Budget"}
        """
        budget = self.get_object()
        new_year = request.data.get('new_year')
        new_name = request.data.get('new_name')
        
        if not new_year or not new_name:
            return Response(
                {'error': 'new_year and new_name are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create new budget
        new_budget = Budget.objects.create(
            name=new_name,
            year=new_year,
            company=budget.company,
            scenario=budget.scenario,
            description=f"Copied from {budget.name}",
            is_active=False,
            created_by=request.user
        )
        
        # Copy all budget entries
        entries = BudgetEntry.objects.filter(budget=budget)
        new_entries = [
            BudgetEntry(
                budget=new_budget,
                account=entry.account,
                cost_center=entry.cost_center,
                month=entry.month,
                budgeted_amount=entry.budgeted_amount,
                notes=entry.notes
            )
            for entry in entries
        ]
        BudgetEntry.objects.bulk_create(new_entries)
        
        serializer = self.get_serializer(new_budget)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BudgetEntryViewSet(viewsets.ModelViewSet):
    """ViewSet for BudgetEntry CRUD operations."""
    
    queryset = BudgetEntry.objects.select_related('budget', 'account', 'cost_center').all()
    serializer_class = BudgetEntrySerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['budget', 'account', 'cost_center', 'month']
    ordering_fields = ['month', 'account__code', 'created_at']
    ordering = ['month', 'account__code']
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        Custom action: Bulk create budget entries.
        POST /api/v1/finance-core/budget-entries/bulk-create/
        Body: {
            "entries": [
                {"budget": 1, "account": 1, "cost_center": 1, "month": 1, "budgeted_amount": 50000},
                {"budget": 1, "account": 1, "cost_center": 1, "month": 2, "budgeted_amount": 52000}
            ]
        }
        """
        entries_data = request.data.get('entries', [])
        if not entries_data:
            return Response(
                {'error': 'entries list is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=entries_data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
```

**Acceptance Criteria**:
- ✅ CRUD operations work for Budget and BudgetEntry
- ✅ Custom actions (`summary`, `copy`, `bulk_create`) implemented
- ✅ Budget summary aggregates by account type
- ✅ Budget copy creates new budget with all entries

---

**Task 4.4: Configure Router**

**File**: `aquamind/apps/finance_core/api/routers/finance_core_router.py`

```python
from rest_framework.routers import DefaultRouter
from aquamind.apps.finance_core.api.viewsets.account_viewset import (
    AccountViewSet, AccountGroupViewSet
)
from aquamind.apps.finance_core.api.viewsets.cost_center_viewset import CostCenterViewSet
from aquamind.apps.finance_core.api.viewsets.budget_viewset import (
    BudgetViewSet, BudgetEntryViewSet
)

router = DefaultRouter()
router.register(r'account-groups', AccountGroupViewSet, basename='account-group')
router.register(r'accounts', AccountViewSet, basename='account')
router.register(r'cost-centers', CostCenterViewSet, basename='cost-center')
router.register(r'budgets', BudgetViewSet, basename='budget')
router.register(r'budget-entries', BudgetEntryViewSet, basename='budget-entry')

urlpatterns = router.urls
```

**File**: `aquamind/apps/finance_core/urls.py`

```python
from django.urls import path, include
from aquamind.apps.finance_core.api.routers.finance_core_router import urlpatterns as router_urls

app_name = 'finance_core'

urlpatterns = [
    path('', include(router_urls)),
]
```

**Update**: `aquamind/api/router.py`

```python
# Add to existing router configuration
from django.urls import path, include

urlpatterns = [
    # ... existing routes
    path('finance-core/', include('aquamind.apps.finance_core.urls')),
]
```

**Acceptance Criteria**:
- ✅ All ViewSets registered in router
- ✅ URLs follow kebab-case convention (`account-groups`, `cost-centers`, etc.)
- ✅ API endpoints accessible at `/api/v1/finance-core/*`

---

#### Week 5: Business Logic and Validation

**Task 5.1: Implement Budget Activation Logic**

**File**: `aquamind/apps/finance_core/services/budget_service.py`

```python
from django.db import transaction
from aquamind.apps.finance_core.models import Budget


class BudgetService:
    """Business logic for budget operations."""
    
    @staticmethod
    @transaction.atomic
    def activate_budget(budget_id: int) -> Budget:
        """
        Activate a budget and deactivate all other budgets for the same company/year.
        
        Args:
            budget_id: ID of the budget to activate
        
        Returns:
            The activated budget
        
        Raises:
            Budget.DoesNotExist: If budget_id is invalid
        """
        budget = Budget.objects.select_for_update().get(id=budget_id)
        
        # Deactivate all other budgets for the same company/year
        Budget.objects.filter(
            company=budget.company,
            year=budget.year
        ).exclude(id=budget_id).update(is_active=False)
        
        # Activate the target budget
        budget.is_active = True
        budget.save()
        
        return budget
    
    @staticmethod
    def get_active_budget(company_id: int, year: int) -> Budget:
        """
        Get the active budget for a company/year.
        
        Args:
            company_id: Company ID
            year: Fiscal year
        
        Returns:
            The active budget
        
        Raises:
            Budget.DoesNotExist: If no active budget exists
        """
        return Budget.objects.get(
            company_id=company_id,
            year=year,
            is_active=True
        )
```

**Acceptance Criteria**:
- ✅ Only one budget per company/year can be active
- ✅ Activation is atomic (uses database transaction)
- ✅ Service methods tested with unit tests

---

**Task 5.2: Implement Budget vs. Actuals Integration**

**File**: `aquamind/apps/finance_core/services/budget_actuals_service.py`

```python
from django.db.models import Sum, Q
from aquamind.apps.finance_core.models import Budget, BudgetEntry
from aquamind.apps.finance.models import FactHarvest, IntercompanyTransaction


class BudgetActualsService:
    """Business logic for Budget vs. Actuals reporting."""
    
    @staticmethod
    def get_budget_vs_actuals(budget_id: int, month: int = None):
        """
        Compare budgeted amounts vs. actual amounts from finance app.
        
        Args:
            budget_id: Budget ID
            month: Optional month filter (1-12)
        
        Returns:
            List of dicts with budget vs. actuals comparison
        """
        budget = Budget.objects.get(id=budget_id)
        
        # Get budget entries
        budget_entries = BudgetEntry.objects.filter(budget=budget)
        if month:
            budget_entries = budget_entries.filter(month=month)
        
        # Aggregate budget by account
        budget_summary = budget_entries.values('account').annotate(
            budgeted_amount=Sum('budgeted_amount')
        )
        
        # Get actuals from finance app (harvest revenue)
        # Note: This is a simplified example. Real implementation would need
        # to map FactHarvest and IntercompanyTransaction to CoA accounts.
        actuals_summary = FactHarvest.objects.filter(
            company=budget.company,
            harvest_date__year=budget.year
        )
        if month:
            actuals_summary = actuals_summary.filter(harvest_date__month=month)
        
        actuals_summary = actuals_summary.aggregate(
            total_revenue=Sum('total_revenue_nok')
        )
        
        # Combine budget and actuals
        # This is a simplified example - real implementation would need
        # a mapping table between FactHarvest and CoA accounts
        return {
            'budget_id': budget_id,
            'year': budget.year,
            'month': month,
            'budget_summary': list(budget_summary),
            'actuals_summary': actuals_summary,
            'variance': None  # Calculate variance based on account mapping
        }
```

**Acceptance Criteria**:
- ✅ Service integrates with existing `finance` app models
- ✅ Budget vs. Actuals comparison returns structured data
- ✅ Month filtering supported

---

#### Week 6: Testing

**Task 6.1: Write Model Tests**

**File**: `aquamind/apps/finance_core/tests/test_models.py`

```python
import pytest
from django.core.exceptions import ValidationError
from aquamind.apps.finance.models import DimCompany
from aquamind.apps.finance_core.models import (
    AccountType, AccountGroup, Account, CostCenter, Budget, BudgetEntry
)


@pytest.mark.django_db
class TestAccountModel:
    def test_create_account(self):
        """Test creating a valid account."""
        account = Account.objects.create(
            code='5100',
            name='Smolt Feed',
            account_type=AccountType.EXPENSE
        )
        assert account.code == '5100'
        assert account.is_active is True
    
    def test_account_code_uniqueness(self):
        """Test that account codes must be unique."""
        Account.objects.create(code='5100', name='Feed', account_type=AccountType.EXPENSE)
        with pytest.raises(Exception):
            Account.objects.create(code='5100', name='Duplicate', account_type=AccountType.EXPENSE)
    
    def test_account_group_type_validation(self):
        """Test that account type must match group type."""
        group = AccountGroup.objects.create(
            code='OPEX',
            name='Operating Expenses',
            account_type=AccountType.EXPENSE
        )
        account = Account(
            code='4000',
            name='Revenue',
            account_type=AccountType.REVENUE,
            group=group
        )
        with pytest.raises(ValidationError):
            account.full_clean()


@pytest.mark.django_db
class TestBudgetModel:
    def test_create_budget(self):
        """Test creating a valid budget."""
        company = DimCompany.objects.create(code='TEST', name='Test Company')
        budget = Budget.objects.create(
            name='2025 Budget',
            year=2025,
            company=company,
            is_active=True
        )
        assert budget.year == 2025
        assert budget.is_active is True
    
    def test_only_one_active_budget_per_company_year(self):
        """Test that only one budget per company/year can be active."""
        company = DimCompany.objects.create(code='TEST', name='Test Company')
        Budget.objects.create(name='Budget 1', year=2025, company=company, is_active=True)
        budget2 = Budget(name='Budget 2', year=2025, company=company, is_active=True)
        with pytest.raises(ValidationError):
            budget2.full_clean()


@pytest.mark.django_db
class TestBudgetEntryModel:
    def test_create_budget_entry(self):
        """Test creating a valid budget entry."""
        company = DimCompany.objects.create(code='TEST', name='Test Company')
        budget = Budget.objects.create(name='2025 Budget', year=2025, company=company)
        account = Account.objects.create(code='5100', name='Feed', account_type=AccountType.EXPENSE)
        cost_center = CostCenter.objects.create(code='FARM-01', name='Farm 1', company=company)
        
        entry = BudgetEntry.objects.create(
            budget=budget,
            account=account,
            cost_center=cost_center,
            month=1,
            budgeted_amount=50000
        )
        assert entry.month == 1
        assert entry.budgeted_amount == 50000
```

**Acceptance Criteria**:
- ✅ All models have test coverage
- ✅ Validation logic tested
- ✅ Tests pass with `pytest`

---

**Task 6.2: Write API Tests**

**File**: `aquamind/apps/finance_core/tests/test_viewsets.py`

```python
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from aquamind.apps.finance.models import DimCompany
from aquamind.apps.finance_core.models import Account, CostCenter, Budget, BudgetEntry

User = get_user_model()


@pytest.mark.django_db
class TestAccountViewSet:
    def test_list_accounts(self):
        """Test listing accounts via API."""
        client = APIClient()
        user = User.objects.create_user(username='testuser', password='testpass')
        client.force_authenticate(user=user)
        
        Account.objects.create(code='5100', name='Feed', account_type='EXPENSE')
        
        response = client.get('/api/v1/finance-core/accounts/')
        assert response.status_code == 200
        assert len(response.data) == 1
    
    def test_create_account(self):
        """Test creating an account via API."""
        client = APIClient()
        user = User.objects.create_user(username='testuser', password='testpass')
        client.force_authenticate(user=user)
        
        data = {
            'code': '5100',
            'name': 'Smolt Feed',
            'account_type': 'EXPENSE'
        }
        response = client.post('/api/v1/finance-core/accounts/', data)
        assert response.status_code == 201
        assert Account.objects.count() == 1


@pytest.mark.django_db
class TestBudgetViewSet:
    def test_budget_summary_action(self):
        """Test budget summary custom action."""
        client = APIClient()
        user = User.objects.create_user(username='testuser', password='testpass')
        client.force_authenticate(user=user)
        
        company = DimCompany.objects.create(code='TEST', name='Test Company')
        budget = Budget.objects.create(name='2025 Budget', year=2025, company=company)
        account = Account.objects.create(code='5100', name='Feed', account_type='EXPENSE')
        cost_center = CostCenter.objects.create(code='FARM-01', name='Farm 1', company=company)
        BudgetEntry.objects.create(
            budget=budget,
            account=account,
            cost_center=cost_center,
            month=1,
            budgeted_amount=50000
        )
        
        response = client.get(f'/api/v1/finance-core/budgets/{budget.id}/summary/')
        assert response.status_code == 200
        assert 'summary_by_type' in response.data
```

**Acceptance Criteria**:
- ✅ All API endpoints have test coverage
- ✅ Custom actions tested
- ✅ Tests pass with `pytest`

---

### Phase 2 Deliverables

- ✅ REST API endpoints implemented for all models
- ✅ Custom actions (`summary`, `copy`, `bulk_create`, `by_type`, `active`) implemented
- ✅ Business logic services created
- ✅ Budget vs. Actuals integration with `finance` app
- ✅ Comprehensive test suite (models and API)

---

## Phase 3: Integration & Reporting (Weeks 7-9)

### Objective

Integrate Financial Core with existing AquaMind modules (Scenario, Finance) and implement reporting views.

### Tasks

#### Week 7: Scenario Integration

**Task 7.1: Add Scenario-Based Budgeting**

The `Budget` model already has a `scenario` foreign key. This task focuses on enabling the frontend to create budgets linked to scenarios.

**Update**: `aquamind/apps/finance_core/api/viewsets/budget_viewset.py`

```python
@action(detail=False, methods=['get'])
def by_scenario(self, request):
    """
    Custom action: Get budgets for a specific scenario.
    GET /api/v1/finance-core/budgets/by-scenario/?scenario_id=1
    """
    scenario_id = request.query_params.get('scenario_id')
    if not scenario_id:
        return Response({'error': 'scenario_id parameter is required'}, status=400)
    
    budgets = self.queryset.filter(scenario_id=scenario_id)
    serializer = self.get_serializer(budgets, many=True)
    return Response(serializer.data)
```

**Acceptance Criteria**:
- ✅ Budgets can be filtered by scenario
- ✅ Frontend can create budgets linked to scenarios

---

**Task 7.2: Add Custom Action to Scenario ViewSet**

**File**: `aquamind/apps/scenario/api/viewsets.py` (Update existing file)

```python
from rest_framework.decorators import action
from rest_framework.response import Response
from aquamind.apps.finance_core.models import Budget
from aquamind.apps.finance_core.api.serializers.budget_serializer import BudgetSerializer

# Add to existing ScenarioViewSet
@action(detail=True, methods=['get'])
def budgets(self, request, pk=None):
    """
    Custom action: Get all budgets for this scenario.
    GET /api/v1/scenario/scenarios/{id}/budgets/
    """
    scenario = self.get_object()
    budgets = Budget.objects.filter(scenario=scenario)
    serializer = BudgetSerializer(budgets, many=True)
    return Response(serializer.data)
```

**Acceptance Criteria**:
- ✅ Scenario detail page can display linked budgets
- ✅ API endpoint tested

---

#### Week 8: Reporting Views

**Task 8.1: Create Budget Summary View**

**File**: `aquamind/apps/finance_core/views/budget_summary_view.py`

```python
from django.db.models import Sum, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from aquamind.apps.finance_core.models import Budget, BudgetEntry


class BudgetSummaryView(APIView):
    """
    API view for budget summary reporting.
    GET /api/v1/finance-core/reports/budget-summary/?budget_id=1
    """
    
    def get(self, request):
        budget_id = request.query_params.get('budget_id')
        if not budget_id:
            return Response({'error': 'budget_id parameter is required'}, status=400)
        
        budget = Budget.objects.get(id=budget_id)
        
        # Aggregate by account type and month
        summary = BudgetEntry.objects.filter(budget=budget).values(
            'account__account_type', 'month'
        ).annotate(
            total=Sum('budgeted_amount')
        ).order_by('month', 'account__account_type')
        
        # Calculate totals by account type
        totals_by_type = BudgetEntry.objects.filter(budget=budget).values(
            'account__account_type'
        ).annotate(
            total=Sum('budgeted_amount')
        )
        
        return Response({
            'budget_id': budget_id,
            'budget_name': budget.name,
            'year': budget.year,
            'monthly_summary': list(summary),
            'totals_by_type': list(totals_by_type)
        })
```

**Update**: `aquamind/apps/finance_core/urls.py`

```python
from django.urls import path, include
from aquamind.apps.finance_core.views.budget_summary_view import BudgetSummaryView

urlpatterns = [
    path('', include(router_urls)),
    path('reports/budget-summary/', BudgetSummaryView.as_view(), name='budget-summary'),
]
```

**Acceptance Criteria**:
- ✅ Budget summary view returns monthly aggregates
- ✅ Totals by account type calculated
- ✅ API endpoint tested

---

**Task 8.2: Create P&L Projection View**

**File**: `aquamind/apps/finance_core/views/pl_projection_view.py`

```python
from django.db.models import Sum, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from aquamind.apps.finance_core.models import Budget, BudgetEntry, AccountType


class PLProjectionView(APIView):
    """
    API view for Profit & Loss projection based on budget.
    GET /api/v1/finance-core/reports/pl-projection/?budget_id=1
    """
    
    def get(self, request):
        budget_id = request.query_params.get('budget_id')
        if not budget_id:
            return Response({'error': 'budget_id parameter is required'}, status=400)
        
        budget = Budget.objects.get(id=budget_id)
        
        # Calculate revenue
        revenue = BudgetEntry.objects.filter(
            budget=budget,
            account__account_type=AccountType.REVENUE
        ).aggregate(total=Sum('budgeted_amount'))['total'] or 0
        
        # Calculate expenses
        expenses = BudgetEntry.objects.filter(
            budget=budget,
            account__account_type=AccountType.EXPENSE
        ).aggregate(total=Sum('budgeted_amount'))['total'] or 0
        
        # Calculate net income
        net_income = revenue - expenses
        
        # Monthly breakdown
        monthly_pl = []
        for month in range(1, 13):
            month_revenue = BudgetEntry.objects.filter(
                budget=budget,
                month=month,
                account__account_type=AccountType.REVENUE
            ).aggregate(total=Sum('budgeted_amount'))['total'] or 0
            
            month_expenses = BudgetEntry.objects.filter(
                budget=budget,
                month=month,
                account__account_type=AccountType.EXPENSE
            ).aggregate(total=Sum('budgeted_amount'))['total'] or 0
            
            monthly_pl.append({
                'month': month,
                'revenue': month_revenue,
                'expenses': month_expenses,
                'net_income': month_revenue - month_expenses
            })
        
        return Response({
            'budget_id': budget_id,
            'budget_name': budget.name,
            'year': budget.year,
            'total_revenue': revenue,
            'total_expenses': expenses,
            'net_income': net_income,
            'monthly_pl': monthly_pl
        })
```

**Acceptance Criteria**:
- ✅ P&L projection calculates revenue, expenses, and net income
- ✅ Monthly breakdown provided
- ✅ API endpoint tested

---

#### Week 9: Documentation and OpenAPI Schema

**Task 9.1: Generate OpenAPI Schema**

```bash
python manage.py spectacular --file schema.yml
```

**Acceptance Criteria**:
- ✅ OpenAPI schema generated
- ✅ All endpoints documented
- ✅ Schema validated

---

**Task 9.2: Update PRD and Data Model Documentation**

**File**: `aquamind/docs/prd.md` (Update)

Add a new section:

```markdown
## 3.X Financial Core Module

### Overview
The Financial Core module provides Chart of Accounts (CoA), Cost Center tracking, and Budgeting functionality for financial planning and forecasting.

### Key Features
- Chart of Accounts management with hierarchical grouping
- Cost Center allocation for operational dimensions
- Monthly budget entry and tracking
- Scenario-based budgeting (integration with Scenario app)
- Budget vs. Actuals reporting (integration with Finance app)
- P&L and Cash Flow projections

### Data Model
See `aquamind/docs/database/data_model.md` for detailed schema.
```

**File**: `aquamind/docs/database/data_model.md` (Update)

Add a new section documenting the 5 new models.

**Acceptance Criteria**:
- ✅ PRD updated with Financial Core section
- ✅ Data model documentation updated

---

### Phase 3 Deliverables

- ✅ Scenario integration complete
- ✅ Reporting views implemented (Budget Summary, P&L Projection)
- ✅ OpenAPI schema generated
- ✅ PRD and data model documentation updated

---

## Phase 4: Testing & Deployment (Weeks 10-12)

### Objective

Comprehensive testing, performance optimization, and deployment preparation.

### Tasks

#### Week 10: Integration Testing

**Task 10.1: End-to-End API Tests**

**File**: `aquamind/apps/finance_core/tests/test_integration.py`

```python
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from aquamind.apps.finance.models import DimCompany
from aquamind.apps.finance_core.models import Account, CostCenter, Budget, BudgetEntry

User = get_user_model()


@pytest.mark.django_db
class TestBudgetWorkflow:
    def test_complete_budget_workflow(self):
        """Test complete workflow: create budget, add entries, get summary."""
        client = APIClient()
        user = User.objects.create_user(username='testuser', password='testpass')
        client.force_authenticate(user=user)
        
        # Create company
        company = DimCompany.objects.create(code='TEST', name='Test Company')
        
        # Create account
        account_data = {'code': '5100', 'name': 'Feed', 'account_type': 'EXPENSE'}
        response = client.post('/api/v1/finance-core/accounts/', account_data)
        assert response.status_code == 201
        account_id = response.data['id']
        
        # Create cost center
        cc_data = {'code': 'FARM-01', 'name': 'Farm 1', 'company': company.id}
        response = client.post('/api/v1/finance-core/cost-centers/', cc_data)
        assert response.status_code == 201
        cost_center_id = response.data['id']
        
        # Create budget
        budget_data = {'name': '2025 Budget', 'year': 2025, 'company': company.id}
        response = client.post('/api/v1/finance-core/budgets/', budget_data)
        assert response.status_code == 201
        budget_id = response.data['id']
        
        # Add budget entries
        entries_data = {
            'entries': [
                {
                    'budget': budget_id,
                    'account': account_id,
                    'cost_center': cost_center_id,
                    'month': month,
                    'budgeted_amount': 50000
                }
                for month in range(1, 13)
            ]
        }
        response = client.post('/api/v1/finance-core/budget-entries/bulk-create/', entries_data)
        assert response.status_code == 201
        
        # Get budget summary
        response = client.get(f'/api/v1/finance-core/budgets/{budget_id}/summary/')
        assert response.status_code == 200
        assert response.data['net_income'] == -600000  # 12 months * 50000 (expenses)
```

**Acceptance Criteria**:
- ✅ End-to-end workflows tested
- ✅ All API endpoints integrated correctly

---

#### Week 11: Performance Optimization

**Task 11.1: Add Database Indexes**

**File**: `aquamind/apps/finance_core/migrations/000X_add_indexes.py`

```python
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('finance_core', '000X_previous_migration'),
    ]
    
    operations = [
        migrations.AddIndex(
            model_name='budgetentry',
            index=models.Index(fields=['budget', 'account', 'month'], name='idx_budget_entry_lookup'),
        ),
        migrations.AddIndex(
            model_name='account',
            index=models.Index(fields=['account_type', 'is_active'], name='idx_account_type_active'),
        ),
    ]
```

**Acceptance Criteria**:
- ✅ Indexes added for common query patterns
- ✅ Query performance improved (measured with Django Debug Toolbar)

---

**Task 11.2: Optimize API Queries**

Update ViewSets to use `select_related` and `prefetch_related`:

```python
# Already implemented in Phase 2, verify optimization
queryset = BudgetEntry.objects.select_related('budget', 'account', 'cost_center').all()
```

**Acceptance Criteria**:
- ✅ N+1 query problems eliminated
- ✅ API response times < 200ms for list endpoints

---

#### Week 12: Deployment Preparation

**Task 12.1: Create Deployment Checklist**

**File**: `aquamind/docs/deployment/financial_core_deployment.md`

```markdown
# Financial Core Deployment Checklist

## Pre-Deployment
- [ ] Run all tests: `pytest aquamind/apps/finance_core/`
- [ ] Generate OpenAPI schema: `python manage.py spectacular --file schema.yml`
- [ ] Run migrations on staging: `python manage.py migrate finance_core`
- [ ] Seed initial data on staging: `python manage.py seed_finance_core`
- [ ] Verify API endpoints on staging

## Deployment
- [ ] Backup production database
- [ ] Run migrations on production: `python manage.py migrate finance_core`
- [ ] Seed initial data on production (if needed)
- [ ] Restart application servers
- [ ] Verify API endpoints on production

## Post-Deployment
- [ ] Monitor error logs for 24 hours
- [ ] Verify frontend integration
- [ ] Train users on new features
```

**Acceptance Criteria**:
- ✅ Deployment checklist created
- ✅ Staging deployment successful
- ✅ Production deployment plan approved

---

### Phase 4 Deliverables

- ✅ Integration tests complete
- ✅ Performance optimizations applied
- ✅ Deployment checklist created
- ✅ Production deployment ready

---

## Acceptance Criteria

### Backend Acceptance Criteria

1. **Data Model**:
   - ✅ All 5 models implemented (`AccountGroup`, `Account`, `CostCenter`, `Budget`, `BudgetEntry`)
   - ✅ Foreign key relationships correctly defined
   - ✅ Validation logic prevents invalid data

2. **API**:
   - ✅ All CRUD endpoints functional
   - ✅ Custom actions implemented (`summary`, `copy`, `bulk_create`, `by_type`, `active`, `by_scenario`)
   - ✅ Filtering, searching, and ordering work correctly
   - ✅ API follows AquaMind conventions (kebab-case, DRF standards)

3. **Integration**:
   - ✅ Scenario integration complete (budgets can be linked to scenarios)
   - ✅ Finance app integration complete (Budget vs. Actuals uses `FactHarvest` and `IntercompanyTransaction`)
   - ✅ No functional overlap with existing `finance` app

4. **Testing**:
   - ✅ Model tests cover validation logic
   - ✅ API tests cover all endpoints
   - ✅ Integration tests cover end-to-end workflows
   - ✅ Test coverage > 80%

5. **Documentation**:
   - ✅ PRD updated with Financial Core section
   - ✅ Data model documentation updated
   - ✅ OpenAPI schema generated
   - ✅ Deployment checklist created

### Frontend Acceptance Criteria

(To be defined in frontend implementation plan)

---

## Risk Mitigation

### Risk 1: Data Migration from FishTalk

**Risk**: Migrating existing Chart of Accounts and budgets from FishTalk to AquaMind.

**Mitigation**:
- Create a data migration script that maps FishTalk `FFAccount` to AquaMind `Account`
- Provide a CSV import tool for manual data entry if automated migration fails
- Test migration on a staging environment with real FishTalk data

### Risk 2: Performance with Large Budgets

**Risk**: Budget entry grids with 12 months × 100+ accounts × 10+ cost centers = 12,000+ entries.

**Mitigation**:
- Use database indexes on `budget`, `account`, `cost_center`, `month`
- Implement pagination for budget entry lists
- Use bulk create/update operations for data entry
- Consider TimescaleDB hypertables for time-series budget data

### Risk 3: Budget vs. Actuals Mapping

**Risk**: Mapping `FactHarvest` and `IntercompanyTransaction` to Chart of Accounts is complex.

**Mitigation**:
- Create a mapping table (`FinanceActualMapping`) that links `FactHarvest` to `Account`
- Provide a UI for finance managers to configure the mapping
- Start with a simple mapping (e.g., all harvest revenue → Account 4000)
- Iterate based on user feedback

### Risk 4: User Adoption

**Risk**: Users may resist switching from FishTalk's familiar budgeting UI.

**Mitigation**:
- Provide comprehensive user training
- Create video tutorials for common workflows
- Offer a "FishTalk Compatibility Mode" that mimics FishTalk's UI layout
- Gather user feedback early and iterate

---

## Conclusion

This implementation plan provides a complete, production-ready roadmap for building the Financial Core module in AquaMind. By following this plan, backend agents will have clear, actionable tasks with acceptance criteria, ensuring high-quality implementation that integrates seamlessly with the existing AquaMind architecture.

The plan is designed for agent-driven development in Cursor.ai, with clear separation of concerns and no temporary code—every component is built for the final architecture.

---

**Next Steps**:
1. Review and approve this implementation plan
2. Assign backend developer resources
3. Begin Phase 1 (Foundation) in Week 1
4. Coordinate with frontend team for UI implementation (see frontend documentation)
