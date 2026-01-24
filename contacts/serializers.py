from rest_framework import serializers
from .models import EmergencyContact, ContactGroup
from django.conf import settings


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ['id', 'name', 'phone_number', 'email', 'relation', 
                 'is_primary', 'is_active', 'notification_preferences',
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        user = self.context['request'].user
    
        if not self.instance:  
            existing_contacts = EmergencyContact.objects.filter(
                user=user,
                is_active=True
            ).count()
            
            try:
                subscription = user.subscription
                max_contacts = subscription.plan.max_contacts
            except:
                max_contacts = settings.MAX_FREE_CONTACTS
            
            if existing_contacts >= max_contacts:
                raise serializers.ValidationError(
                    f'You have reached the maximum number of contacts ({max_contacts}). '
                    'Upgrade to Premium for unlimited contacts.'
                )
        
        return attrs


class ContactGroupSerializer(serializers.ModelSerializer):
    contacts = EmergencyContactSerializer(many=True, read_only=True)
    contact_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = ContactGroup
        fields = ['id', 'name', 'description', 'contacts', 'contact_ids',
                 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        contact_ids = validated_data.pop('contact_ids', [])
        group = ContactGroup.objects.create(**validated_data)
        
        if contact_ids:
            contacts = EmergencyContact.objects.filter(
                id__in=contact_ids,
                user=self.context['request'].user
            )
            group.contacts.set(contacts)
        
        return group
    
    def update(self, instance, validated_data):
        contact_ids = validated_data.pop('contact_ids', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if contact_ids is not None:
            contacts = EmergencyContact.objects.filter(
                id__in=contact_ids,
                user=self.context['request'].user
            )
            instance.contacts.set(contacts)
        
        return instance