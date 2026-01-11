from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils import timezone
from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import SOSAlert, ActivityTimer
from .serializers import (SOSAlertSerializer, ActivityTimerSerializer, 
                         SOSAlertCreateSerializer, SOSStatusUpdateSerializer)
from contacts.models import EmergencyContact
import logging
import threading

logger = logging.getLogger(__name__)


def process_sos_async(sos_alert_id, contact_ids):
    from .tasks import send_sos_notifications, process_sos_media
    from .models import SOSAlert
    
    try:
        send_sos_notifications(sos_alert_id, contact_ids)
        logger.info(f" Уведомления отправлены для SOS {sos_alert_id}")
        
        sos_alert = SOSAlert.objects.get(id=sos_alert_id)
        if sos_alert.audio_file or sos_alert.video_file:
            process_sos_media(sos_alert_id)
            logger.info(f" Медиа обработаны для SOS {sos_alert_id}")
            
    except Exception as e:
        logger.error(f" Ошибка фоновой обработки SOS {sos_alert_id}: {e}", exc_info=True)


@extend_schema_view(
    list=extend_schema(description="Список SOS сигналов"),
    create=extend_schema(description="Создать SOS сигнал с аудио"),
)
class SOSAlertViewSet(viewsets.ModelViewSet):
    serializer_class = SOSAlertSerializer
    permission_classes = [IsAuthenticated]
    queryset = SOSAlert.objects.none()
    parser_classes = [MultiPartParser, FormParser, JSONParser]

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
        
        logger.info(f"📥 Получен запрос на создание SOS")
        
        audio_file = request.FILES.get('audio_file')
        video_file = request.FILES.get('video_file')
        
        if audio_file:
            logger.info(f"🎤 Аудио: {audio_file.name}, {audio_file.size / 1024:.2f} KB")
        if video_file:
            logger.info(f"🎬 Видео: {video_file.name}, {video_file.size / 1024:.2f} KB")
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            sos_alert = serializer.save(user=request.user)
            logger.info(f" SOS создан с ID: {sos_alert.id}")
            
            if sos_alert.audio_file:
                logger.info(f" Аудио загружено: {sos_alert.audio_file.url}")
            if sos_alert.video_file:
                logger.info(f" Видео загружено: {sos_alert.video_file.url}")
                
        except Exception as e:
            logger.error(f" Ошибка создания SOS: {e}", exc_info=True)
            return Response(
                {'error': f'Ошибка загрузки: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        contacts = EmergencyContact.objects.filter(user=request.user, is_active=True)
        
        if not contacts.exists():
            logger.warning(f"⚠️ Нет контактов у {request.user.phone_number}")
        
        contact_ids = list(contacts.values_list('id', flat=True))
        
        if contact_ids:
            thread = threading.Thread(
                target=process_sos_async,
                args=(sos_alert.id, contact_ids),
                daemon=True
            )
            thread.start()
            logger.info(f"🚀 Фоновая обработка запущена для SOS {sos_alert.id}")
        
        response_serializer = SOSAlertSerializer(sos_alert)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=self.get_success_headers(response_serializer.data)
        )

    @action(detail=True, methods=['post'])
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