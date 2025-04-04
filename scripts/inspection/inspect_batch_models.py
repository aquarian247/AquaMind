#!/usr/bin/env python
"""
Batch Models Inspection Script

This script specifically examines the Batch, BatchContainerAssignment, and 
LifeCycleStage models to understand their relationships.
"""
import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
django.setup()

# Import models after Django setup
from django.apps import apps
from django.db.models.fields.related import ForeignKey, ManyToManyField, OneToOneField
from apps.batch.models import Batch, BatchContainerAssignment, LifeCycleStage

def print_section_header(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)

def inspect_model_fields(model):
    """Inspect fields of a model."""
    print_section_header(f"FIELDS FOR: {model.__name__}")
    
    print(f"{'Name':<25} {'Type':<25} {'Null':<8} {'Blank':<8} {'Related Model':<20}")
    print("-" * 90)
    
    for field in model._meta.get_fields():
        field_type = field.__class__.__name__
        null = getattr(field, 'null', 'N/A')
        blank = getattr(field, 'blank', 'N/A')
        
        related_model = "None"
        if hasattr(field, 'related_model') and field.related_model:
            related_model = field.related_model.__name__
            
        print(f"{field.name:<25} {field_type:<25} {str(null):<8} {str(blank):<8} {related_model:<20}")

def inspect_model_relationships(model):
    """Inspect relationships of a model."""
    print_section_header(f"RELATIONSHIPS FOR: {model.__name__}")
    
    # Forward relationships (ForeignKey, ManyToManyField)
    print("Forward Relationships (this model references other models):")
    print(f"{'Field Name':<20} {'Type':<15} {'Related Model':<20} {'Related Name':<20}")
    print("-" * 80)
    
    for field in model._meta.get_fields():
        if isinstance(field, (ForeignKey, OneToOneField, ManyToManyField)):
            field_type = "ForeignKey" if isinstance(field, ForeignKey) else "OneToOneField" if isinstance(field, OneToOneField) else "ManyToManyField"
            related_name = getattr(field, 'related_name', None) or "None"
            print(f"{field.name:<20} {field_type:<15} {field.related_model.__name__:<20} {related_name:<20}")
    
    # Reverse relationships (other models reference this model)
    print("\nReverse Relationships (other models reference this model):")
    print(f"{'Model':<20} {'Field':<20} {'Type':<15} {'Related Name':<20}")
    print("-" * 80)
    
    reverse_relations = [f for f in model._meta.get_fields() 
                         if hasattr(f, 'related_model') and not isinstance(f, (ForeignKey, ManyToManyField, OneToOneField))]
    
    for relation in reverse_relations:
        if relation.related_model != model:  # Skip self-relations
            field_name = relation.field.name if hasattr(relation, 'field') else "Unknown"
            field_type = relation.field.__class__.__name__ if hasattr(relation, 'field') else "Unknown"
            model_name = relation.related_model.__name__
            print(f"{model_name:<20} {field_name:<20} {field_type:<15} {relation.name:<20}")

def main():
    """Main function to inspect the batch models."""
    print_section_header("BATCH MODELS INSPECTION")
    
    # Inspect Batch model
    print("\nInspecting Batch model...")
    inspect_model_fields(Batch)
    inspect_model_relationships(Batch)
    
    # Inspect BatchContainerAssignment model
    print("\nInspecting BatchContainerAssignment model...")
    inspect_model_fields(BatchContainerAssignment)
    inspect_model_relationships(BatchContainerAssignment)
    
    # Inspect LifeCycleStage model
    print("\nInspecting LifeCycleStage model...")
    inspect_model_fields(LifeCycleStage)
    inspect_model_relationships(LifeCycleStage)
    
    print("\nInspection complete!")

if __name__ == "__main__":
    main()
