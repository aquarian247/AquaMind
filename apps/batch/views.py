from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import (
    Species, 
    LifeCycleStage, 
    Batch, 
    BatchContainerAssignment,
    BatchComposition,
    BatchTransfer, 
    MortalityEvent, 
    GrowthSample
)
from .serializers import (
    SpeciesSerializer, 
    LifeCycleStageSerializer, 
    BatchSerializer, 
    BatchContainerAssignmentSerializer,
    BatchCompositionSerializer,
    BatchTransferSerializer, 
    MortalityEventSerializer, 
    GrowthSampleSerializer
)


class SpeciesViewSet(viewsets.ModelViewSet):
    queryset = Species.objects.all()
    serializer_class = SpeciesSerializer
    filterset_fields = ['name', 'scientific_name']
    search_fields = ['name', 'scientific_name', 'description']


class LifeCycleStageViewSet(viewsets.ModelViewSet):
    queryset = LifeCycleStage.objects.all()
    serializer_class = LifeCycleStageSerializer
    filterset_fields = ['name', 'order']
    search_fields = ['name', 'description']


class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer
    filterset_fields = ['status', 'species', 'lifecycle_stage', 'batch_type']
    search_fields = ['batch_number', 'notes']
    
    @action(detail=True, methods=['post'])
    def split_batch(self, request, pk=None):
        """
        Split a batch into two or more new batches.
        This is used when a portion of fish are being moved to different containers.
        """
        batch = self.get_object()
        
        # Validate request data
        if not request.data.get('splits') or not isinstance(request.data.get('splits'), list):
            return Response({'error': 'splits field is required and must be a list'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        splits = request.data.get('splits')
        total_count = sum(split.get('count', 0) for split in splits)
        
        # Check that the total count doesn't exceed the batch's population
        if total_count > batch.population_count:
            return Response({'error': f'Total split count ({total_count}) exceeds batch population ({batch.population_count})'},
                           status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Create new batches for each split
            new_batches = []
            transfers = []
            
            for i, split in enumerate(splits):
                # Create new batch
                new_batch = Batch.objects.create(
                    batch_number=f"{batch.batch_number}-{i+1}",
                    species=batch.species,
                    lifecycle_stage=batch.lifecycle_stage,
                    status='ACTIVE',
                    batch_type='STANDARD',
                    population_count=split.get('count'),
                    avg_weight_g=batch.avg_weight_g,  # Assume same average weight
                    biomass_kg=(split.get('count') * batch.avg_weight_g) / 1000,
                    start_date=timezone.now().date(),
                    notes=f"Split from batch {batch.batch_number}"
                )
                new_batches.append(new_batch)
                
                # Create container assignment if container is specified
                if split.get('container'):
                    assignment = BatchContainerAssignment.objects.create(
                        batch=new_batch,
                        container_id=split.get('container'),
                        population_count=split.get('count'),
                        biomass_kg=(split.get('count') * batch.avg_weight_g) / 1000,
                        assignment_date=timezone.now().date(),
                        is_active=True
                    )
                    
                    # Find an active source assignment to use for transfer record
                    source_assignment = BatchContainerAssignment.objects.filter(
                        batch=batch,
                        is_active=True
                    ).first()
                    
                    if source_assignment:
                        # Record the transfer
                        transfer = BatchTransfer.objects.create(
                            source_batch=batch,
                            destination_batch=new_batch,
                            transfer_type='SPLIT',
                            transfer_date=timezone.now().date(),
                            source_assignment=source_assignment,
                            destination_assignment=assignment,
                            source_count=batch.population_count,
                            transferred_count=split.get('count'),
                            mortality_count=0,
                            source_biomass_kg=batch.biomass_kg,
                            transferred_biomass_kg=(split.get('count') * batch.avg_weight_g) / 1000,
                            source_lifecycle_stage=batch.lifecycle_stage,
                            destination_lifecycle_stage=batch.lifecycle_stage,
                            # Container info is now derived from assignments
                            notes=f"Split from batch {batch.batch_number}"
                        )
                        transfers.append(transfer)
            
            # Store original population count
            original_population_count = batch.population_count
            
            # Update the original batch with remaining fish
            remaining_count = original_population_count - total_count
            batch.population_count = remaining_count
            batch.biomass_kg = (remaining_count * batch.avg_weight_g) / 1000
            batch.save()
            
            # Update any active assignments for the original batch
            for assignment in BatchContainerAssignment.objects.filter(batch=batch, is_active=True):
                # Proportionally reduce the count in each container
                reduction_factor = remaining_count / original_population_count
                assignment.population_count = int(assignment.population_count * reduction_factor)
                assignment.biomass_kg = (assignment.population_count * batch.avg_weight_g) / 1000
                assignment.save()
        
        # Return the created batches
        serializer = self.get_serializer(new_batches, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def merge_batches(self, request, pk=None):
        """
        Merge multiple batches into a single mixed batch.
        Used in emergency situations where batches need to be combined.
        """
        destination_batch = self.get_object()
        
        # Validate request data
        if not request.data.get('source_batches') or not isinstance(request.data.get('source_batches'), list):
            return Response({'error': 'source_batches field is required and must be a list'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        if not request.data.get('container'):
            return Response({'error': 'container field is required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        source_batch_data = request.data.get('source_batches')
        container_id = request.data.get('container')
        
        with transaction.atomic():
            # Mark the destination batch as a mixed batch
            destination_batch.batch_type = 'MIXED'
            destination_batch.save()
            
            total_added_count = 0
            total_added_biomass = 0
            
            for source_data in source_batch_data:
                source_batch_id = source_data.get('batch')
                count = source_data.get('count')
                
                if not source_batch_id or not count:
                    return Response({'error': 'Each source batch must have batch and count specified'}, 
                                   status=status.HTTP_400_BAD_REQUEST)
                
                # Get the source batch
                try:
                    source_batch = Batch.objects.get(pk=source_batch_id)
                except Batch.DoesNotExist:
                    return Response({'error': f'Source batch with id {source_batch_id} does not exist'}, 
                                  status=status.HTTP_404_NOT_FOUND)
                
                # Check that the count doesn't exceed the source batch's population
                if count > source_batch.population_count:
                    return Response({'error': f'Count ({count}) exceeds batch population ({source_batch.population_count}) for batch {source_batch.batch_number}'},
                                   status=status.HTTP_400_BAD_REQUEST)
                
                # Calculate biomass based on source batch average weight
                biomass = (count * source_batch.avg_weight_g) / 1000
                
                # Create batch composition record
                composition = BatchComposition.objects.create(
                    mixed_batch=destination_batch,
                    source_batch=source_batch,
                    percentage=0,  # Will calculate after all additions
                    population_count=count,
                    biomass_kg=biomass
                )
                
                # Find an active source assignment to use for transfer record
                source_assignment = BatchContainerAssignment.objects.filter(
                    batch=source_batch,
                    is_active=True
                ).first()
                
                if source_assignment:
                    # Create destination assignment if it doesn't exist
                    destination_assignment, created = BatchContainerAssignment.objects.get_or_create(
                        batch=destination_batch,
                        container_id=container_id,
                        defaults={
                            'population_count': 0,
                            'biomass_kg': 0,
                            'assignment_date': timezone.now().date(),
                            'is_active': True
                        }
                    )
                    
                    # Record the transfer
                    transfer = BatchTransfer.objects.create(
                        source_batch=source_batch,
                        destination_batch=destination_batch,
                        transfer_type='MERGE',
                        transfer_date=timezone.now().date(),
                        source_assignment=source_assignment,
                        destination_assignment=destination_assignment,
                        source_count=source_batch.population_count,
                        transferred_count=count,
                        mortality_count=0,
                        source_biomass_kg=source_batch.biomass_kg,
                        transferred_biomass_kg=biomass,
                        source_lifecycle_stage=source_batch.lifecycle_stage,
                        destination_lifecycle_stage=destination_batch.lifecycle_stage,
                        # Container info is now derived from assignments
                        is_emergency_mixing=True,
                        notes=f"Merged into mixed batch {destination_batch.batch_number}"
                    )
                    
                    # Update the destination assignment
                    destination_assignment.population_count += count
                    destination_assignment.biomass_kg += biomass
                    destination_assignment.save()
                
                # Update the source batch with remaining fish
                remaining_count = source_batch.population_count - count
                source_batch.population_count = remaining_count
                source_batch.biomass_kg = (remaining_count * source_batch.avg_weight_g) / 1000
                source_batch.save()
                
                # Update any active assignments for the source batch
                for assignment in BatchContainerAssignment.objects.filter(batch=source_batch, is_active=True):
                    # Proportionally reduce the count in each container
                    reduction_factor = remaining_count / (remaining_count + count)
                    assignment.population_count = int(assignment.population_count * reduction_factor)
                    assignment.biomass_kg = (assignment.population_count * source_batch.avg_weight_g) / 1000
                    assignment.save()
                
                total_added_count += count
                total_added_biomass += biomass
            
            # Update destination batch totals
            destination_batch.population_count += total_added_count
            destination_batch.biomass_kg += total_added_biomass
            
            # Recalculate average weight for the mixed batch
            if destination_batch.population_count > 0:
                destination_batch.avg_weight_g = (destination_batch.biomass_kg * 1000) / destination_batch.population_count
            
            destination_batch.save()
            
            # Update percentage values in composition records
            for comp in BatchComposition.objects.filter(mixed_batch=destination_batch):
                comp.percentage = (comp.population_count / destination_batch.population_count) * 100
                comp.save()
        
        # Return the updated batch
        serializer = self.get_serializer(destination_batch)
        return Response(serializer.data)


class BatchContainerAssignmentViewSet(viewsets.ModelViewSet):
    queryset = BatchContainerAssignment.objects.all()
    serializer_class = BatchContainerAssignmentSerializer
    filterset_fields = ['batch', 'container', 'is_active']
    
    @action(detail=False, methods=['get'])
    def by_container(self, request):
        container_id = request.query_params.get('container')
        if not container_id:
            return Response({'error': 'container parameter is required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        assignments = self.queryset.filter(container_id=container_id, is_active=True)
        serializer = self.get_serializer(assignments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_batch(self, request):
        batch_id = request.query_params.get('batch')
        if not batch_id:
            return Response({'error': 'batch parameter is required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        assignments = self.queryset.filter(batch_id=batch_id, is_active=True)
        serializer = self.get_serializer(assignments, many=True)
        return Response(serializer.data)


class BatchCompositionViewSet(viewsets.ModelViewSet):
    queryset = BatchComposition.objects.all()
    serializer_class = BatchCompositionSerializer
    filterset_fields = ['mixed_batch', 'source_batch']


class BatchTransferViewSet(viewsets.ModelViewSet):
    queryset = BatchTransfer.objects.all()
    serializer_class = BatchTransferSerializer
    filterset_fields = ['source_batch', 'destination_batch', 'transfer_type', 'transfer_date', 'is_emergency_mixing']
    search_fields = ['notes']


class MortalityEventViewSet(viewsets.ModelViewSet):
    queryset = MortalityEvent.objects.all()
    serializer_class = MortalityEventSerializer
    filterset_fields = ['batch', 'event_date', 'cause']
    search_fields = ['description']


class GrowthSampleViewSet(viewsets.ModelViewSet):
    queryset = GrowthSample.objects.all()
    serializer_class = GrowthSampleSerializer
    filterset_fields = ['assignment', 'sample_date'] 
    search_fields = ['notes']
