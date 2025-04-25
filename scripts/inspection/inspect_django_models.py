#!/usr/bin/env python
"""
Django Model Inspection Script

This script inspects Django models using the ORM and displays their fields, 
relationships, and other important information.
"""
import os
import sys
import django
from django.apps import apps
from django.db import models
from django.db.models import ForeignKey, ManyToManyField, OneToOneField

# Set up Django environment
# Go up two levels from the script's directory (scripts/inspection) to reach the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
django.setup()

def print_section_header(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)

def inspect_model(model):
    """Inspect a Django model and print its details."""
    print_section_header(f"MODEL: {model.__name__}")
    
    print(f"App: {model._meta.app_label}")
    print(f"DB Table: {model._meta.db_table}")
    print(f"Verbose Name: {model._meta.verbose_name}")
    
    print("\nFields:")
    print("-" * 80)
    
    for field in model._meta.get_fields():
        field_type = field.__class__.__name__
        null = getattr(field, 'null', 'N/A')
        blank = getattr(field, 'blank', 'N/A')
        choices = getattr(field, 'choices', None)
        
        relationship = ""
        if isinstance(field, (ForeignKey, OneToOneField)):
            relationship = f"-> {field.related_model.__name__}"
        elif isinstance(field, ManyToManyField):
            relationship = f"<-> {field.related_model.__name__}"
        elif hasattr(field, 'related_model') and field.related_model:
            relationship = f"<- {field.related_model.__name__}"
        
        print(f"  Field: {field.name}")
        print(f"    Type: {field_type}")
        print(f"    Null: {null}")
        print(f"    Blank: {blank}")
        if choices:
            print(f"    Has Choices: True")
        if relationship:
            print(f"    Relationship: {relationship}")
        print("")
    
    # Print model methods
    print("\nMethods:")
    model_methods = [method for method in dir(model) 
                   if callable(getattr(model, method)) 
                   and not method.startswith('_') 
                   and method not in dir(models.Model)]
    
    for method in model_methods:
        print(f"- {method}()")
    
    # Print constraints if any
    if hasattr(model._meta, 'constraints') and model._meta.constraints:
        print("\nConstraints:")
        for constraint in model._meta.constraints:
            print(f"- {constraint.name}: {constraint}")

def inspect_model_relationships(model):
    """Inspect relationships of a model."""
    print_section_header(f"RELATIONSHIPS FOR: {model.__name__}")
    
    # Forward relationships (ForeignKey, ManyToManyField)
    print("Forward Relationships (this model -> other models):")
    print("-" * 80)
    
    has_forward = False
    for field in model._meta.get_fields():
        if isinstance(field, (ForeignKey, ManyToManyField, OneToOneField)):
            has_forward = True
            # Check if related_model exists before accessing its name
            if field.related_model:
                related_name = getattr(field, 'related_name', None) or f'{field.related_model.__name__.lower()}_set'
                print(f"  {field.name} -> {field.related_model.__name__}")
                print(f"    Accessed as: {model.__name__}.{field.name}")
                print(f"    Reverse accessor: {field.related_model.__name__}.{related_name}")
                print("")
            else:
                print(f"  {field.name} -> [Generic Relation or Undefined Model]")
                print("")
    
    if not has_forward:
        print("  None found.")
        print("")

    # Reverse relationships (other models -> this model):
    print("\nReverse Relationships (other models -> this model):")
    print("-" * 80)
    
    has_reverse = False
    for relation in model._meta.get_fields():
        # Check if it's a reverse relation object AND related_model is not None
        if hasattr(relation, 'related_model') and relation.related_model and not isinstance(relation, (ForeignKey, ManyToManyField, OneToOneField)):
            if relation.related_model != model:  # Skip self-relations
                has_reverse = True
                field_name = relation.name # This is usually the related_query_name or similar
                related_model_name = relation.related_model.__name__
                print(f"  {related_model_name} -> {model.__name__}")
                print(f"    Accessed as: {related_model_name}.{field_name}")
                print("")
    
    if not has_reverse:
        print("  None found.")

def main():
    """Main function to inspect all models or specific ones."""
    print_section_header("DJANGO MODEL INSPECTION")
    
    # Get all apps and models
    all_models = []
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            all_models.append(model)
    
    # Sort models by app and name
    all_models.sort(key=lambda x: (x._meta.app_label, x.__name__))
    
    # Print list of all models in a more structured format
    print(f"Found {len(all_models)} models across {len(apps.get_app_configs())} apps:")
    print("-" * 80)
    
    current_app = ""
    for model in all_models:
        if model._meta.app_label != current_app:
            current_app = model._meta.app_label
            print(f"\nApp: {current_app}")
            print("-" * 40)
        print(f"  - {model.__name__}")
    
    # Ask user which model to inspect
    print("\nEnter model name to inspect (or 'all' for all models, 'q' to quit): ", end="")
    model_name = input().strip()
    
    if model_name.lower() == 'q':
        return
    elif model_name.lower() == 'all':
        for model in all_models:
            inspect_model(model)
            inspect_model_relationships(model)
    else:
        # Find the model by name
        target_models = [m for m in all_models if m.__name__.lower() == model_name.lower()]
        
        if not target_models:
            print(f"Model '{model_name}' not found. Enter a partial name to search: ", end="")
            partial_name = input().strip()
            target_models = [m for m in all_models if partial_name.lower() in m.__name__.lower()]
        
        if not target_models:
            print("No matching models found.")
            return
        
        # If multiple models match, let user choose
        if len(target_models) > 1:
            print(f"Found {len(target_models)} matching models:")
            for i, model in enumerate(target_models, 1):
                print(f"{i}. {model.__name__} (from {model._meta.app_label})")
            print("Enter number to inspect: ", end="")
            try:
                choice = int(input().strip())
                target_model = target_models[choice - 1]
            except (ValueError, IndexError):
                print("Invalid choice.")
                return
        else:
            target_model = target_models[0]
        
        inspect_model(target_model)
        inspect_model_relationships(target_model)

if __name__ == "__main__":
    main()
