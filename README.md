# AlertMe Backend API

![Django](https://img.shields.io/badge/Django-4.2-green)
![DRF](https://img.shields.io/badge/DRF-3.14-blue)
![Python](https://img.shields.io/badge/Python-3.12-yellow)
![License](https://img.shields.io/badge/License-Proprietary-red)

> **⚠️ PROPRIETARY SOFTWARE**  
> This software is the intellectual property of **[Your Name/Company]**.  
> Developed for **[Client Name]** under commercial agreement.  
> **Unauthorized copying, modification, or distribution is strictly prohibited.**

---

## 📱 О проекте

**AlertMe** - это мобильное приложение для обеспечения личной безопасности с функциями:
- 🚨 SOS-сигналы с аудио/видео записью
- 👥 Управление экстренными контактами
- ⏱️ Таймер безопасности
- 📍 Геозоны и отслеживание местоположения
- 💎 Премиум подписки через Telegram Stars
- 📧 Уведомления через SMS, Email и Telegram

---

## 🏗️ Технологический стек

### Backend
- **Django 4.2** - Web framework
- **Django REST Framework** - REST API
- **PostgreSQL / SQLite3** - База данных
- **Simple JWT** - Аутентификация
- **Twilio** - SMS уведомления
- **Telegram Bot API** - Telegram уведомления
- **Gmail SMTP** - Email уведомления

### Дополнительные библиотеки
- `phonenumber-field` - Валидация телефонов
- `django-cors-headers` - CORS
- `drf-spectacular` - OpenAPI документация
- `python-decouple` - Управление конфигом

---

## 🚀 Установка и запуск

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd AlertMe
```

### 2. Создание виртуального окружения

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (для продакшн)
DB_NAME=alertme
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=127.0.0.1
DB_PORT=5432

# Twilio (SMS)
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=+1234567890

# Telegram Bot
TELEGRAM_BOT_TOKEN=your-bot-token

# Email (Gmail)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Site URL
SITE_URL=http://127.0.0.1:8000
```

### 5. Миграции базы данных

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Создание суперпользователя

```bash
python manage.py createsuperuser
```

### 7. Создание планов подписки

```bash
python manage.py shell
```

```python
from subscriptions.models import SubscriptionPlan

# Free план
SubscriptionPlan.objects.create(
    name="Free",
    plan_type="free",
    description="Бесплатный план",
    price_monthly=0,
    price_yearly=0,
    max_contacts=3,
    geozones_enabled=False,
    location_history_enabled=False,
    features={"basic_sos": True}
)

# Premium план
SubscriptionPlan.objects.create(
    name="Personal Premium",
    plan_type="personal_premium",
    description="Премиум подписка",
    price_monthly=100,
    price_yearly=1000,
    max_contacts=999,
    geozones_enabled=True,
    location_history_enabled=True,
    features={"unlimited_contacts": True, "geozones": True, "history": True}
)
```

### 8. Запуск сервера

```bash
python manage.py runserver 0.0.0.0:8000
```

API будет доступно по адресу: `http://127.0.0.1:8000/api/`

---

## 📚 API Документация

### Swagger UI
```
http://127.0.0.1:8000/api/docs/
```

### OpenAPI Schema
```
http://127.0.0.1:8000/api/schema/
```

### Основные эндпоинты

#### Аутентификация
- `POST /api/auth/register/` - Регистрация
- `POST /api/auth/login/` - Вход
- `POST /api/auth/send-sms/` - Отправка SMS кода
- `POST /api/auth/verify-sms/` - Верификация SMS

#### Пользователи
- `GET /api/users/me/` - Профиль текущего пользователя
- `PATCH /api/users/update-profile/` - Обновление профиля

#### SOS
- `POST /api/sos-alerts/` - Создание SOS сигнала
- `GET /api/sos-alerts/` - Список SOS
- `GET /api/sos-alerts/active/` - Активный SOS

#### Контакты
- `GET /api/emergency-contacts/` - Список контактов
- `POST /api/emergency-contacts/` - Добавление контакта
- `POST /api/emergency-contacts/{id}/set_primary/` - Установить основным

#### Подписки
- `GET /api/subscription-plans/` - Доступные планы
- `GET /api/subscriptions/current/` - Текущая подписка
- `POST /api/activation-codes/activate/` - Активация кода

---

## 🔧 Настройка внешних сервисов

### Twilio (SMS)

1. Зарегистрируйтесь на [twilio.com](https://www.twilio.com)
2. Получите Account SID и Auth Token
3. Купите номер телефона
4. Добавьте в `.env`:
```env
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_PHONE_NUMBER=+1234567890
```

### Telegram Bot

1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Получите токен
3. Добавьте в `.env`:
```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
```

### Gmail SMTP

1. Включите 2FA в Google аккаунте
2. Создайте App Password
3. Добавьте в `.env`:
```env
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

---

## 🗂️ Структура проекта

```
AlertMe/
├── AlertMe/              # Настройки проекта
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/             # Аутентификация и пользователи
├── contacts/             # Экстренные контакты
├── sos/                  # SOS сигналы
├── subscriptions/        # Подписки и платежи
├── geolocation/          # Геолокация и геозоны
├── notifications/        # Уведомления (SMS, Email, Telegram)
├── main/                 # Главные API роуты
├── media/                # Загруженные файлы
├── requirements.txt      # Зависимости
└── manage.py
```

---

## 🧪 Тестирование

```bash
# Запуск всех тестов
python manage.py test

# Конкретное приложение
python manage.py test accounts
python manage.py test sos
```

---

## 📦 Развертывание (Production)

### 1. Обновите settings.py

```python
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']
```

### 2. Настройте PostgreSQL

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'alertme',
        'USER': 'postgres',
        'PASSWORD': 'strong-password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 3. Соберите статику

```bash
python manage.py collectstatic --noinput
```

### 4. Используйте Gunicorn

```bash
pip install gunicorn
gunicorn AlertMe.wsgi:application --bind 0.0.0.0:8000
```

### 5. Настройте Nginx (пример)

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /static/ {
        alias /path/to/AlertMe/staticfiles/;
    }

    location /media/ {
        alias /path/to/AlertMe/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🔐 Безопасность

- ✅ JWT токены для аутентификации
- ✅ CORS настроен для мобильных приложений
- ✅ Валидация всех входных данных
- ✅ Ограничение rate limit (будущая фича)
- ✅ HTTPS обязателен в продакшн

---

## 📝 Лицензия

**PROPRIETARY - All Rights Reserved**

© 2026 **[Your Name/Company]**. All rights reserved.

This software and associated documentation files (the "Software") are the proprietary and confidential property of **[Your Name/Company]**.

**COMMERCIAL LICENSE TERMS:**
- Developed under commercial agreement for **[Client Name]**
- Unauthorized use, copying, modification, or distribution is prohibited
- Source code access is restricted to authorized developers only
- No warranty is provided, express or implied

For licensing inquiries, contact: **[your-email@example.com]**

---

## 👨‍💻 Разработчик

**[Your Name]**
- Email: [your-email@example.com]
- Telegram: [@your_username]
- Portfolio: [your-website.com]

**Developed for:** [Client Name/Company]  
**Project Duration:** [Start Date] - [End Date]  
**Version:** 1.0.0

---

## 🐛 Поддержка

Для технической поддержки обращайтесь:
- Email: support@alertme.kg
- Telegram: @AlertMeSupport

---

## 📊 Changelog

### Version 1.0.0 (2026-01-10)
- ✅ Базовая функциональность SOS
- ✅ Управление контактами
- ✅ Аутентификация по номеру телефона
- ✅ Подписки через Telegram Stars
- ✅ SMS/Email/Telegram уведомления
- ✅ Геозоны и история местоположений
- ✅ Таймер безопасности

---

**⚠️ IMPORTANT NOTICE:**  
This is proprietary software developed under commercial agreement.  
Unauthorized use or distribution may result in legal action.bu