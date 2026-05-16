"""
Основной модуль Telegram-бота Money Code.
Обрабатывает команды, callback-запросы, платежи.
"""

import asyncio
import logging
import os
import traceback

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message, CallbackQuery
from aiogram.client.default import DefaultBotProperties

from config import (
    BOT_TOKEN, ADMIN_ID,
    PDF_FREE, PDF_499, PDF_999,
    PRODUCT_499_NAME, PRODUCT_499_DESC,
    PRODUCT_999_NAME, PRODUCT_999_DESC,
    INSTAGRAM_URL
)
from database import (
    add_user, mark_free_guide_sent, has_free_guide,
    save_payment, init_db
)
from keyboards import (
    get_main_menu, get_subscription_check, get_catalog_menu,
    get_payment_button
)
from payments import create_payment

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем бота и диспетчер
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()


# ============================================================
# ОБРАБОТЧИК КОМАНД
# ============================================================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обрабатывает команду /start."""
    user = message.from_user
    await add_user(user.id, user.username, user.first_name)

    welcome_text = (
        f"👋 <b>Привет, {user.first_name}!</b>\n\n"
        f"Я — бот канала <b>Money Code</b>. "
        f"Здесь мы не мотивируем «зарабатывать больше». "
        f"Мы перепрошиваем денежное мышление на уровне кода.\n\n"
        f"<i>Выбери, с чего хочешь начать:</i>"
    )

    await message.answer(welcome_text, reply_markup=get_main_menu())


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обрабатывает команду /help."""
    help_text = (
        "📋 <b>Справка по боту Money Code</b>\n\n"
        "🎁 <b>Бесплатный гайд</b> — диагностика денежных блоков за 15 минут.\n"
        "📘 <b>Методичка за 499₽</b> — система финансовых ритуалов на 30 дней.\n"
        "📗 <b>Методичка за 999₽</b> — глубинная перепрошивка родовых сценариев.\n\n"
        "❓ <i>По вопросам пиши в Instagram:</i> @_mooney.code_"
    )
    await message.answer(help_text)


# ============================================================
# ОБРАБОТЧИК КНОПОК ГЛАВНОГО МЕНЮ
# ============================================================

@dp.message(F.text == "🎁 Получить бесплатный гайд")
async def free_guide_start(message: Message):
    """Показывает предложение получить бесплатный гайд."""
    user = message.from_user

    already_has = await has_free_guide(user.id)
    if already_has:
        await message.answer(
            "✨ Ты уже получал(а) бесплатный гайд «Честный аудит».\n"
            "Если потерял(а) файл — напиши в поддержку: @_mooney.code_"
        )
        return

    text = (
        "🎁 <b>Бесплатный гайд «Честный аудит»</b>\n\n"
        "Ты узнаешь:\n"
        "• Какие 4 архетипа бедности существуют\n"
        "• Какой денежный блок управляет тобой\n"
        "• 3 техники самодиагностики\n\n"
        "<b>Чтобы получить гайд:</b>\n"
        "1️⃣ Подпишись на Instagram канал <b>Money Code</b>\n"
        "2️⃣ Нажми кнопку «Я подписался(ась)»\n"
        "3️⃣ Бот сразу отправит PDF-файл"
    )

    await message.answer(text, reply_markup=get_subscription_check())


@dp.message(F.text == "📚 Купить методички")
async def show_catalog(message: Message):
    """Показывает каталог платных методичек."""
    text = (
        "📚 <b>Методички Money Code</b>\n\n"
        "Выбери, какой уровень проработки тебе нужен:\n\n"
        "📘 <b>«Система финансовых ритуалов» — 499₽</b>\n"
        "30-дневный протокол. 10 ритуалов. Архитектура безопасности.\n\n"
        "📗 <b>«Код личности: Перепрошивка» — 999₽</b>\n"
        "Глубинная работа. Родовые сценарии. Реимпринтинг.\n\n"
        "<i>После оплаты файл придет автоматически.</i>"
    )
    await message.answer(text, reply_markup=get_catalog_menu())


@dp.message(F.text == "💬 О канале Money Code")
async def about_channel(message: Message):
    """Рассказывает о канале."""
    text = (
        "💬 <b>Money Code</b> — это канал о том, как упаковать "
        "финансовые привычки в систему.\n\n"
        "Мы не верим в «волшебные таблетки» и «марафоны желаний». "
        "Мы верим в нейронауку, ритуалы и честную работу с подсознанием.\n\n"
        "📸 <b>Подписывайся:</b> Instagram @_mooney.code_"
    )
    await message.answer(text)


@dp.message(F.text == "🆘 Поддержка")
async def support(message: Message):
    """Контакты поддержки."""
    text = (
        "🆘 <b>Нужна помощь?</b>\n\n"
        "• Если не пришел файл после оплаты\n"
        "• Если потерял(а) методичку\n"
        "• Если есть вопросы по содержанию\n\n"
        "Напиши мне в Instagram: <b>@_mooney.code_</b>\n"
        "Отвечаю в течение 24 часов."
    )
    await message.answer(text)


# ============================================================
# ОБРАБОТЧИК INLINE-КНОПОК (CALLBACK)
# ============================================================

@dp.callback_query(F.data == "check_subscription")
async def process_subscription_check(callback: CallbackQuery):
    """Обрабатывает нажатие «Я подписался»."""
    user = callback.from_user

    try:
        file_path = os.path.join(os.path.dirname(__file__), PDF_FREE)

        if not os.path.exists(file_path):
            await callback.message.answer(
                "😔 Файл временно недоступен. Напиши в поддержку: @_mooney.code_"
            )
            await callback.answer("Файл не найден")
            return

        pdf_file = FSInputFile(file_path)
        await callback.message.answer_document(
            document=pdf_file,
            caption=(
                "✅ <b>Твой гайд «Честный аудит» готов!</b>\n\n"
                "Это первая ступень. Когда найдешь свои денежные блоки — "
                "загляни в платные методички. Они помогут их проработать."
            )
        )

        await mark_free_guide_sent(user.id)

        try:
            await bot.send_message(
                ADMIN_ID,
                f"📥 Пользователь @{user.username or user.id} получил бесплатный гайд."
            )
        except:
            pass

    except Exception as e:
        logger.error(f"Ошибка отправки бесплатного гайда: {e}")
        await callback.message.answer(
            "😔 Произошла ошибка при отправке файла. Напиши в поддержку: @_mooney.code_"
        )

    await callback.answer()


@dp.callback_query(F.data == "buy_499")
async def process_buy_499(callback: CallbackQuery):
    """Создает платеж на 499 рублей."""
    user = callback.from_user

    await callback.message.answer("⏳ Создаю ссылку на оплату...")

    try:
        payment_id, payment_url = await create_payment(
            user_id=user.id,
            amount=499.0,
            product_type="499",
            description=PRODUCT_499_DESC
        )

        await save_payment(user.id, payment_id, 499.0, "499")

        await callback.message.answer(
            f"📘 <b>{PRODUCT_499_NAME}</b>\n\n"
            f"Сумма: <b>499 ₽</b>\n\n"
            f"После оплаты методичка придет автоматически в этот чат.",
            reply_markup=get_payment_button(payment_url, "499 ₽")
        )

    except Exception as e:
        error_details = str(e)
        logger.error(f"Ошибка создания платежа 499: {error_details}")
        logger.error(traceback.format_exc())
        await callback.message.answer(
            f"😔 Ошибка при создании платежа.\n\n"
            f"<b>Код ошибки:</b>\n<code>{error_details[:300]}</code>\n\n"
            f"Пришли этот текст админу: @_mooney.code_"
        )

    await callback.answer()


@dp.callback_query(F.data == "buy_999")
async def process_buy_999(callback: CallbackQuery):
    """Создает платеж на 999 рублей."""
    user = callback.from_user

    await callback.message.answer("⏳ Создаю ссылку на оплату...")

    try:
        payment_id, payment_url = await create_payment(
            user_id=user.id,
            amount=999.0,
            product_type="999",
            description=PRODUCT_999_DESC
        )

        await save_payment(user.id, payment_id, 999.0, "999")

        await callback.message.answer(
            f"📗 <b>{PRODUCT_999_NAME}</b>\n\n"
            f"Сумма: <b>999 ₽</b>\n\n"
            f"После оплаты методичка придет автоматически в этот чат.",
            reply_markup=get_payment_button(payment_url, "999 ₽")
        )

    except Exception as e:
        error_details = str(e)
        logger.error(f"Ошибка создания платежа 999: {error_details}")
        logger.error(traceback.format_exc())
        await callback.message.answer(
            f"😔 Ошибка при создании платежа.\n\n"
            f"<b>Код ошибки:</b>\n<code>{error_details[:300]}</code>\n\n"
            f"Пришли этот текст админу: @pathrea"
        )

    await callback.answer()


@dp.callback_query(F.data == "want_free_first")
async def process_want_free_first(callback: CallbackQuery):
    """Пользователь хочет сначала бесплатный гайд."""
    await callback.message.answer(
        "Хорошее решение! Нажми кнопку 🎁 Получить бесплатный гайд в главном меню."
    )
    await callback.answer()


@dp.callback_query(F.data == "back_to_catalog")
async def process_back_to_catalog(callback: CallbackQuery):
    """Возврат в каталог."""
    text = (
        "📚 <b>Методички Money Code</b>\n\n"
        "📘 <b>«Система финансовых ритуалов» — 499₽</b>\n"
        "📗 <b>«Код личности: Перепрошивка» — 999₽</b>"
    )
    await callback.message.answer(text, reply_markup=get_catalog_menu())
    await callback.answer()


@dp.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery):
    """Возврат в главное меню."""
    await callback.message.answer(
        "🏠 <b>Главное меню</b>\nВыбери действие:",
        reply_markup=get_main_menu()
    )
    await callback.answer()


# ============================================================
# ЗАПУСК БОТА
# ============================================================

async def main():
    """Запуск бота."""
    logger.info("Инициализация базы данных...")
    await init_db()
    logger.info("База данных готова")

    logger.info("Удаление старых вебхуков...")
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Запуск поллинга...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")