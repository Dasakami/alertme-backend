# Базовый образ
FROM python:3.12.5-slim

WORKDIR /app

# Копируем зависимости бота
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем переменные окружения по умолчанию (можно переопределять)
ENV DJANGO_SETTINGS_MODULE=AlertMe.settings
ENV TELEGRAM_BOT_TOKEN="8423156547:AAHvgLbi5syDqaf5iWlvg82QU0qsHN5BEUs"
ENV PYTHONPATH=/app:/app_alertme

# Запуск бота
CMD ["python", "main.py"]
