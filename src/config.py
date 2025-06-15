import os
from typing import List
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # Telegram Bot настройки
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")

    # База данных
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "festival_bot")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "password")

    # Администраторы и сотрудники поддержки
    ADMIN_IDS: List[int] = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
    SUPPORT_STAFF_IDS: List[int] = [int(x) for x in os.getenv("SUPPORT_STAFF_IDS", "").split(",") if x]

    # Каналы и группы
    SUPPORT_GROUP_ID: str = os.getenv("SUPPORT_GROUP_ID")
    SUPPORT_GROUP_TOPICS: bool = os.getenv("SUPPORT_GROUP_TOPICS", "true").lower() == "true"
    FEEDBACK_CHANNEL_ID: str = os.getenv("FEEDBACK_CHANNEL_ID")

    # Email настройки
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    EMAIL_USER: str = os.getenv("EMAIL_USER")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD")
    SUPPORT_EMAIL: str = os.getenv("SUPPORT_EMAIL")

    # Социальные сети
    SOCIAL_LINKS = {
        "Instagram": "https://instagram.com/festival",
        "VK": "https://vk.com/festival",
        "Telegram": "https://t.me/festival_channel",
        "YouTube": "https://youtube.com/festival",
        "Spotify": "https://open.spotify.com/festival"
    }

    # Билеты
    TICKET_PURCHASE_URL: str = os.getenv("TICKET_PURCHASE_URL", "https://tickets.festival.com")

    # Яндекс.Карты маршруты
    YANDEX_MAPS_BASE_URL = "https://yandex.ru/maps/?rtext="

    # Координаты фестиваля (основная точка)
    FESTIVAL_COORDINATES = os.getenv("FESTIVAL_COORDINATES", "55.7558,37.6176")  # Широта, долгота

    # Координаты ключевых точек фестиваля
    LOCATIONS_COORDINATES = {
        "foodcourt": os.getenv("FOODCOURT_COORDINATES", "55.7562,37.6174"),      # Фудкорт
        "workshops": os.getenv("WORKSHOPS_COORDINATES", "55.7556,37.6182"),      # Мастер-классы
        "souvenirs": os.getenv("SOUVENIRS_COORDINATES", "55.7560,37.6170"),      # Сувениры
        "toilets": os.getenv("TOILETS_COORDINATES", "55.7559,37.6178"),          # Туалеты
        "medical": os.getenv("MEDICAL_COORDINATES", "55.7558,37.6176"),          # Медпункт
    }

    # Пути к изображениям карт
    MAPS_IMAGES_PATH: str = os.getenv("MAPS_IMAGES_PATH", "images/")

    # Пути к изображениям карт
    MAPS_IMAGES = {
        "festival_map": os.path.join(os.getenv("MAPS_IMAGES_PATH", "images/"), "festival_map.jpg"),
        "foodcourt": os.path.join(os.getenv("MAPS_IMAGES_PATH", "images/"), "foodcourt_map.jpg"),
        "workshops": os.path.join(os.getenv("MAPS_IMAGES_PATH", "images/"), "workshops_map.jpg"),
        "souvenirs": os.path.join(os.getenv("MAPS_IMAGES_PATH", "images/"), "souvenirs_map.jpg"),
        "toilets": os.path.join(os.getenv("MAPS_IMAGES_PATH", "images/"), "toilets_map.jpg"),
        "medical": os.path.join(os.getenv("MAPS_IMAGES_PATH", "images/"), "medical_map.jpg")
    }

    # Rate limiting настройки
    RATE_LIMIT_SETTINGS = {
        "message_timeout_seconds": 5,           # Таймаут между сообщениями (секунды)
        "hourly_message_limit": 20,             # Лимит сообщений в час
        "daily_message_limit": 100,             # Лимит сообщений в день
        "spam_block_duration_hours": 1,         # Длительность блокировки за спам (часы)
        "daily_block_duration_hours": 24        # Длительность дневной блокировки (часы)
    }

    # Настройки поддержки
    SUPPORT_SETTINGS = {
        "max_tickets_per_user": 5,              # Максимум открытых тикетов на пользователя
        "auto_close_days": 7,                   # Автозакрытие неактивных тикетов (дни)
        "urgent_response_hours": 2,             # Часы для пометки тикета как "срочный"
        "max_message_length": 4000,             # Максимальная длина сообщения
        "min_message_length": 10,               # Минимальная длина сообщения
        "allowed_file_types": [                 # Разрешенные типы файлов
            "photo", "document", "video", "audio"
        ],
        "max_file_size_mb": 20                  # Максимальный размер файла (МБ)
    }

    # Настройки мониторинга
    MONITORING_SETTINGS = {
        "health_check_interval_minutes": 5,     # Интервал проверки здоровья (минуты)
        "log_retention_days": 30,               # Хранение логов (дни)
        "stats_retention_days": 365,            # Хранение статистики (дни)
        "backup_interval_hours": 24,            # Интервал резервного копирования (часы)
        "alert_admins_on_errors": True,         # Уведомлять админов об ошибках
        "max_error_notifications_per_hour": 5   # Максимум уведомлений об ошибках в час
    }

    # Настройки безопасности
    SECURITY_SETTINGS = {
        "enable_rate_limiting": True,           # Включить ограничение скорости
        "enable_spam_detection": True,          # Включить обнаружение спама
        "block_suspicious_users": True,         # Блокировать подозрительных пользователей
        "log_all_actions": True,                # Логировать все действия
        "require_email_verification": False,    # Требовать верификацию email
        "max_login_attempts": 5,                # Максимум попыток входа
        "blacklisted_words": [                  # Черный список слов
            "spam", "casino", "viagra", "bitcoin"
        ]
    }

    # Настройки уведомлений
    NOTIFICATION_SETTINGS = {
        "notify_admins_new_tickets": True,      # Уведомлять админов о новых тикетах
        "notify_admins_urgent_tickets": True,   # Уведомлять об срочных тикетах
        "notify_admins_system_errors": True,    # Уведомлять о системных ошибках
        "notify_admins_high_load": True,        # Уведомлять о высокой нагрузке
        "daily_stats_report": True,             # Ежедневный отчет по статистике
        "weekly_summary_report": True           # Еженедельная сводка
    }

    # Текстовые шаблоны
    TEXT_TEMPLATES = {
        "welcome_message": """
🎵 Добро пожаловать на Музыкальный Фестиваль!

Привет, {user_name}! 👋

Этот бот поможет тебе:
• 📅 Узнать расписание выступлений
• 🗺 Найти нужные места на фестивале
• 🎫 Получить информацию о билетах
• 🎨 Записаться на мастер-классы
• 🆘 Связаться с поддержкой
• 💭 Оставить отзыв

Выбери нужный раздел в меню ниже ⬇️
        """,

        "support_confirmation": """
✅ Ваше обращение #{ticket_id} принято!

⏱ Мы ответим в течение 2 часов.
📱 Ответ придет прямо в этот бот.
🔔 Включите уведомления, чтобы не пропустить ответ!

💬 Вы можете продолжать писать сообщения - они будут добавлены к этому обращению.
        """,

        "rate_limit_warning": """
⏳ {reason}

Пожалуйста, подождите {wait_seconds} секунд перед отправкой следующего сообщения.
        """,

        "ticket_closed_message": """
✅ Обращение #{ticket_id} закрыто

Спасибо за обращение! 
Если возникнут новые вопросы, создайте новое обращение.

🌟 Оцените нашу работу в разделе "💭 Обратная связь"
        """,

        "feedback_thanks": """
✅ Спасибо за отзыв!

📊 Категория: {category}
🌟 Оценка: {stars} ({rating}/5)
💬 Комментарий: {has_comment}

Ваше мнение поможет нам стать лучше! 🙏
        """
    }

    # Emoji и символы
    EMOJIS = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "loading": "⏳",
        "admin": "👨‍💼",
        "support": "🧑‍💼",
        "user": "👤",
        "urgent": "🚨",
        "closed": "🔒",
        "open": "🔓",
        "new": "🆕",
        "star": "⭐",
        "fire": "🔥",
        "rocket": "🚀",
        "heart": "❤️"
    }

    @classmethod
    def get_yandex_route_url(cls, destination_coords: str, start_coords: str = None) -> str:
        """Генерация URL для маршрута в Яндекс.Картах"""
        if not start_coords:
            start_coords = cls.FESTIVAL_COORDINATES
        return f"{cls.YANDEX_MAPS_BASE_URL}{start_coords}~{destination_coords}&rtt=auto"

    def get_database_url(self) -> str:
        """Получение URL для подключения к базе данных"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    def validate_config(self) -> bool:
        """Валидация конфигурации"""
        errors = []

        # Проверка обязательных параметров
        if not self.BOT_TOKEN:
            errors.append("BOT_TOKEN is required")

        if not self.DB_PASSWORD:
            errors.append("DB_PASSWORD is required")

        if not self.ADMIN_IDS:
            errors.append("At least one ADMIN_ID is required")

        # Проверка email настроек (если включены)
        if self.EMAIL_USER and not self.EMAIL_PASSWORD:
            errors.append("EMAIL_PASSWORD is required when EMAIL_USER is set")

        # Проверка групп и каналов
        if self.SUPPORT_GROUP_ID and not self.SUPPORT_GROUP_ID.startswith('-'):
            errors.append("SUPPORT_GROUP_ID should start with '-'")

        if self.FEEDBACK_CHANNEL_ID and not self.FEEDBACK_CHANNEL_ID.startswith('-'):
            errors.append("FEEDBACK_CHANNEL_ID should start with '-'")

        if errors:
            print("Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            return False

        return True

    def get_admin_usernames(self) -> List[str]:
        """Получение списка username администраторов (если известны)"""
        # Здесь можно добавить маппинг ID -> username для удобства
        admin_usernames = {
            # Пример: 123456789: "@admin_user"
        }
        return [admin_usernames.get(admin_id, f"ID:{admin_id}") for admin_id in self.ADMIN_IDS]

    def get_support_staff_usernames(self) -> List[str]:
        """Получение списка username сотрудников поддержки"""
        staff_usernames = {
            # Пример: 111222333: "@support_user"
        }
        return [staff_usernames.get(staff_id, f"ID:{staff_id}") for staff_id in self.SUPPORT_STAFF_IDS]

    def is_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь администратором"""
        return user_id in self.ADMIN_IDS

    def is_support_staff(self, user_id: int) -> bool:
        """Проверка, является ли пользователь сотрудником поддержки"""
        return user_id in self.SUPPORT_STAFF_IDS

    def has_support_access(self, user_id: int) -> bool:
        """Проверка, имеет ли пользователь доступ к поддержке"""
        return self.is_admin(user_id) or self.is_support_staff(user_id)

    def get_user_role(self, user_id: int) -> str:
        """Получение роли пользователя"""
        if self.is_admin(user_id):
            return "admin"
        elif self.is_support_staff(user_id):
            return "support"
        else:
            return "user"

    def get_formatted_template(self, template_name: str, **kwargs) -> str:
        """Получение отформатированного шаблона"""
        template = self.TEXT_TEMPLATES.get(template_name, "")
        try:
            return template.format(**kwargs)
        except KeyError as e:
            print(f"Missing template variable: {e}")
            return template

    def get_rate_limit_config(self) -> dict:
        """Получение конфигурации rate limiting"""
        return self.RATE_LIMIT_SETTINGS

    def get_support_config(self) -> dict:
        """Получение конфигурации поддержки"""
        return self.SUPPORT_SETTINGS

    def get_monitoring_config(self) -> dict:
        """Получение конфигурации мониторинга"""
        return self.MONITORING_SETTINGS

    def get_security_config(self) -> dict:
        """Получение конфигурации безопасности"""
        return self.SECURITY_SETTINGS

    def get_notification_config(self) -> dict:
        """Получение конфигурации уведомлений"""
        return self.NOTIFICATION_SETTINGS

    @property
    def debug_mode(self) -> bool:
        """Режим отладки"""
        return os.getenv("DEBUG", "false").lower() == "true"

    @property
    def log_level(self) -> str:
        """Уровень логирования"""
        return os.getenv("LOG_LEVEL", "INFO").upper()

    @property
    def environment(self) -> str:
        """Окружение (development, staging, production)"""
        return os.getenv("ENVIRONMENT", "development").lower()

    def __post_init__(self):
        """Пост-инициализация конфигурации"""
        # Валидация при создании объекта
        if not self.validate_config():
            raise ValueError("Invalid configuration")

        # Создание директорий если они не существуют
        import pathlib
        pathlib.Path("logs").mkdir(exist_ok=True)
        pathlib.Path("backups").mkdir(exist_ok=True)
        pathlib.Path(self.MAPS_IMAGES_PATH).mkdir(exist_ok=True)

# Создание глобального объекта конфигурации
config = Config()

# Проверка конфигурации при импорте
if __name__ == "__main__":
    if config.validate_config():
        print("✅ Configuration is valid")
        print(f"📊 Environment: {config.environment}")
        print(f"🔍 Debug mode: {config.debug_mode}")
        print(f"📝 Log level: {config.log_level}")
        print(f"👥 Admins: {len(config.ADMIN_IDS)}")
        print(f"🧑‍💼 Support staff: {len(config.SUPPORT_STAFF_IDS)}")
        print(f"💾 Database: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
        print(f"📧 Email configured: {'Yes' if config.EMAIL_USER else 'No'}")
        print(f"🏪 Support group: {'Yes' if config.SUPPORT_GROUP_ID else 'No'}")
        print(f"📢 Feedback channel: {'Yes' if config.FEEDBACK_CHANNEL_ID else 'No'}")
    else:
        print("❌ Configuration validation failed")
        exit(1)