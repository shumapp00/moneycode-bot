"""
Модуль клавиатур для бота Money Code.
Содержит все кнопки, которые видит пользователь.
"""

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню бота."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎁 Получить бесплатный гайд")],
            [KeyboardButton(text="📚 Купить методички")],
            [KeyboardButton(text="💬 О канале Money Code")],
            [KeyboardButton(text="🆘 Поддержка")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие..."
    )


def get_subscription_check() -> InlineKeyboardMarkup:
    """Кнопки для проверки подписки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📸 Подписаться на Money Code в Instagram",
                url="https://www.instagram.com/_mooney.code_"
            )],
            [InlineKeyboardButton(
                text="✅ Я подписался(ась), получить гайд",
                callback_data="check_subscription"
            )]
        ]
    )


def get_catalog_menu() -> InlineKeyboardMarkup:
    """Каталог платных методичек."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📘 Методичка «Система финансовых ритуалов» — 499 ₽",
                callback_data="buy_499"
            )],
            [InlineKeyboardButton(
                text="📗 Методичка «Код личности: Перепрошивка» — 999 ₽",
                callback_data="buy_999"
            )],
            [InlineKeyboardButton(
                text="🎁 Сначала хочу бесплатный гайд",
                callback_data="want_free_first"
            )]
        ]
    )


def get_payment_button(payment_url: str, product_name: str) -> InlineKeyboardMarkup:
    """Кнопка для перехода к оплате."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"💳 Оплатить {product_name}",
                url=payment_url
            )],
            [InlineKeyboardButton(
                text="🔙 Назад в каталог",
                callback_data="back_to_catalog"
            )]
        ]
    )


def get_back_to_menu() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🏠 В главное меню",
                callback_data="main_menu"
            )]
        ]
    )