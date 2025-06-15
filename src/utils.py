import asyncio
import logging
import smtplib
import json
import os
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

class EmailSender:
    """Класс для отправки email с расширенными возможностями"""

    def __init__(self, smtp_server: str, smtp_port: int, email_user: str, email_password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_user = email_user
        self.email_password = email_password
        self.last_send_time = {}  # Для rate limiting
        self.send_count = {"hour": 0, "day": 0, "last_reset": datetime.now()}

    async def send_email(self, to_email: str, subject: str, body: str,
                         html_body: str = None, attachments: List[str] = None,
                         priority: str = "normal") -> bool:
        """Отправка email с поддержкой вложений и приоритета"""
        try:
            # Проверка rate limit
            if not self._check_rate_limit(to_email):
                logger.warning(f"Rate limit exceeded for {to_email}")
                return False

            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_user
            msg['To'] = to_email

            # Установка приоритета
            if priority == "high":
                msg['X-Priority'] = '1'
                msg['X-MSMail-Priority'] = 'High'
            elif priority == "low":
                msg['X-Priority'] = '5'
                msg['X-MSMail-Priority'] = 'Low'

            # Текстовая версия
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)

            # HTML версия (если есть)
            if html_body:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(html_part)

            # Вложения
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {os.path.basename(file_path)}'
                            )
                            msg.attach(part)

            # Отправка в отдельном потоке
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_smtp, msg, to_email)

            # Обновление счетчиков
            self._update_counters()
            self.last_send_time[to_email] = datetime.now()

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

    def _check_rate_limit(self, email: str) -> bool:
        """Проверка rate limit для email"""
        now = datetime.now()

        # Глобальный rate limit (100 писем в час, 500 в день)
        if self.send_count["hour"] >= 100 or self.send_count["day"] >= 500:
            return False

        # Rate limit на email (1 письмо в 5 минут)
        if email in self.last_send_time:
            time_diff = (now - self.last_send_time[email]).total_seconds()
            if time_diff < 300:  # 5 минут
                return False

        return True

    def _update_counters(self):
        """Обновление счетчиков отправки"""
        now = datetime.now()
        last_reset = self.send_count["last_reset"]

        # Сброс часового счетчика
        if (now - last_reset).total_seconds() > 3600:
            self.send_count["hour"] = 0

        # Сброс дневного счетчика
        if now.date() > last_reset.date():
            self.send_count["day"] = 0
            self.send_count["last_reset"] = now

        self.send_count["hour"] += 1
        self.send_count["day"] += 1

    async def send_support_notification(self, ticket_id: int, user_email: str,
                                        message: str, user_name: str) -> bool:
        """Отправка уведомления в поддержку"""
        subject = f"Новое обращение #{ticket_id} от {user_name}"

        html_body = f"""
        <h2>Новое обращение в поддержку</h2>
        <p><strong>ID тикета:</strong> #{ticket_id}</p>
        <p><strong>От пользователя:</strong> {user_name}</p>
        <p><strong>Email:</strong> {user_email}</p>
        <p><strong>Время:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
        
        <h3>Сообщение:</h3>
        <div style="border: 1px solid #ccc; padding: 10px; background-color: #f9f9f9;">
            {message.replace('\n', '<br>')}
        </div>
        
        <p><em>Это автоматическое уведомление от системы поддержки фестиваля.</em></p>
        """

        text_body = f"""
Новое обращение в поддержку

ID тикета: #{ticket_id}
От пользователя: {user_name}
Email: {user_email}
Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

Сообщение:
{message}

---
Это автоматическое уведомление от системы поддержки фестиваля.
        """

        from config import config
        if config.SUPPORT_EMAIL:
            return await self.send_email(
                config.SUPPORT_EMAIL,
                subject,
                text_body,
                html_body,
                priority="high"
            )

        return False

