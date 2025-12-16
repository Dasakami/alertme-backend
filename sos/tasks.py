from celery import shared_task
from django.conf import settings
from django.utils import timezone
from .models import SOSAlert, SOSNotification, ActivityTimer
from contacts.models import EmergencyContact
from notifications.services import NotificationService


@shared_task
def send_sos_notifications(sos_alert_id, contact_ids):
    """
    Отправка SOS уведомлений контактам
    
    Использует NotificationService для автоматического выбора
    между Twilio (продакшн) и Telegram (MVP/fallback)
    """
    try:
        sos_alert = SOSAlert.objects.get(id=sos_alert_id)
        contacts = EmergencyContact.objects.filter(id__in=contact_ids)
        
        # Инициализируем сервис уведомлений
        notification_service = NotificationService()
        
        # Имя пользователя для сообщения
        user = sos_alert.user
        user_name = (
            f"{user.first_name} {user.last_name}".strip() 
            or str(user.phone_number)
        )
        
        for contact in contacts:
            # Создаем запись уведомления
            notif = SOSNotification.objects.create(
                sos_alert=sos_alert,
                contact=contact,
                notification_type='sms',  # или telegram
                content=f"SOS от {user_name}"
            )
            
            # Отправляем через сервис уведомлений
            result = notification_service.send_sos_alert(
                to_phone=str(contact.phone_number),
                user_name=user_name,
                latitude=float(sos_alert.latitude) if sos_alert.latitude else 0,
                longitude=float(sos_alert.longitude) if sos_alert.longitude else 0,
                address=sos_alert.address or None,
                telegram_username=contact.telegram_username  # ИСПОЛЬЗУЕМ НОВОЕ ПОЛЕ
            )
            
            # Обновляем статус уведомления
            if result['success']:
                notif.status = 'sent'
                notif.sent_at = timezone.now()
                notif.notification_type = result['method']  # twilio или telegram
            else:
                notif.status = 'failed'
                notif.error_message = result.get('error', 'Unknown error')
            
            notif.save()
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка отправки SOS уведомлений: {e}")
        import traceback
        traceback.print_exc()
        return False


@shared_task
def process_sos_media(sos_alert_id):
    """Обработка медиа файлов SOS"""
    try:
        sos_alert = SOSAlert.objects.get(id=sos_alert_id)
        
        # Здесь можно:
        # - Сжать аудио/видео
        # - Загрузить в облако (S3)
        # - Извлечь метаданные
        
        return True
    except Exception as e:
        print(f"❌ Ошибка обработки медиа: {e}")
        return False


@shared_task
def check_expired_timers():
    """
    Проверка истекших таймеров активности
    
    Если таймер истек - автоматически создаем SOS alert
    """
    expired_timers = ActivityTimer.objects.filter(
        status='active',
        end_time__lt=timezone.now(),
        notification_sent=False
    )
    
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
                # Отправляем уведомления
                send_sos_notifications.delay(
                    sos_alert.id,
                    list(contacts.values_list('id', flat=True))
                )
            
            # Обновляем таймер
            timer.status = 'expired'
            timer.notification_sent = True
            timer.sos_alert = sos_alert
            timer.save()
            
        except Exception as e:
            print(f"❌ Ошибка обработки истекшего таймера {timer.id}: {e}")
    
    return len(expired_timers)