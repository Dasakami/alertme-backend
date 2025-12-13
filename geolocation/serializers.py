from rest_framework import serializers
from .models import LocationHistory, Geozone, GeozoneEvent, SharedLocation
from contacts.serializers import EmergencyContactSerializer


class LocationHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationHistory
        fields = ['id', 'latitude', 'longitude', 'accuracy', 'altitude',
                 'speed', 'heading', 'address', 'activity_type',
                 'battery_level', 'timestamp', 'created_at']
        read_only_fields = ['id', 'created_at']


class GeozoneSerializer(serializers.ModelSerializer):
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)
    contact_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Geozone
        fields = ['id', 'name', 'description', 'zone_type', 'latitude',
                 'longitude', 'radius', 'polygon_coordinates',
                 'notify_on_enter', 'notify_on_exit', 'is_active',
                 'emergency_contacts', 'contact_ids', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        user = self.context['request'].user
        
        if not self.instance:  
            try:
                subscription = user.subscription
                if not subscription.plan.geozones_enabled:
                    raise serializers.ValidationError(
                        'Geozones feature requires Premium subscription'
                    )
            except:
                raise serializers.ValidationError(
                    'Geozones feature requires Premium subscription'
                )
        
        return attrs
    
    def create(self, validated_data):
        contact_ids = validated_data.pop('contact_ids', [])
        geozone = Geozone.objects.create(**validated_data)
        
        if contact_ids:
            from contacts.models import EmergencyContact
            contacts = EmergencyContact.objects.filter(
                id__in=contact_ids,
                user=self.context['request'].user
            )
            geozone.emergency_contacts.set(contacts)
        
        return geozone


class GeozoneEventSerializer(serializers.ModelSerializer):
    geozone_name = serializers.CharField(source='geozone.name', read_only=True)
    
    class Meta:
        model = GeozoneEvent
        fields = ['id', 'geozone', 'geozone_name', 'event_type',
                 'latitude', 'longitude', 'notification_sent', 'timestamp']
        read_only_fields = ['id', 'notification_sent', 'timestamp']


class SharedLocationSerializer(serializers.ModelSerializer):
    shared_with = EmergencyContactSerializer(read_only=True)
    shared_with_id = serializers.IntegerField(write_only=True)
    share_url = serializers.SerializerMethodField()
    time_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = SharedLocation
        fields = ['id', 'shared_with', 'shared_with_id', 'share_token',
                 'share_url', 'duration_minutes', 'start_time', 'end_time',
                 'status', 'time_remaining', 'created_at']
        read_only_fields = ['id', 'share_token', 'start_time', 'end_time',
                           'created_at']
    
    def get_share_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(
                f'/api/shared-locations/track-by-token/?token={obj.share_token}'
            )
        return None
    
    def get_time_remaining(self, obj):
        if obj.status == 'active':
            from django.utils import timezone
            remaining = (obj.end_time - timezone.now()).total_seconds()
            return max(0, int(remaining))
        return 0