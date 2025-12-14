from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import SMSVerification, UserDevice
from django.utils import timezone
from datetime import timedelta
import random
from django.conf import settings

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['phone_number', 'password', 'password_confirm', 'email', 'language']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password': 'Passwords do not match'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        phone_str = str(validated_data['phone_number']).replace('+', '').replace(' ', '')
        validated_data['username'] = phone_str
        
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


class SendSMSSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    
    def create(self, validated_data):
        phone_number = validated_data['phone_number']
        
        # ═══════════════════════════════════════════════════════════
        # ТЕСТОВЫЙ КОД 123456 (пока нет SMS API)
        # ═══════════════════════════════════════════════════════════
        code = '123456'  # ТЕСТОВЫЙ КОД
        
        # В продакшене будет:
        # code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        expires_at = timezone.now() + timedelta(minutes=10)
        
        # Удаляем старые неверифицированные коды для этого номера
        SMSVerification.objects.filter(
            phone_number=phone_number,
            is_verified=False
        ).delete()
        
        sms_verification = SMSVerification.objects.create(
            phone_number=phone_number,
            code=code,
            expires_at=expires_at
        )
        
        print(f"✅ ТЕСТОВЫЙ КОД для {phone_number}: {code}")
        print(f"⏰ Истекает: {expires_at}")
        
        return sms_verification


class VerifySMSSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        phone_number = attrs['phone_number']
        code = attrs['code']
        
        try:
            sms_verification = SMSVerification.objects.filter(
                phone_number=phone_number,
                code=code,
                is_verified=False,
                expires_at__gt=timezone.now()
            ).latest('created_at')
        except SMSVerification.DoesNotExist:
            raise serializers.ValidationError('Неверный или истекший код')
        
        attrs['sms_verification'] = sms_verification
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'email', 'first_name', 'last_name', 
                  'avatar', 'language', 'is_phone_verified', 'created_at']
        read_only_fields = ['id', 'is_phone_verified', 'created_at']


class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = ['id', 'device_id', 'device_type', 'fcm_token', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        user = self.context['request'].user
        device_id = validated_data['device_id']

        device, created = UserDevice.objects.update_or_create(
            user=user,
            device_id=device_id,
            defaults=validated_data
        )
        return device