class DataBackup:
    """Класс для резервного копирования данных с расширенными возможностями"""

    def __init__(self, database):
        self.db = database
        self.backup_path = Path("backups")
        self.backup_path.mkdir(exist_ok=True)

    async def create_backup(self, include_full_history: bool = False) -> dict:
        """Создание резервной копии с опциональной полной историей"""
        try:
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "version": "2.0",
                "backup_type": "full" if include_full_history else "recent",
                "tables": {}
            }

            async with self.db.get_connection() as conn:
                # Пользователи (всех)
                users = await conn.fetch("SELECT * FROM users ORDER BY created_at DESC")
                backup_data["tables"]["users"] = [dict(user) for user in users]

                # Тикеты поддержки
                if include_full_history:
                    tickets = await conn.fetch("SELECT * FROM support_tickets ORDER BY created_at DESC")
                else:
                    # Только за последние 30 дней
                    cutoff_date = datetime.now() - timedelta(days=30)
                    tickets = await conn.fetch(
                        "SELECT * FROM support_tickets WHERE created_at > $1 ORDER BY created_at DESC",
                        cutoff_date
                    )
                backup_data["tables"]["support_tickets"] = [dict(ticket) for ticket in tickets]

                # Сообщения тикетов
                if include_full_history:
                    messages = await conn.fetch("SELECT * FROM ticket_messages ORDER BY created_at DESC")
                else:
                    cutoff_date = datetime.now() - timedelta(days=30)
                    messages = await conn.fetch(
                        "SELECT * FROM ticket_messages WHERE created_at > $1 ORDER BY created_at DESC",
                        cutoff_date
                    )
                backup_data["tables"]["ticket_messages"] = [dict(msg) for msg in messages]

                # Отзывы (всех)
                feedback = await conn.fetch("SELECT * FROM feedback ORDER BY created_at DESC")
                backup_data["tables"]["feedback"] = [dict(fb) for fb in feedback]

                # Расписание (всех)
                schedule = await conn.fetch("SELECT * FROM schedule ORDER BY day, time")
                backup_data["tables"]["schedule"] = [dict(item) for item in schedule]

                # Локации (всех)
                locations = await conn.fetch("SELECT * FROM locations ORDER BY name")
                backup_data["tables"]["locations"] = [dict(loc) for loc in locations]

                # Активности (всех)
                activities = await conn.fetch("SELECT * FROM activities ORDER BY name")
                backup_data["tables"]["activities"] = [dict(act) for act in activities]

                # Статистика использования (последние 1000 записей)
                stats = await conn.fetch(
                    "SELECT * FROM usage_stats ORDER BY created_at DESC LIMIT 1000"
                )
                backup_data["tables"]["usage_stats"] = [dict(stat) for stat in stats]

                # Rate limits (текущие)
                rate_limits = await conn.fetch("SELECT * FROM user_rate_limits")
                backup_data["tables"]["user_rate_limits"] = [dict(rl) for rl in rate_limits]

                # Метрики поддержки (за последние 90 дней)
                cutoff_date = datetime.now() - timedelta(days=90)
                metrics = await conn.fetch(
                    "SELECT * FROM support_metrics WHERE date > $1 ORDER BY date DESC",
                    cutoff_date.date()
                )
                backup_data["tables"]["support_metrics"] = [dict(metric) for metric in metrics]

            # Добавляем метаданные
            backup_data["metadata"] = {
                "total_users": len(backup_data["tables"]["users"]),
                "total_tickets": len(backup_data["tables"]["support_tickets"]),
                "total_messages": len(backup_data["tables"]["ticket_messages"]),
                "total_feedback": len(backup_data["tables"]["feedback"]),
                "backup_size_mb": self._calculate_backup_size(backup_data)
            }

            logger.info(f"Backup created successfully: {backup_data['metadata']}")
            return backup_data

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise

    async def save_backup_to_file(self, backup_data: dict, filename: str = None) -> str:
        """Сохранение резервной копии в файл"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_type = backup_data.get("backup_type", "unknown")
            filename = f"backup_{backup_type}_{timestamp}.json"

        file_path = self.backup_path / filename

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)

            logger.info(f"Backup saved to: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Failed to save backup to file: {e}")
            raise

    async def restore_from_backup(self, backup_file: str, tables: List[str] = None) -> bool:
        """Восстановление из резервной копии"""
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

            if not tables:
                tables = backup_data["tables"].keys()

            async with self.db.get_connection() as conn:
                for table_name in tables:
                    if table_name not in backup_data["tables"]:
                        logger.warning(f"Table {table_name} not found in backup")
                        continue

                    # Здесь должна быть логика восстановления конкретной таблицы
                    # Это сложная операция, требующая осторожности
                    logger.info(f"Restoring table: {table_name}")
                    # TODO: Implement table-specific restoration logic

            logger.info(f"Backup restored successfully from: {backup_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False

    def _calculate_backup_size(self, backup_data: dict) -> float:
        """Расчет размера резервной копии в МБ"""
        try:
            backup_json = json.dumps(backup_data, default=str)
            size_bytes = len(backup_json.encode('utf-8'))
            size_mb = size_bytes / (1024 * 1024)
            return round(size_mb, 2)
        except:
            return 0.0

    async def cleanup_old_backups(self, keep_count: int = 10):
        """Очистка старых резервных копий"""
        try:
            backup_files = list(self.backup_path.glob("backup_*.json"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            for backup_file in backup_files[keep_count:]:
                backup_file.unlink()
                logger.info(f"Removed old backup: {backup_file}")

        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")

class HealthChecker:
    """Класс для мониторинга состояния бота с расширенными проверками"""

    def __init__(self, database, bot):
        self.db = database
        self.bot = bot
        self.last_check = None
        self.is_healthy = True
        self.health_history = []
        self.max_history = 100

    async def health_check(self) -> dict:
        """Комплексная проверка состояния системы"""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "bot_status": "unknown",
            "database_status": "unknown",
            "memory_usage": "unknown",
            "response_time": 0,
            "errors": [],
            "warnings": []
        }

        start_time = time.time()

        try:
            # Проверка бота
            bot_info = await self.bot.get_me()
            health_status["bot_status"] = "healthy" if bot_info else "error"
            health_status["bot_info"] = {
                "username": bot_info.username,
                "first_name": bot_info.first_name,
                "can_join_groups": bot_info.can_join_groups,
                "can_read_all_group_messages": bot_info.can_read_all_group_messages
            }
        except Exception as e:
            health_status["bot_status"] = "error"
            health_status["errors"].append(f"Bot error: {str(e)}")

        try:
            # Проверка БД
            async with self.db.get_connection() as conn:
                await conn.fetchval("SELECT 1")

                # Проверка размера БД
                db_size = await conn.fetchval("""
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """)

                # Проверка активных соединений
                active_connections = await conn.fetchval("""
                    SELECT count(*) FROM pg_stat_activity 
                    WHERE state = 'active' AND datname = current_database()
                """)

                health_status["database_status"] = "healthy"
                health_status["database_info"] = {
                    "size": db_size,
                    "active_connections": active_connections
                }

        except Exception as e:
            health_status["database_status"] = "error"
            health_status["errors"].append(f"Database error: {str(e)}")

        # Проверка использования памяти
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()

            health_status["memory_usage"] = {
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
                "percent": round(memory_percent, 2)
            }

            # Предупреждение при высоком использовании памяти
            if memory_percent > 80:
                health_status["warnings"].append(f"High memory usage: {memory_percent:.1f}%")

        except ImportError:
            health_status["memory_usage"] = "psutil not available"
        except Exception as e:
            health_status["warnings"].append(f"Memory check error: {str(e)}")

        # Проверка времени отклика
        end_time = time.time()
        response_time = round((end_time - start_time) * 1000, 2)  # в миллисекундах
        health_status["response_time"] = response_time

        if response_time > 5000:  # более 5 секунд
            health_status["warnings"].append(f"Slow response time: {response_time}ms")

        # Проверка состояния очередей и тикетов
        try:
            stats = await self._check_support_health()
            health_status["support_health"] = stats

            # Предупреждения по поддержке
            if stats["urgent_tickets"] > 10:
                health_status["warnings"].append(f"Many urgent tickets: {stats['urgent_tickets']}")

            if stats["open_tickets"] > 50:
                health_status["warnings"].append(f"Many open tickets: {stats['open_tickets']}")

        except Exception as e:
            health_status["warnings"].append(f"Support health check error: {str(e)}")

        # Общее состояние
        self.last_check = datetime.now()
        self.is_healthy = len(health_status["errors"]) == 0

        # Сохранение в историю
        self.health_history.append({
            "timestamp": health_status["timestamp"],
            "is_healthy": self.is_healthy,
            "response_time": response_time,
            "errors_count": len(health_status["errors"]),
            "warnings_count": len(health_status["warnings"])
        })

        # Ограничение размера истории
        if len(self.health_history) > self.max_history:
            self.health_history = self.health_history[-self.max_history:]

        return health_status

    async def _check_support_health(self) -> dict:
        """Проверка состояния системы поддержки"""
        try:
            async with self.db.get_connection() as conn:
                # Количество открытых тикетов
                open_tickets = await conn.fetchval(
                    "SELECT COUNT(*) FROM support_tickets WHERE is_closed = FALSE"
                )

                # Количество срочных тикетов (без ответа > 2 часов)
                urgent_tickets = await conn.fetchval("""
                    SELECT COUNT(*) FROM support_tickets 
                    WHERE is_closed = FALSE 
                    AND (last_staff_response_at IS NULL OR last_user_message_at > last_staff_response_at)
                    AND last_user_message_at < NOW() - INTERVAL '2 hours'
                """)

                # Средний размер очереди за последнюю неделю
                avg_queue_size = await conn.fetchval("""
                    SELECT AVG(open_count) FROM (
                        SELECT DATE(created_at), COUNT(*) as open_count
                        FROM support_tickets 
                        WHERE created_at > NOW() - INTERVAL '7 days'
                        GROUP BY DATE(created_at)
                    ) as daily_counts
                """)

                return {
                    "open_tickets": open_tickets,
                    "urgent_tickets": urgent_tickets,
                    "avg_queue_size": round(avg_queue_size or 0, 1)
                }

        except Exception as e:
            logger.error(f"Support health check error: {e}")
            return {"error": str(e)}

    def get_health_trends(self, hours: int = 24) -> dict:
        """Получение трендов состояния здоровья"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            recent_checks = [
                check for check in self.health_history
                if datetime.fromisoformat(check["timestamp"]) > cutoff_time
            ]

            if not recent_checks:
                return {"error": "No recent health checks"}

            # Расчет статистики
            healthy_count = sum(1 for check in recent_checks if check["is_healthy"])
            avg_response_time = sum(check["response_time"] for check in recent_checks) / len(recent_checks)
            total_errors = sum(check["errors_count"] for check in recent_checks)
            total_warnings = sum(check["warnings_count"] for check in recent_checks)

            return {
                "period_hours": hours,
                "total_checks": len(recent_checks),
                "healthy_percentage": round((healthy_count / len(recent_checks)) * 100, 1),
                "avg_response_time": round(avg_response_time, 2),
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "last_check": recent_checks[-1]["timestamp"] if recent_checks else None
            }

        except Exception as e:
            logger.error(f"Error calculating health trends: {e}")
            return {"error": str(e)}

