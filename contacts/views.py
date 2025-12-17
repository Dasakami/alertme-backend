from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import EmergencyContact, ContactGroup
from .serializers import EmergencyContactSerializer, ContactGroupSerializer


class EmergencyContactViewSet(viewsets.ModelViewSet):
    serializer_class = EmergencyContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmergencyContact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

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
                serializer.save(user=request.user)
                created_contacts.append(serializer.data)
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