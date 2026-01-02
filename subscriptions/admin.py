from django.contrib import admin
from .models import (
	SubscriptionPlan, UserSubscription, PaymentTransaction,
	Feature, ActivationCode
)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
	list_display = ('name', 'plan_type', 'price_monthly', 'is_active', 'created_at')
	search_fields = ('name', 'plan_type')


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
	list_display = ('user', 'plan', 'status', 'start_date', 'end_date')
	search_fields = ('user__phone_number', 'plan__name')
	raw_id_fields = ('user',)


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
	list_display = ('transaction_id', 'user', 'amount', 'currency', 'status', 'created_at')
	search_fields = ('transaction_id', 'user__phone_number')
	raw_id_fields = ('user',)


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
	list_display = ('name', 'code', 'is_premium', 'is_active')
	search_fields = ('name', 'code')


@admin.register(ActivationCode)
class ActivationCodeAdmin(admin.ModelAdmin):
	list_display = ('code', 'plan', 'is_active', 'is_used', 'created_at', 'expires_at')
	search_fields = ('code', 'plan__name')
	raw_id_fields = ('activated_by',)

