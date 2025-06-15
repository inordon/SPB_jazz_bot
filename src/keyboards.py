from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Dict

class Keyboards:
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Главное меню"""
        buttons = [
            [InlineKeyboardButton(text="📅 Расписание", callback_data="schedule")],
            [InlineKeyboardButton(text="🗺 Навигация", callback_data="navigation")],
            [InlineKeyboardButton(text="🎫 Билеты", callback_data="tickets")],
            [InlineKeyboardButton(text="🎨 Активности", callback_data="activities")],
            [InlineKeyboardButton(text="🆘 Поддержка", callback_data="support")],
            [InlineKeyboardButton(text="💭 Обратная связь", callback_data="feedback")],
            [InlineKeyboardButton(text="📱 Соц.сети", callback_data="social")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def back_to_main() -> InlineKeyboardMarkup:
        """Кнопка возврата в главное меню"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])

    @staticmethod
    def schedule_days() -> InlineKeyboardMarkup:
        """Выбор дня расписания"""
        buttons = []
        for day in range(1, 6):
            buttons.append([InlineKeyboardButton(text=f"День {day}", callback_data=f"schedule_day_{day}")])
        buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def navigation_menu() -> InlineKeyboardMarkup:
        """Меню навигации"""
        buttons = [
            [InlineKeyboardButton(text="🗺 Карта фестиваля", callback_data="map")],
            [InlineKeyboardButton(text="🍕 Фудкорт", callback_data="route_foodcourt")],
            [InlineKeyboardButton(text="🎨 Мастер-классы", callback_data="route_workshops")],
            [InlineKeyboardButton(text="🛍 Сувениры", callback_data="route_souvenirs")],
            [InlineKeyboardButton(text="🚻 Туалеты", callback_data="route_toilets")],
            [InlineKeyboardButton(text="🏥 Медпункты", callback_data="route_medical")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def tickets_menu() -> InlineKeyboardMarkup:
        """Меню билетов"""
        buttons = [
            [InlineKeyboardButton(text="💳 Купить билеты", url=config.TICKET_PURCHASE_URL)],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def activities_menu() -> InlineKeyboardMarkup:
        """Меню активностей"""
        buttons = [
            [InlineKeyboardButton(text="🎨 Мастер-классы", callback_data="workshops")],
            [InlineKeyboardButton(text="🎓 Лекторий", callback_data="lectures")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def feedback_categories() -> InlineKeyboardMarkup:
        """Категории для оценки"""
        buttons = [
            [InlineKeyboardButton(text="🎪 Фестиваль в целом", callback_data="feedback_festival")],
            [InlineKeyboardButton(text="🍕 Фудкорты", callback_data="feedback_food")],
            [InlineKeyboardButton(text="🎨 Мастер-классы", callback_data="feedback_workshops")],
            [InlineKeyboardButton(text="🎵 Школа продюсеров", callback_data="feedback_school")],
            [InlineKeyboardButton(text="🏗 Инфраструктура", callback_data="feedback_infrastructure")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def rating_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура для оценки от 1 до 5"""
        buttons = []
        for i in range(1, 6):
            star = "⭐" * i
            buttons.append([InlineKeyboardButton(text=f"{star} {i}", callback_data=f"rating_{i}")])
        buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def social_networks() -> InlineKeyboardMarkup:
        """Социальные сети"""
        buttons = []
        for name, url in config.SOCIAL_LINKS.items():
            buttons.append([InlineKeyboardButton(text=f"📱 {name}", url=url)])
        buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def admin_menu() -> InlineKeyboardMarkup:
        """Меню администратора"""
        buttons = [
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="🎫 Управление тикетами", callback_data="admin_tickets")],
            [InlineKeyboardButton(text="💭 Отзывы", callback_data="admin_feedback")],
            [InlineKeyboardButton(text="📅 Расписание", callback_data="admin_schedule")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)