# subscriptions/views.py - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema, extend_schema_view
import uuid
import logging

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

logger = logging.getLogger(__name__)


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
        description="Получить текущую подписку с проверкой срока",
        responses={200: UserSubscriptionSerializer}
    )
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Один запрос для получения статуса подписки"""
        try:
            subscription = UserSubscription.objects.select_related('plan').get(
                user=request.user
            )
            
            # Проверяем статус и обновляем если нужно
            now = timezone.now()
            
            if subscription.status == 'active' and subscription.end_date <= now:
                subscription.status = 'expired'
                subscription.save(update_fields=['status'])
                logger.info(f"✅ Подписка истекла для {request.user.phone_number}")
            
            # Возвращаем единую структуру
            return Response({
                'id': subscription.id,
                'plan': SubscriptionPlanSerializer(subscription.plan).data,
                'status': subscription.status,
                'is_premium': subscription.status == 'active' and subscription.plan.plan_type != 'free',
                'days_remaining': max(0, (subscription.end_date - now).days) if subscription.status == 'active' else 0,
                'end_date': subscription.end_date.isoformat(),
                'payment_period': subscription.payment_period,
                'auto_renew': subscription.auto_renew,
            })
                
        except UserSubscription.DoesNotExist:
            # Нет подписки = Free план
            return Response({
                'id': None,
                'plan': {'plan_type': 'free', 'name': 'Free'},
                'status': 'free',
                'is_premium': False,
                'days_remaining': 0,
                'end_date': None,
                'payment_period': None,
                'auto_renew': False,
            })
        except Exception as e:
            logger.error(f"❌ Ошибка проверки подписки: {e}", exc_info=True)
            return Response(
                {'error': 'Ошибка проверки подписки'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
        subscription.save(update_fields=['auto_renew'])
        
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
        payment.save(update_fields=['status', 'completed_at'])
        
        subscription = payment.subscription
        subscription.status = 'active'
        subscription.save(update_fields=['status'])
        
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
    serializer_class = ActivationCodeSerializer
    
    @action(detail=False, methods=['post'])
    def activate(self, request):
        """Активация кода с созданием/обновлением подписки"""
        code_str = request.data.get('code', '').strip().upper()
        
        if not code_str:
            return Response(
                {'success': False, 'error': 'Введите код активации'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            activation_code = ActivationCode.objects.select_related('plan').get(code=code_str)
            
            # Проверка валидности
            if not activation_code.is_valid():
                if activation_code.is_used:
                    error = 'Код уже использован'
                elif timezone.now() >= activation_code.expires_at:
                    error = 'Код истек'
                else:
                    error = 'Код недействителен'
                    
                return Response(
                    {'success': False, 'error': error},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Активируем код
            try:
                subscription = activation_code.activate_for_user(request.user)
                subscription.refresh_from_db()
                
                logger.info(
                    f"✅ Код {code_str} активирован для {request.user.phone_number}. "
                    f"Подписка до {subscription.end_date}"
                )
                
                return Response({
                    'success': True,
                    'message': f'Premium подписка активирована до {subscription.end_date.strftime("%d.%m.%Y")}',
                    'subscription': {
                        'id': subscription.id,
                        'plan': subscription.plan.name,
                        'status': subscription.status,
                        'is_premium': True,
                        'days_remaining': (subscription.end_date - timezone.now()).days,
                        'end_date': subscription.end_date.isoformat(),
                    }
                }, status=status.HTTP_200_OK)
                
            except ValueError as e:
                return Response(
                    {'success': False, 'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        except ActivationCode.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Код не найден. Проверьте правильность ввода.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"❌ Ошибка активации кода: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка активации: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def check(self, request):
        """Проверка кода без активации"""
        code_str = request.data.get('code', '').strip().upper()
        
        if not code_str:
            return Response(
                {'error': 'Введите код'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            activation_code = ActivationCode.objects.select_related('plan').get(code=code_str)
            
            return Response({
                'valid': activation_code.is_valid(),
                'plan': activation_code.plan.name,
                'is_used': activation_code.is_used,
                'expires_at': activation_code.expires_at.isoformat(),
            })
            
        except ActivationCode.DoesNotExist:
            return Response(
                {'valid': False, 'error': 'Код не найден'},
                status=status.HTTP_404_NOT_FOUND
            )