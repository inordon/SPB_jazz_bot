#!/bin/bash
set -e

echo "🔧 Настройка Nginx для Festival Bot"
echo "=================================="

# Проверка прав root
if [[ $EUID -ne 0 ]]; then
   echo "❌ Этот скрипт должен запускаться с правами root"
   echo "Запустите: sudo ./setup_nginx.sh"
   exit 1
fi

# Переменные
DOMAIN="spbbot.mjf-bstage.ru"
PROJECT_PATH="/opt/festival-bot"
NGINX_CONFIG="/etc/nginx/conf.d/spbbot.conf"
HTPASSWD_FILE="/etc/nginx/.htpasswd"

echo "📋 Настройки:"
echo "  Домен: $DOMAIN"
echo "  Путь проекта: $PROJECT_PATH"
echo "  Конфигурация Nginx: $NGINX_CONFIG"
echo

# Создание директорий проекта
echo "📁 Создание директорий проекта..."
mkdir -p $PROJECT_PATH/{images,logs,backups}
chown -R www-data:www-data $PROJECT_PATH

# Установка необходимых пакетов
echo "📦 Установка необходимых пакетов..."
apt-get update
apt-get install -y nginx apache2-utils certbot python3-certbot-nginx

# Создание пользователей для базовой аутентификации
echo "👤 Создание пользователей для административного доступа..."

# Запрос пароля для админа
echo "Создайте пароль для пользователя 'admin':"
htpasswd -c $HTPASSWD_FILE admin

# Опционально добавить дополнительных пользователей
read -p "Добавить дополнительного пользователя? [y/N]: " add_user
if [[ $add_user =~ ^[Yy]$ ]]; then
    read -p "Имя пользователя: " username
    echo "Создайте пароль для пользователя '$username':"
    htpasswd $HTPASSWD_FILE $username
fi

# Создание конфигурации Nginx
echo "⚙️ Создание конфигурации Nginx..."

cat > $NGINX_CONFIG << 'EOL'
# Конфигурация для spbbot.mjf-bstage.ru
# Автоматически сгенерировано setup_nginx.sh

# Upstream для Docker контейнеров
upstream festival_bot {
    server 127.0.0.1:8080;
    keepalive 32;
}

upstream festival_grafana {
    server 127.0.0.1:3001;
    keepalive 16;
}

