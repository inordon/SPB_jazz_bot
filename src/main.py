import asyncio
import logging
import sys
import signal
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database import Database
from handlers import BotHandlers
from utils import EmailSender, DataBackup, HealthChecker

# Настройка логирования
def setup_logging():
    """Настройка системы логирования"""
    # Создаем директорию логов если не существует
    import pathlib
    pathlib.Path("logs").mkdir(exist_ok=True)

    # Формат логов
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Настройка корневого логгера
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format=log_format,
        handlers=[
            logging.FileHandler('logs/bot.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Отдельный файл для ошибок
    error_handler = logging.FileHandler('logs/errors.log', encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format))
    logging.getLogger().addHandler(error_handler)

    # Логгер для статистики
    stats_logger = logging.getLogger('stats')
    stats_handler = logging.FileHandler('logs/stats.log', encoding='utf-8')
    stats_handler.setFormatter(logging.Formatter(log_format))
    stats_logger.addHandler(stats_handler)
    stats_logger.setLevel(logging.INFO)

    # Логгер для поддержки
    support_logger = logging.getLogger('support')
    support_handler = logging.FileHandler('logs/support.log', encoding='utf-8')
    support_handler.setFormatter(logging.Formatter(log_format))
    support_logger.addHandler(support_handler)
    support_logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

class FestivalBot:
    """Основной класс бота с расширенными функциями"""

    def __init__(self):
        self.bot = None
        self.dp = None
        self.database = None
        self.handlers = None
        self.email_sender = None
        self.health_checker = None
        self.data_backup = None
        self.running = False
        self.background_tasks = []

    async def setup(self):
        """Настройка бота"""
        try:
            logger.info("Starting bot setup...")

            # Валидация конфигурации
            if not config.validate_config():
                raise ValueError("Invalid configuration")

            logger.info(f"Environment: {config.environment}")
            logger.info(f"Debug mode: {config.debug_mode}")

            # Инициализация бота
            self.bot = Bot(
                token=config.BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            # Проверка токена
            bot_info = await self.bot.get_me()
            logger.info(f"Bot initialized: @{bot_info.username} ({bot_info.first_name})")

            # Диспетчер с хранилищем состояний
            storage = MemoryStorage()
            self.dp = Dispatcher(storage=storage)

            # База данных
            logger.info("Initializing database connection...")
            self.database = Database(config.get_database_url())
            await self.database.create_pool()
            await self.database.init_tables()
            logger.info("Database initialized successfully")

            # Обработчики
            logger.info("Setting up message handlers...")
            self.handlers = BotHandlers(self.database, self.bot)
            self.dp.include_router(self.handlers.router)
            logger.info("Message handlers configured")

            # Email сендер
            if config.EMAIL_USER and config.EMAIL_PASSWORD:
                logger.info("Initializing email sender...")
                self.email_sender = EmailSender(
                    config.SMTP_SERVER,
                    config.SMTP_PORT,
                    config.EMAIL_USER,
                    config.EMAIL_PASSWORD
                )
                logger.info("Email sender initialized")
            else:
                logger.warning("Email settings not configured")

            # Мониторинг здоровья
            logger.info("Initializing health checker...")
            self.health_checker = HealthChecker(self.database, self.bot)
            logger.info("Health checker initialized")

            # Система резервного копирования
            logger.info("Initializing backup system...")
            self.data_backup = DataBackup(self.database)
            logger.info("Backup system initialized")

            # Установка команд бота
            await self._setup_bot_commands()

            logger.info("Bot setup completed successfully")

        except Exception as e:
            logger.error(f"Failed to setup bot: {e}")
            raise

    async def _setup_bot_commands(self):
        """Настройка команд бота"""
        from aiogram.types import BotCommand

        commands = [
            BotCommand(command="start", description="🏠 Главное меню"),
            BotCommand(command="menu", description="📋 Показать меню"),
            BotCommand(command="schedule", description="📅 Расписание"),
            BotCommand(command="navigation", description="🗺 Навигация"),
            BotCommand(command="support", description="🆘 Поддержка"),
            BotCommand(command="feedback", description="💭 Обратная связь"),
        ]

        # Команды для администраторов
        admin_commands = commands + [
            BotCommand(command="admin", description="🔧 Админ панель"),
            BotCommand(command="stats", description="📊 Статистика"),
            BotCommand(command="health", description="🏥 Проверка здоровья"),
        ]

        try:
            # Установка команд для обычных пользователей
            await self.bot.set_my_commands(commands)

            # Установка команд для администраторов
            from aiogram.types import BotCommandScopeChat
            for admin_id in config.ADMIN_IDS:
                try:
                    await self.bot.set_my_commands(
                        admin_commands,
                        scope=BotCommandScopeChat(chat_id=admin_id)
                    )
                except Exception as e:
                    logger.warning(f"Failed to set admin commands for {admin_id}: {e}")

            logger.info("Bot commands configured successfully")

        except Exception as e:
            logger.error(f"Failed to setup bot commands: {e}")

    async def start_background_tasks(self):
        """Запуск фоновых задач"""
        logger.info("Starting background tasks...")

        # Задача мониторинга здоровья
        health_task = asyncio.create_task(self.health_check_loop())
        self.background_tasks.append(health_task)

        # Задача очистки старых данных
        cleanup_task = asyncio.create_task(self.cleanup_loop())
        self.background_tasks.append(cleanup_task)

        # Задача создания резервных копий
        backup_task = asyncio.create_task(self.backup_loop())
        self.background_tasks.append(backup_task)

        # Задача отправки статистики
        stats_task = asyncio.create_task(self.stats_loop())
        self.background_tasks.append(stats_task)

        # Задача мониторинга срочных тикетов
        urgent_tickets_task = asyncio.create_task(self.urgent_tickets_loop())
        self.background_tasks.append(urgent_tickets_task)

        logger.info(f"Started {len(self.background_tasks)} background tasks")

    async def health_check_loop(self):
        """Периодическая проверка здоровья системы"""
        logger.info("Health check loop started")

        while self.running:
            try:
                await asyncio.sleep(config.get_monitoring_config()["health_check_interval_minutes"] * 60)

                if self.health_checker:
                    health_status = await self.health_checker.health_check()

                    if not self.health_checker.is_healthy:
                        logger.warning(f"Health check failed: {health_status}")

                        # Уведомление администраторов о проблемах
                        if config.get_notification_config()["notify_admins_system_errors"]:
                            await self._notify_admins_about_health_issues(health_status)

                    else:
                        logger.debug("Health check passed")

            except asyncio.CancelledError:
                logger.info("Health check loop cancelled")
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def cleanup_loop(self):
        """Периодическая очистка старых данных"""
        logger.info("Cleanup loop started")

        while self.running:
            try:
                # Очистка каждые 24 часа
                await asyncio.sleep(24 * 60 * 60)

                logger.info("Starting data cleanup...")

                # Очистка старых логов
                await self._cleanup_old_logs()

                # Очистка старой статистики
                await self._cleanup_old_stats()

                # Автозакрытие старых тикетов
                await self._auto_close_old_tickets()

                logger.info("Data cleanup completed")

            except asyncio.CancelledError:
                logger.info("Cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    async def backup_loop(self):
        """Периодическое создание резервных копий"""
        logger.info("Backup loop started")

        while self.running:
            try:
                # Резервное копирование каждые 24 часа
                await asyncio.sleep(config.get_monitoring_config()["backup_interval_hours"] * 60 * 60)

                if self.data_backup:
                    logger.info("Creating database backup...")
                    backup_data = await self.data_backup.create_backup()

                    # Сохранение резервной копии в файл
                    import json
                    import os

                    backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    backup_path = os.path.join("backups", backup_filename)

                    with open(backup_path, 'w', encoding='utf-8') as f:
                        json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)

                    logger.info(f"Backup created: {backup_path}")

                    # Очистка старых резервных копий (храним только последние 7)
                    await self._cleanup_old_backups()

            except asyncio.CancelledError:
                logger.info("Backup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Backup error: {e}")

    async def stats_loop(self):
        """Периодическая отправка статистики"""
        logger.info("Stats loop started")

        while self.running:
            try:
                # Отправка статистики каждые 24 часа в 9:00
                now = datetime.now()
                next_report = now.replace(hour=9, minute=0, second=0, microsecond=0)
                if next_report <= now:
                    next_report += timedelta(days=1)

                sleep_seconds = (next_report - now).total_seconds()
                await asyncio.sleep(sleep_seconds)

                if config.get_notification_config()["daily_stats_report"]:
                    await self._send_daily_stats_report()

            except asyncio.CancelledError:
                logger.info("Stats loop cancelled")
                break
            except Exception as e:
                logger.error(f"Stats loop error: {e}")

    async def urgent_tickets_loop(self):
        """Мониторинг срочных тикетов"""
        logger.info("Urgent tickets monitoring started")

        while self.running:
            try:
                # Проверка каждые 30 минут
                await asyncio.sleep(30 * 60)

                if config.get_notification_config()["notify_admins_urgent_tickets"]:
                    urgent_tickets = await self.database.get_tickets_requiring_attention()

                    if urgent_tickets:
                        await self._notify_admins_about_urgent_tickets(urgent_tickets)

            except asyncio.CancelledError:
                logger.info("Urgent tickets monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Urgent tickets monitoring error: {e}")

    async def _notify_admins_about_health_issues(self, health_status: dict):
        """Уведомление администраторов о проблемах со здоровьем системы"""
        try:
            message = f"""
🚨 ПРОБЛЕМЫ С СИСТЕМОЙ

⏰ Время: {health_status['timestamp']}
🤖 Статус бота: {health_status['bot_status']}
💾 Статус БД: {health_status['database_status']}

❌ Ошибки:
{chr(10).join(health_status.get('errors', []))}

🔧 Требуется вмешательство администратора!
            """

            for admin_id in config.ADMIN_IDS:
                try:
                    await self.bot.send_message(admin_id, message)
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id} about health issues: {e}")

        except Exception as e:
            logger.error(f"Failed to notify admins about health issues: {e}")

    async def _notify_admins_about_urgent_tickets(self, urgent_tickets: list):
        """Уведомление администраторов о срочных тикетах"""
        try:
            if len(urgent_tickets) == 0:
                return

            message = f"""
🚨 СРОЧНЫЕ ТИКЕТЫ ({len(urgent_tickets)})

Тикеты без ответа более 2 часов:
            """

            for ticket in urgent_tickets[:5]:  # Показываем только первые 5
                hours = int(ticket['hours_since_last_message'])
                message += f"\n🔥 #{ticket['id']} - {ticket['first_name']} ({hours}ч)"

            if len(urgent_tickets) > 5:
                message += f"\n... и еще {len(urgent_tickets) - 5} тикетов"

            message += f"\n\n📝 Перейдите в админ панель для обработки: /admin"

            for admin_id in config.ADMIN_IDS:
                try:
                    await self.bot.send_message(admin_id, message)
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id} about urgent tickets: {e}")

        except Exception as e:
            logger.error(f"Failed to notify admins about urgent tickets: {e}")

    async def _send_daily_stats_report(self):
        """Отправка ежедневного отчета по статистике"""
        try:
            stats = await self.database.get_support_statistics()
            usage_stats = await self.database.get_usage_stats()
            feedback_stats = await self.database.get_feedback_stats()

            report = f"""
📊 ЕЖЕДНЕВНЫЙ ОТЧЕТ - {datetime.now().strftime('%d.%m.%Y')}

🎫 ПОДДЕРЖКА:
• Новых тикетов: {stats['tickets']['today']}
• Открытых тикетов: {stats['tickets']['open']}
• Ответов сотрудников: {stats['messages']['from_staff']}
• Среднее время ответа: {stats['response_time']['average_minutes']:.1f} мин

👥 ПОЛЬЗОВАТЕЛИ:
• Всего пользователей: {usage_stats['total_users']}
• Всего действий: {usage_stats['total_actions']}

💭 ОТЗЫВЫ:
• Всего отзывов: {feedback_stats['total']['total_feedback']}
• Средняя оценка: {feedback_stats['total']['average_rating']:.1f}/5

🔥 Популярные действия:
            """

            for action in usage_stats['popular_actions'][:3]:
                report += f"• {action['action']}: {action['count']}\n"

            for admin_id in config.ADMIN_IDS:
                try:
                    await self.bot.send_message(admin_id, report)
                except Exception as e:
                    logger.error(f"Failed to send daily report to admin {admin_id}: {e}")

        except Exception as e:
            logger.error(f"Failed to send daily stats report: {e}")

    async def _cleanup_old_logs(self):
        """Очистка старых логов"""
        try:
            import os
            import glob
            from pathlib import Path

            retention_days = config.get_monitoring_config()["log_retention_days"]
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            log_files = glob.glob("logs/*.log*")

            for log_file in log_files:
                file_path = Path(log_file)
                if file_path.stat().st_mtime < cutoff_date.timestamp():
                    os.remove(log_file)
                    logger.info(f"Removed old log file: {log_file}")

        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}")

    async def _cleanup_old_stats(self):
        """Очистка старой статистики"""
        try:
            retention_days = config.get_monitoring_config()["stats_retention_days"]
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            async with self.database.get_connection() as conn:
                # Удаляем старые записи из usage_stats
                await conn.execute("""
                    DELETE FROM usage_stats 
                    WHERE created_at < $1
                """, cutoff_date)

                # Удаляем старые записи из support_metrics
                await conn.execute("""
                    DELETE FROM support_metrics 
                    WHERE date < $1
                """, cutoff_date.date())

            logger.info(f"Cleaned up stats older than {retention_days} days")

        except Exception as e:
            logger.error(f"Failed to cleanup old stats: {e}")

    async def _auto_close_old_tickets(self):
        """Автозакрытие старых неактивных тикетов"""
        try:
            auto_close_days = config.get_support_config()["auto_close_days"]
            cutoff_date = datetime.now() - timedelta(days=auto_close_days)

            async with self.database.get_connection() as conn:
                # Находим тикеты для автозакрытия
                old_tickets = await conn.fetch("""
                    SELECT id, user_id FROM support_tickets 
                    WHERE is_closed = FALSE 
                    AND last_user_message_at < $1
                    AND last_staff_response_at IS NOT NULL
                """, cutoff_date)

                closed_count = 0
                for ticket in old_tickets:
                    success = await self.database.close_ticket(ticket['id'])
                    if success:
                        closed_count += 1

                        # Уведомляем пользователя
                        try:
                            await self.bot.send_message(
                                ticket['user_id'],
                                f"📋 Ваше обращение #{ticket['id']} автоматически закрыто "
                                f"из-за длительной неактивности.\n\n"
                                f"Если вопрос актуален, создайте новое обращение: /start"
                            )
                        except Exception:
                            pass  # Пользователь мог заблокировать бота

                if closed_count > 0:
                    logger.info(f"Auto-closed {closed_count} old tickets")

        except Exception as e:
            logger.error(f"Failed to auto-close old tickets: {e}")

    async def _cleanup_old_backups(self):
        """Очистка старых резервных копий"""
        try:
            import os
            import glob
            from pathlib import Path

            backup_files = sorted(glob.glob("backups/backup_*.json"), reverse=True)

            # Оставляем только последние 7 резервных копий
            for backup_file in backup_files[7:]:
                os.remove(backup_file)
                logger.info(f"Removed old backup: {backup_file}")

        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")

    async def start_polling(self):
        """Запуск polling"""
        try:
            self.running = True
            logger.info("Starting bot polling...")

            # Запуск фоновых задач
            await self.start_background_tasks()

            # Уведомление администраторов о запуске
            startup_message = f"""
🚀 БОТ ЗАПУЩЕН

⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
🌍 Окружение: {config.environment}
🔍 Режим отладки: {'Включен' if config.debug_mode else 'Отключен'}
📊 Версия: 2.0 (с диалогами поддержки)

✅ Все системы работают нормально
            """

            for admin_id in config.ADMIN_IDS:
                try:
                    await self.bot.send_message(admin_id, startup_message)
                except Exception as e:
                    logger.warning(f"Failed to notify admin {admin_id} about startup: {e}")

            # Основной цикл polling
            await self.dp.start_polling(self.bot)

        except Exception as e:
            logger.error(f"Error during polling: {e}")
            raise
        finally:
            await self.cleanup()

    async def stop_background_tasks(self):
        """Остановка фоновых задач"""
        logger.info("Stopping background tasks...")
        self.running = False

        for task in self.background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self.background_tasks.clear()
        logger.info("Background tasks stopped")

    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            logger.info("Starting cleanup...")

            # Остановка фоновых задач
            await self.stop_background_tasks()

            # Уведомление администраторов об остановке
            if self.bot:
                shutdown_message = f"""
🛑 БОТ ОСТАНОВЛЕН

⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
📊 Время работы: {self._get_uptime()}

💾 Создание финальной резервной копии...
                """

                for admin_id in config.ADMIN_IDS:
                    try:
                        await self.bot.send_message(admin_id, shutdown_message)
                    except Exception:
                        pass

            # Создание финальной резервной копии
            if self.data_backup:
                try:
                    logger.info("Creating final backup...")
                    backup_data = await self.data_backup.create_backup()

                    import json
                    import os

                    backup_filename = f"final_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    backup_path = os.path.join("backups", backup_filename)

                    with open(backup_path, 'w', encoding='utf-8') as f:
                        json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)

                    logger.info(f"Final backup created: {backup_path}")
                except Exception as e:
                    logger.error(f"Failed to create final backup: {e}")

            # Закрытие соединений с БД
            if self.database:
                await self.database.close_pool()
                logger.info("Database connections closed")

            # Закрытие сессии бота
            if self.bot:
                await self.bot.session.close()
                logger.info("Bot session closed")

            logger.info("Cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def _get_uptime(self) -> str:
        """Получение времени работы бота"""
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            uptime_seconds = time.time() - process.create_time()
            uptime_td = timedelta(seconds=int(uptime_seconds))

            return str(uptime_td)
        except:
            return "неизвестно"

    def setup_signal_handlers(self):
        """Настройка обработчиков сигналов"""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}")
            # Создаем задачу для graceful shutdown
            asyncio.create_task(self.graceful_shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def graceful_shutdown(self):
        """Плавная остановка бота"""
        logger.info("Initiating graceful shutdown...")

        # Останавливаем прием новых сообщений
        if self.dp:
            await self.dp.stop_polling()

        # Ждем завершения текущих задач
        await asyncio.sleep(2)

        # Очистка ресурсов
        await self.cleanup()

        # Завершение программы
        logger.info("Graceful shutdown completed")
        sys.exit(0)

async def main():
    """Главная функция"""
    # Настройка логирования
    setup_logging()
    logger.info("Festival Bot starting up...")

    # Проверка конфигурации
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables")
        return

    # Логирование конфигурации
    logger.info(f"Environment: {config.environment}")
    logger.info(f"Debug mode: {config.debug_mode}")
    logger.info(f"Log level: {config.log_level}")
    logger.info(f"Database: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
    logger.info(f"Admins configured: {len(config.ADMIN_IDS)}")
    logger.info(f"Support staff configured: {len(config.SUPPORT_STAFF_IDS)}")

    bot = FestivalBot()

    try:
        # Настройка обработчиков сигналов
        bot.setup_signal_handlers()

        # Инициализация бота
        await bot.setup()

        # Запуск polling
        await bot.start_polling()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        # Отправка уведомления об ошибке администраторам
        if bot.bot:
            error_message = f"""
💥 КРИТИЧЕСКАЯ ОШИБКА БОТА

⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
❌ Ошибка: {str(e)}

🔧 Требуется срочное вмешательство!
            """

            for admin_id in config.ADMIN_IDS:
                try:
                    await bot.bot.send_message(admin_id, error_message)
                except Exception:
                    pass
    finally:
        # Финальная очистка
        if bot:
            await bot.cleanup()

if __name__ == "__main__":
    # Проверка версии Python
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        sys.exit(1)

    # Импорт времени для uptime
    import time

    # Запуск бота
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)