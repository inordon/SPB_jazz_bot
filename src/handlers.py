"""
Обработчики сообщений для Telegram-бота музыкального фестиваля
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
        self.router.callback_query(F.data == "skip_comment")(self.skip_feedback_comment)
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

    # Поддержка
    async def start_support(self, query: CallbackQuery, state: FSMContext):
        """Начало процесса обращения в поддержку"""
        await self._log_user_action(query.from_user.id, "support_start")

        text = """
🆘 Служба поддержки

Мы поможем решить любые вопросы!

Для создания обращения нам нужно:
1. Ваш email для связи
2. Описание проблемы или вопроса
3. При необходимости - фотография

Введите ваш email:
        """

        await query.message.edit_text(text, reply_markup=Keyboards.back_to_main())
        await state.set_state(SupportStates.waiting_for_email)
        await query.answer()

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
            "Вы также можете прикрепить фотографию:",
            reply_markup=Keyboards.back_to_main()
        )
        await state.set_state(SupportStates.waiting_for_message)

    async def process_support_message(self, message: Message, state: FSMContext):
        """Обработка сообщения для поддержки"""
        try:
            data = await state.get_data()
            email = data.get("email")

            message_text = message.text or message.caption or ""
            photo_file_id = None

            if message.photo:
                photo_file_id = message.photo[-1].file_id

            # Создание тикета в БД (сначала без thread_id)
            ticket_id = await self.db.create_support_ticket(
                user_id=message.from_user.id,
                email=email,
                message=message_text,
                photo_file_id=photo_file_id
            )

            await self._log_user_action(message.from_user.id, "support_ticket_created",
                                        {"ticket_id": ticket_id})

            # Отправка в группу поддержки с созданием треда
            thread_id, initial_message_id = await self._send_to_support_group(
                ticket_id, message, email, message_text, photo_file_id
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
                "Хотите добавить что-то еще к обращению?",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Добавить сообщение",
                                          callback_data=f"continue_ticket_{ticket_id}")],
                    [InlineKeyboardButton(text="✅ Завершить", callback_data="main_menu")]
                ])
            )

            await state.clear()

        except Exception as e:
            logger.error(f"Error processing support message: {e}")
            await message.answer(
                "❌ Произошла ошибка при создании обращения. Попробуйте позже.",
                reply_markup=Keyboards.back_to_main()
            )
            await state.clear()

    async def _send_to_support_group(self, ticket_id: int, message: Message,
                                     email: str, message_text: str, photo_file_id: str = None) -> tuple:
        """Отправка обращения в группу поддержки с созданием треда"""
        if not config.SUPPORT_GROUP_ID:
            return None, None

        try:
            user = message.from_user
            support_text = f"""
🆘 НОВОЕ ОБРАЩЕНИЕ #{ticket_id}

👤 Пользователь: {user.first_name} {user.last_name or ''}
📧 Email: {email}
🆔 User ID: {user.id}
👤 Username: @{user.username or 'не указан'}

💬 Сообщение:
{message_text}

⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}

📝 Отвечайте в этом треде - ответы автоматически дойдут до пользователя в боте!

⚠️ ВАЖНО: Пользователь увидит ответ от "Сотрудника Поддержки" (анонимно)
👥 Права на ответ имеют только администраторы и сотрудники поддержки
            """

            # Отправка сообщения в группу
            if photo_file_id:
                sent_message = await self.bot.send_photo(
                    config.SUPPORT_GROUP_ID,
                    photo_file_id,
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
                        icon_color=0xF44336  # Красный цвет для новых тикетов
                    )
                    thread_id = forum_topic.message_thread_id

                    # Пересылаем сообщение в созданный тред
                    if photo_file_id:
                        thread_message = await self.bot.send_photo(
                            config.SUPPORT_GROUP_ID,
                            photo_file_id,
                            caption=support_text,
                            message_thread_id=thread_id
                        )
                    else:
                        thread_message = await self.bot.send_message(
                            config.SUPPORT_GROUP_ID,
                            support_text,
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
        """Обработка ответов сотрудников поддержки и администраторов в группе"""
        # Проверяем, что это ответ в треде
        if not message.message_thread_id:
            return

        # Проверяем права пользователя
        user_id = message.from_user.id
        is_admin = user_id in config.ADMIN_IDS
        is_support_staff = user_id in config.SUPPORT_STAFF_IDS

        if not (is_admin or is_support_staff):
            # Если пользователь не имеет прав - игнорируем сообщение
            return

        try:
            # Находим тикет по thread_id
            ticket = await self.db.get_ticket_by_thread(message.message_thread_id)

            if not ticket:
                logger.warning(f"Ticket not found for thread_id: {message.message_thread_id}")
                return

            # Определяем роль отвечающего для отображения пользователю
            if is_admin:
                sender_role = "Администратор Поддержки"
                role_emoji = "👨‍💼"
            else:
                sender_role = "Сотрудник Поддержки"
                role_emoji = "🧑‍💼"

            # Сохраняем ответ в БД с указанием роли
            await self.db.add_support_response(
                ticket_id=ticket['id'],
                staff_user_id=user_id,
                response_text=message.text or message.caption or "",
                is_admin=is_admin
            )

            # Формируем ответ для пользователя (без реального имени сотрудника)
            response_text = f"""