upstream festival_prometheus {
    server 127.0.0.1:9090;
    keepalive 16;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=images:10m rate=20r/s;
limit_req_zone $binary_remote_addr zone=admin:10m rate=5r/s;
limit_req_zone $binary_remote_addr zone=webhook:10m rate=100r/s;

# HTTP сервер
server {
    listen 80;
    server_name spbbot.mjf-bstage.ru;

    # Безопасность
    server_tokens off;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Логирование
    access_log /var/log/nginx/spbbot-access.log;
    error_log /var/log/nginx/spbbot-error.log warn;

    # Основная локация
    location / {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://festival_bot;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        error_page 502 503 504 @bot_down;
    }

    # Health check
    location /health {
        access_log off;
        proxy_pass http://festival_bot/health;
        expires 30s;
        add_header Access-Control-Allow-Origin * always;
    }

    # Статические изображения
    location /images/ {
        limit_req zone=images burst=30 nodelay;
        alias /opt/festival-bot/images/;
        expires 1d;
        add_header Cache-Control "public, immutable";
        try_files $uri $uri/ @missing_image;
    }

    # Административная панель
    location /admin/ {
        limit_req zone=admin burst=10 nodelay;
        auth_basic "Festival Bot Admin";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_pass http://festival_bot/admin/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Мониторинг Grafana
    location /monitoring/ {
        limit_req zone=admin burst=20 nodelay;
        auth_basic "Festival Bot Monitoring";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_pass http://festival_grafana/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Prometheus метрики
    location /metrics/ {
        limit_req zone=admin burst=10 nodelay;
        auth_basic "Festival Bot Metrics";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_pass http://festival_prometheus/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Логи (только для администраторов)
    location /logs/ {
        limit_req zone=admin burst=5 nodelay;
        allow 127.0.0.1;
        deny all;
        auth_basic "Festival Bot Logs";
        auth_basic_user_file /etc/nginx/.htpasswd;
        alias /opt/festival-bot/logs/;
        autoindex on;
        autoindex_exact_size off;
        autoindex_localtime on;
    }

    # Webhook для Telegram
    location /webhook {
        limit_req zone=webhook burst=200 nodelay;
        # Telegram IP ranges
        allow 149.154.160.0/20;
        allow 91.108.4.0/22;
        allow 91.108.8.0/22;
        allow 91.108.12.0/22;
        allow 91.108.16.0/22;
        allow 91.108.56.0/22;
        deny all;

        proxy_pass http://festival_bot/webhook;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Fallback страницы
    location @bot_down {
        internal;
        return 503 '{"status": "Bot temporarily unavailable"}';
        add_header Content-Type application/json;
    }

    location @missing_image {
        internal;
        return 404 '{"error": "Image not found"}';
        add_header Content-Type application/json;
    }

    # Блокировка нежелательных запросов
    location ~ /\. { deny all; access_log off; }
    location ~* \.(env|conf|config|bak)$ { deny all; access_log off; }
    location ~* /(wp-admin|phpmyadmin) { deny all; return 444; }
}
EOL

echo "✅ Конфигурация Nginx создана"

# Проверка конфигурации
echo "🔍 Проверка конфигурации Nginx..."
nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Конфигурация Nginx корректна"
else
    echo "❌ Ошибка в конфигурации Nginx"
    exit 1
fi

# Перезапуск Nginx
echo "🔄 Перезапуск Nginx..."
systemctl reload nginx
systemctl enable nginx

# Проверка статуса
echo "📊 Статус Nginx:"
systemctl status nginx --no-pager -l

# Настройка SSL сертификата
echo
read -p "🔒 Настроить SSL сертификат через Let's Encrypt? [y/N]: " setup_ssl

if [[ $setup_ssl =~ ^[Yy]$ ]]; then
    echo "🔒 Получение SSL сертификата..."
    certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN

    if [ $? -eq 0 ]; then
        echo "✅ SSL сертификат успешно установлен"

        # Настройка автоматического обновления
        echo "⏰ Настройка автоматического обновления SSL..."
        (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
    else
        echo "⚠️ Не удалось получить SSL сертификат"
        echo "Проверьте, что домен $DOMAIN указывает на этот сервер"
    fi
fi

# Настройка логротации
echo "📋 Настройка ротации логов..."
cat > /etc/logrotate.d/spbbot << 'EOL'
/var/log/nginx/spbbot-*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 www-data adm
    postrotate
        if [ -f /var/run/nginx.pid ]; then
            kill -USR1 `cat /var/run/nginx.pid`
        fi
    endscript
}
EOL

# Настройка файрвола (если установлен ufw)
if command -v ufw &> /dev/null; then
    echo "🔥 Настройка файрвола..."
    ufw allow 'Nginx Full'
    ufw allow 22/tcp
    echo "✅ Файрвол настроен"
fi

# Создание скрипта мониторинга
echo "📊 Создание скрипта мониторинга..."
cat > /usr/local/bin/spbbot-status << 'EOL'
#!/bin/bash
echo "🤖 Festival Bot Status"
echo "====================="
echo
echo "📊 Nginx:"
systemctl is-active nginx && echo "✅ Running" || echo "❌ Stopped"
echo
echo "🐳 Docker контейнеры:"
docker-compose -f /opt/festival-bot/docker-compose.yml ps
echo
echo "🌐 HTTP проверка:"
curl -s -o /dev/null -w "Status: %{http_code}, Time: %{time_total}s\n" http://spbbot.mjf-bstage.ru/health
echo
echo "📋 Логи (последние 5 строк):"
tail -5 /var/log/nginx/spbbot-access.log
EOL

chmod +x /usr/local/bin/spbbot-status

echo
echo "🎉 Настройка Nginx завершена!"
echo "=============================="
echo
echo "📍 Что настроено:"
echo "  ✅ Nginx конфигурация для $DOMAIN"
echo "  ✅ Базовая аутентификация для /admin, /monitoring, /metrics"
echo "  ✅ Rate limiting и защита от DDoS"
echo "  ✅ Проксирование к Docker контейнерам"
echo "  ✅ Логирование и ротация логов"
echo "  ✅ Файрвол настроен (если ufw установлен)"
if [[ $setup_ssl =~ ^[Yy]$ ]]; then
echo "  ✅ SSL сертификат от Let's Encrypt"
fi
echo
echo "📱 Доступные URL:"
echo "  🏠 Главная: http://$DOMAIN/"
echo "  ❤️ Health: http://$DOMAIN/health"
echo "  📊 Мониторинг: http://$DOMAIN/monitoring/"
echo "  📈 Метрики: http://$DOMAIN/metrics/"
echo "  🔧 Админка: http://$DOMAIN/admin/"
echo "  🖼️ Изображения: http://$DOMAIN/images/"
echo
echo "👤 Пользователи для входа:"
echo "  Логин: admin"
echo "  Пароль: [тот что вы ввели]"
echo
echo "🔧 Полезные команды:"
echo "  sudo spbbot-status          # Проверка статуса"
echo "  sudo nginx -t               # Проверка конфигурации"
echo "  sudo systemctl reload nginx # Перезагрузка Nginx"
echo "  sudo tail -f /var/log/nginx/spbbot-access.log # Просмотр логов"
echo
echo "🚀 Теперь запустите Docker контейнеры:"
echo "  cd /opt/festival-bot"
echo "  docker-compose up -d"
echo
echo "✨ Готово!"