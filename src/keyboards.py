from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Dict
from config import config

class Keyboards:
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Главное меню (старая версия для совместимости)"""
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
    def main_menu_with_support_indicator(has_active_ticket: bool = False) -> InlineKeyboardMarkup:
        """Главное меню с индикатором активного тикета"""
        support_text = "🆘 Поддержка"
        if has_active_ticket:
            support_text = "🆘 Поддержка 🔴"  # Красный кружок = активный тикет

        buttons = [
            [InlineKeyboardButton(text="📅 Расписание", callback_data="schedule")],
            [InlineKeyboardButton(text="🗺 Навигация", callback_data="navigation")],
            [InlineKeyboardButton(text="🎫 Билеты", callback_data="tickets")],
            [InlineKeyboardButton(text="🎨 Активности", callback_data="activities")],
            [InlineKeyboardButton(text=support_text, callback_data="support")],
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

    # ================== ПОДДЕРЖКА V2 ==================

    @staticmethod
    def support_main_menu(ticket_id: int = None) -> InlineKeyboardMarkup:
        """Главное меню поддержки"""
        if ticket_id:
            # Если есть активный тикет
            buttons = [
                [InlineKeyboardButton(text="💬 Продолжить диалог",
                                      callback_data=f"continue_dialog_{ticket_id}")],
                [InlineKeyboardButton(text="📋 История сообщений",
                                      callback_data=f"show_history_{ticket_id}")],
                [InlineKeyboardButton(text="✅ Закрыть обращение",
                                      callback_data=f"close_ticket_{ticket_id}")],
                [InlineKeyboardButton(text="🆕 Новое обращение",
                                      callback_data="new_ticket")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ]
        else:
            # Если нет активного тикета
            buttons = [
                [InlineKeyboardButton(text="🆕 Создать обращение",
                                      callback_data="new_ticket")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ]

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def active_dialog_menu(ticket_id: int) -> InlineKeyboardMarkup:
        """Меню активного диалога"""
        buttons = [
            [InlineKeyboardButton(text="📋 История сообщений",
                                  callback_data=f"show_history_{ticket_id}")],
            [InlineKeyboardButton(text="✅ Закрыть обращение",
                                  callback_data=f"close_ticket_{ticket_id}")],
            [InlineKeyboardButton(text="◀️ Назад к тикету",
                                  callback_data=f"back_to_ticket_{ticket_id}")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def ticket_history_menu(ticket_id: int) -> InlineKeyboardMarkup:
        """Меню истории тикета"""
        buttons = [
            [InlineKeyboardButton(text="💬 Продолжить диалог",
                                  callback_data=f"continue_dialog_{ticket_id}")],
            [InlineKeyboardButton(text="◀️ Назад к тикету",
                                  callback_data=f"back_to_ticket_{ticket_id}")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def close_ticket_confirm(ticket_id: int) -> InlineKeyboardMarkup:
        """Подтверждение закрытия тикета"""
        buttons = [
            [InlineKeyboardButton(text="✅ Да, закрыть",
                                  callback_data=f"confirm_close_{ticket_id}")],
            [InlineKeyboardButton(text="❌ Отмена",
                                  callback_data=f"back_to_ticket_{ticket_id}")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def after_ticket_closed() -> InlineKeyboardMarkup:
        """Меню после закрытия тикета"""
        buttons = [
            [InlineKeyboardButton(text="🆕 Новое обращение", callback_data="new_ticket")],
            [InlineKeyboardButton(text="💭 Оставить отзыв", callback_data="feedback")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def rate_limit_warning(wait_seconds: int) -> InlineKeyboardMarkup:
        """Клавиатура для предупреждения о лимите"""
        buttons = [
            [InlineKeyboardButton(text="🔄 Попробовать снова",
                                  callback_data="retry_support")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def new_ticket_options() -> InlineKeyboardMarkup:
        """Опции для нового тикета"""
        buttons = [
            [InlineKeyboardButton(text="📝 Текстовое обращение",
                                  callback_data="new_ticket_text")],
            [InlineKeyboardButton(text="📷 С фотографией",
                                  callback_data="new_ticket_photo")],
            [InlineKeyboardButton(text="📄 С документом",
                                  callback_data="new_ticket_document")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="support")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    # ================== ОБРАТНАЯ СВЯЗЬ ==================

    @staticmethod
    def feedback_categories() -> InlineKeyboardMarkup:
        """Категории для оценки"""
        buttons = [
            [InlineKeyboardButton(text="🎪 Фестиваль в целом", callback_data="feedback_festival")],
            [InlineKeyboardButton(text="🍕 Фудкорты", callback_data="feedback_food")],
            [InlineKeyboardButton(text="🎨 Мастер-классы", callback_data="feedback_workshops")],
            [InlineKeyboardButton(text="🎓 Лекторий", callback_data="feedback_lectures")],
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

    # ================== СОЦИАЛЬНЫЕ СЕТИ ==================

    @staticmethod
    def social_networks() -> InlineKeyboardMarkup:
        """Социальные сети"""
        buttons = []
        for name, url in config.SOCIAL_LINKS.items():
            buttons.append([InlineKeyboardButton(text=f"📱 {name}", url=url)])
        buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    # ================== АДМИН ПАНЕЛЬ ==================

    @staticmethod
    def admin_menu() -> InlineKeyboardMarkup:
        """Меню администратора (обновленное)"""
        buttons = [
            [InlineKeyboardButton(text="🎛 Панель поддержки",
                                  callback_data="admin_support_dashboard")],
            [InlineKeyboardButton(text="📊 Общая статистика",
                                  callback_data="admin_stats")],
            [InlineKeyboardButton(text="🎫 Тикеты поддержки",
                                  callback_data="admin_tickets")],
            [InlineKeyboardButton(text="💭 Отзывы",
                                  callback_data="admin_feedback")],
            [InlineKeyboardButton(text="📅 Расписание",
                                  callback_data="admin_schedule")],
            [InlineKeyboardButton(text="👥 Пользователи",
                                  callback_data="admin_users")],
            [InlineKeyboardButton(text="📢 Рассылка",
                                  callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="⚙️ Настройки",
                                  callback_data="admin_settings")],
            [InlineKeyboardButton(text="🔧 Система",
                                  callback_data="admin_system")],
            [InlineKeyboardButton(text="🏠 Главное меню",
                                  callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def admin_support_menu() -> InlineKeyboardMarkup:
        """Админ меню для управления поддержкой"""
        buttons = [
            [InlineKeyboardButton(text="🎛 Панель поддержки",
                                  callback_data="admin_support_dashboard")],
            [InlineKeyboardButton(text="🚨 Срочные тикеты",
                                  callback_data="admin_urgent_tickets")],
            [InlineKeyboardButton(text="📊 Статистика",
                                  callback_data="admin_detailed_stats")],
            [InlineKeyboardButton(text="👥 Активность сотрудников",
                                  callback_data="admin_staff_activity")],
            [InlineKeyboardButton(text="📈 Метрики по дням",
                                  callback_data="admin_daily_metrics")],
            [InlineKeyboardButton(text="🔍 Поиск тикетов",
                                  callback_data="admin_search_tickets")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def admin_support_dashboard_menu() -> InlineKeyboardMarkup:
        """Меню для панели управления поддержкой"""
        buttons = [
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
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def admin_urgent_tickets_menu() -> InlineKeyboardMarkup:
        """Меню для срочных тикетов"""
        buttons = [
            [InlineKeyboardButton(text="🔄 Обновить",
                                  callback_data="admin_urgent_tickets")],
            [InlineKeyboardButton(text="📋 Все открытые тикеты",
                                  callback_data="admin_open_tickets")],
            [InlineKeyboardButton(text="◀️ Назад",
                                  callback_data="admin_support_dashboard")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def admin_stats_menu() -> InlineKeyboardMarkup:
        """Меню статистики админ панели"""
        buttons = [
            [InlineKeyboardButton(text="👥 Активность сотрудников",
                                  callback_data="admin_staff_activity")],
            [InlineKeyboardButton(text="📈 По дням",
                                  callback_data="admin_daily_metrics")],
            [InlineKeyboardButton(text="🔄 Обновить",
                                  callback_data="admin_detailed_stats")],
            [InlineKeyboardButton(text="◀️ Назад",
                                  callback_data="admin_support_dashboard")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def admin_back_to_dashboard() -> InlineKeyboardMarkup:
        """Возврат к панели поддержки"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад к панели",
                                  callback_data="admin_support_dashboard")]
        ])

    # ================== ДОПОЛНИТЕЛЬНЫЕ КЛАВИАТУРЫ ==================

    @staticmethod
    def confirmation_keyboard(confirm_data: str, cancel_data: str = "main_menu") -> InlineKeyboardMarkup:
        """Универсальная клавиатура подтверждения"""
        buttons = [
            [InlineKeyboardButton(text="✅ Да", callback_data=confirm_data)],
            [InlineKeyboardButton(text="❌ Нет", callback_data=cancel_data)]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def pagination_keyboard(current_page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
        """Клавиатура для пагинации"""
        buttons = []

        # Навигационные кнопки
        nav_buttons = []
        if current_page > 1:
            nav_buttons.append(InlineKeyboardButton(text="◀️ Пред",
                                                    callback_data=f"{prefix}_page_{current_page-1}"))

        nav_buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}",
                                                callback_data="noop"))

        if current_page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="След ▶️",
                                                    callback_data=f"{prefix}_page_{current_page+1}"))

        if nav_buttons:
            buttons.append(nav_buttons)

        # Кнопка возврата
        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def loading_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура загрузки"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏳ Загрузка...", callback_data="loading")]
        ])

    @staticmethod
    def error_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура для ошибок"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="retry")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])

    @staticmethod
    def workshop_register_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура для записи на мастер-класс"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Записаться", callback_data="workshop_register")],
            [InlineKeyboardButton(text="◀️ Назад к активностям", callback_data="activities")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])

    @staticmethod
    def contact_info_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура с контактной информацией"""
        buttons = []

        # Если есть email поддержки
        if hasattr(config, 'SUPPORT_EMAIL') and config.SUPPORT_EMAIL:
            buttons.append([InlineKeyboardButton(text="📧 Email поддержки",
                                                 url=f"mailto:{config.SUPPORT_EMAIL}")])

        # Группа поддержки (если публичная)
        # buttons.append([InlineKeyboardButton(text="👥 Группа поддержки",
        #                                      url="https://t.me/your_support_group")])

        buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def quick_actions_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура быстрых действий"""
        buttons = [
            [InlineKeyboardButton(text="🆘 Срочная помощь", callback_data="support")],
            [InlineKeyboardButton(text="📅 Сегодняшнее расписание", callback_data="schedule_today")],
            [InlineKeyboardButton(text="🗺 Как добраться", callback_data="navigation")],
            [InlineKeyboardButton(text="💭 Быстрый отзыв", callback_data="feedback")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    # ================== СПЕЦИАЛЬНЫЕ КЛАВИАТУРЫ ==================

    @staticmethod
    def emergency_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура для экстренных случаев"""
        buttons = [
            [InlineKeyboardButton(text="🚑 Медицинская помощь", callback_data="emergency_medical")],
            [InlineKeyboardButton(text="🚔 Служба безопасности", callback_data="emergency_security")],
            [InlineKeyboardButton(text="🔥 Пожарная служба", callback_data="emergency_fire")],
            [InlineKeyboardButton(text="📞 Экстренная связь 112", url="tel:112")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def accessibility_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура для людей с ограниченными возможностями"""
        buttons = [
            [InlineKeyboardButton(text="♿ Доступная навигация", callback_data="accessibility_navigation")],
            [InlineKeyboardButton(text="🚻 Доступные туалеты", callback_data="accessibility_toilets")],
            [InlineKeyboardButton(text="🎫 Льготные билеты", callback_data="accessibility_tickets")],
            [InlineKeyboardButton(text="📞 Помощь сопровождающего", callback_data="accessibility_help")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def language_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура выбора языка"""
        buttons = [
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="lang_de")],
            [InlineKeyboardButton(text="🇫🇷 Français", callback_data="lang_fr")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)