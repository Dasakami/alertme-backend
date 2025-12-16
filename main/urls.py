# main/urls.py - ОБНОВЛЕННАЯ ВЕРСИЯ
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from accounts.views import (
    UserRegistrationView, SendSMSVerificationView, 
    VerifySMSView, UserProfileViewSet, UserDeviceViewSet,
    CustomTokenObtainView  
)
from contacts.views import EmergencyContactViewSet, ContactGroupViewSet
from sos.views import SOSAlertViewSet, ActivityTimerViewSet
from geolocation.views import LocationHistoryViewSet, GeozoneViewSet, SharedLocationViewSet
from subscriptions.views import (
    SubscriptionPlanViewSet, 
    UserSubscriptionViewSet, 
    PaymentViewSet,
    ActivationCodeViewSet  # НОВОЕ
)

router = DefaultRouter()

router.register(r'users', UserProfileViewSet, basename='user')
router.register(r'devices', UserDeviceViewSet, basename='device')

router.register(r'emergency-contacts', EmergencyContactViewSet, basename='emergency-contact')
router.register(r'contact-groups', ContactGroupViewSet, basename='contact-group')

router.register(r'sos-alerts', SOSAlertViewSet, basename='sos-alert')
router.register(r'activity-timers', ActivityTimerViewSet, basename='activity-timer')

router.register(r'location-history', LocationHistoryViewSet, basename='location-history')
router.register(r'geozones', GeozoneViewSet, basename='geozone')
router.register(r'shared-locations', SharedLocationViewSet, basename='shared-location')

router.register(r'subscription-plans', SubscriptionPlanViewSet, basename='subscription-plan')
router.register(r'subscriptions', UserSubscriptionViewSet, basename='subscription')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'activation-codes', ActivationCodeViewSet, basename='activation-code')  # НОВОЕ

urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # AUTH endpoints
    path('auth/register/', UserRegistrationView.as_view(), name='register'),
    path('auth/send-sms/', SendSMSVerificationView.as_view(), name='send-sms'),
    path('auth/verify-sms/', VerifySMSView.as_view(), name='verify-sms'),
    path('auth/login/', CustomTokenObtainView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)