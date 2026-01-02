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
    queryset = SOSAlert.objects.none()  # ИСПРАВЛЕНО

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # ИСПРАВЛЕНО
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
        
        # Обработка медиа
        if sos_alert.audio_file or sos_alert.video_file:
            process_sos_media(sos_alert.id)
            logger.info("✅ Медиа обработаны")
        
        headers = self.get_success_headers(serializer.data)
        return Response(
            SOSAlertSerializer(sos_alert).data,
            status=status.HTTP_201_CREATED,
            headers=headers
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
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_audio(self, request, pk=None):
        """Загрузка и отправка аудио в Telegram"""
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
        
        # Отправляем в Telegram
        try:
            from notifications.services import NotificationService
            from contacts.models import EmergencyContact
            
            service = NotificationService()
            contacts = EmergencyContact.objects.filter(
                user=request.user,
                is_active=True,
                telegram_username__isnull=False
            )
            
            user = request.user
            user_name = f"{user.first_name} {user.last_name}".strip() or str(user.phone_number)
            
            caption = (
                f"🚨 SOS от {user_name}\n"
                f"📍 {sos_alert.address or 'Неизвестно'}\n"
                f"⏰ {sos_alert.created_at.strftime('%H:%M, %d.%m.%Y')}"
            )
            
            sent_count = 0
            for contact in contacts:
                success = service.send_audio_to_telegram(
                    telegram_username=contact.telegram_username,
                    audio_path=sos_alert.audio_file.path,
                    caption=caption
                )
                if success:
                    sent_count += 1
            
            return Response({
                'success': True,
                'sent_to': sent_count,
                'total_contacts': contacts.count(),
                'audio_url': request.build_absolute_uri(sos_alert.audio_file.url)
            })
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки аудио: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
    queryset = ActivityTimer.objects.none()  # ИСПРАВЛЕНО

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # ИСПРАВЛЕНО
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
    
    

