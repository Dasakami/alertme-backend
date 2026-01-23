# Базовый образ
FROM python:3.12.5-slim

# Устанавливаем системные зависимости (PostgreSQL client для psycopg2)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# Устанавливаем переменные окружения по умолчанию (можно переопределять)
ENV DJANGO_SETTINGS_MODULE=AlertMe.settings
ENV TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN_HERE"

# Запуск бота
CMD ["python", "bot.py"]
