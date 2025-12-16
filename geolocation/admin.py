from django.contrib import admin
from django.utils.html import format_html
from .models import LocationHistory, Geozone, GeozoneEvent, SharedLocation


@admin.register(LocationHistory)
class LocationHistoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_phone', 'coordinates', 'accuracy', 'activity_type',
                    'battery_level', 'timestamp']
    list_filter = ['activity_type', 'timestamp', 'created_at']
    search_fields = ['user__phone_number', 'address']
    readonly_fields = ['created_at', 'map_display']
    ordering = ['-timestamp']
    
    raw_id_fields = ['user']
    
    fieldsets = (
        ('Пользователь', {
            'fields': ('user',)
        }),
        ('Координаты', {
            'fields': ('latitude', 'longitude', 'accuracy', 'altitude', 'map_display')
        }),
        ('Движение', {
            'fields': ('speed', 'heading', 'activity_type')
        }),
        ('Дополнительно', {
            'fields': ('address', 'battery_level', 'timestamp')
        }),
        ('Системная информация', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'Телефон'
    
    def coordinates(self, obj):
        return f"{obj.latitude}, {obj.longitude}"
    coordinates.short_description = 'Координаты'
    
    def map_display(self, obj):
        if obj.latitude and obj.longitude:
            return format_html(
                '<a href="https://go.2gis.com/show_point?lat={}&lon={}" target="_blank">'
                'Открыть на карте</a>',
                obj.latitude, obj.longitude
            )
        return '-'
    map_display.short_description = 'Карта'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(Geozone)
class GeozoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'user_phone', 'zone_type_badge', 'radius', 
                    'is_active', 'created_at']
    list_filter = ['zone_type', 'is_active', 'notify_on_enter', 
                   'notify_on_exit', 'created_at']
    search_fields = ['name', 'user__phone_number', 'description']
    readonly_fields = ['created_at', 'updated_at', 'map_display']
    ordering = ['-created_at']
    
    raw_id_fields = ['user']
    filter_horizontal = ['emergency_contacts']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'name', 'description', 'zone_type', 'is_active')
        }),
        ('Геометрия', {
            'fields': ('latitude', 'longitude', 'radius', 'polygon_coordinates', 
                      'map_display')
        }),
        ('Уведомления', {
            'fields': ('notify_on_enter', 'notify_on_exit', 'emergency_contacts')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'Телефон'
    
    def zone_type_badge(self, obj):
        colors = {
            'safe': 'green',
            'dangerous': 'red',
            'custom': 'blue'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            colors.get(obj.zone_type, 'gray'),
            obj.get_zone_type_display()
        )
    zone_type_badge.short_description = 'Тип зоны'
    
    def map_display(self, obj):
        """Отображение ссылки на карту в админке"""
        if obj.latitude and obj.longitude:
            return format_html(
                '<a href="https://www.google.com/maps/search/?api=1&query={},{}" target="_blank">'
                'Открыть на Google Maps</a>',
                obj.latitude, obj.longitude
            )
        return '-'
    map_display.short_description = 'Карта'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user').prefetch_related('emergency_contacts')


@admin.register(GeozoneEvent)
class GeozoneEventAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_phone', 'geozone_name', 'event_type_badge', 
                    'notification_sent', 'timestamp']
    list_filter = ['event_type', 'notification_sent', 'timestamp']
    search_fields = ['user__phone_number', 'geozone__name']
    readonly_fields = ['user', 'geozone', 'event_type', 'latitude', 'longitude',
                       'timestamp', 'map_display']
    ordering = ['-timestamp']
    
    raw_id_fields = ['user', 'geozone']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'geozone', 'event_type')
        }),
        ('Локация', {
            'fields': ('latitude', 'longitude', 'map_display')
        }),
        ('Уведомления', {
            'fields': ('notification_sent', 'timestamp')
        }),
    )
    
    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'Телефон'
    
    def geozone_name(self, obj):
        return obj.geozone.name
    geozone_name.short_description = 'Геозона'
    
    def event_type_badge(self, obj):
        colors = {
            'enter': 'green',
            'exit': 'orange'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            colors.get(obj.event_type, 'gray'),
            obj.get_event_type_display()
        )
    event_type_badge.short_description = 'Событие'
    
    def map_display(self, obj):
        if obj.latitude and obj.longitude:
            return format_html(
                '<a href="https://go.2gis.com/show_point?lat={}&lon={}" target="_blank">'
                'Открыть на карте</a>',
                obj.latitude, obj.longitude
            )
        return '-'
    map_display.short_description = 'Карта'
    
    def has_add_permission(self, request):
        return False
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'geozone')


@admin.register(SharedLocation)
class SharedLocationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_phone', 'shared_with_name', 'status_badge',
                    'duration_minutes', 'start_time', 'end_time']
    list_filter = ['status', 'created_at']
    search_fields = ['user__phone_number', 'shared_with__name', 'share_token']
    readonly_fields = ['user', 'shared_with', 'share_token', 'start_time', 
                       'end_time', 'created_at', 'updated_at', 'share_link']
    ordering = ['-created_at']
    
    raw_id_fields = ['user', 'shared_with']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'shared_with', 'status')
        }),
        ('Настройки доступа', {
            'fields': ('share_token', 'share_link', 'duration_minutes')
        }),
        ('Временные метки', {
            'fields': ('start_time', 'end_time', 'created_at', 'updated_at')
        }),
    )
    
    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'Пользователь'
    
    def shared_with_name(self, obj):
        return f"{obj.shared_with.name} ({obj.shared_with.phone_number})"
    shared_with_name.short_description = 'Делится с'
    
    def status_badge(self, obj):
        colors = {
            'active': 'green',
            'expired': 'gray',
            'cancelled': 'red'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'
    
    def share_link(self, obj):
        if obj.share_token:
            link = f"/api/shared-locations/track-by-token/?token={obj.share_token}"
            return format_html(
                '<a href="{}" target="_blank">Открыть ссылку</a><br>'
                '<input type="text" value="{}" readonly style="width: 100%;">',
                link, link
            )
        return '-'
    share_link.short_description = 'Ссылка для отслеживания'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'shared_with')