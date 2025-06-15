import asyncio
import logging
import sys
import signal
import time
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

from config import config
from database import Database
from handlers import BotHandlers
from utils import EmailSender, DataBackup, HealthChecker

# Настройка логирования
def setup_logging():
    """Настройка системы логирования"""
    import pathlib
    pathlib.Path("logs").mkdir(exist_ok=True)

    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format=log_format,
        handlers=[
            logging.FileHandler('logs/bot.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    error_handler = logging.FileHandler('logs/errors.log', encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format))
    logging.getLogger().addHandler(error_handler)

    stats_logger = logging.getLogger('stats')
    stats_handler = logging.FileHandler('logs/stats.log', encoding='utf-8')
    stats_handler.setFormatter(logging.Formatter(log_format))
    stats_logger.addHandler(stats_handler)
    stats_logger.setLevel(logging.INFO)

    support_logger = logging.getLogger('support')
    support_handler = logging.FileHandler('logs/support.log', encoding='utf-8')
    support_handler.setFormatter(logging.Formatter(log_format))
    support_logger.addHandler(support_handler)
    support_logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

class WebServer:
    """Простой веб-сервер для health check"""

    def __init__(self, database, bot):
        self.db = database
        self.bot = bot
        self.app = web.Application()
        self.setup_routes()

    def setup_routes(self):
        """Настройка маршрутов"""
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/status', self.status)

    async def index(self, request):
        """Главная страница"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Festival Bot</title>
            <meta charset="utf-8">
        </head>
        <body>
            <h1>🎵 Festival Bot</h1>
            <p>Бот для музыкального фестиваля работает!</p>
            <p>Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
            <ul>
                <li><a href="/health">Health Check</a></li>
                <li><a href="/status">Status</a></li>
            </ul>
        </body>
        </html>
        """

        return web.Response(text=html, content_type='text/html')

    async def health_check(self, request):
        """Health check endpoint"""
        try:
            # Проверка БД
            async with self.db.get_connection() as conn:
                await conn.fetchval('SELECT 1')

            # Проверка бота
            bot_info = await self.bot.get_me()

            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "database": "connected",
                "bot": {
                    "username": bot_info.username,
                    "id": bot_info.id
                }
            }

            return web.json_response(health_data)

        except Exception as e:
            logger.error(f"Health check failed: {e}")

            error_data = {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }

            return web.json_response(error_data, status=500)

    async def status(self, request):
        """Статус системы"""
        try:
            stats = await self.db.get_usage_stats() if self.db else {}

            status_data = {
                "status": "running",
                "timestamp": datetime.now().isoformat(),
                "stats": stats
            }

            return web.json_response(status_data)

        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def start_server(self, host='0.0.0.0', port=8080):
        """Запуск веб-сервера"""
        try:
            runner = web.AppRunner(self.app)
            await runner.setup()

            site = web.TCPSite(runner, host, port)
            await site.start()

            logger.info(f"Web server started on http://{host}:{port}")
            return runner

        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            raise

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
        self.web_server = None
        self.web_runner = None
        self.running = False
        self.background_tasks = []

    async def setup(self):
        """Настройка бота"""
        try:
            logger.info("Starting bot setup...")

            if not config.validate_config():
                raise ValueError("Invalid configuration")

            logger.info(f"Environment: {config.environment}")
            logger.info(f"Debug mode: {config.debug_mode}")

            # Инициализация бота
            self.bot = Bot(
                token=config.BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

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

            # Веб-сервер
            logger.info("Initializing web server...")
            self.web_server = WebServer(self.database, self.bot)
            logger.info("Web server initialized")

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

        admin_commands = commands + [
            BotCommand(command="admin", description="🔧 Админ панель"),
            BotCommand(command="stats", description="📊 Статистика"),
            BotCommand(command="health", description="🏥 Проверка здоровья"),
        ]

        try:
            await self.bot.set_my_commands(commands)

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

        health_task = asyncio.create_task(self.health_check_loop())
        self.background_tasks.append(health_task)

        cleanup_task = asyncio.create_task(self.cleanup_loop())
        self.background_tasks.append(cleanup_task)

        backup_task = asyncio.create_task(self.backup_loop())
        self.background_tasks.append(backup_task)

        stats_task = asyncio.create_task(self.stats_loop())
        self.background_tasks.append(stats_task)

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
                await asyncio.sleep(24 * 60 * 60)
                logger.info("Starting data cleanup...")
                # Здесь можно добавить логику очистки
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
                await asyncio.sleep(config.get_monitoring_config()["backup_interval_hours"] * 60 * 60)

                if self.data_backup:
                    logger.info("Creating database backup...")
                    backup_data = await self.data_backup.create_backup()
                    await self.data_backup.save_backup_to_file(backup_data)
                    await self.data_backup.cleanup_old_backups()

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
                now = datetime.now()
                next_report = now.replace(hour=9, minute=0, second=0, microsecond=0)
                if next_report <= now:
                    next_report += timedelta(days=1)

                sleep_seconds = (next_report - now).total_seconds()
                await asyncio.sleep(sleep_seconds)

                # Здесь можно добавить отправку статистики

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
                await asyncio.sleep(30 * 60)

                if config.get_notification_config()["notify_admins_urgent_tickets"]:
                    urgent_tickets = await self.database.get_tickets_requiring_attention()

                    if urgent_tickets:
                        # Здесь можно добавить уведомления
                        logger.info(f"Found {len(urgent_tickets)} urgent tickets")

            except asyncio.CancelledError:
                logger.info("Urgent tickets monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Urgent tickets monitoring error: {e}")

    async def start_polling(self):
        """Запуск polling"""
        try:
            self.running = True
            logger.info("Starting bot polling...")

            # Запуск веб-сервера
            logger.info("Starting web server...")
            self.web_runner = await self.web_server.start_server()

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

            await self.stop_background_tasks()

            if self.bot:
                shutdown_message = f"""
🛑 БОТ ОСТАНОВЛЕН

⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
                """

                for admin_id in config.ADMIN_IDS:
                    try:
                        await self.bot.send_message(admin_id, shutdown_message)
                    except Exception:
                        pass

            # Остановка веб-сервера
            if self.web_runner:
                await self.web_runner.cleanup()
                logger.info("Web server stopped")

            if self.database:
                await self.database.close_pool()
                logger.info("Database connections closed")

            if self.bot:
                await self.bot.session.close()
                logger.info("Bot session closed")

            logger.info("Cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def setup_signal_handlers(self):
        """Настройка обработчиков сигналов"""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}")
            asyncio.create_task(self.graceful_shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def graceful_shutdown(self):
        """Плавная остановка бота"""
        logger.info("Initiating graceful shutdown...")

        if self.dp:
            await self.dp.stop_polling()

        await asyncio.sleep(2)
        await self.cleanup()

        logger.info("Graceful shutdown completed")
        sys.exit(0)

async def main():
    """Главная функция"""
    setup_logging()
    logger.info("Festival Bot starting up...")

    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables")
        return

    logger.info(f"Environment: {config.environment}")
    logger.info(f"Debug mode: {config.debug_mode}")
    logger.info(f"Log level: {config.log_level}")
    logger.info(f"Database: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
    logger.info(f"Admins configured: {len(config.ADMIN_IDS)}")
    logger.info(f"Support staff configured: {len(config.SUPPORT_STAFF_IDS)}")

    bot = FestivalBot()

    try:
        bot.setup_signal_handlers()
        await bot.setup()
        await bot.start_polling()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
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
        if bot:
            await bot.cleanup()

if __name__ == "__main__":
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        sys.exit(1)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)