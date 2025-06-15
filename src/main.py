
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class FestivalBot:
    """Основной класс бота"""

    def __init__(self):
        self.bot = None
        self.dp = None
        self.database = None
        self.handlers = None
        self.email_sender = None
        self.health_checker = None

    async def setup(self):
        """Настройка бота"""
        try:
            # Инициализация бота
            self.bot = Bot(
                token=config.BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            # Диспетчер с хранилищем состояний
            storage = MemoryStorage()
            self.dp = Dispatcher(storage=storage)

            # База данных
            self.database = Database(config.get_database_url())
            await self.database.create_pool()
            await self.database.init_tables()

            # Обработчики
            self.handlers = BotHandlers(self.database, self.bot)
            self.dp.include_router(self.handlers.router)

            # Email сендер
            if config.EMAIL_USER and config.EMAIL_PASSWORD:
                self.email_sender = EmailSender(
                    config.SMTP_SERVER,
                    config.SMTP_PORT,
                    config.EMAIL_USER,
                    config.EMAIL_PASSWORD
                )

            # Мониторинг здоровья
            self.health_checker = HealthChecker(self.database, self.bot)

            logger.info("Bot setup completed successfully")

        except Exception as e:
            logger.error(f"Failed to setup bot: {e}")
            raise

    async def start_polling(self):
        """Запуск polling"""
        try:
            logger.info("Starting bot polling...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Error during polling: {e}")
            raise
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            if self.database:
                await self.database.close_pool()

            if self.bot:
                await self.bot.session.close()

            logger.info("Cleanup completed")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def health_check_loop(self):
        """Периодическая проверка здоровья системы"""
        while True:
            try:
                await asyncio.sleep(300)  # Проверка каждые 5 минут

                if self.health_checker:
                    health_status = await self.health_checker.health_check()

                    if not self.health_checker.is_healthy:
                        logger.warning(f"Health check failed: {health_status}")

                        # Уведомление администраторов
                        for admin_id in config.ADMIN_IDS:
                            try:
                                await self.bot.send_message(
                                    admin_id,
                                    f"⚠️ Проблемы с ботом:\n{health_status['errors']}"
                                )
                            except Exception:
                                pass

            except Exception as e:
                logger.error(f"Health check error: {e}")

async def main():
    """Главная функция"""
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables")
        return

    bot = FestivalBot()

    try:
        await bot.setup()

        # Запуск проверки здоровья в фоне
        health_task = asyncio.create_task(bot.health_check_loop())

        # Запуск polling
        await bot.start_polling()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        if 'health_task' in locals():
            health_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())