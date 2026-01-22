from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import (
    SubscriptionPlan, UserSubscription, PaymentTransaction,
    Feature, ActivationCode, BotSettings
)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_type', 'price_monthly', 'price_stars_display', 'is_active', 'created_at')
    search_fields = ('name', 'plan_type')
    list_filter = ('is_active', 'plan_type')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'plan_type', 'description', 'is_active')
        }),
        ('Цены', {
            'fields': ('price_monthly', 'price_yearly', 'price_stars'),
            'description': 'price_stars - цена в Telegram Stars'
        }),
        ('Возможности', {
            'fields': ('max_contacts', 'geozones_enabled', 'location_history_enabled', 'features')
        }),
    )
    
    def price_stars_display(self, obj):
        return format_html('<b>⭐ {}</b>', obj.price_stars)
    price_stars_display.short_description = 'Price (Stars)'


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status_colored', 'start_date', 'end_date', 'is_premium_display')
    search_fields = ('user__phone_number', 'plan__name')
    list_filter = ('status', 'plan', 'payment_period')
    raw_id_fields = ('user',)
    date_hierarchy = 'created_at'
    
    def status_colored(self, obj):
        colors = {
            'active': 'green',
            'expired': 'red',
            'cancelled': 'orange',
            'pending': 'blue'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'
    
    def is_premium_display(self, obj):
        if obj.is_premium():
            return format_html('<span style="color: green;">✓ Premium</span>')
        return format_html('<span style="color: gray;">Free</span>')
    is_premium_display.short_description = 'Premium'


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'user', 'amount', 'currency', 'payment_method', 'status_colored', 'created_at')
    search_fields = ('transaction_id', 'user__phone_number', 'telegram_payment_charge_id')
    list_filter = ('status', 'payment_method', 'currency', 'created_at')
    raw_id_fields = ('user', 'subscription')
    date_hierarchy = 'created_at'
    readonly_fields = ('transaction_id', 'telegram_payment_charge_id', 'created_at', 'completed_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'subscription', 'transaction_id', 'status')
        }),
        ('Платеж', {
            'fields': ('amount', 'currency', 'payment_method')
        }),
        ('Telegram Stars', {
            'fields': ('telegram_payment_charge_id', 'telegram_user_id'),
            'classes': ('collapse',)
        }),
        ('Дополнительно', {
            'fields': ('provider_response', 'error_message', 'created_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_colored(self, obj):
        colors = {
            'completed': 'green',
            'pending': 'orange',
            'failed': 'red',
            'refunded': 'blue'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_premium', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_premium', 'is_active')


@admin.register(ActivationCode)
class ActivationCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'plan', 'is_test_display', 'status_display', 'telegram_user_id', 'created_at', 'expires_at')
    search_fields = ('code', 'plan__name', 'telegram_user_id', 'activated_by__phone_number')
    list_filter = ('is_active', 'is_used', 'is_test', 'plan', 'created_at')
    raw_id_fields = ('activated_by', 'payment_transaction')
    date_hierarchy = 'created_at'
    readonly_fields = ('code', 'activated_at', 'created_at')
    
    fieldsets = (
        ('Код активации', {
            'fields': ('code', 'plan', 'is_test', 'is_active')
        }),
        ('Telegram', {
            'fields': ('telegram_user_id', 'payment_amount', 'payment_transaction')
        }),
        ('Активация', {
            'fields': ('is_used', 'activated_by', 'activated_at')
        }),
        ('Даты', {
            'fields': ('created_at', 'expires_at')
        }),
    )
    
    def is_test_display(self, obj):
        if obj.is_test:
            return format_html('<span style="color: orange; font-weight: bold;">🧪 TEST</span>')
        return format_html('<span style="color: green;">💰 PAID</span>')
    is_test_display.short_description = 'Type'
    
    def status_display(self, obj):
        if obj.is_used:
            return format_html('<span style="color: gray;">✓ Used</span>')
        elif not obj.is_active:
            return format_html('<span style="color: red;">✗ Inactive</span>')
        elif obj.expires_at < timezone.now():
            return format_html('<span style="color: orange;">⏰ Expired</span>')
        else:
            return format_html('<span style="color: green;">✓ Active</span>')
    status_display.short_description = 'Status'


from django.utils import timezone


@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'default_price_stars', 'subscription_days', 'test_mode_enabled', 'updated_at')
    
    fieldsets = (
        ('👥 Администраторы', {
            'fields': ('admin_telegram_ids',),
            'description': 'Укажите Telegram User IDs админов через запятую'
        }),
        ('💰 Настройки цен', {
            'fields': ('default_price_stars', 'subscription_days', 'code_expiration_hours'),
        }),
        ('🧪 Режим работы', {
            'fields': ('test_mode_enabled',),
            'description': 'Тестовый режим позволяет генерировать бесплатные коды'
        }),
        ('📊 Статистика', {
            'fields': ('total_payments_received', 'total_codes_generated', 'total_codes_activated'),
            'classes': ('collapse',),
        }),
    )
    
    def has_add_permission(self, request):
        # Разрешаем создание только если нет записей
        return not BotSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Запрещаем удаление
        return False
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        messages.success(request, '✅ Настройки бота обновлены!')


# Кастомная админка для быстрого обзора
class SubscriptionAdminSite(admin.AdminSite):
    site_header = "AlertMe - Управление подписками"
    site_title = "AlertMe Admin"
    index_title = "Панель управления"