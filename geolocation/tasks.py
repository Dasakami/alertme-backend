from django.contrib.auth import get_user_model
from .models import LocationHistory, Geozone, GeozoneEvent
from math import radians, sin, cos, sqrt, atan2

User = get_user_model()


def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000 
    
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), 
                                            float(lat2), float(lon2)])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


def check_geozone_events(user_id, location_id):
    try:
        user = User.objects.get(id=user_id)
        current_location = LocationHistory.objects.get(id=location_id)
        geozones = Geozone.objects.filter(user=user, is_active=True)
        
        for geozone in geozones:
            distance = calculate_distance(
                current_location.latitude,
                current_location.longitude,
                geozone.latitude,
                geozone.longitude
            )
            
            is_inside = distance <= geozone.radius
            last_event = GeozoneEvent.objects.filter(
                user=user,
                geozone=geozone
            ).order_by('-timestamp').first()
            if last_event:
                was_inside = last_event.event_type == 'enter'
                
                if is_inside and not was_inside and geozone.notify_on_enter:
                    event = GeozoneEvent.objects.create(
                        user=user,
                        geozone=geozone,
                        event_type='enter',
                        latitude=current_location.latitude,
                        longitude=current_location.longitude
                    )
                    send_geozone_notification(event.id)
                
                elif not is_inside and was_inside and geozone.notify_on_exit:
                    event = GeozoneEvent.objects.create(
                        user=user,
                        geozone=geozone,
                        event_type='exit',
                        latitude=current_location.latitude,
                        longitude=current_location.longitude
                    )
                    send_geozone_notification(event.id)
            else:
                if is_inside and geozone.notify_on_enter:
                    event = GeozoneEvent.objects.create(
                        user=user,
                        geozone=geozone,
                        event_type='enter',
                        latitude=current_location.latitude,
                        longitude=current_location.longitude
                    )
                    send_geozone_notification(event.id)
        
        return True
    except Exception as e:
        print(f"Error checking geozone events: {e}")
        return False


def send_geozone_notification(event_id):
    try:
        event = GeozoneEvent.objects.get(id=event_id)
        geozone = event.geozone
        contacts = geozone.emergency_contacts.filter(is_active=True)
        
        if not contacts.exists():
            from contacts.models import EmergencyContact
            contacts = EmergencyContact.objects.filter(
                user=event.user,
                is_active=True
            )
        for contact in contacts:
            message = _generate_geozone_message(event)
            
            from notifications.sms_service import SMSService
            from sos.models import SOSNotification
            
            notif = SOSNotification.objects.create(
                sos_alert=None,
                contact=contact,
                notification_type='sms',
                content=message
            )
            sms_service = SMSService()
            success = sms_service.send_sms(
                to_phone=str(contact.phone_number),
                message=message
            )
            
            if success:
                notif.status = 'sent'
            else:
                notif.status = 'failed'
            notif.save()
        
        event.notification_sent = True
        event.save()
        
        return True
    except Exception as e:
        print(f"Error sending geozone notification: {e}")
        return False


def _generate_geozone_message(event):
    """Generate notification message for geozone event"""
    user = event.user
    geozone = event.geozone
    
    if event.event_type == 'enter':
        message = f"📍 {user.phone_number} вошел в зону '{geozone.name}'"
    else:
        message = f"📍 {user.phone_number} вышел из зоны '{geozone.name}'"
    
    message += f"\n\nТип зоны: {geozone.get_zone_type_display()}"
    message += f"\nВремя: {event.timestamp.strftime('%H:%M, %d.%m.%Y')}"
    
    return message


def cleanup_old_location_history():
    """Clean up location history older than 90 days"""
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=90)
    
    deleted_count = LocationHistory.objects.filter(
        timestamp__lt=cutoff_date
    ).delete()[0]
    
    return deleted_count