import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailSender:
    """Класс для отправки email"""

    def __init__(self, smtp_server: str, smtp_port: int, email_user: str, email_password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_user = email_user
        self.email_password = email_password

    async def send_email(self, to_email: str, subject: str, body: str, html_body: str = None):
        """Отправка email"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_user
            msg['To'] = to_email

            # Текстовая версия
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)

            # HTML версия (если есть)
            if html_body:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(html_part)

            # Отправка в отдельном потоке
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_smtp, msg, to_email)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def _send_smtp(self, msg, to_email: str):
        """Синхронная отправка SMTP"""
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.email_user, self.email_password)
            server.send_message(msg, to_addresses=[to_email])

class DataBackup:
    """Класс для резервного копирования данных"""

    def __init__(self, database: Database):
        self.db = database

    async def create_backup(self) -> dict:
        """Создание резервной копии"""
        try:
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "users": [],
                "support_tickets": [],
                "feedback": [],
                "schedule": [],
                "usage_stats": []
            }

            async with self.db.get_connection() as conn:
                # Пользователи
                users = await conn.fetch("SELECT * FROM users")
                backup_data["users"] = [dict(user) for user in users]

                # Тикеты поддержки
                tickets = await conn.fetch("SELECT * FROM support_tickets")
                backup_data["support_tickets"] = [dict(ticket) for ticket in tickets]

                # Отзывы
                feedback = await conn.fetch("SELECT * FROM feedback")
                backup_data["feedback"] = [dict(fb) for fb in feedback]

                # Расписание
                schedule = await conn.fetch("SELECT * FROM schedule")
                backup_data["schedule"] = [dict(item) for item in schedule]

                # Статистика (последние 1000 записей)
                stats = await conn.fetch("SELECT * FROM usage_stats ORDER BY created_at DESC LIMIT 1000")
                backup_data["usage_stats"] = [dict(stat) for stat in stats]

            logger.info("Backup created successfully")
            return backup_data

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise

class HealthChecker:
    """Класс для мониторинга состояния бота"""

    def __init__(self, database: Database, bot):
        self.db = database
        self.bot = bot
        self.last_check = None
        self.is_healthy = True

    async def health_check(self) -> dict:
        """Проверка состояния системы"""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "bot_status": "unknown",
            "database_status": "unknown",
            "errors": []
        }

        try:
            # Проверка бота
            bot_info = await self.bot.get_me()
            health_status["bot_status"] = "healthy" if bot_info else "error"
        except Exception as e:
            health_status["bot_status"] = "error"
            health_status["errors"].append(f"Bot error: {str(e)}")

        try:
            # Проверка БД
            async with self.db.get_connection() as conn:
                await conn.fetchval("SELECT 1")
            health_status["database_status"] = "healthy"
        except Exception as e:
            health_status["database_status"] = "error"
            health_status["errors"].append(f"Database error: {str(e)}")

        self.last_check = datetime.now()
        self.is_healthy = len(health_status["errors"]) == 0

        return health_status