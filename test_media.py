# test_media.py
# Создайте этот файл в корне проекта и запустите: python manage.py shell < test_media.py

from sos.models import SOSAlert
from django.contrib.auth import get_user_model

User = get_user_model()

# Создаем тестовый SOS
user = User.objects.first()
if user:
    sos = SOSAlert.objects.create(
        user=user,
        status='active',
        latitude=42.8746,
        longitude=74.5698,
        address='Тестовый адрес, Бишкек',
        activation_method='button',
        notes='Тестовый SOS для проверки медиа'
    )
    
    print(f"✅ Создан тестовый SOS с ID: {sos.id}")
    print(f"📍 Откройте в браузере:")
    print(f"   http://10.77.141.53:8000/api/media/sos/{sos.id}/")
    print(f"\n📊 Админка:")
    print(f"   http://10.77.141.53:8000/admin/sos/sosalert/{sos.id}/change/")
else:
    print("❌ Пользователи не найдены. Создайте пользователя сначала.")