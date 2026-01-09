from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import SOSAlert, ActivityTimer, SOSNotification
from .serializers import (SOSAlertSerializer, ActivityTimerSerializer, 
                         SOSAlertCreateSerializer, SOSStatusUpdateSerializer)
from .tasks import send_sos_notifications, process_sos_media
from contacts.models import EmergencyContact

import logging

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(description="Список SOS сигналов"),
    create=extend_schema(description="Создать SOS сигнал"),
)
class SOSAlertViewSet(viewsets.ModelViewSet):
    serializer_class = SOSAlertSerializer
    permission_classes = [IsAuthenticated]
    queryset = SOSAlert.objects.none()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return SOSAlert.objects.none()
        return SOSAlert.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return SOSAlertCreateSerializer
        elif self.action == 'update_status':
            return SOSStatusUpdateSerializer
        return SOSAlertSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Создание SOS без медиа (медиа загружается отдельно)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        sos_alert = serializer.save(user=request.user)
        
        contacts = EmergencyContact.objects.filter(
            user=request.user,
            is_active=True
        )
        
        if not contacts.exists():
            return Response(
                {'error': 'No emergency contacts configured'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        contact_ids = list(contacts.values_list('id', flat=True))
        
        # Отправляем уведомления синхронно
        send_sos_notifications(sos_alert.id, contact_ids)
        logger.info("✅ SOS уведомления отправлены")
        
        headers = self.get_success_headers(serializer.data)
        return Response(
            SOSAlertSerializer(sos_alert).data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def update_status(self, request, pk=None):
        sos_alert = self.get_object()
        serializer = self.get_serializer(sos_alert, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        new_status = serializer.validated_data['status']
        sos_alert.status = new_status
        
        if new_status in ['resolved', 'cancelled', 'false_alarm']:
            sos_alert.resolved_at = timezone.now()
        
        sos_alert.save()
        return Response(SOSAlertSerializer(sos_alert).data)
    
    @extend_schema(
        description="✅ Загрузка аудио файла для SOS",
        request={'multipart/form-data': {'type': 'object', 'properties': {'audio': {'type': 'string', 'format': 'binary'}}}},
    )
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_audio(self, request, pk=None):
        """✅ Загрузка аудио файла"""
        sos_alert = self.get_object()
        
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return Response(
                {'error': 'No audio file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Сохраняем аудио
        sos_alert.audio_file = audio_file
        sos_alert.save()
        
        logger.info(f"✅ Аудио загружено для SOS {sos_alert.id}: {audio_file.name}")
        
        # Обрабатываем медиа
        process_sos_media(sos_alert.id)
        
        # Повторно отправляем уведомления с обновленной информацией
        contacts = EmergencyContact.objects.filter(
            user=request.user,
            is_active=True
        )
        
        if contacts.exists():
            contact_ids = list(contacts.values_list('id', flat=True))
            
            # Отправляем только email уведомления (SMS уже были отправлены)
            from .tasks import send_email_notifications_only
            try:
                send_email_notifications_only(sos_alert.id, contact_ids)
            except:
                # Если функция не существует, пропускаем
                pass
        
        return Response({
            'success': True,
            'message': 'Audio uploaded successfully',
            'audio_url': request.build_absolute_uri(sos_alert.audio_file.url) if sos_alert.audio_file else None,
            'sos_id': sos_alert.id
        })

    @extend_schema(
        description="✅ Загрузка видео файла для SOS",
        request={'multipart/form-data': {'type': 'object', 'properties': {'video': {'type': 'string', 'format': 'binary'}}}},
    )
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_video(self, request, pk=None):
        """✅ Загрузка видео файла"""
        sos_alert = self.get_object()
        
        video_file = request.FILES.get('video')
        if not video_file:
            return Response(
                {'error': 'No video file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Сохраняем видео
        sos_alert.video_file = video_file
        sos_alert.save()
        
        logger.info(f"✅ Видео загружено для SOS {sos_alert.id}: {video_file.name}")
        
        # Обрабатываем медиа
        process_sos_media(sos_alert.id)
        
        return Response({
            'success': True,
            'message': 'Video uploaded successfully',
            'video_url': request.build_absolute_uri(sos_alert.video_file.url) if sos_alert.video_file else None,
            'sos_id': sos_alert.id
        })

    @action(detail=False, methods=['get'])
    def active(self, request):
        active_alert = SOSAlert.objects.filter(
            user=request.user,
            status='active'
        ).first()
        
        if active_alert:
            return Response(SOSAlertSerializer(active_alert).data)
        return Response({'detail': 'No active SOS alert'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def history(self, request):
        queryset = self.get_queryset().filter(
            status__in=['resolved', 'cancelled', 'false_alarm']
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(description="Список таймеров"),
)
class ActivityTimerViewSet(viewsets.ModelViewSet):
    serializer_class = ActivityTimerSerializer
    permission_classes = [IsAuthenticated]
    queryset = ActivityTimer.objects.none()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ActivityTimer.objects.none()
        return ActivityTimer.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        ActivityTimer.objects.filter(
            user=request.user,
            status='active'
        ).update(status='cancelled')
        
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        duration = serializer.validated_data['duration_minutes']
        start_time = timezone.now()
        end_time = start_time + timezone.timedelta(minutes=duration)
        
        serializer.save(
            user=self.request.user,
            start_time=start_time,
            end_time=end_time
        )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        timer = self.get_object()
        timer.status = 'completed'
        timer.save()
        return Response({'detail': 'Timer completed successfully'})

    @action(detail=False, methods=['get'])
    def active(self, request):
        active_timer = ActivityTimer.objects.filter(
            user=request.user,
            status='active',
            end_time__gt=timezone.now()
        ).first()
        
        if active_timer:
            return Response(self.get_serializer(active_timer).data)
        return Response({'detail': 'No active timer'}, status=status.HTTP_404_NOT_FOUND)