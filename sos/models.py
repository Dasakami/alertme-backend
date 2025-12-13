from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class SOSAlert(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('resolved', 'Resolved'),
        ('false_alarm', 'False Alarm'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sos_alerts')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_accuracy = models.FloatField(null=True, blank=True)  # in meters
    address = models.TextField(blank=True)
    map_link = models.URLField(max_length=500, blank=True)
    
    audio_file = models.FileField(upload_to='sos/audio/%Y/%m/%d/', blank=True, null=True)
    video_file = models.FileField(upload_to='sos/video/%Y/%m/%d/', blank=True, null=True)
    
    activation_method = models.CharField(max_length=50, choices=[
        ('button', 'Button Press'),
        ('slider', 'Slider'),
        ('voice', 'Voice Command'),
        ('timer', 'Timer Expiry'),
    ], default='button')
    
    notes = models.TextField(blank=True)
    device_info = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('SOS Alert')
        verbose_name_plural = _('SOS Alerts')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"SOS-{self.id} by {self.user.phone_number} - {self.status}"


class SOSNotification(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('read', 'Read'),
    ]

    NOTIFICATION_TYPE_CHOICES = [
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('email', 'Email'),
    ]

    sos_alert = models.ForeignKey(SOSAlert, on_delete=models.CASCADE, related_name='notifications')
    contact = models.ForeignKey('contacts.EmergencyContact', on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    content = models.TextField()
    error_message = models.TextField(blank=True)
    
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('SOS Notification')
        verbose_name_plural = _('SOS Notifications')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} to {self.contact.name} - {self.status}"


class ActivityTimer(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activity_timers')
    duration_minutes = models.IntegerField(verbose_name=_('Duration (minutes)'))
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    check_in_message = models.TextField(blank=True)
    notification_sent = models.BooleanField(default=False)
    sos_alert = models.ForeignKey(SOSAlert, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='timer_alerts')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Activity Timer')
        verbose_name_plural = _('Activity Timers')
        ordering = ['-created_at']

    def __str__(self):
        return f"Timer-{self.id} by {self.user.phone_number} - {self.status}"
    

