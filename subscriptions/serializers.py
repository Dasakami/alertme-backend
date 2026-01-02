from rest_framework import serializers
from .models import SubscriptionPlan, UserSubscription, PaymentTransaction, ActivationCode
from django.utils import timezone


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Сериалайзер для планов подписки"""
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'plan_type', 'description', 'price_monthly',
                 'price_yearly', 'features', 'max_contacts', 'geozones_enabled',
                 'location_history_enabled', 'is_active']


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """Сериалайзер для подписки пользователя"""
    plan = SubscriptionPlanSerializer(read_only=True)
    days_remaining = serializers.SerializerMethodField()
    is_premium = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSubscription
        fields = ['id', 'plan', 'status', 'payment_period', 'start_date',
                 'end_date', 'auto_renew', 'days_remaining', 'is_premium',
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_days_remaining(self, obj):
        """Количество дней до истечения подписки"""
        if obj.status == 'active':
            remaining = (obj.end_date - timezone.now()).days
            return max(0, remaining)
        return 0
    
    def get_is_premium(self, obj):
        """Проверка активности премиум подписки"""
        return obj.is_premium()


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Сериалайзер для истории платежей"""
    class Meta:
        model = PaymentTransaction
        fields = ['id', 'amount', 'currency', 'payment_method',
                 'transaction_id', 'status', 'created_at', 'completed_at']
        read_only_fields = ['id', 'transaction_id', 'status', 
                           'created_at', 'completed_at']


class SubscribeSerializer(serializers.Serializer):
    """Сериалайзер для оформления подписки"""
    plan_id = serializers.IntegerField()
    payment_period = serializers.ChoiceField(
        choices=[('monthly', 'Monthly'), ('yearly', 'Yearly')]
    )
    payment_method = serializers.ChoiceField(
        choices=PaymentTransaction.PAYMENT_METHOD_CHOICES
    )
    
    def validate_plan_id(self, value):
        try:
            plan = SubscriptionPlan.objects.get(id=value, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError('Invalid plan')
        return plan
    
    def validate(self, attrs):
        attrs['plan'] = attrs.pop('plan_id')
        return attrs


class ActivationCodeSerializer(serializers.ModelSerializer):
    """Сериалайзер для кодов активации"""
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    is_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = ActivationCode
        fields = ['code', 'plan_name', 'is_valid', 'is_used', 'expires_at', 'created_at']
        read_only_fields = fields
    
    def get_is_valid(self, obj):
        """Проверка валидности кода"""
        return obj.is_valid()


class ActivationCodeActivateSerializer(serializers.Serializer):
    """Сериалайзер для активации кода"""
    code = serializers.CharField(max_length=20, required=True)
    
    def validate_code(self, value):
        """Валидация кода"""
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError('Code cannot be empty')
        return value
