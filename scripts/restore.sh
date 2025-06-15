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