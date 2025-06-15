#!/bin/bash
# ===========================================
# СКРИПТЫ ДЛЯ DOCKER УПРАВЛЕНИЯ
# ===========================================
cat > scripts/entrypoint.sh << 'EOF'
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
chmod 644 /app/src/*.py

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
EOF

# scripts/backup.sh - Скрипт резервного копирования
cat > scripts/backup.sh << 'EOF'
#!/bin/bash
set -e

echo "📦 Starting backup process..."

# Создание директории для бэкапов
BACKUP_DIR="/app/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Бэкап базы данных
echo "💾 Creating database backup..."
PGPASSWORD="${DB_PASSWORD}" pg_dump \
    -h "${DB_HOST:-postgres}" \
    -p "${DB_PORT:-5432}" \
    -U "${DB_USER:-festival_user}" \
    -d "${DB_NAME:-festival_bot}" \
    --clean --if-exists --no-owner --no-privileges \
    > "$BACKUP_DIR/database.sql"

# Бэкап файлов конфигурации
echo "⚙️ Backing up configuration..."
cp -r /app/config "$BACKUP_DIR/" 2>/dev/null || true

# Бэкап изображений
echo "🖼️ Backing up images..."
cp -r /app/images "$BACKUP_DIR/" 2>/dev/null || true

# Создание архива
echo "🗜️ Creating archive..."
cd /app/backups
tar -czf "backup_$(date +%Y%m%d_%H%M%S).tar.gz" "$(basename "$BACKUP_DIR")"
rm -rf "$BACKUP_DIR"

# Очистка старых бэкапов (оставляем последние 7)
echo "🧹 Cleaning old backups..."
ls -t backup_*.tar.gz | tail -n +8 | xargs rm -f

echo "✅ Backup completed successfully!"
EOF

# scripts/restore.sh - Скрипт восстановления
cat > scripts/restore.sh << 'EOF'
#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "❌ Usage: $0 <backup_file.tar.gz>"
    exit 1
fi

BACKUP_FILE="$1"
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "🔄 Starting restore process from: $BACKUP_FILE"

# Создание временной директории
TEMP_DIR="/tmp/restore_$(date +%s)"
mkdir -p "$TEMP_DIR"

# Извлечение архива
echo "📦 Extracting backup..."
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

# Поиск директории с бэкапом
BACKUP_DIR=$(find "$TEMP_DIR" -type d -name "backup_*" | head -1)
if [ -z "$BACKUP_DIR" ]; then
    echo "❌ Invalid backup archive structure"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Восстановление базы данных
if [ -f "$BACKUP_DIR/database.sql" ]; then
    echo "💾 Restoring database..."
    PGPASSWORD="${DB_PASSWORD}" psql \
        -h "${DB_HOST:-postgres}" \
        -p "${DB_PORT:-5432}" \
        -U "${DB_USER:-festival_user}" \
        -d "${DB_NAME:-festival_bot}" \
        < "$BACKUP_DIR/database.sql"
fi

# Восстановление конфигурации
if [ -d "$BACKUP_DIR/config" ]; then
    echo "⚙️ Restoring configuration..."
    cp -r "$BACKUP_DIR/config/"* /app/config/ 2>/dev/null || true
fi

# Восстановление изображений
if [ -d "$BACKUP_DIR/images" ]; then
    echo "🖼️ Restoring images..."
    cp -r "$BACKUP_DIR/images/"* /app/images/ 2>/dev/null || true
fi

# Очистка
rm -rf "$TEMP_DIR"

echo "✅ Restore completed successfully!"
EOF

# scripts/health_check.sh - Детальная проверка здоровья
cat > scripts/health_check.sh << 'EOF'
#!/bin/bash

# Функция для проверки сервиса
check_service() {
    local service_name=$1
    local check_command=$2

    echo -n "🔍 Checking $service_name... "
    if eval "$check_command" &>/dev/null; then
        echo "✅ OK"
        return 0
    else
        echo "❌ FAILED"
        return 1
    fi
}

echo "🏥 Festival Bot Health Check"
echo "=========================="

failed_checks=0

# Проверка PostgreSQL
if ! check_service "PostgreSQL" "nc -z ${DB_HOST:-postgres} ${DB_PORT:-5432}"; then
    ((failed_checks++))
fi

# Проверка Redis (если настроен)
if [ -n "${REDIS_HOST}" ]; then
    if ! check_service "Redis" "nc -z ${REDIS_HOST} ${REDIS_PORT:-6379}"; then
        ((failed_checks++))
    fi
fi

# Проверка подключения к базе данных
if ! check_service "Database Connection" "python /app/health_check.py"; then
    ((failed_checks++))
fi

# Проверка файловой системы
if ! check_service "Logs Directory" "[ -w /app/logs ]"; then
    ((failed_checks++))
fi

if ! check_service "Backups Directory" "[ -w /app/backups ]"; then
    ((failed_checks++))
fi

# Проверка конфигурации
if ! check_service "Bot Configuration" "cd /app/src && python -c 'from config import config; config.validate_config()'"; then
    ((failed_checks++))
fi

echo "=========================="
if [ $failed_checks -eq 0 ]; then
    echo "🎉 All checks passed! Bot is healthy."
    exit 0
else
    echo "⚠️ $failed_checks check(s) failed!"
    exit 1
fi
EOF

# scripts/logs.sh - Просмотр логов
cat > scripts/logs.sh << 'EOF'
#!/bin/bash

# Функция для отображения меню
show_menu() {
    echo "📋 Festival Bot Logs"
    echo "==================="
    echo "1) Bot logs (main)"
    echo "2) Error logs"
    echo "3) Support logs"
    echo "4) Stats logs"
    echo "5) All logs (live)"
    echo "6) Clear all logs"
    echo "q) Quit"
    echo
}

# Функция для очистки логов
clear_logs() {
    read -p "⚠️ Are you sure you want to clear all logs? [y/N]: " confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then
        rm -f /app/logs/*.log
        echo "✅ All logs cleared!"
    else
        echo "❌ Operation cancelled."
    fi
}

while true; do
    show_menu
    read -p "Choose option: " choice

    case $choice in
        1)
            echo "📄 Bot logs:"
            tail -f /app/logs/bot.log 2>/dev/null || echo "No bot logs found"
            ;;
        2)
            echo "❌ Error logs:"
            tail -f /app/logs/errors.log 2>/dev/null || echo "No error logs found"
            ;;
        3)
            echo "🆘 Support logs:"
            tail -f /app/logs/support.log 2>/dev/null || echo "No support logs found"
            ;;
        4)
            echo "📊 Stats logs:"
            tail -f /app/logs/stats.log 2>/dev/null || echo "No stats logs found"
            ;;
        5)
            echo "📋 All logs (live):"
            tail -f /app/logs/*.log 2>/dev/null || echo "No logs found"
            ;;
        6)
            clear_logs
            ;;
        q|Q)
            echo "👋 Goodbye!"
            exit 0
            ;;
        *)
            echo "❌ Invalid option"
            ;;
    esac

    echo
    read -p "Press Enter to continue..."
    clear
done
EOF

# Делаем все скрипты исполняемыми
chmod +x scripts/*.sh

echo "✅ Docker scripts created successfully!"
echo "📁 Created files:"
echo "  - scripts/entrypoint.sh"
echo "  - scripts/backup.sh"
echo "  - scripts/restore.sh"
echo "  - scripts/health_check.sh"
echo "  - scripts/logs.sh"