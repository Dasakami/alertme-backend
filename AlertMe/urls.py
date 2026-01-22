from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from main.views import (
    base_temp, 
    account_deletion_view, 
    privacy_policy_view,
    handler404,
    handler500,
    handler403,
)
urlpatterns = [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),  
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}), 
    path('admin/', admin.site.urls),
    path('api/', include('main.urls')),
    path('', base_temp),
    path('account-deletion/', account_deletion_view, name='account_deletion'),
    path('privacy-policy/', privacy_policy_view, name='privacy_policy'),
]

handler404 = 'main.views.handler404'
handler500 = 'main.views.handler500'
handler403 = 'main.views.handler403'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

