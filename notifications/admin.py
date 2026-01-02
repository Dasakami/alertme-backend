from django.contrib import admin
from .models import TelegramUser, MediaAccessToken, SOSMediaLog


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'chat_id', 'first_name', 'last_name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['username', 'chat_id', 'first_name', 'last_name', 'phone_number']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Telegram Info', {
            'fields': ('chat_id', 'username', 'first_name', 'last_name')
        }),
        ('App Connection', {
            'fields': ('user', 'phone_number')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(MediaAccessToken)
class MediaAccessTokenAdmin(admin.ModelAdmin):
    list_display = ('token', 'sos_alert', 'user', 'expires_at', 'accessed_count')
    search_fields = ('token', 'user__phone_number', 'sos_alert__id')
    readonly_fields = ('created_at', 'last_accessed')


@admin.register(SOSMediaLog)
class SOSMediaLogAdmin(admin.ModelAdmin):
    list_display = ('sos_alert', 'media_type', 'file_path', 'file_size', 'upload_status', 'created_at')
    list_filter = ('media_type', 'upload_status', 'created_at')
    search_fields = ('sos_alert__id', 'file_path')
    readonly_fields = ('created_at', 'uploaded_at')