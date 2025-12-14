from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class PhoneNumberBackend(ModelBackend):
    """
    Авторизация по номеру телефона вместо username
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Если передан phone_number, используем его
        phone_number = kwargs.get('phone_number') or username
        
        if phone_number is None or password is None:
            return None
        
        try:
            # Ищем пользователя по номеру телефона
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            # Защита от timing attacks
            User().set_password(password)
            return None
        
        # Проверяем пароль
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None