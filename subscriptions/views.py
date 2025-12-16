from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import (
    SubscriptionPlan, 
    UserSubscription, 
    PaymentTransaction,
    ActivationCode
)
from .serializers import (
    SubscriptionPlanSerializer, 
    UserSubscriptionSerializer,
    PaymentTransactionSerializer, 
    SubscribeSerializer,
    ActivationCodeSerializer
)
import uuid


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [AllowAny]
    queryset = SubscriptionPlan.objects.filter(is_active=True)


@extend_schema_view(
    list=extend_schema(description="Список подписок пользователя"),
    retrieve=extend_schema(description="Детали подписки"),
)
class UserSubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = UserSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    queryset = UserSubscription.objects.none()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return UserSubscription.objects.none()
        return UserSubscription.objects.filter(user=self.request.user)

    @extend_schema(
        description="Получить текущую подписку",
        responses={200: UserSubscriptionSerializer}
    )
    @action(detail=False, methods=['get'])
    def current(self, request):
        try:
            subscription = UserSubscription.objects.get(user=request.user)
            serializer = self.get_serializer(subscription)
            return Response(serializer.data)
        except UserSubscription.DoesNotExist:
            return Response({
                'detail': 'No active subscription',
                'plan': 'free'
            })

    @extend_schema(
        description="Оформить подписку",
        request=SubscribeSerializer,
        responses={201: UserSubscriptionSerializer}
    )
    @action(detail=False, methods=['post'])
    def subscribe(self, request):
        serializer = SubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        plan = serializer.validated_data['plan']
        payment_period = serializer.validated_data['payment_period']
        payment_method = serializer.validated_data['payment_method']
        
        start_date = timezone.now()
        if payment_period == 'monthly':
            end_date = start_date + timedelta(days=30)
            amount = plan.price_monthly
        else:
            end_date = start_date + timedelta(days=365)
            amount = plan.price_yearly
        
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

    @extend_schema(
        description="Отменить подписку",
        responses={200: dict}
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        subscription = self.get_object()
        subscription.auto_renew = False
        subscription.save()
        
        return Response({
            'detail': 'Subscription will not renew after current period',
            'end_date': subscription.end_date
        })


@extend_schema_view(
    list=extend_schema(description="История платежей"),
)
class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentTransactionSerializer
    permission_classes = [IsAuthenticated]
    queryset = PaymentTransaction.objects.none()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PaymentTransaction.objects.none()
        return PaymentTransaction.objects.filter(user=self.request.user)

    @extend_schema(
        description="Обработать платеж",
        responses={200: PaymentTransactionSerializer}
    )
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        payment = self.get_object()
        
        if payment.status != 'pending':
            return Response(
                {'error': 'Payment already processed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment.status = 'completed'
        payment.completed_at = timezone.now()
        payment.save()
        
        subscription = payment.subscription
        subscription.status = 'active'
        subscription.save()
        
        return Response({
            'detail': 'Payment successful',
            'payment': self.get_serializer(payment).data,
            'subscription': UserSubscriptionSerializer(subscription).data
        })


@extend_schema_view(
    activate=extend_schema(
        description="Активировать код подписки",
        request={'application/json': {'type': 'object', 'properties': {'code': {'type': 'string'}}}},
        responses={200: dict, 400: dict, 404: dict}
    ),
    check=extend_schema(
        description="Проверить код без активации",
        request={'application/json': {'type': 'object', 'properties': {'code': {'type': 'string'}}}},
        responses={200: dict, 404: dict}
    )
)
class ActivationCodeViewSet(viewsets.ViewSet):
    """ViewSet для активации кодов из Telegram"""
    permission_classes = [IsAuthenticated]
    serializer_class = ActivationCodeSerializer  # ДОБАВЛЕНО для Swagger
    
    @action(detail=False, methods=['post'])
    def activate(self, request):
        code_str = request.data.get('code', '').strip().upper()
        
        if not code_str:
            return Response(
                {'error': 'Введите код активации'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            activation_code = ActivationCode.objects.get(code=code_str)
            
            if not activation_code.is_valid():
                if activation_code.is_used:
                    return Response(
                        {'error': 'Код уже использован'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                elif timezone.now() >= activation_code.expires_at:
                    return Response(
                        {'error': 'Код истек'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                else:
                    return Response(
                        {'error': 'Код недействителен'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            subscription = activation_code.activate_for_user(request.user)
            
            return Response({
                'success': True,
                'message': f'Premium подписка активирована до {subscription.end_date.strftime("%d.%m.%Y")}',
                'subscription': UserSubscriptionSerializer(subscription).data
            }, status=status.HTTP_200_OK)
            
        except ActivationCode.DoesNotExist:
            return Response(
                {'error': 'Код не найден. Проверьте правильность ввода.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Ошибка активации: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def check(self, request):
        code_str = request.data.get('code', '').strip().upper()
        
        if not code_str:
            return Response(
                {'error': 'Введите код'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            activation_code = ActivationCode.objects.get(code=code_str)
            
            return Response({
                'valid': activation_code.is_valid(),
                'plan': activation_code.plan.name,
                'is_used': activation_code.is_used,
                'expires_at': activation_code.expires_at,
            })
            
        except ActivationCode.DoesNotExist:
            return Response(
                {'valid': False, 'error': 'Код не найден'},
                status=status.HTTP_404_NOT_FOUND
            )


