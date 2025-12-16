from django.db import models
from django.conf import settings


class TelegramUser(models.Model):
    """
    Связь между пользователями приложения и Telegram
    
    Заполняется когда пользователь пишет /start боту
    """
    # Связь с пользователем приложения (опционально)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='telegram_profile'
    )
    
    # Telegram данные
    chat_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    
    # Для контактов (когда добавляют username контакта)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Telegram User'
        verbose_name_plural = 'Telegram Users'
    
    def __str__(self):
        return f"@{self.username or self.chat_id}"