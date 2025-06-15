"""
Обработчики сообщений для Telegram-бота (Часть 1)
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError

from config import config
from database import Database
from keyboards import Keyboards

# Состояния для FSM
class SupportStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_message = State()
    waiting_for_continuation = State()

class FeedbackStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_rating = State()
    waiting_for_comment = State()

class AdminStates(StatesGroup):
    waiting_for_schedule_data = State()

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self, database: Database, bot):
        self.db = database
        self.bot = bot
        self.router = Router()
        self._setup_handlers()

    def _setup_handlers(self):
        """Настройка обработчиков"""
        # Команды
        self.router.message(Command("start"))(self.cmd_start)
        self.router.message(Command("menu"))(self.cmd_menu)
        self.router.message(Command("admin"))(self.cmd_admin)

        # Callback запросы
        self.router.callback_query(F.data == "main_menu")(self.show_main_menu)
        self.router.callback_query(F.data == "schedule")(self.show_schedule)
        self.router.callback_query(F.data.startswith("schedule_day_"))(self.show_schedule_day)
        self.router.callback_query(F.data == "navigation")(self.show_navigation)
        self.router.callback_query(F.data == "map")(self.send_festival_map)
        self.router.callback_query(F.data.startswith("route_"))(self.show_location_map)
        self.router.callback_query(F.data == "tickets")(self.show_tickets)
        self.router.callback_query(F.data == "activities")(self.show_activities)
        self.router.callback_query(F.data == "workshops")(self.show_workshops)
        self.router.callback_query(F.data == "lectures")(self.show_lectures)
        self.router.callback_query(F.data == "support")(self.start_support)
        self.router.callback_query(F.data == "feedback")(self.start_feedback)
        self.router.callback_query(F.data.startswith("feedback_"))(self.select_feedback_category)
        self.router.callback_query(F.data.startswith("rating_"))(self.select_rating)
        self.router.callback_query(F.data == "social")(self.show_social_networks)

        # Админ функции
        self.router.callback_query(F.data.startswith("admin_"))(self.handle_admin_actions)

        # Сообщения от сотрудников поддержки в группе (ответы в тредах)
        self.router.message(F.chat.id == int(config.SUPPORT_GROUP_ID) if config.SUPPORT_GROUP_ID else None)(self.handle_support_response)

        # Состояния поддержки
        self.router.message(StateFilter(SupportStates.waiting_for_email))(self.process_support_email)
        self.router.message(StateFilter(SupportStates.waiting_for_message))(self.process_support_message)
        self.router.message(StateFilter(SupportStates.waiting_for_continuation))(self.process_support_continuation)

        # Состояния обратной связи
        self.router.message(StateFilter(FeedbackStates.waiting_for_comment))(self.process_feedback_comment)

        # Обработка всех остальных сообщений
        self.router.message()(self.handle_unknown_message)

    async def _log_user_action(self, user_id: int, action: str, details: Dict = None):
        """Логирование действий пользователя"""
        try:
            await self.db.log_user_action(user_id, action, details)
        except Exception as e:
            logger.error(f"Failed to log user action: {e}")

    async def _update_user_info(self, message_or_query):
        """Обновление информации о пользователе"""
        try:
            user = message_or_query.from_user
            await self.db.add_user(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code
            )
            await self.db.update_user_activity(user.id)
        except Exception as e:
            logger.error(f"Failed to update user info: {e}")

    # Основные команды
    async def cmd_start(self, message: Message):
        """Обработка команды /start"""
        try:
            await self._update_user_info(message)
            await self._log_user_action(message.from_user.id, "start_command")

            welcome_text = f"""
🎵 Добро пожаловать на Музыкальный Фестиваль!

Привет, {message.from_user.first_name}! 👋

Этот бот поможет тебе:
• 📅 Узнать расписание выступлений
• 🗺 Найти нужные места на фестивале
• 🎫 Получить информацию о билетах
• 🎨 Записаться на мастер-классы
• 🆘 Связаться с поддержкой
• 💭 Оставить отзыв

Выбери нужный раздел в меню ниже ⬇️
            """

            await message.answer(welcome_text, reply_markup=Keyboards.main_menu())

        except Exception as e:
            logger.error(f"Error in cmd_start: {e}")
            await message.answer("Произошла ошибка. Попробуйте позже.")

    async def cmd_menu(self, message: Message):
        """Показ главного меню"""
        await self.show_main_menu_message(message)

    async def cmd_admin(self, message: Message):
        """Админ панель"""
        if message.from_user.id in config.ADMIN_IDS:
            await message.answer("🔧 Админ панель", reply_markup=Keyboards.admin_menu())
        else:
            await message.answer("❌ У вас нет прав доступа к админ панели.")

    # Главное меню
    async def show_main_menu(self, query: CallbackQuery):
        """Показ главного меню (callback)"""
        await self._update_user_info(query)
        await self._log_user_action(query.from_user.id, "main_menu")

        await query.message.edit_text(
            "🎵 Главное меню\n\nВыберите нужный раздел:",
            reply_markup=Keyboards.main_menu()
        )
        await query.answer()

    async def show_main_menu_message(self, message: Message):
        """Показ главного меню (сообщение)"""
        await self._update_user_info(message)
        await self._log_user_action(message.from_user.id, "main_menu")

        await message.answer(
            "🎵 Главное меню\n\nВыберите нужный раздел:",
            reply_markup=Keyboards.main_menu()
        )

    # Расписание
    async def show_schedule(self, query: CallbackQuery):
        """Показ меню расписания"""
        await self._log_user_action(query.from_user.id, "schedule_menu")

        text = """