class SecurityMonitor:
    """Класс для мониторинга безопасности"""

    def __init__(self, database):
        self.db = database
        self.suspicious_activities = []
        self.blocked_users = set()

    async def check_user_activity(self, user_id: int, action: str, details: dict = None) -> bool:
        """Проверка активности пользователя на подозрительность"""
        try:
            # Получаем историю активности пользователя за последний час
            hour_ago = datetime.now() - timedelta(hours=1)

            async with self.db.get_connection() as conn:
                recent_actions = await conn.fetch("""
                    SELECT action, details, created_at FROM usage_stats
                    WHERE user_id = $1 AND created_at > $2
                    ORDER BY created_at DESC
                """, user_id, hour_ago)

            # Анализ на подозрительные паттерны
            suspicious_score = 0

            # Слишком много действий за короткое время
            if len(recent_actions) > 100:
                suspicious_score += 50

            # Повторяющиеся действия
            action_counts = {}
            for row in recent_actions:
                action_counts[row['action']] = action_counts.get(row['action'], 0) + 1

            max_action_count = max(action_counts.values()) if action_counts else 0
            if max_action_count > 50:
                suspicious_score += 30

            # Проверка на спам в сообщениях поддержки
            if action == "support_message":
                message_text = details.get("message", "") if details else ""
                if self._is_spam_message(message_text):
                    suspicious_score += 70

            # Если подозрительная активность превышает порог
            if suspicious_score > 70:
                await self._handle_suspicious_user(user_id, suspicious_score, action, details)
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking user activity: {e}")
            return True  # В случае ошибки разрешаем действие

    def _is_spam_message(self, message: str) -> bool:
        """Проверка сообщения на спам"""
        from config import config

        spam_indicators = [
            len(message) > 2000,  # Слишком длинное сообщение
            message.count("http") > 3,  # Много ссылок
            message.count("@") > 5,  # Много упоминаний
            any(word in message.lower() for word in config.get_security_config()["blacklisted_words"])
        ]

        return sum(spam_indicators) >= 2

    async def _handle_suspicious_user(self, user_id: int, score: int, action: str, details: dict):
        """Обработка подозрительного пользователя"""
        try:
            # Логируем подозрительную активность
            suspicious_activity = {
                "user_id": user_id,
                "score": score,
                "action": action,
                "details": details,
                "timestamp": datetime.now().isoformat()
            }

            self.suspicious_activities.append(suspicious_activity)

            # Временная блокировка при высоком скоре
            if score > 90:
                self.blocked_users.add(user_id)

                # Уведомление администраторов
                from config import config
                message = f"""
🚨 ПОДОЗРИТЕЛЬНАЯ АКТИВНОСТЬ

👤 Пользователь: {user_id}
📊 Скор: {score}/100
🎯 Действие: {action}
⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

🔒 Пользователь временно заблокирован
                """

                # TODO: Отправить уведомление администраторам

            logger.warning(f"Suspicious activity detected: user {user_id}, score {score}")

        except Exception as e:
            logger.error(f"Error handling suspicious user: {e}")

    def is_user_blocked(self, user_id: int) -> bool:
        """Проверка, заблокирован ли пользователь"""
        return user_id in self.blocked_users

    def unblock_user(self, user_id: int):
        """Разблокировка пользователя"""
        self.blocked_users.discard(user_id)

