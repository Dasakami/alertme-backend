from django.contrib import admin
from .models import TelegramUser


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