📅 Расписание фестиваля

Фестиваль проходит 5 дней.
Выберите день для просмотра программы:
        """

        await query.message.edit_text(text, reply_markup=Keyboards.schedule_days())
        await query.answer()

    async def show_schedule_day(self, query: CallbackQuery):
        """Показ расписания конкретного дня"""
        day = int(query.data.split("_")[-1])
        await self._log_user_action(query.from_user.id, "schedule_day", {"day": day})

        try:
            schedule = await self.db.get_schedule_by_day(day)

            if schedule:
                text = f"📅 Расписание - День {day}\n\n"
                for item in schedule:
                    text += f"🕐 {item['time'].strftime('%H:%M')} - {item['artist_name']}\n"
                    text += f"🎪 Сцена: {item['stage']}\n"
                    if item['description']:
                        text += f"📝 {item['description']}\n"
                    text += "\n"
            else:
                text = f"📅 День {day}\n\nРасписание пока не опубликовано.\nСледите за обновлениями!"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="schedule")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])

            await query.message.edit_text(text, reply_markup=keyboard)
            await query.answer()

        except Exception as e:
            logger.error(f"Error showing schedule day {day}: {e}")
            await query.answer("Ошибка при загрузке расписания", show_alert=True)

    # Навигация
    async def show_navigation(self, query: CallbackQuery):
        """Показ меню навигации"""
        await self._log_user_action(query.from_user.id, "navigation_menu")

        text = """
🗺 Навигация по фестивалю

Выберите, что вас интересует:
• Общая карта фестиваля
• Маршруты до ключевых точек
• Информация о локациях
        """

        await query.message.edit_text(text, reply_markup=Keyboards.navigation_menu())
        await query.answer()

    async def send_festival_map(self, query: CallbackQuery):
        """Отправка общей карты фестиваля"""
        await self._log_user_action(query.from_user.id, "festival_map")

        try:
            # Построение маршрута до фестиваля
            route_url = config.get_yandex_route_url(config.FESTIVAL_COORDINATES)

            # Клавиатура с маршрутом
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗺 Построить маршрут", url=route_url)],
                [InlineKeyboardButton(text="◀️ Назад к навигации", callback_data="navigation")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])

            # Отправка изображения карты
            try:
                from aiogram.types import FSInputFile

                map_image = FSInputFile(config.MAPS_IMAGES["festival_map"])
                await query.message.answer_photo(
                    photo=map_image,
                    caption="🗺 **Карта фестиваля**\n\n"
                            "📍 Основные зоны:\n"
                            "• Главная сцена - центр\n"
                            "• Малая сцена - север\n"
                            "• Фудкорт - восток\n"
                            "• Мастер-классы - запад\n"
                            "• Сувениры - вход\n\n"
                            "Нажмите \"Построить маршрут\" для навигации до фестиваля",
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )

            except FileNotFoundError:
                # Если файл карты не найден, отправляем текстовое описание
                await query.message.edit_text(
                    "🗺 **Карта фестиваля**\n\n"
                    "📍 Основные зоны:\n"
                    "• Главная сцена - центр территории\n"
                    "• Малая сцена - северная часть\n"
                    "• Фудкорт - восточная часть\n"
                    "• Мастер-классы - западная часть\n"
                    "• Сувениры - у главного входа\n"
                    "• Туалеты - по периметру\n"
                    "• Медпункт - рядом с главной сценой\n\n"
                    "Нажмите \"Построить маршрут\" для навигации до фестиваля",
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )

        except Exception as e:
            logger.error(f"Error sending festival map: {e}")
            await query.answer("Ошибка при загрузке карты", show_alert=True)

        await query.answer()

    async def show_location_map(self, query: CallbackQuery):
        """Показ карты конкретной локации с маршрутом"""
        location = query.data.split("_", 1)[1]
        await self._log_user_action(query.from_user.id, "location_map", {"location": location})

        # Информация о локациях
        locations_info = {
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
        }

        location_info = locations_info.get(location)
        if not location_info:
            await query.answer("Локация не найдена", show_alert=True)
            return

        try:
            # Получение координат для маршрута
            coords = config.LOCATIONS_COORDINATES.get(location, config.FESTIVAL_COORDINATES)
            route_url = config.get_yandex_route_url(coords)

            # Формирование текста
            details_text = "\n".join([f"• {detail}" for detail in location_info["details"]])
            caption_text = f"**{location_info['title']}**\n\n" \
                           f"{location_info['description']}\n\n" \
                           f"📋 **Что здесь есть:**\n{details_text}\n\n" \
                           f"Нажмите \"Построить маршрут\" для навигации"

            # Клавиатура с маршрутом
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗺 Построить маршрут", url=route_url)],
                [InlineKeyboardButton(text="◀️ Назад к навигации", callback_data="navigation")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])

            # Попытка отправить изображение
            try:
                from aiogram.types import FSInputFile

                map_image_path = config.MAPS_IMAGES.get(location)
                if map_image_path:
                    map_image = FSInputFile(map_image_path)
                    await query.message.answer_photo(
                        photo=map_image,
                        caption=caption_text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                else:
                    # Если нет специального изображения, отправляем текст
                    await query.message.edit_text(
                        caption_text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )

            except FileNotFoundError:
                # Если файл не найден, отправляем только текст
                await query.message.edit_text(
                    caption_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )

        except Exception as e:
            logger.error(f"Error showing location map for {location}: {e}")
            await query.answer("Ошибка при загрузке информации о локации", show_alert=True)

        await query.answer()