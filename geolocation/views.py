from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from datetime import timedelta
from .models import LocationHistory, Geozone, GeozoneEvent, SharedLocation
from .serializers import (LocationHistorySerializer, GeozoneSerializer, 
                          GeozoneEventSerializer, SharedLocationSerializer)
from .tasks import check_geozone_events
import secrets


class LocationHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = LocationHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = LocationHistory.objects.filter(user=self.request.user)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset

    def perform_create(self, serializer):
        location = serializer.save(user=self.request.user)
        
        # Check geozones after saving location
        check_geozone_events.delay(self.request.user.id, location.id)

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get most recent location"""
        location = LocationHistory.objects.filter(
            user=request.user
        ).order_by('-timestamp').first()
        
        if location:
            serializer = self.get_serializer(location)
            return Response(serializer.data)
        
        return Response(
            {'detail': 'No location history available'},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(detail=False, methods=['get'])
    def track(self, request):
        """Get location track for the last N hours"""
        hours = int(request.query_params.get('hours', 24))
        since = timezone.now() - timedelta(hours=hours)
        
        locations = LocationHistory.objects.filter(
            user=request.user,
            timestamp__gte=since
        ).order_by('timestamp')
        
        serializer = self.get_serializer(locations, many=True)
        return Response(serializer.data)


class GeozoneViewSet(viewsets.ModelViewSet):
    serializer_class = GeozoneSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Geozone.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        """Get events for this geozone"""
        geozone = self.get_object()
        events = GeozoneEvent.objects.filter(
            geozone=geozone
        ).order_by('-timestamp')
        
        # Pagination
        page = self.paginate_queryset(events)
        if page is not None:
            serializer = GeozoneEventSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = GeozoneEventSerializer(events, many=True)
        return Response(serializer.data)


class SharedLocationViewSet(viewsets.ModelViewSet):
    serializer_class = SharedLocationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SharedLocation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Generate unique share token
        share_token = secrets.token_urlsafe(32)
        
        duration = serializer.validated_data['duration_minutes']
        start_time = timezone.now()
        end_time = start_time + timedelta(minutes=duration)
        
        serializer.save(
            user=self.request.user,
            share_token=share_token,
            start_time=start_time,
            end_time=end_time
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        shared_location = self.get_object()
        shared_location.status = 'cancelled'
        shared_location.save()
        return Response({'detail': 'Location sharing cancelled'})

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def track_by_token(self, request):
        """Track shared location by token (no auth required)"""
        token = request.query_params.get('token')
        
        if not token:
            return Response(
                {'error': 'Token required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            shared_location = SharedLocation.objects.get(
                share_token=token,
                status='active',
                end_time__gt=timezone.now()
            )
        except SharedLocation.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired token'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get recent locations
        locations = LocationHistory.objects.filter(
            user=shared_location.user,
            timestamp__gte=shared_location.start_time
        ).order_by('-timestamp')[:50]
        
        return Response({
            'shared_location': self.get_serializer(shared_location).data,
            'locations': LocationHistorySerializer(locations, many=True).data
        })