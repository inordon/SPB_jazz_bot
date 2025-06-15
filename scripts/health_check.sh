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