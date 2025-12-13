from django.db import models
from django.conf import settings
from phonenumber_field.modelfields import PhoneNumberField
from django.utils.translation import gettext_lazy as _


class EmergencyContact(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='emergency_contacts')
    name = models.CharField(max_length=255, verbose_name=_('Name'))
    phone_number = PhoneNumberField(verbose_name=_('Phone Number'))
    email = models.EmailField(blank=True, null=True, verbose_name=_('Email'))
    relation = models.CharField(max_length=100, blank=True, verbose_name=_('Relation'))
    is_primary = models.BooleanField(default=False, verbose_name=_('Primary Contact'))
    is_active = models.BooleanField(default=True)
    notification_preferences = models.JSONField(default=dict, blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Emergency Contact')
        verbose_name_plural = _('Emergency Contacts')
        ordering = ['-is_primary', 'name']
        unique_together = ['user', 'phone_number']

    def __str__(self):
        return f"{self.name} ({self.phone_number})"

    def save(self, *args, **kwargs):
        if self.is_primary:
            EmergencyContact.objects.filter(user=self.user, is_primary=True).exclude(id=self.id).update(is_primary=False)
        super().save(*args, **kwargs)


class ContactGroup(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contact_groups')
    name = models.CharField(max_length=255, verbose_name=_('Group Name'))
    description = models.TextField(blank=True)
    contacts = models.ManyToManyField(EmergencyContact, related_name='groups')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Contact Group')
        verbose_name_plural = _('Contact Groups')
        ordering = ['name']

    def __str__(self):
        return f"{self.user.phone_number} - {self.name}"
    