from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from datetime import timedelta
from .models import SubscriptionPlan, UserSubscription, PaymentTransaction
from .serializers import (SubscriptionPlanSerializer, UserSubscriptionSerializer,
                         PaymentTransactionSerializer, SubscribeSerializer)
import uuid


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [AllowAny]
    queryset = SubscriptionPlan.objects.filter(is_active=True)


class UserSubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = UserSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserSubscription.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current subscription"""
        try:
            subscription = UserSubscription.objects.get(user=request.user)
            serializer = self.get_serializer(subscription)
            return Response(serializer.data)
        except UserSubscription.DoesNotExist:
            return Response({
                'detail': 'No active subscription',
                'plan': 'free'
            })

    @action(detail=False, methods=['post'])
    def subscribe(self, request):
        """Subscribe to a plan"""
        serializer = SubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        plan = serializer.validated_data['plan']
        payment_period = serializer.validated_data['payment_period']
        payment_method = serializer.validated_data['payment_method']
        
        # Calculate dates
        start_date = timezone.now()
        if payment_period == 'monthly':
            end_date = start_date + timedelta(days=30)
            amount = plan.price_monthly
        else:
            end_date = start_date + timedelta(days=365)
            amount = plan.price_yearly
        
        # Create or update subscription
        subscription, created = UserSubscription.objects.update_or_create(
            user=request.user,
            defaults={
                'plan': plan,
                'status': 'pending',
                'payment_period': payment_period,
                'start_date': start_date,
                'end_date': end_date,
            }
        )
        
        # Create payment transaction
        transaction = PaymentTransaction.objects.create(
            user=request.user,
            subscription=subscription,
            amount=amount,
            payment_method=payment_method,
            transaction_id=str(uuid.uuid4()),
            status='pending'
        )
        
        return Response({
            'subscription': UserSubscriptionSerializer(subscription).data,
            'payment': PaymentTransactionSerializer(transaction).data,
            'payment_url': f'/api/payments/{transaction.id}/process/'
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel subscription"""
        subscription = self.get_object()
        subscription.auto_renew = False
        subscription.save()
        
        return Response({
            'detail': 'Subscription will not renew after current period',
            'end_date': subscription.end_date
        })


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PaymentTransaction.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Process payment (mock implementation)"""
        payment = self.get_object()
        
        if payment.status != 'pending':
            return Response(
                {'error': 'Payment already processed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # In production, integrate with real payment gateway
        # For now, simulate successful payment
        payment.status = 'completed'
        payment.completed_at = timezone.now()
        payment.save()
        
        # Activate subscription
        subscription = payment.subscription
        subscription.status = 'active'
        subscription.save()
        
        return Response({
            'detail': 'Payment successful',
            'payment': self.get_serializer(payment).data,
            'subscription': UserSubscriptionSerializer(subscription).data
        })

    @action(detail=True, methods=['post'])
    def webhook(self, request, pk=None):
        """Webhook for payment provider callbacks"""
        # Implement payment provider webhook logic here
        # This would verify the webhook signature and update payment status
        pass