from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import SMSVerification, UserDevice
from django.utils import timezone
from datetime import timedelta
from phonenumber_field.serializerfields import PhoneNumberField as PhoneNumberSerializerField

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Регистрация нового пользователя
    
    Требуется только: phone_number, password
    """
    phone_number = PhoneNumberSerializerField(
        help_text='Формат: +996555123456 или 996555123456'
    )
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        min_length=6,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True, 
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ['phone_number', 'password', 'password_confirm', 'email', 'language']

    def validate_phone_number(self, value):
        phone_str = str(value)
        if not phone_str.startswith('+996'):
            raise serializers.ValidationError(
                'Номер должен начинаться с +996 (например: +996555123456)'
            )
        if len(phone_str) != 13:
            raise serializers.ValidationError(
                'Неверный формат номера. Должно быть 9 цифр после +996'
            )
        
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password': 'Пароли не совпадают'
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


class SendSMSSerializer(serializers.Serializer):
    phone_number = PhoneNumberSerializerField(
        help_text='Формат: +996555123456'
    )
    
    def validate_phone_number(self, value):
        phone_str = str(value)
        
        if not phone_str.startswith('+996'):
            raise serializers.ValidationError(
                'Номер должен начинаться с +996'
            )
        
        if len(phone_str) != 13:
            raise serializers.ValidationError(
                'Неверный формат номера'
            )
        
        return value
    
    def create(self, validated_data):
        phone_number = validated_data['phone_number']
        code = '123456'
        
        expires_at = timezone.now() + timedelta(minutes=10)
        SMSVerification.objects.filter(
            phone_number=phone_number,
            is_verified=False
        ).delete()
        
        sms_verification = SMSVerification.objects.create(
            phone_number=phone_number,
            code=code,
            expires_at=expires_at
        )
        
        print(f" ТЕСТОВЫЙ КОД для {phone_number}: {code}")
        print(f" Истекает: {expires_at}")
        
        return sms_verification


class VerifySMSSerializer(serializers.Serializer):
    phone_number = PhoneNumberSerializerField()
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
        fields = [
            'id', 
            'phone_number', 
            'email', 
            'first_name', 
            'last_name', 
            'telegram_username',
            'avatar', 
            'language', 
            'is_phone_verified',
            'is_premium',
            'created_at'
        ]
        read_only_fields = ['id', 'phone_number', 'is_phone_verified', 'is_premium', 'created_at']
    
    def validate_telegram_username(self, value):
        """Валидация Telegram username"""
        if value:
            value = value.lstrip('@')
            if not value.replace('_', '').isalnum():
                raise serializers.ValidationError(
                    'Username может содержать только буквы, цифры и _'
                )
            if len(value) < 5 or len(value) > 32:
                raise serializers.ValidationError(
                    'Username должен быть от 5 до 32 символов'
                )
        
        return value


class UserDeviceSerializer(serializers.ModelSerializer):
    """
    Опционально: для управления устройствами
    Можно не использовать если не нужно
    """
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