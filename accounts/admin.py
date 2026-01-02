from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, SMSVerification, UserDevice


class CustomUserAdmin(UserAdmin):
    model = User
    
    list_display = ('phone_number', 'first_name', 'last_name', 'email', 
                    'is_premium', 'is_phone_verified', 'is_staff', 'is_active')
    list_filter = ('is_premium', 'is_staff', 'is_superuser', 'is_active', 'is_phone_verified')
    
    fieldsets = (
        (None, {'fields': ('phone_number', 'username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'avatar', 'telegram_username')}),
        ('Settings', {'fields': ('language', 'fcm_token', 'is_phone_verified', 'is_premium')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 
                                    'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'email', 'first_name', 'last_name',
                       'password1', 'password2'),
        }),
    )
    
    search_fields = ('phone_number', 'email', 'first_name', 'last_name', 'username')
    ordering = ('phone_number',)


@admin.register(SMSVerification)
class SMSVerificationAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'code', 'is_verified', 'created_at', 'expires_at')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('phone_number', 'code')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_type', 'device_id', 'is_active', 'created_at')
    list_filter = ('device_type', 'is_active', 'created_at')
    search_fields = ('user__phone_number', 'device_id')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')


admin.site.register(User, CustomUserAdmin)