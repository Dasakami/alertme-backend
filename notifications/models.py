from django.db import models
from django.conf import settings
from django.utils import timezone

class TelegramUser(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='telegram_profile'
    )
    chat_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Telegram User'
        verbose_name_plural = 'Telegram Users'
    
    def __str__(self):
        return f"@{self.username or self.chat_id}"


class MediaAccessToken(models.Model):
    token = models.CharField(max_length=255, unique=True, db_index=True)
    sos_alert = models.ForeignKey(
        'sos.SOSAlert',
        on_delete=models.CASCADE,
        related_name='access_tokens'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='media_tokens'
    )
    
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    accessed_count = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Media Access Token'
        verbose_name_plural = 'Media Access Tokens'
        indexes = [
            models.Index(fields=['token', 'expires_at']),
        ]
    
    def __str__(self):
        return f"{self.token[:10]}... for SOS {self.sos_alert_id}"
    
    def is_valid(self) -> bool:
        return self.expires_at > timezone.now()


class SOSMediaLog(models.Model):
    sos_alert = models.ForeignKey(
        'sos.SOSAlert',
        on_delete=models.CASCADE,
        related_name='media_logs'
    )
    
    MEDIA_TYPE_CHOICES = [
        ('audio', 'Audio'),
        ('video', 'Video'),
    ]
    
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    file_path = models.CharField(max_length=500)
    file_size = models.IntegerField()  
    duration_seconds = models.IntegerField(null=True, blank=True)
    
    upload_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('uploaded', 'Uploaded'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    
    media_url = models.URLField(max_length=500, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'SOS Media Log'
        verbose_name_plural = 'SOS Media Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_media_type_display()} - SOS {self.sos_alert_id}"
