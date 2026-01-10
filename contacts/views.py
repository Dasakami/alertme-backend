from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import IntegrityError
from .models import EmergencyContact, ContactGroup
from .serializers import EmergencyContactSerializer, ContactGroupSerializer
import logging

logger = logging.getLogger(__name__)


class EmergencyContactViewSet(viewsets.ModelViewSet):
    serializer_class = EmergencyContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmergencyContact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """✅ ИСПРАВЛЕНО: Обработка ошибки дублирования"""
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError as e:
            error_message = str(e)
            
            if 'phone_number' in error_message.lower():
                return Response(
                    {
                        'error': 'Контакт с таким номером телефона уже существует',
                        'detail': 'Вы уже добавили контакт с номером +{}'.format(
                            request.data.get('phone_number', '')
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif 'unique' in error_message.lower():
                return Response(
                    {
                        'error': 'Такой контакт уже существует',
                        'detail': 'Проверьте, возможно вы уже добавили этот контакт'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                logger.error(f"Неизвестная ошибка IntegrityError: {e}")
                return Response(
                    {'error': 'Ошибка при добавлении контакта'},
                    status=status.HTTP_400_BAD_REQUEST
                )

    def update(self, request, *args, **kwargs):
        """✅ ИСПРАВЛЕНО: Обработка ошибки дублирования при обновлении"""
        try:
            return super().update(request, *args, **kwargs)
        except IntegrityError as e:
            error_message = str(e)
            
            if 'phone_number' in error_message.lower():
                return Response(
                    {
                        'error': 'Контакт с таким номером уже существует',
                        'detail': 'Другой контакт уже использует этот номер телефона'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                return Response(
                    {'error': 'Ошибка при обновлении контакта'},
                    status=status.HTTP_400_BAD_REQUEST
                )

    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        contact = self.get_object()
        EmergencyContact.objects.filter(
            user=request.user,
            is_primary=True
        ).update(is_primary=False)
        
        contact.is_primary = True
        contact.save()
        
        return Response({'detail': 'Contact set as primary'})

    @action(detail=False, methods=['get'])
    def primary(self, request):
        primary_contact = EmergencyContact.objects.filter(
            user=request.user,
            is_primary=True,
            is_active=True
        ).first()
        
        if primary_contact:
            serializer = self.get_serializer(primary_contact)
            return Response(serializer.data)
        
        return Response(
            {'detail': 'No primary contact set'},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(detail=False, methods=['post'])
    def import_from_phone(self, request):
        contacts_data = request.data.get('contacts', [])
        
        created_contacts = []
        errors = []
        
        for contact_data in contacts_data:
            serializer = self.get_serializer(data=contact_data)
            if serializer.is_valid():
                try:
                    serializer.save(user=request.user)
                    created_contacts.append(serializer.data)
                except IntegrityError:
                    errors.append({
                        'contact': contact_data,
                        'error': 'Контакт уже существует'
                    })
            else:
                errors.append({
                    'contact': contact_data,
                    'errors': serializer.errors
                })
        
        return Response({
            'created': len(created_contacts),
            'contacts': created_contacts,
            'errors': errors
        })


class ContactGroupViewSet(viewsets.ModelViewSet):
    serializer_class = ContactGroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ContactGroup.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def add_contacts(self, request, pk=None):
        group = self.get_object()
        contact_ids = request.data.get('contact_ids', [])
        
        contacts = EmergencyContact.objects.filter(
            id__in=contact_ids,
            user=request.user
        )
        
        group.contacts.add(*contacts)
        
        return Response({
            'detail': f'Added {contacts.count()} contacts to group',
            'group': self.get_serializer(group).data
        })

    @action(detail=True, methods=['post'])
    def remove_contacts(self, request, pk=None):
        group = self.get_object()
        contact_ids = request.data.get('contact_ids', [])
        
        contacts = EmergencyContact.objects.filter(
            id__in=contact_ids,
            user=request.user
        )
        
        group.contacts.remove(*contacts)
        
        return Response({
            'detail': f'Removed {contacts.count()} contacts from group',
            'group': self.get_serializer(group).data
        })