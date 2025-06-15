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

    # Администраторы
    ADMIN_IDS: List[int] = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

    # Каналы и группы
    SUPPORT_GROUP_ID: str = os.getenv("SUPPORT_GROUP_ID")
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

    # Яндекс.Карты маршруты
    YANDEX_MAPS_BASE_URL = "https://yandex.ru/maps/?rtext="

    # Координаты фестиваля (основная точка)
    FESTIVAL_COORDINATES = "55.7558,37.6176"  # Широта, долгота

    # Координаты ключевых точек фестиваля
    LOCATIONS_COORDINATES = {
        "foodcourt": "55.7562,37.6174",      # Фудкорт
        "workshops": "55.7556,37.6182",      # Мастер-классы
        "souvenirs": "55.7560,37.6170",      # Сувениры
        "toilets": "55.7559,37.6178",        # Туалеты
        "medical": "55.7558,37.6176",        # Медпункт
    }

    # Пути к изображениям карт
    MAPS_IMAGES = {
        "festival_map": "images/festival_map.jpg",
        "foodcourt": "images/foodcourt_map.jpg",
        "workshops": "images/workshops_map.jpg",
        "souvenirs": "images/souvenirs_map.jpg",
        "toilets": "images/toilets_map.jpg",
        "medical": "images/medical_map.jpg"
    }

    @classmethod
    def get_yandex_route_url(cls, destination_coords: str, start_coords: str = None) -> str:
        """Генерация URL для маршрута в Яндекс.Картах"""
        if not start_coords:
            start_coords = cls.FESTIVAL_COORDINATES
        return f"{cls.YANDEX_MAPS_BASE_URL}{start_coords}~{destination_coords}&rtt=auto"

    # Пути к изображениям карт (добавить в конфигурацию)
    MAPS_IMAGES_PATH: str = os.getenv("MAPS_IMAGES_PATH", "images/")

    def get_database_url(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

config = Config()