🆘 Ответ по обращению #{ticket['id']}

{role_emoji} От: {sender_role}
⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}

💬 Ответ:
{message.text or message.caption or ""}

───────────────────────
❓ Если вопрос решен, можете создать новое обращение в случае других проблем через: /start → 🆘 Поддержка

💡 Оцените нашу работу в разделе: /start → 💭 Обратная связь
            """

            # Отправляем ответ пользователю в бот
            try:
                if message.photo:
                    await self.bot.send_photo(
                        ticket['user_id'],
                        message.photo[-1].file_id,
                        caption=response_text
                    )
                elif message.document:
                    await self.bot.send_document(
                        ticket['user_id'],
                        message.document.file_id,
                        caption=response_text
                    )
                elif message.video:
                    await self.bot.send_video(
                        ticket['user_id'],
                        message.video.file_id,
                        caption=response_text
                    )
                else:
                    await self.bot.send_message(
                        ticket['user_id'],
                        response_text
                    )

                # Подтверждение в треде (показываем роль отвечающего)
                real_name = message.from_user.first_name or "Пользователь"
                await message.reply(
                    f"✅ Ответ отправлен пользователю\n"
                    f"👤 Пользователь: {ticket['first_name']} (ID: {ticket['user_id']})\n"
                    f"📝 От: {real_name} ({sender_role})\n"
                    f"📱 Пользователь увидит ответ от \"{sender_role}\""
                )

                # Логируем ответ с указанием роли
                await self._log_user_action(
                    user_id,
                    "support_response_sent",
                    {
                        "ticket_id": ticket['id'],
                        "user_id": ticket['user_id'],
                        "is_admin": is_admin,
                        "role": sender_role
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
                """

                await message.reply(error_message)

        except Exception as e:
            logger.error(f"Error handling support response: {e}")
            await message.reply(
                f"❌ Ошибка при обработке ответа\n"
                f"📝 Детали: {str(e)}"
            )

    # Обратная связь
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
        text = f"""
💭 Оценка: {category_name}
🌟 Ваша оценка: {stars} ({rating}/5)

Теперь напишите комментарий (необязательно):
Что вам понравилось или что можно улучшить?
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
        """Сохранение отзыва"""
        try:
            data = await state.get_data()
            category = data.get("category")
            category_name = data.get("category_name")
            rating = data.get("rating")
            user_id = message_or_query.from_user.id

            # Сохранение в БД
            await self.db.add_feedback(user_id, category, rating, comment)

            await self._log_user_action(user_id, "feedback_submitted", {
                "category": category,
                "rating": rating,
                "has_comment": bool(comment)
            })

            # Отправка в канал отзывов
            if config.FEEDBACK_CHANNEL_ID:
                stars = "⭐" * rating
                feedback_text = f"""
💭 НОВЫЙ ОТЗЫВ

📊 Категория: {category_name}
🌟 Оценка: {stars} ({rating}/5)
👤 От: {message_or_query.from_user.first_name}

💬 Комментарий:
{comment or 'Без комментария'}

⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}
                """

                try:
                    await self.bot.send_message(config.FEEDBACK_CHANNEL_ID, feedback_text)
                except Exception as e:
                    logger.error(f"Failed to send feedback to channel: {e}")

            success_text = f"""
✅ Спасибо за отзыв!

📊 Категория: {category_name}
🌟 Оценка: {"⭐" * rating} ({rating}/5)
💬 Комментарий: {"Добавлен" if comment else "Не добавлен"}

Ваше мнение поможет нам стать лучше! 🙏
            """

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

    # Социальные сети
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

    # Админ функции
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

        text = """
❓ Не понимаю эту команду.

Используйте меню ниже или команды:
• /start - начать работу с ботом
• /menu - показать главное меню

Выберите нужный раздел:
        """

        await message.answer(text, reply_markup=Keyboards.main_menu())