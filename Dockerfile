# Многоступенчатая сборка для минимизации размера
FROM python:3.11-alpine AS builder

# Установка зависимостей для сборки
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    libffi-dev

# Создание виртуального окружения
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Финальная стадия - минимальный образ
FROM python:3.11-alpine

# Установка только runtime зависимостей
RUN apk add --no-cache \
    postgresql-client \
    libpq \
    && rm -rf /var/cache/apk/*

# Копирование виртуального окружения из builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Создание пользователя для безопасности
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

# Рабочая директория
WORKDIR /app

# Копирование только необходимых файлов
COPY src/ ./src/
COPY scripts/entrypoint.sh ./scripts/
COPY health_check.py ./

# Установка прав
RUN chmod +x scripts/entrypoint.sh health_check.py && \
    chown -R appuser:appgroup /app

# Переменные окружения
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Переключение на пользователя
USER appuser

# Порт
EXPOSE 8080

# Health check (упрощенный)
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python health_check.py || exit 1

# Запуск
ENTRYPOINT ["./scripts/entrypoint.sh"]
CMD ["python", "src/main.py"]