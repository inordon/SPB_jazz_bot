import asyncio
import asyncpg
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

    async def create_pool(self):
        """Создание пула соединений с БД"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("Database pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise

    async def close_pool(self):
        """Закрытие пула соединений"""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")

    @asynccontextmanager
    async def get_connection(self):
        """Контекстный менеджер для получения соединения"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        async with self.pool.acquire() as connection:
            yield connection

    async def init_tables(self):
        """Инициализация таблиц БД"""
        async with self.get_connection() as conn:
            # Пользователи
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    language_code VARCHAR(10),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Обращения в поддержку
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(id),
                    email VARCHAR(255),
                    message TEXT,
                    photo_file_id VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Отзывы
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(id),
                    category VARCHAR(100),
                    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Расписание
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schedule (
                    id SERIAL PRIMARY KEY,
                    day INTEGER CHECK (day >= 1 AND day <= 5),
                    time TIME,
                    artist_name VARCHAR(255),
                    stage VARCHAR(100),
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Локации
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS locations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE,
                    description TEXT,
                    coordinates VARCHAR(100),
                    map_image_url VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Активности
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255),
                    type VARCHAR(100),
                    description TEXT,
                    schedule_info TEXT,
                    location VARCHAR(255),
                    registration_required BOOLEAN DEFAULT FALSE,
                    registration_url VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Статистика использования
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(id),
                    action VARCHAR(255),
                    details JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            logger.info("Database tables initialized successfully")

    # Методы для работы с пользователями
    async def add_user(self, user_id: int, username: str = None,
                       first_name: str = None, last_name: str = None,
                       language_code: str = None):
        """Добавление нового пользователя"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO users (id, username, first_name, last_name, language_code)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    language_code = EXCLUDED.language_code,
                    last_activity = CURRENT_TIMESTAMP
            """, user_id, username, first_name, last_name, language_code)

    async def update_user_activity(self, user_id: int):
        """Обновление времени последней активности пользователя"""
        async with self.get_connection() as conn:
            await conn.execute("""
                UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE id = $1
            """, user_id)

    # Методы для поддержки
    async def create_support_ticket(self, user_id: int, email: str,
                                    message: str, photo_file_id: str = None) -> int:
        """Создание тикета поддержки"""
        async with self.get_connection() as conn:
            ticket_id = await conn.fetchval("""
                INSERT INTO support_tickets (user_id, email, message, photo_file_id)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """, user_id, email, message, photo_file_id)
            return ticket_id

    async def get_support_tickets(self, status: str = None) -> List[Dict]:
        """Получение тикетов поддержки"""
        async with self.get_connection() as conn:
            if status:
                rows = await conn.fetch("""
                    SELECT st.*, u.username, u.first_name, u.last_name
                    FROM support_tickets st
                    JOIN users u ON st.user_id = u.id
                    WHERE st.status = $1
                    ORDER BY st.created_at DESC
                """, status)
            else:
                rows = await conn.fetch("""
                    SELECT st.*, u.username, u.first_name, u.last_name
                    FROM support_tickets st
                    JOIN users u ON st.user_id = u.id
                    ORDER BY st.created_at DESC
                """)
            return [dict(row) for row in rows]

    # Методы для отзывов
    async def add_feedback(self, user_id: int, category: str,
                           rating: int, comment: str = None):
        """Добавление отзыва"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO feedback (user_id, category, rating, comment)
                VALUES ($1, $2, $3, $4)
            """, user_id, category, rating, comment)

    async def get_feedback_stats(self) -> Dict:
        """Получение статистики отзывов"""
        async with self.get_connection() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_feedback,
                    AVG(rating) as average_rating,
                    COUNT(DISTINCT user_id) as unique_users
                FROM feedback
            """)

            category_stats = await conn.fetch("""
                SELECT 
                    category,
                    COUNT(*) as count,
                    AVG(rating) as avg_rating
                FROM feedback
                GROUP BY category
                ORDER BY count DESC
            """)

            return {
                "total": dict(stats),
                "by_category": [dict(row) for row in category_stats]
            }

    # Методы для расписания
    async def get_schedule_by_day(self, day: int) -> List[Dict]:
        """Получение расписания по дню"""
        async with self.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT * FROM schedule
                WHERE day = $1
                ORDER BY time
            """, day)
            return [dict(row) for row in rows]

    async def add_schedule_item(self, day: int, time: str, artist_name: str,
                                stage: str, description: str = None):
        """Добавление элемента расписания"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO schedule (day, time, artist_name, stage, description)
                VALUES ($1, $2, $3, $4, $5)
            """, day, time, artist_name, stage, description)

    # Статистика
    async def log_user_action(self, user_id: int, action: str, details: Dict = None):
        """Логирование действий пользователя"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO usage_stats (user_id, action, details)
                VALUES ($1, $2, $3)
            """, user_id, action, details)

    async def get_usage_stats(self) -> Dict:
        """Получение статистики использования"""
        async with self.get_connection() as conn:
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            total_actions = await conn.fetchval("SELECT COUNT(*) FROM usage_stats")

            popular_actions = await conn.fetch("""
                SELECT action, COUNT(*) as count
                FROM usage_stats
                GROUP BY action
                ORDER BY count DESC
                LIMIT 10
            """)

            return {
                "total_users": total_users,
                "total_actions": total_actions,
                "popular_actions": [dict(row) for row in popular_actions]
            }