# Базовый образ
FROM python:3.12.5-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=AlertMe.settings
ENV TELEGRAM_BOT_TOKEN=""

CMD ["python", "bot.py"]
