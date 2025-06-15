import asyncio
import asyncpg
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
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

            # Обращения в поддержку (обновленная версия)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(id),
                    email VARCHAR(255),
                    message TEXT,
                    photo_file_id VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'open',
                    thread_id INTEGER,
                    initial_message_id INTEGER,
                    is_closed BOOLEAN DEFAULT FALSE,
                    closed_at TIMESTAMP,
                    last_user_message_at TIMESTAMP,
                    last_staff_response_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Сообщения в диалоге тикета
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ticket_messages (
                    id SERIAL PRIMARY KEY,
                    ticket_id INTEGER REFERENCES support_tickets(id) ON DELETE CASCADE,
                    user_id BIGINT,
                    is_staff BOOLEAN DEFAULT FALSE,
                    is_admin BOOLEAN DEFAULT FALSE,
                    message_text TEXT,
                    photo_file_id VARCHAR(255),
                    document_file_id VARCHAR(255),
                    video_file_id VARCHAR(255),
                    message_type VARCHAR(50) DEFAULT 'text',
                    thread_message_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Защита от спама
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_rate_limits (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_count_hour INTEGER DEFAULT 1,
                    message_count_day INTEGER DEFAULT 1,
                    is_rate_limited BOOLEAN DEFAULT FALSE,
                    rate_limit_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Метрики поддержки
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS support_metrics (
                    id SERIAL PRIMARY KEY,
                    date DATE DEFAULT CURRENT_DATE,
                    tickets_created INTEGER DEFAULT 0,
                    tickets_closed INTEGER DEFAULT 0,
                    messages_from_users INTEGER DEFAULT 0,
                    messages_from_staff INTEGER DEFAULT 0,
                    avg_response_time_minutes INTEGER DEFAULT 0,
                    total_response_time_minutes INTEGER DEFAULT 0,
                    responses_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date)
                )
            """)

            # Ответы сотрудников поддержки и администраторов (старая таблица - оставляем для совместимости)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS support_responses (
                    id SERIAL PRIMARY KEY,
                    ticket_id INTEGER REFERENCES support_tickets(id),
                    staff_user_id BIGINT,
                    response_text TEXT,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

            # Создание индексов
            await self._create_indexes(conn)

            logger.info("Database tables initialized successfully")

    async def _create_indexes(self, conn):
        """Создание индексов для производительности"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity)",
            "CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status)",
            "CREATE INDEX IF NOT EXISTS idx_support_tickets_thread_id ON support_tickets(thread_id)",
            "CREATE INDEX IF NOT EXISTS idx_support_tickets_is_closed ON support_tickets(is_closed)",
            "CREATE INDEX IF NOT EXISTS idx_support_tickets_last_user_message ON support_tickets(last_user_message_at)",
            "CREATE INDEX IF NOT EXISTS idx_ticket_messages_ticket_id ON ticket_messages(ticket_id)",
            "CREATE INDEX IF NOT EXISTS idx_ticket_messages_created_at ON ticket_messages(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_ticket_messages_user_id ON ticket_messages(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_rate_limits_user_id ON user_rate_limits(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_support_metrics_date ON support_metrics(date)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_category ON feedback(category)",
            "CREATE INDEX IF NOT EXISTS idx_schedule_day ON schedule(day)",
            "CREATE INDEX IF NOT EXISTS idx_usage_stats_action ON usage_stats(action)",
            "CREATE INDEX IF NOT EXISTS idx_usage_stats_created_at ON usage_stats(created_at)"
        ]

        for index_sql in indexes:
            try:
                await conn.execute(index_sql)
            except Exception as e:
                logger.warning(f"Failed to create index: {e}")

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

    # Методы для защиты от спама
    async def check_rate_limit(self, user_id: int) -> Dict[str, Any]:
        """Проверка ограничений скорости для пользователя"""
        async with self.get_connection() as conn:
            now = datetime.now()

            # Получаем или создаем запись о лимитах пользователя
            rate_limit = await conn.fetchrow("""
                SELECT * FROM user_rate_limits WHERE user_id = $1
            """, user_id)

            if not rate_limit:
                # Создаем новую запись
                await conn.execute("""
                    INSERT INTO user_rate_limits (user_id, last_message_at, message_count_hour, message_count_day)
                    VALUES ($1, $2, 1, 1)
                """, user_id, now)
                return {"can_send": True, "wait_seconds": 0, "reason": ""}

            last_message_at = rate_limit['last_message_at']

            # Проверяем глобальную блокировку
            if rate_limit['is_rate_limited'] and rate_limit['rate_limit_until'] and now < rate_limit['rate_limit_until']:
                wait_seconds = int((rate_limit['rate_limit_until'] - now).total_seconds())
                return {
                    "can_send": False,
                    "wait_seconds": wait_seconds,
                    "reason": f"Превышен лимит сообщений. Попробуйте через {wait_seconds} секунд."
                }

            # Проверяем таймаут между сообщениями (5 секунд)
            time_since_last = (now - last_message_at).total_seconds()
            if time_since_last < 5:
                wait_seconds = int(5 - time_since_last)
                return {
                    "can_send": False,
                    "wait_seconds": wait_seconds,
                    "reason": f"Подождите {wait_seconds} секунд перед отправкой следующего сообщения."
                }

            # Обновляем счетчики
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(days=1)

            # Считаем сообщения за последний час и день
            hour_count = await conn.fetchval("""
                SELECT COUNT(*) FROM ticket_messages 
                WHERE user_id = $1 AND is_staff = FALSE AND created_at > $2
            """, user_id, hour_ago)

            day_count = await conn.fetchval("""
                SELECT COUNT(*) FROM ticket_messages 
                WHERE user_id = $1 AND is_staff = FALSE AND created_at > $2
            """, user_id, day_ago)

            # Проверяем лимиты (20 сообщений в час, 100 в день)
            if hour_count >= 20:
                rate_limit_until = now + timedelta(hours=1)
                await conn.execute("""
                    UPDATE user_rate_limits 
                    SET is_rate_limited = TRUE, rate_limit_until = $2, updated_at = $3
                    WHERE user_id = $1
                """, user_id, rate_limit_until, now)
                return {
                    "can_send": False,
                    "wait_seconds": 3600,
                    "reason": "Превышен лимит сообщений в час (20). Попробуйте через час."
                }

            if day_count >= 100:
                rate_limit_until = now + timedelta(hours=24)
                await conn.execute("""
                    UPDATE user_rate_limits 
                    SET is_rate_limited = TRUE, rate_limit_until = $2, updated_at = $3
                    WHERE user_id = $1
                """, user_id, rate_limit_until, now)
                return {
                    "can_send": False,
                    "wait_seconds": 86400,
                    "reason": "Превышен дневной лимит сообщений (100). Попробуйте завтра."
                }

            # Обновляем время последнего сообщения
            await conn.execute("""
                UPDATE user_rate_limits 
                SET last_message_at = $2, message_count_hour = $3, message_count_day = $4, 
                    is_rate_limited = FALSE, rate_limit_until = NULL, updated_at = $2
                WHERE user_id = $1
            """, user_id, now, hour_count + 1, day_count + 1)

            return {"can_send": True, "wait_seconds": 0, "reason": ""}

    # Методы для поддержки v2 (с диалогами)
    async def get_user_active_ticket(self, user_id: int) -> Optional[Dict]:
        """Получение активного тикета пользователя"""
        async with self.get_connection() as conn:
            row = await conn.fetchrow("""
                SELECT st.*, u.username, u.first_name, u.last_name
                FROM support_tickets st
                JOIN users u ON st.user_id = u.id
                WHERE st.user_id = $1 AND st.is_closed = FALSE
                ORDER BY st.created_at DESC
                LIMIT 1
            """, user_id)
            return dict(row) if row else None

    async def create_support_ticket_v2(self, user_id: int, email: str, message: str,
                                       photo_file_id: str = None, document_file_id: str = None,
                                       video_file_id: str = None) -> int:
        """Создание нового тикета поддержки (версия 2)"""
        async with self.get_connection() as conn:
            now = datetime.now()

            # Закрываем предыдущие открытые тикеты пользователя
            await conn.execute("""
                UPDATE support_tickets 
                SET is_closed = TRUE, closed_at = $2
                WHERE user_id = $1 AND is_closed = FALSE
            """, user_id, now)

            # Создаем новый тикет
            ticket_id = await conn.fetchval("""
                INSERT INTO support_tickets (user_id, email, message, photo_file_id, 
                                           last_user_message_at, status)
                VALUES ($1, $2, $3, $4, $5, 'open')
                RETURNING id
            """, user_id, email, message, photo_file_id, now)

            # Добавляем первое сообщение в диалог
            message_type = "text"
            if photo_file_id:
                message_type = "photo"
            elif document_file_id:
                message_type = "document"
            elif video_file_id:
                message_type = "video"

            await conn.execute("""
                INSERT INTO ticket_messages (ticket_id, user_id, is_staff, message_text, 
                                           photo_file_id, document_file_id, video_file_id, message_type)
                VALUES ($1, $2, FALSE, $3, $4, $5, $6, $7)
            """, ticket_id, user_id, message, photo_file_id, document_file_id, video_file_id, message_type)

            return ticket_id

    async def add_ticket_message(self, ticket_id: int, user_id: int, message_text: str = None,
                                 photo_file_id: str = None, document_file_id: str = None,
                                 video_file_id: str = None, is_staff: bool = False, is_admin: bool = False,
                                 thread_message_id: int = None) -> int:
        """Добавление сообщения к тикету"""
        async with self.get_connection() as conn:
            now = datetime.now()

            # Определяем тип сообщения
            message_type = "text"
            if photo_file_id:
                message_type = "photo"
            elif document_file_id:
                message_type = "document"
            elif video_file_id:
                message_type = "video"

            # Добавляем сообщение
            message_id = await conn.fetchval("""
                INSERT INTO ticket_messages (ticket_id, user_id, is_staff, is_admin, message_text,
                                           photo_file_id, document_file_id, video_file_id, 
                                           message_type, thread_message_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
            """, ticket_id, user_id, is_staff, is_admin, message_text, photo_file_id,
                                             document_file_id, video_file_id, message_type, thread_message_id)

            # Обновляем время последнего сообщения в тикете
            if is_staff:
                await conn.execute("""
                    UPDATE support_tickets 
                    SET last_staff_response_at = $2, updated_at = $2
                    WHERE id = $1
                """, ticket_id, now)
            else:
                await conn.execute("""
                    UPDATE support_tickets 
                    SET last_user_message_at = $2, updated_at = $2
                    WHERE id = $1
                """, ticket_id, now)

            return message_id

    async def close_ticket(self, ticket_id: int, closed_by_user_id: int = None) -> bool:
        """Закрытие тикета"""
        async with self.get_connection() as conn:
            now = datetime.now()

            result = await conn.execute("""
                UPDATE support_tickets 
                SET is_closed = TRUE, closed_at = $2, status = 'closed', updated_at = $2
                WHERE id = $1 AND is_closed = FALSE
            """, ticket_id, now)

            # Логируем закрытие тикета
            if closed_by_user_id:
                await self.log_user_action(closed_by_user_id, "ticket_closed", {"ticket_id": ticket_id})

            return result == "UPDATE 1"

    async def get_ticket_messages(self, ticket_id: int, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Получение сообщений тикета"""
        async with self.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT tm.*, u.username, u.first_name, u.last_name
                FROM ticket_messages tm
                JOIN users u ON tm.user_id = u.id
                WHERE tm.ticket_id = $1
                ORDER BY tm.created_at ASC
                LIMIT $2 OFFSET $3
            """, ticket_id, limit, offset)
            return [dict(row) for row in rows]

    async def get_ticket_with_last_messages(self, ticket_id: int, messages_limit: int = 10) -> Optional[Dict]:
        """Получение тикета с последними сообщениями"""
        async with self.get_connection() as conn:
            # Получаем тикет
            ticket = await conn.fetchrow("""
                SELECT st.*, u.username, u.first_name, u.last_name
                FROM support_tickets st
                JOIN users u ON st.user_id = u.id
                WHERE st.id = $1
            """, ticket_id)

            if not ticket:
                return None

            # Получаем последние сообщения
            messages = await conn.fetch("""
                SELECT tm.*, u.username as msg_username, u.first_name as msg_first_name, u.last_name as msg_last_name
                FROM ticket_messages tm
                JOIN users u ON tm.user_id = u.id
                WHERE tm.ticket_id = $1
                ORDER BY tm.created_at DESC
                LIMIT $2
            """, ticket_id, messages_limit)

            ticket_dict = dict(ticket)
            ticket_dict['messages'] = [dict(msg) for msg in reversed(messages)]

            return ticket_dict

    async def update_ticket_thread_info(self, ticket_id: int, thread_id: int, initial_message_id: int):
        """Обновление информации о треде для тикета"""
        async with self.get_connection() as conn:
            await conn.execute("""
                UPDATE support_tickets 
                SET thread_id = $1, initial_message_id = $2, updated_at = CURRENT_TIMESTAMP
                WHERE id = $3
            """, thread_id, initial_message_id, ticket_id)

    async def get_ticket_by_thread(self, thread_id: int) -> Optional[Dict]:
        """Получение тикета по ID треда"""
        async with self.get_connection() as conn:
            row = await conn.fetchrow("""
                SELECT st.*, u.username, u.first_name, u.last_name
                FROM support_tickets st
                JOIN users u ON st.user_id = u.id
                WHERE st.thread_id = $1
            """, thread_id)
            return dict(row) if row else None

    # Статистика и метрики поддержки
    async def get_support_statistics(self) -> Dict[str, Any]:
        """Получение подробной статистики поддержки"""
        async with self.get_connection() as conn:
            now = datetime.now()
            today = now.date()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)

            # Основные метрики
            stats = {
                "tickets": {
                    "total": await conn.fetchval("SELECT COUNT(*) FROM support_tickets"),
                    "open": await conn.fetchval("SELECT COUNT(*) FROM support_tickets WHERE is_closed = FALSE"),
                    "closed": await conn.fetchval("SELECT COUNT(*) FROM support_tickets WHERE is_closed = TRUE"),
                    "today": await conn.fetchval("SELECT COUNT(*) FROM support_tickets WHERE created_at::date = $1", today),
                    "this_week": await conn.fetchval("SELECT COUNT(*) FROM support_tickets WHERE created_at > $1", week_ago),
                    "this_month": await conn.fetchval("SELECT COUNT(*) FROM support_tickets WHERE created_at > $1", month_ago)
                },
                "messages": {
                    "total": await conn.fetchval("SELECT COUNT(*) FROM ticket_messages"),
                    "from_users": await conn.fetchval("SELECT COUNT(*) FROM ticket_messages WHERE is_staff = FALSE"),
                    "from_staff": await conn.fetchval("SELECT COUNT(*) FROM ticket_messages WHERE is_staff = TRUE"),
                    "today": await conn.fetchval("SELECT COUNT(*) FROM ticket_messages WHERE created_at::date = $1", today),
                    "this_week": await conn.fetchval("SELECT COUNT(*) FROM ticket_messages WHERE created_at > $1", week_ago),
                    "this_month": await conn.fetchval("SELECT COUNT(*) FROM ticket_messages WHERE created_at > $1", month_ago)
                }
            }

            # Среднее время ответа (в минутах)
            avg_response_time = await conn.fetchval("""
                SELECT AVG(EXTRACT(EPOCH FROM (tm_staff.created_at - tm_user.created_at))/60)
                FROM ticket_messages tm_user
                JOIN ticket_messages tm_staff ON tm_user.ticket_id = tm_staff.ticket_id
                WHERE tm_user.is_staff = FALSE 
                AND tm_staff.is_staff = TRUE
                AND tm_staff.created_at > tm_user.created_at
                AND tm_staff.created_at > $1
            """, week_ago)

            stats["response_time"] = {
                "average_minutes": round(avg_response_time or 0, 2),
                "average_hours": round((avg_response_time or 0) / 60, 2)
            }

            # Активность сотрудников за неделю
            staff_activity = await conn.fetch("""
                SELECT user_id, COUNT(*) as message_count, is_admin
                FROM ticket_messages
                WHERE is_staff = TRUE AND created_at > $1
                GROUP BY user_id, is_admin
                ORDER BY message_count DESC
            """, week_ago)

            stats["staff_activity"] = [dict(row) for row in staff_activity]

            # Топ пользователей по количеству сообщений
            top_users = await conn.fetch("""
                SELECT tm.user_id, u.first_name, u.username, COUNT(*) as message_count
                FROM ticket_messages tm
                JOIN users u ON tm.user_id = u.id
                WHERE tm.is_staff = FALSE AND tm.created_at > $1
                GROUP BY tm.user_id, u.first_name, u.username
                ORDER BY message_count DESC
                LIMIT 10
            """, week_ago)

            stats["top_users"] = [dict(row) for row in top_users]

            # Метрики по дням за последнюю неделю
            daily_metrics = await conn.fetch("""
                SELECT 
                    created_at::date as date,
                    COUNT(*) as tickets_created,
                    COUNT(*) FILTER (WHERE is_closed = TRUE) as tickets_closed
                FROM support_tickets
                WHERE created_at > $1
                GROUP BY created_at::date
                ORDER BY date DESC
            """, week_ago)

            stats["daily_metrics"] = [dict(row) for row in daily_metrics]

            return stats

    async def get_tickets_requiring_attention(self) -> List[Dict]:
        """Получение тикетов, требующих внимания"""
        async with self.get_connection() as conn:
            # Тикеты без ответа более 2 часов
            urgent_tickets = await conn.fetch("""
                SELECT st.*, u.username, u.first_name, u.last_name,
                       EXTRACT(EPOCH FROM (NOW() - st.last_user_message_at))/3600 as hours_since_last_message
                FROM support_tickets st
                JOIN users u ON st.user_id = u.id
                WHERE st.is_closed = FALSE 
                AND (st.last_staff_response_at IS NULL OR st.last_user_message_at > st.last_staff_response_at)
                AND st.last_user_message_at < NOW() - INTERVAL '2 hours'
                ORDER BY st.last_user_message_at ASC
            """)

            return [dict(row) for row in urgent_tickets]

    async def search_tickets(self, search_query: str = None, user_id: int = None,
                             status: str = None, limit: int = 50) -> List[Dict]:
        """Поиск тикетов по различным критериям"""
        async with self.get_connection() as conn:
            conditions = []
            params = []
            param_count = 0

            if search_query:
                param_count += 1
                conditions.append(f"(st.message ILIKE ${param_count} OR u.first_name ILIKE ${param_count} OR u.username ILIKE ${param_count})")
                params.append(f"%{search_query}%")

            if user_id:
                param_count += 1
                conditions.append(f"st.user_id = ${param_count}")
                params.append(user_id)

            if status:
                if status == "open":
                    conditions.append("st.is_closed = FALSE")
                elif status == "closed":
                    conditions.append("st.is_closed = TRUE")

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            query = f"""
                SELECT st.*, u.username, u.first_name, u.last_name
                FROM support_tickets st
                JOIN users u ON st.user_id = u.id
                {where_clause}
                ORDER BY st.created_at DESC
                LIMIT {limit}
            """

            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    # Старые методы поддержки (для совместимости)
    async def create_support_ticket(self, user_id: int, email: str,
                                    message: str, photo_file_id: str = None,
                                    thread_id: int = None, initial_message_id: int = None) -> int:
        """Создание тикета поддержки (старый метод для совместимости)"""
        return await self.create_support_ticket_v2(user_id, email, message, photo_file_id)

    async def add_support_response(self, ticket_id: int, staff_user_id: int, response_text: str, is_admin: bool = False):
        """Добавление ответа сотрудника поддержки или администратора (старый метод)"""
        await self.add_ticket_message(
            ticket_id=ticket_id,
            user_id=staff_user_id,
            message_text=response_text,
            is_staff=True,
            is_admin=is_admin
        )

    async def get_support_tickets(self, status: str = None) -> List[Dict]:
        """Получение тикетов поддержки (старый метод)"""
        return await self.search_tickets(status=status)

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