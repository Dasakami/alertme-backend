from celery import shared_task
from django.contrib.auth import get_user_model
from .models import LocationHistory, Geozone, GeozoneEvent
from math import radians, sin, cos, sqrt, atan2

User = get_user_model()


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    R = 6371000  # Earth's radius in meters
    
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), 
                                            float(lat2), float(lon2)])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


@shared_task
def check_geozone_events(user_id, location_id):
    """Check if user entered or exited any geozones"""
    try:
        user = User.objects.get(id=user_id)
        current_location = LocationHistory.objects.get(id=location_id)
        
        # Get active geozones for this user
        geozones = Geozone.objects.filter(user=user, is_active=True)
        
        for geozone in geozones:
            distance = calculate_distance(
                current_location.latitude,
                current_location.longitude,
                geozone.latitude,
                geozone.longitude
            )
            
            is_inside = distance <= geozone.radius
            
            # Get last event for this geozone
            last_event = GeozoneEvent.objects.filter(
                user=user,
                geozone=geozone
            ).order_by('-timestamp').first()
            
            # Determine if we need to create an event
            if last_event:
                was_inside = last_event.event_type == 'enter'
                
                if is_inside and not was_inside and geozone.notify_on_enter:
                    # User entered zone
                    event = GeozoneEvent.objects.create(
                        user=user,
                        geozone=geozone,
                        event_type='enter',
                        latitude=current_location.latitude,
                        longitude=current_location.longitude
                    )
                    send_geozone_notification.delay(event.id)
                
                elif not is_inside and was_inside and geozone.notify_on_exit:
                    # User exited zone
                    event = GeozoneEvent.objects.create(
                        user=user,
                        geozone=geozone,
                        event_type='exit',
                        latitude=current_location.latitude,
                        longitude=current_location.longitude
                    )
                    send_geozone_notification.delay(event.id)
            else:
                # First time checking, only create enter event if inside
                if is_inside and geozone.notify_on_enter:
                    event = GeozoneEvent.objects.create(
                        user=user,
                        geozone=geozone,
                        event_type='enter',
                        latitude=current_location.latitude,
                        longitude=current_location.longitude
                    )
                    send_geozone_notification.delay(event.id)
        
        return True
    except Exception as e:
        print(f"Error checking geozone events: {e}")
        return False


@shared_task
def send_geozone_notification(event_id):
    """Send notification for geozone event"""
    try:
        event = GeozoneEvent.objects.get(id=event_id)
        geozone = event.geozone
        
        # Get contacts for this geozone
        contacts = geozone.emergency_contacts.filter(is_active=True)
        
        if not contacts.exists():
            # Use all emergency contacts if no specific ones set
            from contacts.models import EmergencyContact
            contacts = EmergencyContact.objects.filter(
                user=event.user,
                is_active=True
            )
        
        # Send notifications
        for contact in contacts:
            message = _generate_geozone_message(event)
            
            # Import SMS task
            from sos.tasks import send_sms_notification
            from sos.models import SOSNotification
            
            notif = SOSNotification.objects.create(
                sos_alert=None,
                contact=contact,
                notification_type='sms',
                content=message
            )
            send_sms_notification.delay(notif.id)
        
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


@shared_task
def cleanup_old_location_history():
    """Clean up location history older than 90 days"""
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=90)
    
    deleted_count = LocationHistory.objects.filter(
        timestamp__lt=cutoff_date
    ).delete()[0]
    
    return deleted_count