import os
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # Telegram Bot настройки
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # База данных
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "festival_bot")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    # Администраторы и сотрудники поддержки (ИСПРАВЛЕНО)
    ADMIN_IDS: List[int] = field(default_factory=lambda: [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()])
    SUPPORT_STAFF_IDS: List[int] = field(default_factory=lambda: [int(x) for x in os.getenv("SUPPORT_STAFF_IDS", "").split(",") if x.strip()])

    # Каналы и группы
    SUPPORT_GROUP_ID: Optional[str] = os.getenv("SUPPORT_GROUP_ID")
    SUPPORT_GROUP_TOPICS: bool = os.getenv("SUPPORT_GROUP_TOPICS", "true").lower() == "true"
    FEEDBACK_CHANNEL_ID: Optional[str] = os.getenv("FEEDBACK_CHANNEL_ID")

    # Email настройки
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    EMAIL_USER: Optional[str] = os.getenv("EMAIL_USER")
    EMAIL_PASSWORD: Optional[str] = os.getenv("EMAIL_PASSWORD")
    SUPPORT_EMAIL: Optional[str] = os.getenv("SUPPORT_EMAIL")

    # Социальные сети (ИСПРАВЛЕНО)
    SOCIAL_LINKS: Dict[str, str] = field(default_factory=lambda: {
        "Instagram": "https://instagram.com/festival",
        "VK": "https://vk.com/festival",
        "Telegram": "https://t.me/festival_channel",
        "YouTube": "https://youtube.com/festival",
        "Spotify": "https://open.spotify.com/festival"
    })

    # Билеты
    TICKET_PURCHASE_URL: str = os.getenv("TICKET_PURCHASE_URL", "https://tickets.festival.com")

    # Яндекс.Карты маршруты
    YANDEX_MAPS_BASE_URL: str = "https://yandex.ru/maps/?rtext="

    # Координаты фестиваля (основная точка)
    FESTIVAL_COORDINATES: str = os.getenv("FESTIVAL_COORDINATES", "55.7558,37.6176")

    # Координаты ключевых единичных точек (ИСПРАВЛЕНО)
    SINGLE_LOCATIONS_COORDINATES: Dict[str, str] = field(default_factory=lambda: {
        "foodcourt": os.getenv("FOODCOURT_COORDINATES", "55.7562,37.6174"),
        "workshops": os.getenv("WORKSHOPS_COORDINATES", "55.7556,37.6182"),
        "main_stage": os.getenv("MAIN_STAGE_COORDINATES", "55.7558,37.6176"),
        "small_stage": os.getenv("SMALL_STAGE_COORDINATES", "55.7560,37.6180"),
        "lecture_hall": os.getenv("LECTURE_HALL_COORDINATES", "55.7559,37.6179"),
    })

    # Пути к изображениям карт
    MAPS_IMAGES_PATH: str = os.getenv("MAPS_IMAGES_PATH", "images/")

    # Пути к изображениям карт (ИСПРАВЛЕНО)
    MAPS_IMAGES: Dict[str, str] = field(default_factory=lambda: {
        "festival_map": os.path.join(os.getenv("MAPS_IMAGES_PATH", "images/"), "festival_map.jpg"),
        "main_stage": os.path.join(os.getenv("MAPS_IMAGES_PATH", "images/"), "main_stage_map.jpg"),
        "small_stage": os.path.join(os.getenv("MAPS_IMAGES_PATH", "images/"), "small_stage_map.jpg"),
        "lecture_hall": os.path.join(os.getenv("MAPS_IMAGES_PATH", "images/"), "lecture_hall_map.jpg"),
        "foodcourt": os.path.join(os.getenv("MAPS_IMAGES_PATH", "images/"), "foodcourt_map.jpg"),
        "workshops": os.path.join(os.getenv("MAPS_IMAGES_PATH", "images/"), "workshops_map.jpg"),
        "souvenirs": os.path.join(os.getenv("MAPS_IMAGES_PATH", "images/"), "souvenirs_map.jpg"),
        "toilets": os.path.join(os.getenv("MAPS_IMAGES_PATH", "images/"), "toilets_map.jpg"),
        "medical": os.path.join(os.getenv("MAPS_IMAGES_PATH", "images/"), "medical_map.jpg")
    })

    # Информация о локациях для отображения (ИСПРАВЛЕНО)
    LOCATIONS_INFO: Dict[str, Dict[str, any]] = field(default_factory=lambda: {
        "main_stage": {
            "title": "🎤 Главная сцена",
            "description": "Основная концертная площадка фестиваля",
            "details": [
                "🎵 Главные хедлайнеры",
                "🔊 Профессиональная звуковая система",
                "💡 Световое шоу",
                "📺 Большие экраны",
                "👥 Вместимость: 5000 человек"
            ]
        },
        "small_stage": {
            "title": "🎭 Малая сцена",
            "description": "Камерная площадка для небольших составов",
            "details": [
                "🎶 Камерные выступления",
                "🎸 Инди и альтернатива",
                "🎤 Молодые исполнители",
                "🎺 Джаз и блюз",
                "👥 Вместимость: 1000 человек"
            ]
        },
        "lecture_hall": {
            "title": "🎓 Лекционный зал",
            "description": "Образовательная зона для лекций и семинаров",
            "details": [
                "📚 Лекции о музыке",
                "🎼 Мастер-классы теории",
                "💼 Музыкальный бизнес",
                "🧠 Психология творчества",
                "👥 Вместимость: 200 человек"
            ]
        },
        "foodcourt": {
            "title": "🍕 Фудкорт",
            "description": "Зона питания с различными кафе и ресторанами",
            "details": [
                "🍕 Пицца и итальянская кухня",
                "🍔 Бургеры и фаст-фуд",
                "🥗 Здоровое питание",
                "☕ Кофе и напитки",
                "🍰 Десерты и выпечка"
            ]
        },
        "workshops": {
            "title": "🎨 Зона мастер-классов",
            "description": "Образовательная зона с творческими мастер-классами",
            "details": [
                "🎸 Музыкальные инструменты",
                "🎤 Вокальные техники",
                "💻 Создание музыки",
                "✍️ Написание песен",
                "🎧 Звукорежиссура"
            ]
        },
        "souvenirs": {
            "title": "🛍 Сувенирные магазины",
            "description": "Официальная сувенирная продукция фестиваля",
            "details": [
                "👕 Футболки и толстовки",
                "🧢 Кепки и головные уборы",
                "🎸 Музыкальные аксессуары",
                "📀 Диски и винил",
                "🎁 Подарочные наборы"
            ]
        },
        "toilets": {
            "title": "🚻 Туалеты",
            "description": "Санитарные зоны на территории фестиваля",
            "details": [
                "🚹 Мужские туалеты",
                "🚺 Женские туалеты",
                "♿ Для людей с ограниченными возможностями",
                "👶 Пеленальные комнаты",
                "🧼 Умывальники"
            ]
        },
        "medical": {
            "title": "🏥 Медицинские пункты",
            "description": "Медицинская помощь и первая помощь",
            "details": [
                "🩺 Врачи и медсестры",
                "💊 Базовые медикаменты",
                "🚑 Связь с скорой помощью",
                "📞 Экстренная связь: 112",
                "⚕️ Круглосуточно"
            ]
        }
    })

    # Rate limiting настройки (ИСПРАВЛЕНО)
    RATE_LIMIT_SETTINGS: Dict[str, int] = field(default_factory=lambda: {
        "message_timeout_seconds": 5,
        "hourly_message_limit": 20,
        "daily_message_limit": 100,
        "spam_block_duration_hours": 1,
        "daily_block_duration_hours": 24
    })

    # Настройки поддержки (ИСПРАВЛЕНО)
    SUPPORT_SETTINGS: Dict[str, any] = field(default_factory=lambda: {
        "max_tickets_per_user": 5,
        "auto_close_days": 7,
        "urgent_response_hours": 2,
        "max_message_length": 4000,
        "min_message_length": 10,
        "allowed_file_types": ["photo", "document", "video", "audio"],
        "max_file_size_mb": 20
    })

    # Настройки критических отзывов (ИСПРАВЛЕНО)
    CRITICAL_FEEDBACK_SETTINGS: Dict[str, any] = field(default_factory=lambda: {
        "critical_rating_threshold": 2,
        "urgent_rating_threshold": 1,
        "notify_admins": True,
        "notify_support_group": True,
        "auto_create_ticket": False,
        "require_immediate_action": True,
        "max_critical_per_hour": 5,
        "escalation_delay_hours": 2,
    })

    # Рекомендации по категориям для критических отзывов (ИСПРАВЛЕНО)
    CATEGORY_RECOMMENDATIONS: Dict[str, List[str]] = field(default_factory=lambda: {
        "festival": [
            "Проверить общую организацию мероприятия",
            "Рассмотреть жалобы на безопасность или комфорт",
            "Проанализировать работу всех служб",
            "Связаться с руководством фестиваля"
        ],
        "food": [
            "Проверить качество еды и обслуживания в фудкорте",
            "Связаться с поставщиками питания",
            "Проверить санитарные условия",
            "Рассмотреть ценовую политику",
            "Проконтролировать время ожидания"
        ],
        "workshops": [
            "Связаться с ведущими мастер-классов",
            "Проверить качество материалов и оборудования",
            "Рассмотреть организацию пространства",
            "Проанализировать программу мастер-классов",
            "Проверить уровень подготовки инструкторов"
        ],
        "lectures": [
            "Связаться с лекторами",
            "Проверить качество звука и видимость",
            "Рассмотреть содержание программы",
            "Проанализировать организацию лектория",
            "Проверить комфорт аудитории"
        ],
        "infrastructure": [
            "Проверить состояние туалетов и медпунктов",
            "Рассмотреть навигацию и указатели",
            "Проанализировать безопасность территории",
            "Проверить доступность для людей с ограниченными возможностями",
            "Улучшить освещение и чистоту"
        ]
    })

    # Настройки мониторинга (ИСПРАВЛЕНО)
    MONITORING_SETTINGS: Dict[str, any] = field(default_factory=lambda: {
        "health_check_interval_minutes": 5,
        "log_retention_days": 30,
        "stats_retention_days": 365,
        "backup_interval_hours": 24,
        "alert_admins_on_errors": True,
        "max_error_notifications_per_hour": 5
    })

    # Настройки безопасности (ИСПРАВЛЕНО)
    SECURITY_SETTINGS: Dict[str, any] = field(default_factory=lambda: {
        "enable_rate_limiting": True,
        "enable_spam_detection": True,
        "block_suspicious_users": True,
        "log_all_actions": True,
        "require_email_verification": False,
        "max_login_attempts": 5,
        "blacklisted_words": ["spam", "casino", "viagra", "bitcoin"]
    })

    # Настройки уведомлений (ИСПРАВЛЕНО)
    NOTIFICATION_SETTINGS: Dict[str, bool] = field(default_factory=lambda: {
        "notify_admins_new_tickets": True,
        "notify_admins_urgent_tickets": True,
        "notify_admins_system_errors": True,
        "notify_admins_high_load": True,
        "notify_admins_critical_feedback": True,
        "daily_stats_report": True,
        "weekly_summary_report": True
    })

    # Текстовые шаблоны (ИСПРАВЛЕНО)
    TEXT_TEMPLATES: Dict[str, str] = field(default_factory=lambda: {
        "welcome_message": """
🎵 Добро пожаловать на Музыкальный Фестиваль!

Привет, {user_name}! 👋

Этот бот поможет тебе:
- 📅 Узнать расписание выступлений
- 🗺 Найти нужные места на фестивале
- 🎫 Получить информацию о билетах
- 🎨 Записаться на мастер-классы
- 🆘 Связаться с поддержкой
- 💭 Оставить отзыв

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
        """,

        "critical_feedback_admin": """
🚨 {severity} ОТЗЫВ

📊 Категория: {category_name}
🌟 Оценка: {stars} ({rating}/5)
⚡ Приоритет: {priority}

👤 От пользователя:
- Имя: {user_name}
- Username: @{username}
- ID: {user_id}

💬 Комментарий:
{comment}

⏰ Время: {timestamp}

🎯 РЕКОМЕНДУЕМЫЕ ДЕЙСТВИЯ:
{recommendations}

📞 КОНТАКТ С ПОЛЬЗОВАТЕЛЕМ:
- Telegram: @{username}
- ID для связи: {user_id}

💡 Этот отзыв требует оперативного внимания!
        """,

        "critical_feedback_support_group": """
🚨 КРИТИЧЕСКИЙ ОТЗЫВ ТРЕБУЕТ ВНИМАНИЯ

📊 {category_name}: {stars} ({rating}/5)
👤 {user_name} (@{username})

💬 "{comment}"

🎯 Кто-то может связаться с пользователем для решения проблемы?
        """,

        "critical_feedback_user_response": """
😔 Спасибо за честный отзыв

📊 Категория: {category_name}
🌟 Оценка: {stars} ({rating}/5)
💬 Комментарий: {comment_status}

Мы очень сожалеем о негативном опыте и обязательно разберемся с ситуацией.

🔧 Наши администраторы уже уведомлены о проблеме.
📞 Если нужна срочная помощь, обратитесь в поддержку: /start → 🆘 Поддержка

💙 Мы ценим ваше мнение и работаем над улучшениями!
        """,

        "neutral_feedback_user_response": """
🤔 Спасибо за честную оценку

📊 Категория: {category_name}
🌟 Оценка: {stars} ({rating}/5)
💬 Комментарий: {comment_status}

Ваше мнение поможет нам стать лучше!

💡 Если есть конкретные предложения по улучшению, напишите в поддержку.
        """,

        "positive_feedback_user_response": """
🎉 Спасибо за отличный отзыв!

📊 Категория: {category_name}
🌟 Оценка: {stars} ({rating}/5)
💬 Комментарий: {comment_status}

Мы рады, что вам понравилось!

🌟 Поделитесь впечатлениями с друзьями в наших соцсетях!
        """
    })

    # Emoji и символы (ИСПРАВЛЕНО)
    EMOJIS: Dict[str, str] = field(default_factory=lambda: {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "loading": "⏳",
        "admin": "👨‍💼",
        "support": "🧑‍💼",
        "user": "👤",
        "urgent": "🚨",
        "critical": "🔴",
        "high": "🟡",
        "closed": "🔒",
        "open": "🔓",
        "new": "🆕",
        "star": "⭐",
        "fire": "🔥",
        "rocket": "🚀",
        "heart": "❤️"
    })

    # Множественные локации (метод)
    def get_multiple_locations(self) -> Dict[str, List[Dict[str, str]]]:
        """Получение множественных локаций с названиями"""
        locations = {}

        # Сувениры
        souvenirs_coords = os.getenv("SOUVENIRS_COORDINATES", "55.7560,37.6170").split(";")
        souvenirs_names = os.getenv("SOUVENIRS_NAMES", "Сувенирный магазин").split(";")
        locations["souvenirs"] = [
            {"name": name.strip(), "coordinates": coord.strip()}
            for name, coord in zip(souvenirs_names, souvenirs_coords)
        ]

        # Туалеты
        toilets_coords = os.getenv("TOILETS_COORDINATES", "55.7559,37.6178").split(";")
        toilets_names = os.getenv("TOILETS_NAMES", "Туалеты").split(";")
        locations["toilets"] = [
            {"name": name.strip(), "coordinates": coord.strip()}
            for name, coord in zip(toilets_names, toilets_coords)
        ]

        # Медпункты
        medical_coords = os.getenv("MEDICAL_COORDINATES", "55.7558,37.6176").split(";")
        medical_names = os.getenv("MEDICAL_NAMES", "Медпункт").split(";")
        locations["medical"] = [
            {"name": name.strip(), "coordinates": coord.strip()}
            for name, coord in zip(medical_names, medical_coords)
        ]

        return locations

    @property
    def MULTIPLE_LOCATIONS(self) -> Dict[str, List[Dict[str, str]]]:
        """Получение множественных локаций с названиями"""
        return self.get_multiple_locations()

    @classmethod
    def get_yandex_route_url(cls, destination_coords: str, start_coords: str = None) -> str:
        """Генерация URL для маршрута в Яндекс.Картах"""
        if not start_coords:
            start_coords = os.getenv("FESTIVAL_COORDINATES", "55.7558,37.6176")
        return f"https://yandex.ru/maps/?rtext={start_coords}~{destination_coords}&rtt=auto"

    def get_location_coordinates(self, location_type: str, location_index: int = 0) -> str:
        """Получение координат локации по типу и индексу"""
        # Для единичных локаций
        if location_type in self.SINGLE_LOCATIONS_COORDINATES:
            return self.SINGLE_LOCATIONS_COORDINATES[location_type]

        # Для множественных локаций
        multiple_locations = self.MULTIPLE_LOCATIONS
        if location_type in multiple_locations:
            locations = multiple_locations[location_type]
            if 0 <= location_index < len(locations):
                return locations[location_index]["coordinates"]

        # По умолчанию возвращаем координаты фестиваля
        return self.FESTIVAL_COORDINATES

    def get_location_name(self, location_type: str, location_index: int = 0) -> str:
        """Получение названия локации по типу и индексу"""
        # Для множественных локаций
        multiple_locations = self.MULTIPLE_LOCATIONS
        if location_type in multiple_locations:
            locations = multiple_locations[location_type]
            if 0 <= location_index < len(locations):
                return locations[location_index]["name"]

        # Для единичных локаций возвращаем стандартное название
        location_titles = {
            "main_stage": "Главная сцена",
            "small_stage": "Малая сцена",
            "lecture_hall": "Лекционный зал",
            "foodcourt": "Фудкорт",
            "workshops": "Мастер-классы"
        }

        return location_titles.get(location_type, "Неизвестная локация")

    def get_all_locations_of_type(self, location_type: str) -> List[Dict[str, str]]:
        """Получение всех локаций определенного типа"""
        multiple_locations = self.MULTIPLE_LOCATIONS
        if location_type in multiple_locations:
            return multiple_locations[location_type]

        # Для единичных локаций
        if location_type in self.SINGLE_LOCATIONS_COORDINATES:
            return [{
                "name": self.get_location_name(location_type),
                "coordinates": self.SINGLE_LOCATIONS_COORDINATES[location_type]
            }]

        return []

    def get_critical_feedback_config(self) -> dict:
        """Получение конфигурации критических отзывов"""
        return self.CRITICAL_FEEDBACK_SETTINGS

    def get_category_recommendations(self, category: str) -> List[str]:
        """Получение рекомендаций по категории"""
        base_recommendations = [
            "Связаться с пользователем для уточнения проблемы",
            "Проанализировать ситуацию и принять меры"
        ]

        category_specific = self.CATEGORY_RECOMMENDATIONS.get(category, [])
        return base_recommendations + category_specific

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

        # Проверка координат
        def validate_coordinates(coords_str: str, name: str):
            try:
                for coord_pair in coords_str.split(";"):
                    lat, lng = coord_pair.strip().split(",")
                    float(lat.strip())
                    float(lng.strip())
            except (ValueError, IndexError):
                errors.append(f"Invalid coordinates format for {name}: {coords_str}")

        # Проверяем основные координаты
        validate_coordinates(self.FESTIVAL_COORDINATES, "FESTIVAL_COORDINATES")

        # Проверяем множественные координаты
        try:
            for location_type in ["souvenirs", "toilets", "medical"]:
                locations = self.get_all_locations_of_type(location_type)
                for i, location in enumerate(locations):
                    validate_coordinates(location["coordinates"], f"{location_type}[{i}]")
        except Exception as e:
            errors.append(f"Error validating multiple locations: {str(e)}")

        if errors:
            print("Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            return False

        return True

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

        # Показываем информацию о локациях
        print(f"\n📍 Locations configured:")
        try:
            for location_type in ["souvenirs", "toilets", "medical"]:
                locations = config.get_all_locations_of_type(location_type)
                print(f"  {location_type}: {len(locations)} points")
                for i, loc in enumerate(locations):
                    print(f"    {i+1}. {loc['name']} ({loc['coordinates']})")
        except Exception as e:
            print(f"  Error loading locations: {e}")

        # Показываем настройки критических отзывов
        critical_config = config.get_critical_feedback_config()
        print(f"\n🚨 Critical feedback settings:")
        print(f"  Critical threshold: <= {critical_config['critical_rating_threshold']} stars")
        print(f"  Urgent threshold: <= {critical_config['urgent_rating_threshold']} stars")
        print(f"  Notify admins: {critical_config['notify_admins']}")
        print(f"  Notify support group: {critical_config['notify_support_group']}")
    else:
        print("❌ Configuration validation failed")
        exit(1)