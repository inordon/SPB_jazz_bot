# Многоэтапная сборка для оптимизации размера образа
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim as builder

# Установка системных зависимостей для сборки
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    musl-dev \
    libffi-dev \
    libssl-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Создание виртуального окружения
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копирование и установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel setuptools && \
    pip install --no-cache-dir -r requirements.txt

# Финальный образ
FROM python:${PYTHON_VERSION}-slim

# Метаданные образа
LABEL maintainer="Festival Bot Team"
LABEL version="2.0"
LABEL description="Telegram bot for music festival with advanced support system"

# Создание пользователя для безопасности
RUN groupadd -r botuser && useradd -r -g botuser botuser

# Установка только необходимых runtime зависимостей
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Копирование виртуального окружения из builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Установка рабочей директории
WORKDIR /app

# Создание необходимых директорий
RUN mkdir -p /app/src /app/logs /app/images /app/backups /app/config && \
    chown -R botuser:botuser /app

# Копирование исходного кода
COPY --chown=botuser:botuser src/ /app/src/
COPY --chown=botuser:botuser images/ /app/images/
COPY --chown=botuser:botuser config/ /app/config/

# Копирование скриптов
COPY --chown=botuser:botuser scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.sh

# Копирование файла здоровья для health check
COPY --chown=botuser:botuser <<EOF /app/health_check.py
#!/usr/bin/env python3
import sys
import asyncio
import asyncpg
import os
from datetime import datetime

async def health_check():
    try:
        # Проверка подключения к БД
        conn = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'postgres'),
            port=int(os.getenv('DB_PORT', 5432)),
            user=os.getenv('DB_USER', 'festival_user'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'festival_bot'),
            timeout=5
        )
        await conn.fetchval('SELECT 1')
        await conn.close()

        print(f"✅ Health check passed at {datetime.now()}")
        return 0
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(health_check()))
EOF

RUN chmod +x /app/health_check.py

# Переключение на непривилегированного пользователя
USER botuser

# Настройка переменных окружения
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Открытие порта для health check
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python /app/health_check.py || exit 1

# Точка входа
ENTRYPOINT ["/app/scripts/entrypoint.sh"]

# Команда по умолчанию
CMD ["python", "/app/src/main.py"]