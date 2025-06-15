#!/bin/bash
set -e

echo "🚀 Starting Festival Bot..."
echo "📅 Date: $(date)"
echo "🌍 Environment: ${ENVIRONMENT:-production}"
echo "🔍 Debug: ${DEBUG:-false}"

# Функция для ожидания готовности сервиса
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3

    echo "⏳ Waiting for $service_name to be ready..."
    while ! nc -z "$host" "$port"; do
        echo "⏳ $service_name is not ready yet. Waiting..."
        sleep 2
    done
    echo "✅ $service_name is ready!"
}

# Ожидание готовности PostgreSQL
wait_for_service "${DB_HOST:-postgres}" "${DB_PORT:-5432}" "PostgreSQL"

# Ожидание готовности Redis (если используется)
if [ -n "${REDIS_HOST}" ]; then
    wait_for_service "${REDIS_HOST}" "${REDIS_PORT:-6379}" "Redis"
fi

# Проверка обязательных переменных окружения
check_required_env() {
    local var_name=$1
    if [ -z "${!var_name}" ]; then
        echo "❌ Error: Required environment variable $var_name is not set"
        exit 1
    fi
}

echo "🔍 Checking required environment variables..."
check_required_env "BOT_TOKEN"
check_required_env "ADMIN_IDS"
check_required_env "DB_PASSWORD"

# Проверка подключения к базе данных
echo "🔍 Testing database connection..."
python << 'PYTHON_SCRIPT'
import asyncio
import asyncpg
import os
import sys

async def test_db():
    try:
        conn = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'postgres'),
            port=int(os.getenv('DB_PORT', 5432)),
            user=os.getenv('DB_USER', 'festival_user'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'festival_bot'),
            timeout=10
        )
        await conn.fetchval('SELECT 1')
        await conn.close()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if not asyncio.run(test_db()):
    sys.exit(1)
PYTHON_SCRIPT

# Создание необходимых директорий
echo "📁 Creating directories..."
mkdir -p /app/logs /app/backups

# Установка прав доступа
echo "🔒 Setting permissions..."
chmod 755 /app/logs /app/backups

# Валидация конфигурации
echo "⚙️ Validating configuration..."
cd /app/src
python -c "
import sys
sys.path.insert(0, '/app/src')
try:
    from config import config
    if config.validate_config():
        print('✅ Configuration is valid')
    else:
        print('❌ Configuration validation failed')
        sys.exit(1)
except Exception as e:
    print(f'❌ Configuration error: {e}')
    sys.exit(1)
"

echo "🎉 Initialization completed successfully!"
echo "▶️ Starting bot with command: $@"

# Запуск переданной команды
exec "$@"