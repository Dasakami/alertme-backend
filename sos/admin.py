from django.contrib import admin
from .models import SOSAlert, SOSNotification, ActivityTimer


@admin.register(SOSAlert)
class SOSAlertAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'status', 'has_audio', 'has_video', 'created_at', 'resolved_at')
	list_filter = ('status', 'created_at')
	search_fields = ('user__phone_number', 'id', 'address')
	raw_id_fields = ('user',)
	readonly_fields = ('created_at', 'updated_at', 'media_link')
	
	fieldsets = (
		('Основная информация', {
			'fields': ('user', 'status', 'created_at', 'updated_at', 'resolved_at')
		}),
		('Локация', {
			'fields': ('latitude', 'longitude', 'location_accuracy', 'address', 'map_link')
		}),
		('Медиа', {
			'fields': ('audio_file', 'video_file', 'media_link')
		}),
		('Дополнительно', {
			'fields': ('activation_method', 'notes', 'device_info')
		}),
	)
	
	def has_audio(self, obj):
		return bool(obj.audio_file)
	has_audio.short_description = 'Аудио'
	has_audio.boolean = True
	
	def has_video(self, obj):
		return bool(obj.video_file)
	has_video.short_description = 'Видео'
	has_video.boolean = True
	
	def media_link(self, obj):
		if obj.id:
			from django.utils.html import format_html
			return format_html(
				'<a href="/media/sos/{0}/" target="_blank">👁️ Смотреть медиа</a>',
				obj.id
			)
		return '-'
	media_link.short_description = 'Просмотр медиа'


@admin.register(SOSNotification)
class SOSNotificationAdmin(admin.ModelAdmin):
	list_display = ('sos_alert', 'contact', 'notification_type', 'status', 'sent_at')
	list_filter = ('notification_type', 'status', 'created_at')
	search_fields = ('contact__phone_number', 'sos_alert__id')
	raw_id_fields = ('sos_alert', 'contact')


@admin.register(ActivityTimer)
class ActivityTimerAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'status', 'start_time', 'end_time')
	list_filter = ('status', 'created_at')
	search_fields = ('user__phone_number',)
	raw_id_fields = ('user',)
