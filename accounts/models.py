from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.utils.translation import gettext_lazy as _
import uuid


class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError(_('The Phone Number must be set'))
        
        # Автоматически генерируем username как UUID
        if 'username' not in extra_fields or not extra_fields.get('username'):
            extra_fields['username'] = str(uuid.uuid4())
        
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractUser):
    """
    Кастомная модель пользователя
    
    ГЛАВНОЕ ПОЛЕ: phone_number (для авторизации)
    username: автоматически генерируется как UUID (не используется пользователем)
    telegram_username: пользователь вводит сам в настройках для SOS уведомлений
    """
    
    # Username существует (требование Django), но генерируется автоматически
    username = models.CharField(
        max_length=150, 
        unique=True, 
        null=True, 
        blank=True,
        help_text='Автоматически генерируется, не используется пользователем'
    )
    
    # ГЛАВНОЕ ПОЛЕ для авторизации
    phone_number = PhoneNumberField(
        unique=True, 
        verbose_name=_('Phone Number'),
        help_text='Формат: +996XXXXXXXXX'
    )
    
    # Опциональные поля
    email = models.EmailField(blank=True, null=True, verbose_name=_('Email'))
    
    # НОВОЕ: Telegram username для SOS уведомлений
    telegram_username = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Telegram Username',
        help_text='Ваш @username в Telegram (без @). Используется для SOS уведомлений.'
    )
    
    is_phone_verified = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    language = models.CharField(
        max_length=2, 
        choices=[('ru', 'Russian'), ('ky', 'Kyrgyz')], 
        default='ru'
    )
    
    # FCM токен для push уведомлений
    fcm_token = models.TextField(
        blank=True, 
        null=True, 
        verbose_name='Firebase Token'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Поле для авторизации
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []
    
    objects = CustomUserManager()

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        return str(self.phone_number)
    
    def save(self, *args, **kwargs):
        # Автоматически генерируем username если его нет
        if not self.username:
            self.username = str(uuid.uuid4())
        super().save(*args, **kwargs)


class SMSVerification(models.Model):
    phone_number = PhoneNumberField()
    code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('SMS Verification')
        verbose_name_plural = _('SMS Verifications')

    def __str__(self):
        return f"{self.phone_number} - {self.code}"


class UserDevice(models.Model):
    """
    Опционально: для управления устройствами и push уведомлениями
    Можно удалить если не используется
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    device_id = models.CharField(max_length=255, unique=True)
    device_type = models.CharField(
        max_length=50, 
        choices=[('android', 'Android'), ('ios', 'iOS')]
    )
    fcm_token = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('User Device')
        verbose_name_plural = _('User Devices')

    def __str__(self):
        return f"{self.user.phone_number} - {self.device_type}"