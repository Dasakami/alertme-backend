from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import SMSVerification, UserDevice
from .serializers import (
    UserRegistrationSerializer, SendSMSSerializer, VerifySMSSerializer,
    UserSerializer, UserDeviceSerializer
)
from .tasks import send_verification_sms
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Registration successful. Please verify your phone number.'
        }, status=status.HTTP_201_CREATED)


class SendSMSVerificationView(generics.CreateAPIView):
    serializer_class = SendSMSSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sms_verification = serializer.save()
        
        from notifications.sms_service import SMSService
        sms_service = SMSService()
        
        message = f"Ваш код подтверждения AlertMe: {sms_verification.code}\nДействителен 10 минут"
        success = sms_service.send_sms(
            to_phone=str(sms_verification.phone_number),
            message=message
        )
        
        if success:
            logger.info(f"✅ SMS код отправлен на {sms_verification.phone_number}")
        
        return Response({
            'detail': 'Verification code sent',
            'phone_number': str(sms_verification.phone_number)
        })


class VerifySMSView(generics.CreateAPIView):
    serializer_class = VerifySMSSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        sms_verification = serializer.validated_data['sms_verification']
        sms_verification.is_verified = True
        sms_verification.save()
        
        try:
            user = User.objects.get(phone_number=sms_verification.phone_number)
            user.is_phone_verified = True
            user.save()
            
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'detail': 'Phone verified',
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            })
        except User.DoesNotExist:
            return Response({
                'detail': 'Phone verified. Please complete registration.',
                'phone_verified': True
            })


from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import serializers

class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)


@extend_schema(
    request=LoginSerializer,
    responses={200: UserSerializer},
    examples=[
        OpenApiExample(
            'Login Example',
            value={
                'phone_number': '+996555123456',
                'password': 'password123'
            }
        )
    ]
)
class CustomTokenObtainView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    
    def post(self, request):
        phone_number = request.data.get('phone_number')
        password = request.data.get('password')
        
        if not phone_number or not password:
            return Response(
                {'error': 'Phone number and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(request, phone_number=phone_number, password=password)
        
        if user is None:
            return Response(
                {'error': 'Invalid phone number or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.is_active:
            return Response(
                {'error': 'User account is disabled'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    ГЛАВНЫЙ API ДЛЯ РАБОТЫ С ПРОФИЛЕМ
    
    GET /api/users/me/ - получить данные текущего пользователя
    PUT/PATCH /api/users/update-profile/ - обновить профиль
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        ✅ ЕДИНАЯ ТОЧКА для получения данных пользователя
        
        Возвращает:
        - Все данные профиля
        - Premium статус (is_premium)
        - Telegram username
        - Аватар и т.д.
        """
        user = request.user
        
        # Обновляем is_premium из подписки
        try:
            from subscriptions.models import UserSubscription
            from django.utils import timezone
            
            subscription = UserSubscription.objects.select_related('plan').get(user=user)
            
            # Проверяем не истекла ли подписка
            if subscription.status == 'active' and subscription.end_date <= timezone.now():
                subscription.status = 'expired'
                subscription.save(update_fields=['status'])
            
            # Обновляем is_premium
            user.is_premium = (
                subscription.status == 'active' and 
                subscription.plan.plan_type != 'free'
            )
            user.save(update_fields=['is_premium'])
            
        except UserSubscription.DoesNotExist:
            # Нет подписки = не премиум
            if user.is_premium:
                user.is_premium = False
                user.save(update_fields=['is_premium'])
        
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """
        ✅ ОБНОВЛЕНИЕ ПРОФИЛЯ
        
        Принимает:
        - first_name
        - last_name
        - email
        - telegram_username
        - language
        """
        user = request.user
        serializer = self.get_serializer(
            user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        logger.info(f"✅ Профиль обновлен: {user.phone_number}")
        
        return Response({
            'success': True,
            'message': 'Профиль успешно обновлен',
            'user': serializer.data
        })


class UserDeviceViewSet(viewsets.ModelViewSet):
    serializer_class = UserDeviceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserDevice.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        device = self.get_object()
        device.is_active = False
        device.save()
        return Response({'detail': 'Device deactivated'})