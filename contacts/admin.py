from django.contrib import admin
from .models import EmergencyContact, ContactGroup


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
	list_display = ('name', 'phone_number', 'user', 'is_primary', 'is_active', 'created_at')
	list_filter = ('is_active', 'is_primary', 'created_at')
	search_fields = ('name', 'phone_number', 'user__phone_number')
	raw_id_fields = ('user',)
	readonly_fields = ('created_at', 'updated_at')


@admin.register(ContactGroup)
class ContactGroupAdmin(admin.ModelAdmin):
	list_display = ('name', 'user', 'is_active', 'created_at')
	list_filter = ('is_active', 'created_at')
	search_fields = ('name', 'user__phone_number')
	raw_id_fields = ('user',)
