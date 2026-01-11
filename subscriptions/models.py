   
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
from django.utils import timezone

class SubscriptionPlan(models.Model):
    PLAN_TYPE_CHOICES = [
        ('free', 'Free'),
        ('personal_premium', 'Personal Premium'),
        ('business', 'Business'),
    ]

    name = models.CharField(max_length=100, verbose_name=_('Plan Name'))
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES, unique=True)
    description = models.TextField(blank=True)
    
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    features = models.JSONField(default=dict)
    max_contacts = models.IntegerField(default=1)
    geozones_enabled = models.BooleanField(default=False)
    location_history_enabled = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Subscription Plan')
        verbose_name_plural = _('Subscription Plans')

    def __str__(self):
        return self.name


class UserSubscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending Payment'),
    ]

    PAYMENT_PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    payment_period = models.CharField(max_length=10, choices=PAYMENT_PERIOD_CHOICES, default='monthly')
    
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    auto_renew = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('User Subscription')
        verbose_name_plural = _('User Subscriptions')

    def __str__(self):
        return f"{self.user.phone_number} - {self.plan.name} ({self.status})"

    def is_premium(self):
        return self.plan.plan_type != 'free' and self.status == 'active'


class PaymentTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('mobile_o', 'O!'),
        ('mobile_mega', 'MegaCom'),
        ('mobile_beeline', 'Beeline'),
        ('card', 'Bank Card'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name='payments')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='KGS')
    
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    provider_response = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Payment Transaction')
        verbose_name_plural = _('Payment Transactions')
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.transaction_id} - {self.amount} {self.currency}"


class Feature(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_premium = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Feature')
        verbose_name_plural = _('Features')

    def __str__(self):
        return self.name
    

class ActivationCode(models.Model):
    """Коды активации подписок"""
    code = models.CharField(max_length=20, unique=True, db_index=True)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name='activation_codes')
    telegram_user_id = models.BigIntegerField(null=True, blank=True)
    payment_amount = models.IntegerField(help_text='Сумма в Telegram Stars')
    is_active = models.BooleanField(default=True, db_index=True)
    is_used = models.BooleanField(default=False, db_index=True)
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='activated_codes'
    )
    activated_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        verbose_name = _('Activation Code')
        verbose_name_plural = _('Activation Codes')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code', 'is_active']),
            models.Index(fields=['is_used', 'expires_at']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.plan.name} ({'USED' if self.is_used else 'ACTIVE'})"
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)
    
    def is_valid(self) -> bool:
        """Проверка валидности кода"""
        return (
            self.is_active and 
            not self.is_used and 
            timezone.now() < self.expires_at
        )
    
    def activate_for_user(self, user):
        """Активация кода для пользователя с проверкой и синхронизацией is_premium"""
        if not self.is_valid():
            if self.is_used:
                raise ValueError('Код уже использован')
            elif timezone.now() >= self.expires_at:
                raise ValueError('Код истек')
            elif not self.is_active:
                raise ValueError('Код деактивирован')
            else:
                raise ValueError('Код недействителен')
        
        existing_subscription = UserSubscription.objects.filter(
            user=user,
            plan=self.plan,
            status='active'
        ).first()
        
        if existing_subscription and existing_subscription.end_date > timezone.now():
            existing_subscription.end_date = existing_subscription.end_date + timedelta(days=30)
            existing_subscription.save(update_fields=['end_date', 'updated_at'])
            subscription = existing_subscription
        else:
            subscription, created = UserSubscription.objects.update_or_create(
                user=user,
                defaults={
                    'plan': self.plan,
                    'status': 'active',
                    'payment_period': 'monthly',
                    'start_date': timezone.now(),
                    'end_date': timezone.now() + timedelta(days=30),
                    'auto_renew': False,
                }
            )
        
        self.is_used = True
        self.activated_by = user
        self.activated_at = timezone.now()
        self.save(update_fields=['is_used', 'activated_by', 'activated_at', 'updated_at'])
        
        user.is_premium = (self.plan.plan_type != 'free' and subscription.status == 'active')
        user.save(update_fields=['is_premium'])
        
        return subscription