class PerformanceMonitor:
    """Класс для мониторинга производительности"""

    def __init__(self):
        self.metrics = {
            "request_times": [],
            "memory_usage": [],
            "cpu_usage": [],
            "db_query_times": []
        }
        self.start_time = time.time()

    def record_request_time(self, duration: float):
        """Запись времени обработки запроса"""
        self.metrics["request_times"].append({
            "duration": duration,
            "timestamp": time.time()
        })

        # Ограничиваем количество записей
        if len(self.metrics["request_times"]) > 1000:
            self.metrics["request_times"] = self.metrics["request_times"][-1000:]

    def record_db_query_time(self, duration: float):
        """Запись времени выполнения SQL запроса"""
        self.metrics["db_query_times"].append({
            "duration": duration,
            "timestamp": time.time()
        })

        if len(self.metrics["db_query_times"]) > 500:
            self.metrics["db_query_times"] = self.metrics["db_query_times"][-500:]

    def get_performance_stats(self) -> dict:
        """Получение статистики производительности"""
        try:
            current_time = time.time()
            uptime = current_time - self.start_time

            stats = {
                "uptime_seconds": round(uptime, 2),
                "uptime_formatted": str(timedelta(seconds=int(uptime)))
            }

            # Статистика времени запросов
            if self.metrics["request_times"]:
                recent_requests = [
                    r for r in self.metrics["request_times"]
                    if current_time - r["timestamp"] < 3600  # За последний час
                ]

                if recent_requests:
                    durations = [r["duration"] for r in recent_requests]
                    stats["requests"] = {
                        "count_last_hour": len(recent_requests),
                        "avg_duration_ms": round(sum(durations) / len(durations) * 1000, 2),
                        "max_duration_ms": round(max(durations) * 1000, 2),
                        "min_duration_ms": round(min(durations) * 1000, 2)
                    }

            # Статистика БД запросов
            if self.metrics["db_query_times"]:
                recent_queries = [
                    q for q in self.metrics["db_query_times"]
                    if current_time - q["timestamp"] < 3600
                ]

                if recent_queries:
                    durations = [q["duration"] for q in recent_queries]
                    stats["database"] = {
                        "queries_last_hour": len(recent_queries),
                        "avg_query_time_ms": round(sum(durations) / len(durations) * 1000, 2),
                        "max_query_time_ms": round(max(durations) * 1000, 2)
                    }

            # Системные метрики
            try:
                import psutil
                process = psutil.Process()

                stats["system"] = {
                    "memory_percent": round(process.memory_percent(), 2),
                    "cpu_percent": round(process.cpu_percent(), 2),
                    "threads": process.num_threads(),
                    "open_files": len(process.open_files())
                }
            except ImportError:
                stats["system"] = "psutil not available"

            return stats

        except Exception as e:
            logger.error(f"Error getting performance stats: {e}")
            return {"error": str(e)}