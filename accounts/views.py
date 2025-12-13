from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .models import SMSVerification, UserDevice
from .serializers import (
    UserRegistrationSerializer, SendSMSSerializer, VerifySMSSerializer,
    UserSerializer, UserDeviceSerializer
)
from .tasks import send_verification_sms

User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class SendSMSVerificationView(generics.CreateAPIView):
    serializer_class = SendSMSSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sms_verification = serializer.save()
        
        # Send SMS asynchronously
        send_verification_sms.delay(sms_verification.id)
        
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
        
        # Check if user exists with this phone number
        try:
            user = User.objects.get(phone_number=sms_verification.phone_number)
            user.is_phone_verified = True
            user.save()
            
            # Generate tokens
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


class UserProfileViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        serializer = self.get_serializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def update_fcm_token(self, request):
        fcm_token = request.data.get('fcm_token')
        if not fcm_token:
            return Response(
                {'error': 'FCM token required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        request.user.fcm_token = fcm_token
        request.user.save()
        
        return Response({'detail': 'FCM token updated'})

    @action(detail=False, methods=['delete'])
    def delete_account(self, request):
        """Delete user account"""
        user = request.user
        user.is_active = False
        user.save()
        
        # In production, might want to anonymize instead of delete
        # user.delete()
        
        return Response({'detail': 'Account deactivated'})


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