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