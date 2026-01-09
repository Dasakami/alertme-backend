# sos/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import SOSAlert, SOSNotification, ActivityTimer


@admin.register(SOSAlert)
class SOSAlertAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'user_link',
        'status_badge', 
        'has_media',
        'location_link',
        'created_at',
        'actions_column'
    ]
    list_filter = ['status', 'activation_method', 'created_at']
    search_fields = ['user__phone_number', 'user__first_name', 'user__last_name', 'address']
    readonly_fields = [
        'created_at', 
        'updated_at', 
        'map_preview',
        'media_preview',
        'notification_status'
    ]
    
    fieldsets = (
        ('📋 Основная информация', {
            'fields': ('user', 'status', 'activation_method', 'notes')
        }),
        ('📍 Местоположение', {
            'fields': (
                'latitude', 
                'longitude', 
                'location_accuracy', 
                'address',
                'map_link',
                'map_preview'
            )
        }),
        ('🎬 Медиа файлы', {
            'fields': ('audio_file', 'video_file', 'media_preview')
        }),
        ('📊 Статистика', {
            'fields': ('notification_status', 'created_at', 'updated_at', 'resolved_at')
        }),
    )
    
    def user_link(self, obj):
        """Ссылка на пользователя"""
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.user.phone_number
        )
    user_link.short_description = '👤 Пользователь'
    
    def status_badge(self, obj):
        """Цветной статус"""
        colors = {
            'active': '#dc2626',
            'resolved': '#059669',
            'cancelled': '#6b7280',
            'false_alarm': '#f59e0b',
        }
        color = colors.get(obj.status, '#6b7280')
        
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 4px 12px; border-radius: 12px; font-weight: 600;">'
            '{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = '🔴 Статус'
    
    def has_media(self, obj):
        """Наличие медиа"""
        icons = []
        if obj.audio_file:
            icons.append('🎤')
        if obj.video_file:
            icons.append('🎬')
        return ' '.join(icons) if icons else '—'
    has_media.short_description = '🎬 Медиа'
    
    def location_link(self, obj):
        """Ссылка на карту"""
        if obj.latitude and obj.longitude:
            url = f"https://www.google.com/maps/search/?api=1&query={obj.latitude},{obj.longitude}"
            return format_html(
                '<a href="{}" target="_blank">📍 Карта</a>',
                url
            )
        return '—'
    location_link.short_description = '🗺️ Карта'
    
    def actions_column(self, obj):
        """Кнопки действий"""
        media_url = reverse('media_preview', args=[obj.id])
        
        buttons = [
            f'<a href="{media_url}" target="_blank" '
            f'style="background: #0891b2; color: white; padding: 4px 12px; '
            f'border-radius: 6px; text-decoration: none; margin-right: 5px;">'
            f'🎬 Медиа</a>'
        ]
        
        if obj.latitude and obj.longitude:
            map_url = f"https://www.google.com/maps/search/?api=1&query={obj.latitude},{obj.longitude}"
            buttons.append(
                f'<a href="{map_url}" target="_blank" '
                f'style="background: #059669; color: white; padding: 4px 12px; '
                f'border-radius: 6px; text-decoration: none;">'
                f'🗺️ Карта</a>'
            )
        
        return format_html(' '.join(buttons))
    actions_column.short_description = '⚡ Действия'
    
    def map_preview(self, obj):
        """Превью карты"""
        if obj.latitude and obj.longitude:
            # Embed Google Maps
            map_url = f"https://www.google.com/maps/search/?api=1&query={obj.latitude},{obj.longitude}"
            return format_html(
                '<iframe width="100%" height="300" frameborder="0" style="border:0; border-radius: 8px;" '
                'src="https://www.google.com/maps?q={},{}&output=embed"></iframe>'
                '<br><a href="{}" target="_blank" style="color: #0891b2;">🗺️ Открыть на карте</a>',
                obj.latitude,
                obj.longitude,
                map_url
            )
        return '—'
    map_preview.short_description = '🗺️ Карта'
    
    def media_preview(self, obj):
        """Превью медиа"""
        html = []
        
        if obj.audio_file:
            html.append(
                f'<div style="margin-bottom: 15px;">'
                f'<strong>🎤 Аудио:</strong><br>'
                f'<audio controls style="width: 100%; max-width: 400px;">'
                f'<source src="{obj.audio_file.url}" type="audio/aac">'
                f'</audio><br>'
                f'<a href="{obj.audio_file.url}" download>⬇️ Скачать аудио</a>'
                f'</div>'
            )
        
        if obj.video_file:
            html.append(
                f'<div style="margin-bottom: 15px;">'
                f'<strong>🎬 Видео:</strong><br>'
                f'<video controls style="width: 100%; max-width: 400px;">'
                f'<source src="{obj.video_file.url}" type="video/mp4">'
                f'</video><br>'
                f'<a href="{obj.video_file.url}" download>⬇️ Скачать видео</a>'
                f'</div>'
            )
        
        if not html:
            return '—'
        
        return mark_safe(''.join(html))
    media_preview.short_description = '🎬 Медиа превью'
    
    def notification_status(self, obj):
        """Статус уведомлений"""
        notifications = obj.notifications.all()
        
        if not notifications:
            return '—'
        
        stats = {
            'total': notifications.count(),
            'sent': notifications.filter(status='sent').count(),
            'failed': notifications.filter(status='failed').count(),
        }
        
        html = f"""
        <div style="background: #f9fafb; padding: 15px; border-radius: 8px;">
            <div style="margin-bottom: 10px;">
                <strong>📊 Всего уведомлений:</strong> {stats['total']}
            </div>
            <div style="margin-bottom: 10px;">
                <strong style="color: #059669;">✅ Отправлено:</strong> {stats['sent']}
            </div>
            <div>
                <strong style="color: #dc2626;">❌ Не удалось:</strong> {stats['failed']}
            </div>
        </div>
        """
        
        return mark_safe(html)
    notification_status.short_description = '📊 Уведомления'


@admin.register(SOSNotification)
class SOSNotificationAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'sos_link',
        'contact_info',
        'notification_type',
        'status_badge',
        'sent_at'
    ]
    list_filter = ['notification_type', 'status', 'created_at']
    search_fields = ['contact__name', 'contact__phone_number', 'content']
    readonly_fields = ['created_at', 'sent_at', 'delivered_at', 'read_at']
    
    def sos_link(self, obj):
        """Ссылка на SOS"""
        url = reverse('admin:sos_sosalert_change', args=[obj.sos_alert.id])
        return format_html(
            '<a href="{}">SOS #{}</a>',
            url,
            obj.sos_alert.id
        )
    sos_link.short_description = '🚨 SOS'
    
    def contact_info(self, obj):
        """Информация о контакте"""
        return format_html(
            '<strong>{}</strong><br>{}',
            obj.contact.name,
            obj.contact.phone_number
        )
    contact_info.short_description = '👤 Контакт'
    
    def status_badge(self, obj):
        """Цветной статус"""
        colors = {
            'pending': '#f59e0b',
            'sent': '#059669',
            'delivered': '#0891b2',
            'failed': '#dc2626',
            'read': '#6b7280',
        }
        color = colors.get(obj.status, '#6b7280')
        
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 4px 12px; border-radius: 12px; font-weight: 600;">'
            '{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = '📊 Статус'


@admin.register(ActivityTimer)
class ActivityTimerAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'duration_minutes',
        'status',
        'end_time',
        'notification_sent'
    ]
    list_filter = ['status', 'notification_sent', 'created_at']
    search_fields = ['user__phone_number', 'check_in_message']
    readonly_fields = ['created_at', 'updated_at']