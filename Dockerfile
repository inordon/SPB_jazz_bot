# ===== МНОГОЭТАПНАЯ СБОРКА =====
# Этап 1: Сборка зависимостей
FROM python:3.11-alpine AS builder

# Устанавливаем только необходимые для сборки пакеты
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    linux-headers

# Создаем виртуальное окружение
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копируем только requirements.txt для кэширования
COPY requirements.txt .

# Устанавливаем зависимости в виртуальное окружение
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ===== Этап 2: Финальный образ =====
FROM python:3.11-alpine AS production

# Устанавливаем только runtime зависимости
RUN apk add --no-cache \
    postgresql-client \
    curl \
    ca-certificates

# Копируем виртуальное окружение из builder этапа
COPY --from=builder /opt/venv /opt/venv

# Рабочая директория
WORKDIR /app

# Создаем непривилегированного пользователя
RUN addgroup -g 1001 -S festival && \
    adduser -S festival -u 1001 -G festival

# Копируем только необходимые файлы приложения
COPY --chown=festival:festival src/ ./src/
COPY --chown=festival:festival scripts/ ./scripts/
COPY --chown=festival:festival health_check.py ./

# Права на выполнение
RUN chmod +x scripts/*.sh health_check.py

# Переменные окружения
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random

# Переключаемся на непривилегированного пользователя
USER festival

# Порт
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python health_check.py || exit 1

# Запуск
ENTRYPOINT ["./scripts/entrypoint.sh"]
CMD ["python", "-m", "main"]