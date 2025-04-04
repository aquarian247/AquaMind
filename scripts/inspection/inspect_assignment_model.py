#!/usr/bin/env python
"""
Inspects the BatchContainerAssignment model and its relationship with LifeCycleStage.
"""
import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
django.setup()

# Import after Django setup
from apps.batch.models import BatchContainerAssignment, LifeCycleStage

def print_divider():
    print("-" * 80)

# Print BatchContainerAssignment fields
print("\nBatchContainerAssignment Model Fields:")
print_divider()
print(f"{'Field Name':<25} {'Type':<25} {'Related Model':<20}")
print_divider()

for field in BatchContainerAssignment._meta.get_fields():
    field_type = field.__class__.__name__
    related_model = "None"
    
    if hasattr(field, 'related_model') and field.related_model:
        related_model = field.related_model.__name__
        
    print(f"{field.name:<25} {field_type:<25} {related_model:<20}")

# Check for lifecycle_stage field specifically
lifecycle_field = None
for field in BatchContainerAssignment._meta.get_fields():
    if field.name == 'lifecycle_stage':
        lifecycle_field = field
        break

print_divider()
print("\nLifeCycleStage Relationship Details:")
print_divider()

if lifecycle_field:
    print(f"Field name: {lifecycle_field.name}")
    print(f"Field type: {lifecycle_field.__class__.__name__}")
    print(f"Related model: {lifecycle_field.related_model.__name__}")
    print(f"On delete: {lifecycle_field.remote_field.on_delete.__name__}")
    print(f"Related name: {lifecycle_field.remote_field.related_name or 'None'}")
    print(f"Null allowed: {lifecycle_field.null}")
    print(f"Blank allowed: {lifecycle_field.blank}")
else:
    print("No 'lifecycle_stage' field found in BatchContainerAssignment model!")

# Check if any BatchContainerAssignment instances have lifecycle_stage set
print_divider()
print("\nData Check:")
print_divider()

total_assignments = BatchContainerAssignment.objects.count()
with_stage = BatchContainerAssignment.objects.exclude(lifecycle_stage=None).count()
print(f"Total BatchContainerAssignment records: {total_assignments}")
print(f"Records with lifecycle_stage set: {with_stage}")
print(f"Percentage with stage: {(with_stage/total_assignments)*100 if total_assignments else 0:.1f}%")

# List a few sample records
print_divider()
print("\nSample Records:")
print_divider()
print(f"{'ID':<5} {'Batch':<15} {'Container':<15} {'Lifecycle Stage':<25} {'Active':<10}")
print_divider()

for assignment in BatchContainerAssignment.objects.all()[:5]:
    batch_num = assignment.batch.batch_number if assignment.batch else "None"
    container = assignment.container.name if assignment.container else "None"
    stage = assignment.lifecycle_stage.name if assignment.lifecycle_stage else "None"
    active = "Yes" if assignment.is_active else "No"
    print(f"{assignment.id:<5} {batch_num:<15} {container:<15} {stage:<25} {active:<10}")
