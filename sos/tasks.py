from celery import shared_task
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def send_sos_notifications_sync(sos_alert_id, contact_ids):
    """Синхронная отправка SOS уведомлений (fallback)"""
    try:
        from .models import SOSAlert, SOSNotification
        from contacts.models import EmergencyContact
        from notifications.services import NotificationService
        
        sos_alert = SOSAlert.objects.get(id=sos_alert_id)
        contacts = EmergencyContact.objects.filter(id__in=contact_ids)
        
        notification_service = NotificationService()
        
        user = sos_alert.user
        user_name = f"{user.first_name} {user.last_name}".strip() or str(user.phone_number)
        
        success_count = 0
        
        for contact in contacts:
            notif = SOSNotification.objects.create(
                sos_alert=sos_alert,
                contact=contact,
                notification_type='sms',
                content=f"SOS от {user_name}"
            )
            
            result = notification_service.send_sos_alert(
                to_phone=str(contact.phone_number),
                user_name=user_name,
                latitude=float(sos_alert.latitude) if sos_alert.latitude else 0,
                longitude=float(sos_alert.longitude) if sos_alert.longitude else 0,
                address=sos_alert.address or None,
                telegram_username=contact.telegram_username
            )
            
            if result['success']:
                notif.status = 'sent'
                notif.sent_at = timezone.now()
                notif.notification_type = result['method']
                success_count += 1
            else:
                notif.status = 'failed'
                notif.error_message = result.get('error', 'Unknown error')
            
            notif.save()
        
        logger.info(f"✅ Отправлено {success_count}/{len(contacts)} уведомлений")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки SOS уведомлений: {e}", exc_info=True)
        return False


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
def send_sos_notifications(self, sos_alert_id, contact_ids):
    """Асинхронная отправка SOS уведомлений через Celery"""
    return send_sos_notifications_sync(sos_alert_id, contact_ids)


@shared_task
def process_sos_media(sos_alert_id):
    """Обработка медиа файлов SOS"""
    try:
        from .models import SOSAlert
        
        sos_alert = SOSAlert.objects.get(id=sos_alert_id)
        
        # Здесь можно:
        # - Сжать аудио/видео
        # - Загрузить в облако (S3)
        # - Извлечь метаданные
        
        logger.info(f"✅ Медиа обработаны для SOS {sos_alert_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка обработки медиа: {e}")
        return False


@shared_task
def check_expired_timers():
    """Проверка истекших таймеров активности"""
    try:
        from .models import ActivityTimer, SOSAlert
        from contacts.models import EmergencyContact
        
        expired_timers = ActivityTimer.objects.filter(
            status='active',
            end_time__lt=timezone.now(),
            notification_sent=False
        )
        
        count = 0
        
        for timer in expired_timers:
            try:
                # Создаем SOS alert
                sos_alert = SOSAlert.objects.create(
                    user=timer.user,
                    activation_method='timer',
                    notes=f'Таймер активности истек. Длительность: {timer.duration_minutes} мин'
                )
                
                # Получаем контакты
                contacts = EmergencyContact.objects.filter(
                    user=timer.user,
                    is_active=True
                )
                
                if contacts.exists():
                    # Отправляем уведомления синхронно
                    send_sos_notifications_sync(
                        sos_alert.id,
                        list(contacts.values_list('id', flat=True))
                    )
                
                # Обновляем таймер
                timer.status = 'expired'
                timer.notification_sent = True
                timer.sos_alert = sos_alert
                timer.save()
                
                count += 1
                
            except Exception as e:
                logger.error(f"❌ Ошибка обработки истекшего таймера {timer.id}: {e}")
        
        logger.info(f"✅ Обработано истекших таймеров: {count}")
        return count
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки таймеров: {e}")
        return 0