from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def send_sos_notifications_sync(sos_alert_id, contact_ids):
    """
    ✅ ИСПРАВЛЕННАЯ отправка SOS уведомлений
    
    Формат сообщения:
    🚨 ЭКСТРЕННАЯ ТРЕВОГА!
    
    [Имя] активировал SOS!
    
    📍 Адрес: [адрес]
    🗺️ Карта: [ссылка на Google Maps]
    
    🎬 Медиа (аудио/видео): [ссылка]
    
    ⏰ Время: HH:MM, DD.MM.YYYY
    
    ❗ Это автоматическое сообщение из AlertMe
    """
    try:
        from .models import SOSAlert, SOSNotification
        from contacts.models import EmergencyContact
        from notifications.sms_service import SMSService
        from django.conf import settings
        
        sos_alert = SOSAlert.objects.get(id=sos_alert_id)
        contacts = EmergencyContact.objects.filter(id__in=contact_ids)
        
        sms_service = SMSService()
        
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
            
            # ✅ ИСПРАВЛЕННОЕ форматирование сообщения
            message = _format_sos_message_fixed(
                user_name=user_name,
                latitude=float(sos_alert.latitude) if sos_alert.latitude else None,
                longitude=float(sos_alert.longitude) if sos_alert.longitude else None,
                address=sos_alert.address or None,
                sos_alert_id=sos_alert_id,
                has_audio=bool(sos_alert.audio_file),
                has_video=bool(sos_alert.video_file)
            )
            
            # Отправляем SMS
            media_urls = []
            if sos_alert.audio_file:
                try:
                    media_urls.append(sos_alert.audio_file.url)
                except Exception:
                    pass
            if sos_alert.video_file:
                try:
                    media_urls.append(sos_alert.video_file.url)
                except Exception:
                    pass

            success = sms_service.send_sms(
                to_phone=str(contact.phone_number),
                message=message,
                media_urls=media_urls if media_urls else None
            )
            
            if success:
                notif.status = 'sent'
                notif.sent_at = timezone.now()
                notif.notification_type = 'sms'
                success_count += 1
            else:
                notif.status = 'failed'
                notif.error_message = 'SMS delivery failed'
            
            notif.save()
        
        logger.info(f"✅ Отправлено {success_count}/{len(contacts)} SOS уведомлений")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки SOS уведомлений: {e}", exc_info=True)
        return False


def _format_sos_message_fixed(
    user_name: str,
    latitude: float = None,
    longitude: float = None,
    address: str = None,
    sos_alert_id: int = None,
    has_audio: bool = False,
    has_video: bool = False
) -> str:
    """
    ✅ ИСПРАВЛЕННОЕ форматирование SOS сообщения
    
    Красивое, информативное сообщение с:
    - Адресом (если есть)
    - Ссылкой на Google Maps
    - Ссылкой на медиа (аудио/видео)
    - Временем активации
    """
    base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')
    
    # 🚨 Заголовок
    message = "🚨 ЭКСТРЕННАЯ ТРЕВОГА!\n\n"
    message += f"{user_name} активировал SOS!\n\n"
    
    # 📍 Адрес или координаты
    if address:
        message += f"📍 Адрес:\n{address}\n\n"
    elif latitude and longitude:
        message += f"📍 Координаты:\n{latitude:.4f}, {longitude:.4f}\n\n"
    
    # 🗺️ Ссылка на карту
    if latitude and longitude:
        google_maps_url = f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"
        message += f"🗺️ Карта:\n{google_maps_url}\n\n"
    
    # 🎬 Ссылка на медиа (если есть аудио или видео)
    if (has_audio or has_video) and sos_alert_id:
        media_url = f"{base_url}/api/media/sos/{sos_alert_id}/"
        media_types = []
        if has_audio:
            media_types.append("аудио")
        if has_video:
            media_types.append("видео")
        
        message += f"🎬 Медиа ({', '.join(media_types)}):\n{media_url}\n\n"
    
    # ⏰ Время
    now = timezone.now()
    message += f"⏰ Время: {now.strftime('%H:%M, %d.%m.%Y')}\n\n"
    
    # ❗ Подпись
    message += "❗ ПОМОГИТЕ ЕМУ СРОЧНО!\n"
    message += "Это автоматическое сообщение из AlertMe"
    
    return message


def send_sos_notifications(sos_alert_id, contact_ids):
    """Отправка SOS уведомлений (синхронная)"""
    return send_sos_notifications_sync(sos_alert_id, contact_ids)


def process_sos_media(sos_alert_id):
    """Обработка медиа файлов SOS"""
    try:
        from .models import SOSAlert
        from notifications.models import SOSMediaLog
        from notifications.media_service import MediaService
        
        sos_alert = SOSAlert.objects.get(id=sos_alert_id)
        
        # Обработка аудио
        if sos_alert.audio_file:
            try:
                file_size = sos_alert.audio_file.size
                
                SOSMediaLog.objects.create(
                    sos_alert=sos_alert,
                    media_type='audio',
                    file_path=sos_alert.audio_file.name,
                    file_size=file_size,
                    upload_status='uploaded',
                    media_url=sos_alert.audio_file.url,
                    uploaded_at=timezone.now()
                )
                
                logger.info(f"✅ Аудио обработано для SOS {sos_alert_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка обработки аудио: {e}")
        
        # Обработка видео
        if sos_alert.video_file:
            try:
                file_size = sos_alert.video_file.size
                
                SOSMediaLog.objects.create(
                    sos_alert=sos_alert,
                    media_type='video',
                    file_path=sos_alert.video_file.name,
                    file_size=file_size,
                    upload_status='uploaded',
                    media_url=sos_alert.video_file.url,
                    uploaded_at=timezone.now()
                )
                
                logger.info(f"✅ Видео обработано для SOS {sos_alert_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка обработки видео: {e}")
        
        logger.info(f"✅ Медиа обработаны для SOS {sos_alert_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка обработки медиа: {e}")
        return False


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