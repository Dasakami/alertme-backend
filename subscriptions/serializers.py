from rest_framework import serializers
from .models import SubscriptionPlan, UserSubscription, PaymentTransaction,ActivationCode


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'plan_type', 'description', 'price_monthly',
                 'price_yearly', 'features', 'max_contacts', 'geozones_enabled',
                 'location_history_enabled']


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    days_remaining = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSubscription
        fields = ['id', 'plan', 'status', 'payment_period', 'start_date',
                 'end_date', 'auto_renew', 'days_remaining', 'is_active',
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_days_remaining(self, obj):
        if obj.status == 'active':
            from django.utils import timezone
            remaining = (obj.end_date - timezone.now()).days
            return max(0, remaining)
        return 0
    
    def get_is_active(self, obj):
        return obj.is_premium()


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = ['id', 'amount', 'currency', 'payment_method',
                 'transaction_id', 'status', 'created_at', 'completed_at']
        read_only_fields = ['id', 'transaction_id', 'status', 
                           'created_at', 'completed_at']


class SubscribeSerializer(serializers.Serializer):
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
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    
    class Meta:
        model = ActivationCode
        fields = ['code', 'plan_name', 'is_used', 'expires_at', 'created_at']
        read_only_fields = fields