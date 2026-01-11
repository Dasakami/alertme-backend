
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class LocationHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='location_history')
    latitude = models.DecimalField(max_digits=12, decimal_places=8)
    longitude = models.DecimalField(max_digits=12, decimal_places=8)
    accuracy = models.FloatField(help_text=_('Location accuracy in meters'))
    altitude = models.FloatField(null=True, blank=True)
    speed = models.FloatField(null=True, blank=True, help_text=_('Speed in m/s'))
    heading = models.FloatField(null=True, blank=True, help_text=_('Heading in degrees'))
    
    address = models.TextField(blank=True)
    activity_type = models.CharField(max_length=50, blank=True, choices=[
        ('stationary', 'Stationary'),
        ('walking', 'Walking'),
        ('running', 'Running'),
        ('driving', 'Driving'),
    ])
    
    battery_level = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Location History')
        verbose_name_plural = _('Location Histories')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]

    def __str__(self):
        return f"{self.user.phone_number} at {self.timestamp}"


class Geozone(models.Model):
    ZONE_TYPE_CHOICES = [
        ('safe', 'Safe Zone'),
        ('dangerous', 'Dangerous Zone'),
        ('custom', 'Custom Zone'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='geozones')
    name = models.CharField(max_length=255, verbose_name=_('Zone Name'))
    description = models.TextField(blank=True)
    zone_type = models.CharField(max_length=20, choices=ZONE_TYPE_CHOICES, default='safe')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    radius = models.FloatField(help_text=_('Radius in meters'))
    polygon_coordinates = models.JSONField(null=True, blank=True, 
                                          help_text=_('Array of [lat, lng] coordinates'))
    
    notify_on_enter = models.BooleanField(default=True)
    notify_on_exit = models.BooleanField(default=True)
    
    is_active = models.BooleanField(default=True)
    emergency_contacts = models.ManyToManyField('contacts.EmergencyContact', 
                                                blank=True, 
                                                related_name='geozones')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Geozone')
        verbose_name_plural = _('Geozones')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.zone_type})"


class GeozoneEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ('enter', 'Entered Zone'),
        ('exit', 'Exited Zone'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    geozone = models.ForeignKey(Geozone, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=10, choices=EVENT_TYPE_CHOICES)
    
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    notification_sent = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Geozone Event')
        verbose_name_plural = _('Geozone Events')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['geozone', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.user.phone_number} {self.event_type} {self.geozone.name}"


class SharedLocation(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shared_locations')
    shared_with = models.ForeignKey('contacts.EmergencyContact', on_delete=models.CASCADE)
    
    share_token = models.CharField(max_length=64, unique=True)
    duration_minutes = models.IntegerField(help_text=_('Duration of sharing in minutes'))
    
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Shared Location')
        verbose_name_plural = _('Shared Locations')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.phone_number} sharing with {self.shared_with.name}"
 