from celery import shared_task
from django.conf import settings
from django.utils import timezone
from .models import SOSAlert, SOSNotification, ActivityTimer
from contacts.models import EmergencyContact
import requests
import json


@shared_task
def send_sos_notifications(sos_alert_id, contact_ids):
    """Send SOS notifications to emergency contacts via SMS, Push, Email"""
    try:
        sos_alert = SOSAlert.objects.get(id=sos_alert_id)
        contacts = EmergencyContact.objects.filter(id__in=contact_ids)
        
        for contact in contacts:
            # Create notification records
            notifications = []
            
            # SMS notification
            sms_notif = SOSNotification.objects.create(
                sos_alert=sos_alert,
                contact=contact,
                notification_type='sms',
                content=_generate_sms_content(sos_alert, contact)
            )
            notifications.append(('sms', sms_notif))
            
            # Push notification
            push_notif = SOSNotification.objects.create(
                sos_alert=sos_alert,
                contact=contact,
                notification_type='push',
                content=_generate_push_content(sos_alert, contact)
            )
            notifications.append(('push', push_notif))
            
            # Email notification (if email exists)
            if contact.email:
                email_notif = SOSNotification.objects.create(
                    sos_alert=sos_alert,
                    contact=contact,
                    notification_type='email',
                    content=_generate_email_content(sos_alert, contact)
                )
                notifications.append(('email', email_notif))
            
            # Send notifications
            for notif_type, notif in notifications:
                if notif_type == 'sms':
                    send_sms_notification.delay(notif.id)
                elif notif_type == 'push':
                    send_push_notification.delay(notif.id)
                elif notif_type == 'email':
                    send_email_notification.delay(notif.id)
        
        return True
    except Exception as e:
        print(f"Error sending SOS notifications: {e}")
        return False


@shared_task
def send_sms_notification(notification_id):
    """Send SMS notification via SMS.kg"""
    try:
        notification = SOSNotification.objects.get(id=notification_id)
        
        if not settings.SMS_API_KEY:
            notification.status = 'failed'
            notification.error_message = 'SMS API not configured'
            notification.save()
            return False
        
        phone = str(notification.contact.phone_number)
        message = notification.content
        
        # SMS.kg API call
        response = requests.post(
            settings.SMS_API_URL,
            json={
                'key': settings.SMS_API_KEY,
                'phone': phone,
                'message': message,
            },
            timeout=10
        )
        
        if response.status_code == 200:
            notification.status = 'sent'
            notification.sent_at = timezone.now()
        else:
            notification.status = 'failed'
            notification.error_message = response.text
        
        notification.save()
        return True
        
    except Exception as e:
        notification.status = 'failed'
        notification.error_message = str(e)
        notification.save()
        return False


@shared_task
def send_push_notification(notification_id):
    """Send push notification via Firebase"""
    try:
        notification = SOSNotification.objects.get(id=notification_id)
        
        # Get user devices for this contact (if they're also app users)
        # This would require matching phone numbers
        # For now, we'll skip this implementation
        
        notification.status = 'sent'
        notification.sent_at = timezone.now()
        notification.save()
        return True
        
    except Exception as e:
        notification.status = 'failed'
        notification.error_message = str(e)
        notification.save()
        return False


@shared_task
def send_email_notification(notification_id):
    """Send email notification"""
    try:
        notification = SOSNotification.objects.get(id=notification_id)
        
        # Use Django's email backend
        from django.core.mail import send_mail
        
        send_mail(
            subject=f'🚨 SOS Alert from {notification.sos_alert.user.phone_number}',
            message=notification.content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.contact.email],
            fail_silently=False,
        )
        
        notification.status = 'sent'
        notification.sent_at = timezone.now()
        notification.save()
        return True
        
    except Exception as e:
        notification.status = 'failed'
        notification.error_message = str(e)
        notification.save()
        return False


@shared_task
def process_sos_media(sos_alert_id):
    """Process uploaded audio/video files"""
    try:
        sos_alert = SOSAlert.objects.get(id=sos_alert_id)
        
        # Here you could:
        # - Compress media files
        # - Generate thumbnails
        # - Extract metadata
        # - Upload to S3 if not already there
        
        return True
    except Exception as e:
        print(f"Error processing SOS media: {e}")
        return False


@shared_task
def check_expired_timers():
    """Check for expired activity timers and trigger SOS alerts"""
    expired_timers = ActivityTimer.objects.filter(
        status='active',
        end_time__lt=timezone.now(),
        notification_sent=False
    )
    
    for timer in expired_timers:
        # Create SOS alert from expired timer
        sos_alert = SOSAlert.objects.create(
            user=timer.user,
            activation_method='timer',
            notes=f'Activity timer expired. Duration: {timer.duration_minutes} minutes'
        )
        
        # Send notifications
        contacts = EmergencyContact.objects.filter(
            user=timer.user,
            is_active=True
        )
        
        if contacts.exists():
            send_sos_notifications.delay(
                sos_alert.id,
                list(contacts.values_list('id', flat=True))
            )
        
        timer.status = 'expired'
        timer.notification_sent = True
        timer.sos_alert = sos_alert
        timer.save()


def _generate_sms_content(sos_alert, contact):
    """Generate SMS message content"""
    user = sos_alert.user
    message = f"🚨 ЭКСТРЕННАЯ ТРЕВОГА!\n\n"
    message += f"{user.phone_number} активировал SOS!\n"
    
    if sos_alert.latitude and sos_alert.longitude:
        # ИЗМЕНЕНО: Google Maps ссылка
        google_maps_url = (
            f"https://www.google.com/maps/search/?api=1"
            f"&query={sos_alert.latitude},{sos_alert.longitude}"
        )
        message += f"\n📍 Локация: {google_maps_url}\n"
    
    message += f"\nВремя: {sos_alert.created_at.strftime('%H:%M, %d.%m.%Y')}"
    
    return message

def _generate_push_content(sos_alert, contact):
    """Generate push notification content"""
    return json.dumps({
        'title': '🚨 SOS Alert',
        'body': f'{sos_alert.user.phone_number} needs help!',
        'data': {
            'sos_alert_id': sos_alert.id,
            'latitude': str(sos_alert.latitude),
            'longitude': str(sos_alert.longitude),
            'map_link': sos_alert.map_link,
        }
    })


def _generate_email_content(sos_alert, contact):
    """Generate email content"""
    user = sos_alert.user
    content = f"Emergency SOS Alert\n\n"
    content += f"User: {user.phone_number}\n"
    content += f"Time: {sos_alert.created_at.strftime('%H:%M, %d %B %Y')}\n\n"
    
    if sos_alert.latitude and sos_alert.longitude:
        content += f"Location: {sos_alert.latitude}, {sos_alert.longitude}\n"
        content += f"Map: {sos_alert.map_link}\n\n"
    
    if sos_alert.notes:
        content += f"Notes: {sos_alert.notes}\n"
    
    return content