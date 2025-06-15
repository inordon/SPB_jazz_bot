import asyncio
import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError

from config import config
from database import Database
from keyboards import Keyboards

# Обновленные состояния для FSM
class SupportStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_message = State()
    active_ticket_dialog = State()
    waiting_for_new_ticket_email = State()
    waiting_for_new_ticket_message = State()

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
        self.router.callback_query(F.data == "skip_comment")(self.skip_feedback_comment)
        self.router.callback_query(F.data == "social")(self.show_social_networks)

        # Новые обработчики для диалогов поддержки
        self.router.callback_query(F.data.startswith("continue_dialog_"))(self.continue_dialog)
        self.router.callback_query(F.data.startswith("show_history_"))(self.show_ticket_history)
        self.router.callback_query(F.data.startswith("close_ticket_"))(self.close_ticket_confirm)
        self.router.callback_query(F.data.startswith("confirm_close_"))(self.confirm_close_ticket)
        self.router.callback_query(F.data.startswith("back_to_ticket_"))(self.back_to_ticket)
        self.router.callback_query(F.data == "new_ticket")(self.start_new_ticket_flow)

        # Админ функции
        self.router.callback_query(F.data.startswith("admin_"))(self.handle_admin_actions)

        # Сообщения от сотрудников поддержки в группе (ответы в тредах)
        if config.SUPPORT_GROUP_ID:
            self.router.message(F.chat.id == int(config.SUPPORT_GROUP_ID))(self.handle_support_response)

        # Состояния поддержки
        self.router.message(StateFilter(SupportStates.waiting_for_email))(self.process_support_email)
        self.router.message(StateFilter(SupportStates.waiting_for_message))(self.process_support_message)
        self.router.message(StateFilter(SupportStates.active_ticket_dialog))(self.process_active_dialog_message)
        self.router.message(StateFilter(SupportStates.waiting_for_new_ticket_email))(self.process_new_ticket_email)
        self.router.message(StateFilter(SupportStates.waiting_for_new_ticket_message))(self.process_new_ticket_message)

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

            # Проверяем наличие активного тикета для индикатора
            active_ticket = await self.db.get_user_active_ticket(message.from_user.id)
            has_active_ticket = active_ticket is not None

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

            if has_active_ticket:
                welcome_text += f"\n🔴 У вас есть активное обращение #{active_ticket['id']} в поддержку"

            await message.answer(welcome_text, reply_markup=Keyboards.main_menu_with_support_indicator(has_active_ticket))

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

        # Проверяем наличие активного тикета
        active_ticket = await self.db.get_user_active_ticket(query.from_user.id)
        has_active_ticket = active_ticket is not None

        text = "🎵 Главное меню\n\nВыберите нужный раздел:"
        if has_active_ticket:
            text += f"\n\n🔴 У вас есть активное обращение #{active_ticket['id']} в поддержку"

        await query.message.edit_text(text, reply_markup=Keyboards.main_menu_with_support_indicator(has_active_ticket))
        await query.answer()

    async def show_main_menu_message(self, message: Message):
        """Показ главного меню (сообщение)"""
        await self._update_user_info(message)
        await self._log_user_action(message.from_user.id, "main_menu")

        # Проверяем наличие активного тикета
        active_ticket = await self.db.get_user_active_ticket(message.from_user.id)
        has_active_ticket = active_ticket is not None

        text = "🎵 Главное меню\n\nВыберите нужный раздел:"
        if has_active_ticket:
            text += f"\n\n🔴 У вас есть активное обращение #{active_ticket['id']} в поддержку"

        await message.answer(text, reply_markup=Keyboards.main_menu_with_support_indicator(has_active_ticket))

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

    # Билеты
    async def show_tickets(self, query: CallbackQuery):
        """Показ информации о билетах"""
        await self._log_user_action(query.from_user.id, "tickets_menu")

        text = """
🎫 Билеты на фестиваль

Доступны различные типы билетов:
• Входной билет (1 день)
• Семейный билет (5 человек)  
• Абонементы (2, 3, 5 дней)

💡 Все билеты включают:
• Доступ ко всем сценам
• Участие в мастер-классах
• Доступ к зонам отдыха

Для покупки билетов нажмите кнопку ниже.
        """

        await query.message.edit_text(text, reply_markup=Keyboards.tickets_menu())
        await query.answer()

    # Активности
    async def show_activities(self, query: CallbackQuery):
        """Показ меню активностей"""
        await self._log_user_action(query.from_user.id, "activities_menu")

        text = """
🎨 Активности фестиваля

На фестивале доступны различные образовательные и творческие активности:

🎨 **Мастер-классы** - практические творческие воркшопы
🎓 **Лекторий** - теоретические лекции и семинары

Выберите интересующую активность:
        """

        await query.message.edit_text(text, reply_markup=Keyboards.activities_menu())
        await query.answer()

    async def show_workshops(self, query: CallbackQuery):
        """Показ информации о мастер-классах"""
        await self._log_user_action(query.from_user.id, "workshops_info")

        text = """
🎨 Мастер-классы

📅 Расписание:
• 12:00-13:30 - "Основы игры на гитаре"
• 14:00-15:30 - "Создание музыки на компьютере"
• 16:00-17:30 - "Вокальная техника"
• 18:00-19:30 - "Написание песен"

📍 Локация: Белые шатры (западная зона)

👥 Участники: до 20 человек в группе
🎫 Стоимость: включено в билет
📝 Запись: через администратора или в шатре

🎁 Каждый участник получает:
• Сертификат участника
• Учебные материалы
• Запись мастер-класса

💡 Рекомендуем записаться заранее!
        """

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Записаться", callback_data="workshop_register")],
            [InlineKeyboardButton(text="◀️ Назад к активностям", callback_data="activities")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])

        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def show_lectures(self, query: CallbackQuery):
        """Показ информации о лектории"""
        await self._log_user_action(query.from_user.id, "lectures_info")

        text = """
🎓 Лекторий

📅 Расписание лекций:
• 10:00-11:00 - "История джаза: от истоков до наших дней"
• 11:30-12:30 - "Музыкальная индустрия сегодня"
• 13:00-14:00 - "Авторское право в музыке"
• 15:00-16:00 - "Психология творчества"
• 16:30-17:30 - "Продвижение музыканта в цифровую эпоху"

📍 Локация: Лекционный зал (центральная зона)

👥 Участники: до 100 человек
🎫 Стоимость: включено в билет
📝 Запись: не требуется, свободный вход

🎁 Дополнительно:
• Запись всех лекций
• Презентации спикеров
• Возможность задать вопросы
• Networking с экспертами

💡 Лекции проходят каждый день фестиваля!
        """

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Расписание всех лекций", callback_data="lectures_schedule")],
            [InlineKeyboardButton(text="◀️ Назад к активностям", callback_data="activities")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])

        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    # ================== ПОДДЕРЖКА V2 (С ДИАЛОГАМИ) ==================

    async def start_support(self, query: CallbackQuery, state: FSMContext):
        """Начало процесса работы с поддержкой - проверяем активные тикеты"""
        await self._log_user_action(query.from_user.id, "support_start")

        # Проверяем есть ли активный тикет
        active_ticket = await self.db.get_user_active_ticket(query.from_user.id)

        if active_ticket:
            # Показываем активный тикет
            await self._show_active_ticket(query, active_ticket, state)
        else:
            # Начинаем создание нового тикета
            await self._start_new_ticket(query, state)

    async def _show_active_ticket(self, query: CallbackQuery, ticket: Dict, state: FSMContext):
        """Показ активного тикета с опциями"""
        ticket_id = ticket['id']
        created_date = ticket['created_at'].strftime('%d.%m.%Y %H:%M')

        # Получаем последние сообщения
        ticket_with_messages = await self.db.get_ticket_with_last_messages(ticket_id, 3)

        text = f"""
💬 У вас есть активное обращение #{ticket_id}

📅 Создано: {created_date}
📧 Email: {ticket['email']}
📝 Первое сообщение: {ticket['message'][:100]}{'...' if len(ticket['message']) > 100 else ''}

💭 Последние сообщения:
        """

        if ticket_with_messages and ticket_with_messages.get('messages'):
            for msg in ticket_with_messages['messages'][-3:]:
                sender = "🧑‍💼 Поддержка" if msg['is_staff'] else "👤 Вы"
                msg_text = msg['message_text'][:50] if msg['message_text'] else "[Медиа]"
                msg_time = msg['created_at'].strftime('%H:%M')
                text += f"\n{sender} ({msg_time}): {msg_text}{'...' if len(msg.get('message_text', '')) > 50 else ''}"

        text += "\n\nВыберите действие:"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Продолжить диалог",
                                  callback_data=f"continue_dialog_{ticket_id}")],
            [InlineKeyboardButton(text="📝 История сообщений",
                                  callback_data=f"show_history_{ticket_id}")],
            [InlineKeyboardButton(text="✅ Закрыть обращение",
                                  callback_data=f"close_ticket_{ticket_id}")],
            [InlineKeyboardButton(text="🆕 Новое обращение",
                                  callback_data="new_ticket")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])

        await query.message.edit_text(text, reply_markup=keyboard)

    async def _start_new_ticket(self, query: CallbackQuery, state: FSMContext):
        """Начало создания нового тикета"""
        text = """
🆘 Создание нового обращения

Мы поможем решить любые вопросы!

Для создания обращения нам нужно:
1. Ваш email для связи
2. Описание проблемы или вопроса
3. При необходимости - фотография или документ

Введите ваш email:
        """

        await query.message.edit_text(text, reply_markup=Keyboards.back_to_main())
        await state.set_state(SupportStates.waiting_for_email)

    # Обработчики callback'ов для диалогов
    async def continue_dialog(self, query: CallbackQuery, state: FSMContext):
        """Продолжение диалога по активному тикету"""
        ticket_id = int(query.data.split("_")[-1])

        # Проверяем rate limit
        rate_check = await self.db.check_rate_limit(query.from_user.id)
        if not rate_check["can_send"]:
            await query.answer(rate_check["reason"], show_alert=True)
            return

        await state.update_data(active_ticket_id=ticket_id)
        await state.set_state(SupportStates.active_ticket_dialog)

        text = f"""
💬 Диалог по обращению #{ticket_id}

Напишите ваше сообщение. Вы можете отправить:
• Текстовое сообщение
• Фотографию с описанием
• Документ
• Видео

Ваше сообщение будет передано команде поддержки.
        """

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 История сообщений",
                                  callback_data=f"show_history_{ticket_id}")],
            [InlineKeyboardButton(text="✅ Закрыть обращение",
                                  callback_data=f"close_ticket_{ticket_id}")],
            [InlineKeyboardButton(text="◀️ Назад к тикету",
                                  callback_data=f"back_to_ticket_{ticket_id}")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])

        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def show_ticket_history(self, query: CallbackQuery):
        """Показ истории сообщений тикета"""
        ticket_id = int(query.data.split("_")[-1])

        try:
            messages = await self.db.get_ticket_messages(ticket_id, limit=20)

            if not messages:
                await query.answer("История сообщений пуста", show_alert=True)
                return

            text = f"📋 История обращения #{ticket_id}\n\n"

            for msg in messages[-10:]:  # Последние 10 сообщений
                sender_icon = "🧑‍💼" if msg['is_staff'] else "👤"
                sender_name = "Поддержка" if msg['is_staff'] else "Вы"
                time_str = msg['created_at'].strftime('%d.%m %H:%M')

                if msg['message_text']:
                    msg_preview = msg['message_text'][:100]
                    if len(msg['message_text']) > 100:
                        msg_preview += "..."
                else:
                    msg_preview = f"[{msg['message_type'].upper()}]"

                text += f"{sender_icon} {sender_name} ({time_str}):\n{msg_preview}\n\n"

            if len(messages) > 10:
                text += f"... и еще {len(messages) - 10} сообщений"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 Продолжить диалог",
                                      callback_data=f"continue_dialog_{ticket_id}")],
                [InlineKeyboardButton(text="◀️ Назад к тикету",
                                      callback_data=f"back_to_ticket_{ticket_id}")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])

            await query.message.edit_text(text, reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error showing ticket history: {e}")
            await query.answer("Ошибка при загрузке истории", show_alert=True)

    async def close_ticket_confirm(self, query: CallbackQuery):
        """Подтверждение закрытия тикета"""
        ticket_id = int(query.data.split("_")[-1])

        text = f"""
❓ Закрыть обращение #{ticket_id}?

После закрытия:
• Диалог будет завершен
• История сообщений сохранится
• Вы сможете создать новое обращение

Вы уверены?
        """

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, закрыть",
                                  callback_data=f"confirm_close_{ticket_id}")],
            [InlineKeyboardButton(text="❌ Отмена",
                                  callback_data=f"back_to_ticket_{ticket_id}")]
        ])

        await query.message.edit_text(text, reply_markup=keyboard)

    async def confirm_close_ticket(self, query: CallbackQuery, state: FSMContext):
        """Подтверждение закрытия тикета"""
        ticket_id = int(query.data.split("_")[-1])

        try:
            success = await self.db.close_ticket(ticket_id, query.from_user.id)

            if success:
                # Уведомляем в группу поддержки
                await self._notify_support_ticket_closed(ticket_id, query.from_user)

                text = f"""
✅ Обращение #{ticket_id} закрыто

Спасибо за обращение! 
Если возникнут новые вопросы, создайте новое обращение.

🌟 Оцените нашу работу в разделе "💭 Обратная связь"
                """

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🆕 Новое обращение", callback_data="new_ticket")],
                    [InlineKeyboardButton(text="💭 Оставить отзыв", callback_data="feedback")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
                ])

                await query.message.edit_text(text, reply_markup=keyboard)
                await state.clear()

            else:
                await query.answer("Ошибка при закрытии тикета", show_alert=True)

        except Exception as e:
            logger.error(f"Error closing ticket {ticket_id}: {e}")
            await query.answer("Ошибка при закрытии тикета", show_alert=True)

    async def back_to_ticket(self, query: CallbackQuery, state: FSMContext):
        """Возврат к просмотру тикета"""
        ticket_id = int(query.data.split("_")[-1])

        try:
            ticket = await self.db.get_ticket_with_last_messages(ticket_id, 3)
            if ticket:
                await self._show_active_ticket(query, ticket, state)
            else:
                await query.answer("Тикет не найден", show_alert=True)
                await self.show_main_menu(query)
        except Exception as e:
            logger.error(f"Error returning to ticket {ticket_id}: {e}")
            await query.answer("Ошибка при загрузке тикета", show_alert=True)

    async def start_new_ticket_flow(self, query: CallbackQuery, state: FSMContext):
        """Начало создания нового тикета (callback)"""
        await state.clear()
        await self._start_new_ticket(query, state)

    # Обработка email для поддержки
    async def process_support_email(self, message: Message, state: FSMContext):
        """Обработка email для поддержки"""
        email = message.text.strip()

        # Простая валидация email
        if "@" not in email or "." not in email:
            await message.answer(
                "❌ Неверный формат email. Попробуйте еще раз:\n\nПример: your@email.com",
                reply_markup=Keyboards.back_to_main()
            )
            return

        await state.update_data(email=email)
        await message.answer(
            f"✅ Email сохранен: {email}\n\n"
            "Теперь опишите вашу проблему или задайте вопрос.\n"
            "Вы также можете прикрепить фотографию, документ или видео:",
            reply_markup=Keyboards.back_to_main()
        )
        await state.set_state(SupportStates.waiting_for_message)

    async def process_support_message(self, message: Message, state: FSMContext):
        """Обработка сообщения для поддержки"""
        try:
            data = await state.get_data()
            email = data.get("email")

            message_text = message.text or message.caption or ""
            photo_file_id = message.photo[-1].file_id if message.photo else None
            document_file_id = message.document.file_id if message.document else None
            video_file_id = message.video.file_id if message.video else None

            # Создание тикета в БД
            ticket_id = await self.db.create_support_ticket_v2(
                user_id=message.from_user.id,
                email=email,
                message=message_text,
                photo_file_id=photo_file_id,
                document_file_id=document_file_id,
                video_file_id=video_file_id
            )

            await self._log_user_action(message.from_user.id, "support_ticket_created",
                                        {"ticket_id": ticket_id})

            # Отправка в группу поддержки с созданием треда
            thread_id, initial_message_id = await self._send_to_support_group_v2(
                ticket_id, message, email, message_text, photo_file_id, document_file_id, video_file_id
            )

            # Обновление тикета с информацией о треде
            if thread_id and initial_message_id:
                await self.db.update_ticket_thread_info(ticket_id, thread_id, initial_message_id)

            # Отправляем подтверждение пользователю
            await message.answer(
                f"✅ Ваше обращение #{ticket_id} принято!\n\n"
                "⏱ Мы ответим в течение 2 часов.\n"
                "📱 Ответ придет прямо в этот бот от Сотрудника Поддержки.\n"
                "🔔 Включите уведомления, чтобы не пропустить ответ!\n\n"
                "💬 Вы можете продолжать писать сообщения - они будут добавлены к этому обращению.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💬 Продолжить диалог",
                                          callback_data=f"continue_dialog_{ticket_id}")],
                    [InlineKeyboardButton(text="✅ Завершить", callback_data="main_menu")]
                ])
            )

            # Устанавливаем состояние активного диалога
            await state.update_data(active_ticket_id=ticket_id)
            await state.set_state(SupportStates.active_ticket_dialog)

        except Exception as e:
            logger.error(f"Error processing support message: {e}")
            await message.answer(
                "❌ Произошла ошибка при создании обращения. Попробуйте позже.",
                reply_markup=Keyboards.back_to_main()
            )
            await state.clear()

    # Обработка сообщений в активном диалоге
    async def process_active_dialog_message(self, message: Message, state: FSMContext):
        """Обработка сообщений в активном диалоге"""
        try:
            # Проверяем rate limit
            rate_check = await self.db.check_rate_limit(message.from_user.id)
            if not rate_check["can_send"]:
                await message.answer(
                    f"⏳ {rate_check['reason']}\n\nПопробуйте через {rate_check['wait_seconds']} секунд.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
                    ])
                )
                return

            data = await state.get_data()
            ticket_id = data.get("active_ticket_id")

            if not ticket_id:
                await state.clear()
                await message.answer("Диалог завершен. Создайте новое обращение.",
                                     reply_markup=Keyboards.main_menu())
                return

            # Получаем файлы
            photo_file_id = message.photo[-1].file_id if message.photo else None
            document_file_id = message.document.file_id if message.document else None
            video_file_id = message.video.file_id if message.video else None
            message_text = message.text or message.caption or ""

            # Добавляем сообщение к тикету
            message_id = await self.db.add_ticket_message(
                ticket_id=ticket_id,
                user_id=message.from_user.id,
                message_text=message_text,
                photo_file_id=photo_file_id,
                document_file_id=document_file_id,
                video_file_id=video_file_id,
                is_staff=False
            )

            # Отправляем в группу поддержки
            await self._send_dialog_message_to_support(ticket_id, message, message_text,
                                                       photo_file_id, document_file_id, video_file_id)

            await self._log_user_action(message.from_user.id, "support_dialog_message",
                                        {"ticket_id": ticket_id, "message_id": message_id})

            # Подтверждение пользователю
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 История сообщений",
                                      callback_data=f"show_history_{ticket_id}")],
                [InlineKeyboardButton(text="✅ Закрыть обращение",
                                      callback_data=f"close_ticket_{ticket_id}")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])

            await message.answer(
                f"✅ Сообщение отправлено команде поддержки!\n\n"
                f"💬 Обращение #{ticket_id} остается активным.\n"
                f"📱 Ответ придет в этот бот от Сотрудника Поддержки.\n\n"
                f"Можете продолжать писать сообщения в этом диалоге.",
                reply_markup=keyboard
            )

        except Exception as e:
            logger.error(f"Error processing dialog message: {e}")
            await message.answer(
                "❌ Произошла ошибка при отправке сообщения. Попробуйте позже.",
                reply_markup=Keyboards.back_to_main()
            )

    async def _send_dialog_message_to_support(self, ticket_id: int, message: Message,
                                              message_text: str, photo_file_id: str = None,
                                              document_file_id: str = None, video_file_id: str = None):
        """Отправка сообщения диалога в группу поддержки"""
        if not config.SUPPORT_GROUP_ID:
            return

        try:
            # Получаем тикет для определения thread_id
            ticket = await self.db.get_ticket_by_thread(ticket_id)
            thread_id = ticket.get('thread_id') if ticket else None

            user = message.from_user
            support_text = f"""
💬 СООБЩЕНИЕ В ДИАЛОГЕ #{ticket_id}

👤 От: {user.first_name} {user.last_name or ''}
⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}

💬 Сообщение:
{message_text}

📝 Ответьте в этом треде для продолжения диалога
            """

            # Отправляем в тред (если есть) или в общий чат
            if thread_id and config.SUPPORT_GROUP_TOPICS:
                if photo_file_id:
                    await self.bot.send_photo(
                        config.SUPPORT_GROUP_ID,
                        photo_file_id,
                        caption=support_text,
                        message_thread_id=thread_id
                    )
                elif document_file_id:
                    await self.bot.send_document(
                        config.SUPPORT_GROUP_ID,
                        document_file_id,
                        caption=support_text,
                        message_thread_id=thread_id
                    )
                elif video_file_id:
                    await self.bot.send_video(
                        config.SUPPORT_GROUP_ID,
                        video_file_id,
                        caption=support_text,
                        message_thread_id=thread_id
                    )
                else:
                    await self.bot.send_message(
                        config.SUPPORT_GROUP_ID,
                        support_text,
                        message_thread_id=thread_id
                    )
            else:
                # Отправляем в общий чат группы
                if photo_file_id:
                    await self.bot.send_photo(config.SUPPORT_GROUP_ID, photo_file_id, caption=support_text)
                elif document_file_id:
                    await self.bot.send_document(config.SUPPORT_GROUP_ID, document_file_id, caption=support_text)
                elif video_file_id:
                    await self.bot.send_video(config.SUPPORT_GROUP_ID, video_file_id, caption=support_text)
                else:
                    await self.bot.send_message(config.SUPPORT_GROUP_ID, support_text)

        except Exception as e:
            logger.error(f"Failed to send dialog message to support group: {e}")

    async def _send_to_support_group_v2(self, ticket_id: int, message: Message,
                                        email: str, message_text: str, photo_file_id: str = None,
                                        document_file_id: str = None, video_file_id: str = None) -> tuple:
        """Обновленная отправка обращения в группу поддержки с улучшенным форматированием"""
        if not config.SUPPORT_GROUP_ID:
            return None, None

        try:
            user = message.from_user
            media_info = ""
            if photo_file_id:
                media_info = "📷 + Фотография"
            elif document_file_id:
                media_info = "📄 + Документ"
            elif video_file_id:
                media_info = "🎥 + Видео"

            support_text = f"""
🆘 НОВОЕ ОБРАЩЕНИЕ #{ticket_id}

👤 Пользователь: {user.first_name} {user.last_name or ''}
📧 Email: {email}
🆔 User ID: {user.id}
👤 Username: @{user.username or 'не указан'}

💬 Сообщение:
{message_text}

{media_info}

⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 ИНСТРУКЦИЯ ДЛЯ СОТРУДНИКОВ:
• Отвечайте в этом треде - ответы автоматически дойдут до пользователя
• Пользователь увидит ответ от "Сотрудника Поддержки" (анонимно)
• Диалог будет активным до закрытия тикета пользователем
• Все сообщения сохраняются в истории для анализа

⚠️ ПРАВА НА ОТВЕТ: только администраторы и сотрудники поддержки
            """

            # Отправка сообщения в группу
            sent_message = None
            if photo_file_id:
                sent_message = await self.bot.send_photo(
                    config.SUPPORT_GROUP_ID,
                    photo_file_id,
                    caption=support_text
                )
            elif document_file_id:
                sent_message = await self.bot.send_document(
                    config.SUPPORT_GROUP_ID,
                    document_file_id,
                    caption=support_text
                )
            elif video_file_id:
                sent_message = await self.bot.send_video(
                    config.SUPPORT_GROUP_ID,
                    video_file_id,
                    caption=support_text
                )
            else:
                sent_message = await self.bot.send_message(
                    config.SUPPORT_GROUP_ID,
                    support_text
                )

            # Если группа поддерживает топики, создаем тред
            thread_id = None
            if config.SUPPORT_GROUP_TOPICS:
                try:
                    # Создание треда (форум-топика)
                    forum_topic = await self.bot.create_forum_topic(
                        chat_id=config.SUPPORT_GROUP_ID,
                        name=f"Тикет #{ticket_id} - {user.first_name}",
                        icon_color=0xFF5722  # Оранжевый цвет для новых тикетов
                    )
                    thread_id = forum_topic.message_thread_id

                    # Отправляем детальную информацию в тред
                    detailed_info = f"""
📋 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О ТИКЕТЕ #{ticket_id}

👤 ПОЛЬЗОВАТЕЛЬ:
• Имя: {user.first_name} {user.last_name or ''}
• Username: @{user.username or 'не указан'}
• ID: {user.id}
• Email: {email}

💬 ПЕРВОЕ СООБЩЕНИЕ:
{message_text}

⏰ Создано: {datetime.now().strftime('%d.%m.%Y %H:%M')}

📊 СТАТУС: Новый тикет, ожидает ответа
🎯 ПРИОРИТЕТ: Обычный (ответить в течение 2 часов)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 НАЧИНАЙТЕ ДИАЛОГ - отвечайте в этом треде
                    """

                    thread_message = None
                    if photo_file_id:
                        thread_message = await self.bot.send_photo(
                            config.SUPPORT_GROUP_ID,
                            photo_file_id,
                            caption=detailed_info,
                            message_thread_id=thread_id
                        )
                    elif document_file_id:
                        thread_message = await self.bot.send_document(
                            config.SUPPORT_GROUP_ID,
                            document_file_id,
                            caption=detailed_info,
                            message_thread_id=thread_id
                        )
                    elif video_file_id:
                        thread_message = await self.bot.send_video(
                            config.SUPPORT_GROUP_ID,
                            video_file_id,
                            caption=detailed_info,
                            message_thread_id=thread_id
                        )
                    else:
                        thread_message = await self.bot.send_message(
                            config.SUPPORT_GROUP_ID,
                            detailed_info,
                            message_thread_id=thread_id
                        )

                    return thread_id, thread_message.message_id

                except Exception as e:
                    logger.error(f"Failed to create forum topic: {e}")
                    # Если не удалось создать тред, возвращаем обычное сообщение
                    return None, sent_message.message_id

            return None, sent_message.message_id

        except Exception as e:
            logger.error(f"Failed to send to support group: {e}")
            return None, None

    async def handle_support_response(self, message: Message):
        """Улучшенная обработка ответов сотрудников поддержки и администраторов в группе"""
        # Проверяем, что это ответ в треде или есть reply
        if not message.message_thread_id and not message.reply_to_message:
            return

        # Проверяем права пользователя
        user_id = message.from_user.id
        is_admin = user_id in config.ADMIN_IDS
        is_support_staff = user_id in config.SUPPORT_STAFF_IDS

        if not (is_admin or is_support_staff):
            # Если пользователь не имеет прав - игнорируем сообщение
            return

        try:
            ticket = None

            # Ищем тикет по thread_id или по reply
            if message.message_thread_id:
                ticket = await self.db.get_ticket_by_thread(message.message_thread_id)
            elif message.reply_to_message:
                # Ищем тикет по содержимому replied сообщения
                replied_text = message.reply_to_message.text or message.reply_to_message.caption or ""
                if "ОБРАЩЕНИЕ #" in replied_text or "ДИАЛОГЕ #" in replied_text:
                    ticket_match = re.search(r'#(\d+)', replied_text)
                    if ticket_match:
                        ticket_id = int(ticket_match.group(1))
                        ticket = await self.db.get_ticket_with_last_messages(ticket_id, 1)

            if not ticket:
                logger.warning(f"Ticket not found for message from user {user_id}")
                await message.reply("❌ Не удалось найти тикет для ответа")
                return

            # Проверяем, что тикет не закрыт
            if ticket.get('is_closed'):
                await message.reply(f"⚠️ Тикет #{ticket['id']} уже закрыт")
                return

            # Определяем роль отвечающего для отображения пользователю
            if is_admin:
                sender_role = "Администратор Поддержки"
                role_emoji = "👨‍💼"
            else:
                sender_role = "Сотрудник Поддержки"
                role_emoji = "🧑‍💼"

            # Получаем содержимое ответа
            response_text = message.text or message.caption or ""
            photo_file_id = message.photo[-1].file_id if message.photo else None
            document_file_id = message.document.file_id if message.document else None
            video_file_id = message.video.file_id if message.video else None

            # Сохраняем ответ в БД
            await self.db.add_ticket_message(
                ticket_id=ticket['id'],
                user_id=user_id,
                message_text=response_text,
                photo_file_id=photo_file_id,
                document_file_id=document_file_id,
                video_file_id=video_file_id,
                is_staff=True,
                is_admin=is_admin,
                thread_message_id=message.message_id
            )

            # Формируем ответ для пользователя (без реального имени сотрудника)
            response_for_user = f"""
🆘 Ответ по обращению #{ticket['id']}

{role_emoji} От: {sender_role}
⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}

💬 Ответ:
{response_text}

───────────────────────
💬 Вы можете продолжить диалог - просто напишите сообщение в боте
✅ Для закрытия обращения используйте: /start → 🆘 Поддержка → Закрыть обращение

💡 Оцените нашу работу: /start → 💭 Обратная связь
            """

            # Отправляем ответ пользователю в бот
            try:
                if photo_file_id:
                    await self.bot.send_photo(
                        ticket['user_id'],
                        photo_file_id,
                        caption=response_for_user
                    )
                elif document_file_id:
                    await self.bot.send_document(
                        ticket['user_id'],
                        document_file_id,
                        caption=response_for_user
                    )
                elif video_file_id:
                    await self.bot.send_video(
                        ticket['user_id'],
                        video_file_id,
                        caption=response_for_user
                    )
                else:
                    await self.bot.send_message(
                        ticket['user_id'],
                        response_for_user
                    )

                # Подтверждение в треде с дополнительной информацией
                real_name = message.from_user.first_name or "Пользователь"
                confirm_text = f"""
✅ Ответ отправлен пользователю

👤 Пользователь: {ticket['first_name']} (ID: {ticket['user_id']})
📝 От: {real_name} ({sender_role})
📱 Пользователь увидит ответ от "{sender_role}"

💬 Диалог остается активным - пользователь может продолжить переписку
📊 Ответ засчитан в статистику поддержки

🔧 Доступные команды:
• Отвечайте в этом треде для продолжения диалога
• Пользователь может закрыть тикет самостоятельно
                """

                await message.reply(confirm_text)

                # Логируем ответ с указанием роли
                await self._log_user_action(
                    user_id,
                    "support_response_sent",
                    {
                        "ticket_id": ticket['id'],
                        "user_id": ticket['user_id'],
                        "is_admin": is_admin,
                        "role": sender_role,
                        "has_media": bool(photo_file_id or document_file_id or video_file_id)
                    }
                )

            except Exception as e:
                logger.error(f"Failed to send response to user {ticket['user_id']}: {e}")

                # Детальная ошибка в треде
                error_message = f"""
❌ Не удалось отправить ответ пользователю

👤 Пользователь: {ticket['first_name']} {ticket['last_name'] or ''}
🆔 User ID: {ticket['user_id']}
📧 Email: {ticket['email']}
❌ Ошибка: {str(e)}

💡 Возможные причины:
• Пользователь заблокировал бота
• Пользователь удалил аккаунт  
• Технические проблемы

📧 Рекомендуется связаться по email: {ticket['email']}

🔧 Тикет остается активным - можно попробовать связаться позже
                """

                await message.reply(error_message)

        except Exception as e:
            logger.error(f"Error handling support response: {e}")
            await message.reply(
                f"❌ Ошибка при обработке ответа\n"
                f"📝 Детали: {str(e)}\n"
                f"🔧 Обратитесь к администратору"
            )

    async def _notify_support_ticket_closed(self, ticket_id: int, user):
        """Уведомление в группу поддержки о закрытии тикета"""
        if not config.SUPPORT_GROUP_ID:
            return

        try:
            notification_text = f"""
✅ ТИКЕТ #{ticket_id} ЗАКРЫТ

👤 Пользователь: {user.first_name} {user.last_name or ''}
🆔 User ID: {user.id}
⏰ Время закрытия: {datetime.now().strftime('%d.%m.%Y %H:%M')}

📊 Тикет закрыт пользователем
            """

            # Получаем тикет для thread_id
            ticket = await self.db.get_ticket_by_thread(ticket_id)
            thread_id = ticket.get('thread_id') if ticket else None

            if thread_id and config.SUPPORT_GROUP_TOPICS:
                await self.bot.send_message(
                    config.SUPPORT_GROUP_ID,
                    notification_text,
                    message_thread_id=thread_id
                )
            else:
                await self.bot.send_message(config.SUPPORT_GROUP_ID, notification_text)

        except Exception as e:
            logger.error(f"Failed to notify support about ticket closure: {e}")

    # ================== ОБРАТНАЯ СВЯЗЬ (ОБНОВЛЕНО) ==================

    async def start_feedback(self, query: CallbackQuery, state: FSMContext):
        """Начало процесса оставления отзыва"""
        await self._log_user_action(query.from_user.id, "feedback_start")

        text = """
💭 Обратная связь

Ваше мнение очень важно для нас!

Выберите категорию для оценки:
        """

        await query.message.edit_text(text, reply_markup=Keyboards.feedback_categories())
        await state.set_state(FeedbackStates.waiting_for_category)
        await query.answer()

    async def select_feedback_category(self, query: CallbackQuery, state: FSMContext):
        """Выбор категории для оценки"""
        category = query.data.replace("feedback_", "")

        categories = {
            "festival": "Фестиваль в целом",
            "food": "Фудкорты",
            "workshops": "Мастер-классы",
            "lectures": "Лекторий",
            "infrastructure": "Инфраструктура"
        }

        category_name = categories.get(category, "Неизвестная категория")

        await state.update_data(category=category, category_name=category_name)

        text = f"""
💭 Оценка: {category_name}

Поставьте оценку от 1 до 5 звезд:
        """

        await query.message.edit_text(text, reply_markup=Keyboards.rating_keyboard())
        await state.set_state(FeedbackStates.waiting_for_rating)
        await query.answer()

    async def select_rating(self, query: CallbackQuery, state: FSMContext):
        """Выбор оценки"""
        rating = int(query.data.replace("rating_", ""))

        data = await state.get_data()
        category_name = data.get("category_name", "Неизвестная категория")

        await state.update_data(rating=rating)

        stars = "⭐" * rating

        # Разные сообщения в зависимости от оценки
        if rating <= 2:
            text = f"""
💭 Оценка: {category_name}
🌟 Ваша оценка: {stars} ({rating}/5)

😔 Нам очень жаль, что у вас остались негативные впечатления.

Пожалуйста, расскажите подробнее, что пошло не так?
Ваш комментарий поможет нам исправить ситуацию:
            """
        elif rating == 3:
            text = f"""
💭 Оценка: {category_name}
🌟 Ваша оценка: {stars} ({rating}/5)

Спасибо за честную оценку! 

Расскажите, что можно улучшить:
            """
        else:  # rating >= 4
            text = f"""
💭 Оценка: {category_name}
🌟 Ваша оценка: {stars} ({rating}/5)

🎉 Спасибо за высокую оценку!

Поделитесь, что вам особенно понравилось (необязательно):
            """

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Пропустить комментарий",
                                  callback_data="skip_comment")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])

        await query.message.edit_text(text, reply_markup=keyboard)
        await state.set_state(FeedbackStates.waiting_for_comment)
        await query.answer()

    async def process_feedback_comment(self, message: Message, state: FSMContext):
        """Обработка комментария к отзыву"""
        await self._save_feedback(message, state, message.text)

    async def skip_feedback_comment(self, query: CallbackQuery, state: FSMContext):
        """Пропуск комментария к отзыву"""
        await self._save_feedback(query, state, None)

    async def _save_feedback(self, message_or_query, state: FSMContext, comment: str = None):
        """Сохранение отзыва с системой уведомлений о критических оценках"""
        try:
            data = await state.get_data()
            category = data.get("category")
            category_name = data.get("category_name")
            rating = data.get("rating")
            user_id = message_or_query.from_user.id
            user = message_or_query.from_user

            # Сохранение в БД
            await self.db.add_feedback(user_id, category, rating, comment)

            await self._log_user_action(user_id, "feedback_submitted", {
                "category": category,
                "rating": rating,
                "has_comment": bool(comment),
                "is_critical": rating <= 2
            })

            # 🚨 КРИТИЧЕСКИЕ ОТЗЫВЫ (рейтинг 1-2)
            if rating <= 2:
                await self._handle_critical_feedback(user, category, category_name, rating, comment)

            # Отправка в канал отзывов (обычная логика)
            if config.FEEDBACK_CHANNEL_ID:
                await self._send_feedback_to_channel(user, category_name, rating, comment)

            # Формирование ответа пользователю
            success_text = await self._generate_feedback_response(category_name, rating, comment)

            if hasattr(message_or_query, 'answer'):
                await message_or_query.answer(success_text, reply_markup=Keyboards.back_to_main())
            else:
                await message_or_query.message.edit_text(success_text,
                                                         reply_markup=Keyboards.back_to_main())

            await state.clear()

        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
            error_text = "❌ Произошла ошибка при сохранении отзыва. Попробуйте позже."

            if hasattr(message_or_query, 'answer'):
                await message_or_query.answer(error_text, reply_markup=Keyboards.back_to_main())
            else:
                await message_or_query.message.edit_text(error_text,
                                                         reply_markup=Keyboards.back_to_main())
            await state.clear()

    async def _handle_critical_feedback(self, user, category: str, category_name: str,
                                        rating: int, comment: str = None):
        """Обработка критических отзывов (рейтинг 1-2)"""
        try:
            # Определяем уровень критичности
            if rating == 1:
                severity = "🔴 КРИТИЧЕСКИЙ"
                priority = "ВЫСОКИЙ"
                emoji = "🚨"
            else:  # rating == 2
                severity = "🟡 НИЗКИЙ"
                priority = "СРЕДНИЙ"
                emoji = "⚠️"

            # Формируем уведомление для администраторов
            critical_message = f"""
{emoji} {severity} ОТЗЫВ

📊 Категория: {category_name}
🌟 Оценка: {"⭐" * rating} ({rating}/5)
⚡ Приоритет: {priority}

👤 От пользователя:
• Имя: {user.first_name} {user.last_name or ''}
• Username: @{user.username or 'не указан'}
• ID: {user.id}

💬 Комментарий:
{comment or "Без комментария"}

⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 РЕКОМЕНДУЕМЫЕ ДЕЙСТВИЯ:
"""

            # Добавляем рекомендации в зависимости от категории
            recommendations = self._get_category_recommendations(category, rating)
            critical_message += "\n".join([f"• {rec}" for rec in recommendations])

            critical_message += f"""

📞 КОНТАКТ С ПОЛЬЗОВАТЕЛЕМ:
• Telegram: @{user.username or 'нет username'}
• ID для связи: {user.id}
• Создать тикет поддержки для пользователя?

💡 Этот отзыв требует оперативного внимания!
            """

            # Отправляем уведомления всем администраторам
            for admin_id in config.ADMIN_IDS:
                try:
                    await self.bot.send_message(admin_id, critical_message)
                    logger.info(f"Critical feedback notification sent to admin {admin_id}")
                except Exception as e:
                    logger.error(f"Failed to send critical feedback notification to admin {admin_id}: {e}")

            # Если есть группа поддержки, отправляем и туда
            if config.SUPPORT_GROUP_ID:
                try:
                    group_message = f"""
{emoji} КРИТИЧЕСКИЙ ОТЗЫВ ТРЕБУЕТ ВНИМАНИЯ

📊 {category_name}: {"⭐" * rating} ({rating}/5)
👤 {user.first_name} (@{user.username or 'нет username'})

💬 "{comment or 'Без комментария'}"

🎯 Кто-то может связаться с пользователем для решения проблемы?
                    """

                    await self.bot.send_message(config.SUPPORT_GROUP_ID, group_message)
                    logger.info("Critical feedback notification sent to support group")
                except Exception as e:
                    logger.error(f"Failed to send critical feedback notification to support group: {e}")

            # Логируем критический отзыв
            stats_logger = logging.getLogger('stats')
            stats_logger.warning(f"Critical feedback: user_id={user.id}, category={category}, rating={rating}, comment_length={len(comment or '')}")

        except Exception as e:
            logger.error(f"Failed to handle critical feedback: {e}")

    def _get_category_recommendations(self, category: str, rating: int) -> List[str]:
        """Получение рекомендаций по категориям для критических отзывов"""
        base_recommendations = [
            "Связаться с пользователем для уточнения проблемы",
            "Проанализировать ситуацию и принять меры"
        ]

        category_specific = {
            "festival": [
                "Проверить общую организацию мероприятия",
                "Рассмотреть жалобы на безопасность или комфорт",
                "Проанализировать работу всех служб"
            ],
            "food": [
                "Проверить качество еды и обслуживания в фудкорте",
                "Связаться с поставщиками питания",
                "Проверить санитарные условия",
                "Рассмотреть ценовую политику"
            ],
            "workshops": [
                "Связаться с ведущими мастер-классов",
                "Проверить качество материалов и оборудования",
                "Рассмотреть организацию пространства",
                "Проанализировать программу мастер-классов"
            ],
            "lectures": [
                "Связаться с лекторами",
                "Проверить качество звука и видимость",
                "Рассмотреть содержание программы",
                "Проанализировать организацию лектория"
            ],
            "infrastructure": [
                "Проверить состояние туалетов и медпунктов",
                "Рассмотреть навигацию и указатели",
                "Проанализировать безопасность территории",
                "Проверить доступность для людей с ограниченными возможностями"
            ]
        }

        recommendations = base_recommendations.copy()
        if category in category_specific:
            recommendations.extend(category_specific[category])

        # Для особо критических отзывов (рейтинг 1)
        if rating == 1:
            recommendations.extend([
                "🚨 СРОЧНО: Принять немедленные меры",
                "Рассмотреть возможность компенсации",
                "Публично ответить на критику (если это оправдано)"
            ])

        return recommendations

    async def _send_feedback_to_channel(self, user, category_name: str, rating: int, comment: str = None):
        """Отправка обычного отзыва в канал"""
        try:
            stars = "⭐" * rating

            # Добавляем индикатор для низких оценок
            rating_indicator = ""
            if rating <= 2:
                rating_indicator = " 🚨"
            elif rating == 3:
                rating_indicator = " ⚠️"
            elif rating >= 4:
                rating_indicator = " ✨"

            feedback_text = f"""
💭 НОВЫЙ ОТЗЫВ{rating_indicator}

📊 Категория: {category_name}
🌟 Оценка: {stars} ({rating}/5)
👤 От: {user.first_name}

💬 Комментарий:
{comment or 'Без комментария'}

⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}
            """

            await self.bot.send_message(config.FEEDBACK_CHANNEL_ID, feedback_text)
            logger.info(f"Feedback sent to channel: rating={rating}, category={category_name}")

        except Exception as e:
            logger.error(f"Failed to send feedback to channel: {e}")

    def _generate_feedback_response(self, category_name: str, rating: int, comment: str = None) -> str:
        """Генерация ответа пользователю в зависимости от оценки"""
        stars = "⭐" * rating

        if rating <= 2:
            response = f"""
😔 Спасибо за честный отзыв

📊 Категория: {category_name}
🌟 Оценка: {stars} ({rating}/5)
💬 Комментарий: {"Добавлен" if comment else "Не добавлен"}

Мы очень сожалеем о негативном опыте и обязательно разберемся с ситуацией.

🔧 Наши администраторы уже уведомлены о проблеме.
📞 Если нужна срочная помощь, обратитесь в поддержку: /start → 🆘 Поддержка

💙 Мы ценим ваше мнение и работаем над улучшениями!
            """
        elif rating == 3:
            response = f"""
🤔 Спасибо за честную оценку

📊 Категория: {category_name}
🌟 Оценка: {stars} ({rating}/5)
💬 Комментарий: {"Добавлен" if comment else "Не добавлен"}

Ваше мнение поможет нам стать лучше!

💡 Если есть конкретные предложения по улучшению, напишите в поддержку.
            """
        else:  # rating >= 4
            response = f"""
🎉 Спасибо за отличный отзыв!

📊 Категория: {category_name}
🌟 Оценка: {stars} ({rating}/5)
💬 Комментарий: {"Добавлен" if comment else "Не добавлен"}

Мы рады, что вам понравилось! 

🌟 Поделитесь впечатлениями с друзьями в наших соцсетях!
            """

        return response
    # ================== СОЦИАЛЬНЫЕ СЕТИ ==================

    async def show_social_networks(self, query: CallbackQuery):
        """Показ социальных сетей"""
        await self._log_user_action(query.from_user.id, "social_networks")

        text = """
📱 Социальные сети фестиваля

Подписывайтесь на наши аккаунты:
• Новости и анонсы
• Фото и видео с фестиваля
• Интервью с артистами
• Розыгрыши билетов

Выберите социальную сеть:
        """

        await query.message.edit_text(text, reply_markup=Keyboards.social_networks())
        await query.answer()

    # ================== АДМИН ФУНКЦИИ ==================

    async def handle_admin_actions(self, query: CallbackQuery):
        """Обработка админских действий"""
        if query.from_user.id not in config.ADMIN_IDS:
            await query.answer("❌ Недостаточно прав", show_alert=True)
            return

        action = query.data.replace("admin_", "")

        if action == "stats":
            await self._show_admin_stats(query)
        elif action == "tickets":
            await self._show_admin_tickets(query)
        elif action == "feedback":
            await self._show_admin_feedback(query)
        elif action == "schedule":
            await self._show_admin_schedule(query)
        elif action == "support_dashboard":
            await self._show_admin_support_dashboard(query)
        elif action == "urgent_tickets":
            await self._show_admin_urgent_tickets(query)
        elif action == "detailed_stats":
            await self._show_admin_detailed_stats(query)
        elif action == "staff_activity":
            await self._show_admin_staff_activity(query)
        elif action == "daily_metrics":
            await self._show_admin_daily_metrics(query)
        elif action == "open_tickets":
            await self._show_admin_open_tickets(query)

    async def _show_admin_support_dashboard(self, query: CallbackQuery):
        """Показ панели управления поддержкой"""
        try:
            stats = await self.db.get_support_statistics()
            urgent_tickets = await self.db.get_tickets_requiring_attention()

            text = f"""
🎛 ПАНЕЛЬ УПРАВЛЕНИЯ ПОДДЕРЖКОЙ

📊 ОСНОВНЫЕ МЕТРИКИ:
━━━━━━━━━━━━━━━━━━━━━━━
📋 Всего тикетов: {stats['tickets']['total']}
🔄 Открытых: {stats['tickets']['open']}
✅ Закрытых: {stats['tickets']['closed']}

📅 ЗА СЕГОДНЯ:
• Новых тикетов: {stats['tickets']['today']}
• Сообщений: {stats['messages']['today']}

📈 ЗА НЕДЕЛЮ:
• Тикетов: {stats['tickets']['this_week']}
• Сообщений от пользователей: {stats['messages']['from_users']}
• Ответов сотрудников: {stats['messages']['from_staff']}

⏱ ВРЕМЯ ОТВЕТА:
• Среднее: {stats['response_time']['average_minutes']:.1f} мин
• В часах: {stats['response_time']['average_hours']:.1f} ч

🚨 ТРЕБУЮТ ВНИМАНИЯ: {len(urgent_tickets)} тикетов
            """

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚨 Срочные тикеты",
                                      callback_data="admin_urgent_tickets")],
                [InlineKeyboardButton(text="📊 Подробная статистика",
                                      callback_data="admin_detailed_stats")],
                [InlineKeyboardButton(text="👥 Активность сотрудников",
                                      callback_data="admin_staff_activity")],
                [InlineKeyboardButton(text="📈 Метрики по дням",
                                      callback_data="admin_daily_metrics")],
                [InlineKeyboardButton(text="📋 Все открытые тикеты",
                                      callback_data="admin_open_tickets")],
                [InlineKeyboardButton(text="🔄 Обновить",
                                      callback_data="admin_support_dashboard")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")]
            ])

            await query.message.edit_text(text, reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error showing admin support dashboard: {e}")
            await query.answer("Ошибка при загрузке панели", show_alert=True)

    async def _show_admin_urgent_tickets(self, query: CallbackQuery):
        """Показ срочных тикетов, требующих внимания"""
        try:
            urgent_tickets = await self.db.get_tickets_requiring_attention()

            if not urgent_tickets:
                text = "✅ Нет тикетов, требующих срочного внимания!"
            else:
                text = f"🚨 СРОЧНЫЕ ТИКЕТЫ ({len(urgent_tickets)})\n\n"

                for ticket in urgent_tickets[:10]:  # Показываем первые 10
                    hours = int(ticket['hours_since_last_message'])
                    text += f"🔥 #{ticket['id']} - {ticket['first_name']}\n"
                    text += f"⏰ Без ответа: {hours} ч\n"
                    text += f"📧 {ticket['email']}\n"
                    text += f"💬 {ticket['message'][:60]}...\n\n"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить",
                                      callback_data="admin_urgent_tickets")],
                [InlineKeyboardButton(text="📋 Все открытые тикеты",
                                      callback_data="admin_open_tickets")],
                [InlineKeyboardButton(text="◀️ Назад",
                                      callback_data="admin_support_dashboard")]
            ])

            await query.message.edit_text(text, reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error showing urgent tickets: {e}")
            await query.answer("Ошибка при загрузке срочных тикетов", show_alert=True)

    async def _show_admin_detailed_stats(self, query: CallbackQuery):
        """Показ подробной статистики"""
        try:
            stats = await self.db.get_support_statistics()

            text = f"""
📊 ПОДРОБНАЯ СТАТИСТИКА ПОДДЕРЖКИ

📋 ТИКЕТЫ:
━━━━━━━━━━━━━━━━━━━━━━━
• Всего: {stats['tickets']['total']}
• Открытых: {stats['tickets']['open']}
• Закрытых: {stats['tickets']['closed']}
• Сегодня: {stats['tickets']['today']}
• За неделю: {stats['tickets']['this_week']}
• За месяц: {stats['tickets']['this_month']}

💬 СООБЩЕНИЯ:
━━━━━━━━━━━━━━━━━━━━━━━
• Всего: {stats['messages']['total']}
• От пользователей: {stats['messages']['from_users']}
• От сотрудников: {stats['messages']['from_staff']}
• Сегодня: {stats['messages']['today']}
• За неделю: {stats['messages']['this_week']}
• За месяц: {stats['messages']['this_month']}

⏱ ВРЕМЯ ОТВЕТА:
━━━━━━━━━━━━━━━━━━━━━━━
• Среднее: {stats['response_time']['average_minutes']:.1f} мин
• В часах: {stats['response_time']['average_hours']:.1f} ч

👑 ТОП-5 АКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ:
            """

            for i, user in enumerate(stats['top_users'][:5], 1):
                username = f"@{user['username']}" if user['username'] else "без username"
                text += f"{i}. {user['first_name']} ({username}): {user['message_count']} сообщений\n"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👥 Активность сотрудников",
                                      callback_data="admin_staff_activity")],
                [InlineKeyboardButton(text="📈 По дням",
                                      callback_data="admin_daily_metrics")],
                [InlineKeyboardButton(text="🔄 Обновить",
                                      callback_data="admin_detailed_stats")],
                [InlineKeyboardButton(text="◀️ Назад",
                                      callback_data="admin_support_dashboard")]
            ])

            await query.message.edit_text(text, reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error showing detailed stats: {e}")
            await query.answer("Ошибка при загрузке статистики", show_alert=True)

    async def _show_admin_staff_activity(self, query: CallbackQuery):
        """Показ активности сотрудников"""
        try:
            stats = await self.db.get_support_statistics()

            text = "👥 АКТИВНОСТЬ СОТРУДНИКОВ (за неделю)\n\n"

            if not stats['staff_activity']:
                text += "📭 Нет активности сотрудников за последнюю неделю"
            else:
                for i, staff in enumerate(stats['staff_activity'], 1):
                    role = "👨‍💼 Администратор" if staff['is_admin'] else "🧑‍💼 Сотрудник"
                    text += f"{i}. {role} (ID: {staff['user_id']})\n"
                    text += f"   💬 Ответов: {staff['message_count']}\n\n"

            text += f"\n📊 Общая статистика ответов:\n"
            text += f"• Всего ответов: {stats['messages']['from_staff']}\n"
            text += f"• Среднее время ответа: {stats['response_time']['average_minutes']:.1f} мин\n"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 Общая статистика",
                                      callback_data="admin_detailed_stats")],
                [InlineKeyboardButton(text="🔄 Обновить",
                                      callback_data="admin_staff_activity")],
                [InlineKeyboardButton(text="◀️ Назад",
                                      callback_data="admin_support_dashboard")]
            ])

            await query.message.edit_text(text, reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error showing staff activity: {e}")
            await query.answer("Ошибка при загрузке активности", show_alert=True)

    async def _show_admin_daily_metrics(self, query: CallbackQuery):
        """Показ метрик по дням"""
        try:
            stats = await self.db.get_support_statistics()

            text = "📈 МЕТРИКИ ПО ДНЯМ (последняя неделя)\n\n"

            if not stats['daily_metrics']:
                text += "📭 Нет данных за последнюю неделю"
            else:
                for day in stats['daily_metrics']:
                    date_str = day['date'].strftime('%d.%m')
                    text += f"📅 {date_str}:\n"
                    text += f"   🆕 Создано: {day['tickets_created']}\n"
                    text += f"   ✅ Закрыто: {day['tickets_closed']}\n\n"

            # Добавляем сводку
            total_created = sum(day['tickets_created'] for day in stats['daily_metrics'])
            total_closed = sum(day['tickets_closed'] for day in stats['daily_metrics'])

            text += f"📋 Итого за неделю:\n"
            text += f"• Создано: {total_created}\n"
            text += f"• Закрыто: {total_closed}\n"
            text += f"• Среднее в день: {total_created/7:.1f}\n"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 Общая статистика",
                                      callback_data="admin_detailed_stats")],
                [InlineKeyboardButton(text="🔄 Обновить",
                                      callback_data="admin_daily_metrics")],
                [InlineKeyboardButton(text="◀️ Назад",
                                      callback_data="admin_support_dashboard")]
            ])

            await query.message.edit_text(text, reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error showing daily metrics: {e}")
            await query.answer("Ошибка при загрузке метрик", show_alert=True)

    async def _show_admin_open_tickets(self, query: CallbackQuery):
        """Показ всех открытых тикетов"""
        try:
            tickets = await self.db.search_tickets(status="open", limit=20)

            if not tickets:
                text = "✅ Нет открытых тикетов!"
            else:
                text = f"📋 ОТКРЫТЫЕ ТИКЕТЫ ({len(tickets)})\n\n"

                for ticket in tickets[:15]:  # Показываем первые 15
                    created_date = ticket['created_at'].strftime('%d.%m %H:%M')
                    text += f"🎫 #{ticket['id']} - {ticket['first_name']}\n"
                    text += f"📧 {ticket['email']}\n"
                    text += f"📅 {created_date}\n"
                    text += f"💬 {ticket['message'][:50]}...\n\n"

                if len(tickets) > 15:
                    text += f"... и еще {len(tickets) - 15} тикетов"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚨 Срочные тикеты",
                                      callback_data="admin_urgent_tickets")],
                [InlineKeyboardButton(text="🔄 Обновить",
                                      callback_data="admin_open_tickets")],
                [InlineKeyboardButton(text="◀️ Назад",
                                      callback_data="admin_support_dashboard")]
            ])

            await query.message.edit_text(text, reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error showing open tickets: {e}")
            await query.answer("Ошибка при загрузке тикетов", show_alert=True)

    # Старые админ методы (для совместимости)
    async def _show_admin_stats(self, query: CallbackQuery):
        """Показ статистики для администратора"""
        try:
            stats = await self.db.get_usage_stats()
            feedback_stats = await self.db.get_feedback_stats()

            text = f"""
📊 СТАТИСТИКА БОТА

👥 Пользователи: {stats['total_users']}
🔄 Всего действий: {stats['total_actions']}
💭 Отзывов: {feedback_stats['total']['total_feedback']}
⭐ Средняя оценка: {feedback_stats['total']['average_rating']:.1f}/5

🔥 Популярные действия:
            """

            for action in stats['popular_actions'][:5]:
                text += f"• {action['action']}: {action['count']}\n"

            text += f"\n📈 Отзывы по категориям:\n"

            for category in feedback_stats['by_category'][:5]:
                text += f"• {category['category']}: {category['avg_rating']:.1f}/5 ({category['count']} отзывов)\n"

            await query.message.edit_text(text, reply_markup=Keyboards.admin_menu())

        except Exception as e:
            logger.error(f"Error showing admin stats: {e}")
            await query.answer("Ошибка при загрузке статистики", show_alert=True)

    async def _show_admin_tickets(self, query: CallbackQuery):
        """Показ тикетов поддержки для администратора"""
        try:
            tickets = await self.db.get_support_tickets("open")

            if not tickets:
                text = "📋 Нет открытых обращений"
            else:
                text = f"🎫 ОТКРЫТЫЕ ОБРАЩЕНИЯ ({len(tickets)})\n\n"

                for ticket in tickets[:10]:  # Показываем только первые 10
                    text += f"#{ticket['id']} - {ticket['first_name']}\n"
                    text += f"📧 {ticket['email']}\n"
                    text += f"💬 {ticket['message'][:50]}...\n"
                    text += f"⏰ {ticket['created_at'].strftime('%d.%m %H:%M')}\n\n"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_tickets")],
                [InlineKeyboardButton(text="🎛 Панель поддержки", callback_data="admin_support_dashboard")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")]
            ])

            await query.message.edit_text(text, reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error showing admin tickets: {e}")
            await query.answer("Ошибка при загрузке тикетов", show_alert=True)

    async def _show_admin_feedback(self, query: CallbackQuery):
        """Показ отзывов для администратора"""
        try:
            feedback_stats = await self.db.get_feedback_stats()

            text = f"""
💭 СТАТИСТИКА ОТЗЫВОВ

📊 Общая статистика:
• Всего отзывов: {feedback_stats['total']['total_feedback']}
• Средняя оценка: {feedback_stats['total']['average_rating']:.1f}/5
• Уникальных пользователей: {feedback_stats['total']['unique_users']}

📈 По категориям:
            """

            for category in feedback_stats['by_category']:
                text += f"• {category['category']}: {category['avg_rating']:.1f}/5 ({category['count']})\n"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_feedback")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")]
            ])

            await query.message.edit_text(text, reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error showing admin feedback: {e}")
            await query.answer("Ошибка при загрузке отзывов", show_alert=True)

    async def _show_admin_schedule(self, query: CallbackQuery):
        """Показ управления расписанием для администратора"""
        text = """
📅 УПРАВЛЕНИЕ РАСПИСАНИЕМ

Функции:
• Просмотр текущего расписания
• Добавление новых выступлений
• Редактирование существующих
• Удаление записей

Выберите действие:
        """

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👀 Просмотр расписания", callback_data="admin_view_schedule")],
            [InlineKeyboardButton(text="➕ Добавить выступление", callback_data="admin_add_schedule")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")]
        ])

        await query.message.edit_text(text, reply_markup=keyboard)

    # Обработка неизвестных сообщений
    async def handle_unknown_message(self, message: Message):
        """Обработка неизвестных сообщений"""
        await self._update_user_info(message)
        await self._log_user_action(message.from_user.id, "unknown_message", {"text": message.text})

        # Проверяем наличие активного тикета для индикатора
        active_ticket = await self.db.get_user_active_ticket(message.from_user.id)
        has_active_ticket = active_ticket is not None

        text = """
❓ Не понимаю эту команду.

Используйте меню ниже или команды:
• /start - начать работу с ботом
• /menu - показать главное меню

Выберите нужный раздел:
        """

        if has_active_ticket:
            text += f"\n\n🔴 У вас есть активное обращение #{active_ticket['id']} в поддержку"

        await message.answer(text, reply_markup=Keyboards.main_menu_with_support_indicator(has_active_ticket))