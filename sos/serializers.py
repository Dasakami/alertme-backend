from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import SOSAlert, ActivityTimer, SOSNotification
from contacts.serializers import EmergencyContactSerializer


class SOSNotificationSerializer(serializers.ModelSerializer):
    contact = EmergencyContactSerializer(read_only=True)
    
    class Meta:
        model = SOSNotification
        fields = ['id', 'contact', 'notification_type', 'status', 'content',
                 'sent_at', 'delivered_at', 'read_at', 'error_message']
        read_only_fields = ['id', 'sent_at', 'delivered_at', 'read_at']


class SOSAlertSerializer(serializers.ModelSerializer):
    notifications = SOSNotificationSerializer(many=True, read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = SOSAlert
        fields = ['id', 'user', 'user_phone', 'status', 'latitude', 'longitude',
                 'location_accuracy', 'address', 'map_link', 'audio_file', 'video_file',
                 'activation_method', 'notes', 'device_info', 'notifications',
                 'created_at', 'updated_at', 'resolved_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'resolved_at']


class SOSAlertCreateSerializer(serializers.ModelSerializer):
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    location_accuracy = serializers.FloatField(required=False, allow_null=True)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    location_accuracy = serializers.FloatField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = SOSAlert
        fields = ['latitude', 'longitude', 'location_accuracy', 'address',
                 'audio_file', 'video_file', 'activation_method', 'notes', 'device_info']
    
    def validate_latitude(self, value):
        if value is not None:
            try:
                lat = float(value)
                if not (-90 <= lat <= 90):
                    raise serializers.ValidationError('Широта должна быть между -90 и 90')
            except (TypeError, ValueError):
                raise serializers.ValidationError('Неверный формат координаты широты')
        return value
    
    def validate_longitude(self, value):
        if value is not None:
            try:
                lon = float(value)
                if not (-180 <= lon <= 180):
                    raise serializers.ValidationError('Долгота должна быть между -180 и 180')
            except (TypeError, ValueError):
                raise serializers.ValidationError('Неверный формат координаты долготы')
        return value
    
    def create(self, validated_data):
        if validated_data.get('latitude') and validated_data.get('longitude'):
            lat = validated_data['latitude']
            lng = validated_data['longitude']
            validated_data['map_link'] = (
                f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
            )
        
        if 'notes' not in validated_data or validated_data['notes'] is None:
            validated_data['notes'] = ''
        
        return super().create(validated_data)


class SOSStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=SOSAlert.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)


class ActivityTimerSerializer(serializers.ModelSerializer):
    time_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = ActivityTimer
        fields = ['id', 'duration_minutes', 'start_time', 'end_time', 'status',
                 'check_in_message', 'time_remaining', 'created_at']
        read_only_fields = ['id', 'start_time', 'end_time', 'created_at']
    
    @extend_schema_field(serializers.IntegerField)  
    def get_time_remaining(self, obj) -> int:
        if obj.status == 'active':
            from django.utils import timezone
            remaining = (obj.end_time - timezone.now()).total_seconds()
            return max(0, int(remaining))
        return 0