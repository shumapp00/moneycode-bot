"""
Основной модуль Telegram-бота Money Code.
Обрабатывает команды, callback-запросы, платежи.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, types, F
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
    save_payment, mark_payment_success, get_all_users_count,
    init_db
)
from keyboards import (
    get_main_menu, get_subscription_check, get_catalog_menu,
    get_payment_button, get_back_to_menu
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
        f"Я — бот канала <b>Money Code</b>. Здесь мы не мотивируем «зарабатывать больше». "
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
        "❓ <i>По вопросам пиши в Instagram:</i> @moneycode"
    )
    await message.answer(help_text)


# ============================================================
# ОБРАБОТЧИК КНОПОК ГЛАВНОГО МЕНЮ
# ============================================================

@dp.message(F.text == "🎁 Получить бесплатный гайд")
async def free_guide_start(message: Message):
    """Показывает предложение получить бесплатный гайд."""
    user = message.from_user
    
    # Проверяем, получал ли уже
    if await has_free_guide(user.id):
        await message.answer(
            "✨ Ты уже получал(а) бесплатный гайд «Честный аудит».\n"
            "Если потерял(а) файл — напиши в поддержку: @moneycode"
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
        "📸 <b>Подписывайся:</b> Instagram @moneycode"
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
        "Напиши мне в Instagram: <b>@moneycode</b>\n"
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
    
    # В реальном проекте тут была бы проверка подписки через API Instagram.
    # Пока просто отдаем файл.
    
    try:
        pdf_file = FSInputFile(PDF_FREE)
        await callback.message.answer_document(
            document=pdf_file,
            caption=(
                "✅ <b>Твой гайд «Честный аудит» готов!</b>\n\n"
                "Это первая ступень. Когда найдешь свои денежные блоки — "
                "загляни в платные методички. Они помогут их проработать."
            )
        )
        await mark_free_guide_sent(user.id)
        
        # Уведомление админу
        await bot.send_message(
            ADMIN_ID,
            f"📥 Пользователь @{user.username or user.id} получил бесплатный гайд."
        )
        
    except FileNotFoundError:
        await callback.message.answer(
            "😔 Файл временно недоступен. Напиши в поддержку: @moneycode"
        )
    
    await callback.answer("Гайд отправлен! 📩")


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
        logger.error(f"Ошибка создания платежа 499: {e}")
        await callback.message.answer(
            "😔 Произошла ошибка при создании платежа. Попробуй позже или напиши в поддержку."
        )
    
    await callback.answer()


@dp.callback_query(F.data == "buy_999")
async def process_buy_999(callback: CallbackQuery):
    """Создает платеж."""
    

# ============================================================
# ЗАПУСК БОТА
# ============================================================

async def main():
    """Запуск бота."""
    print(">>> Инициализация базы данных...")
    await init_db()
    print(">>> База данных готова")
    
    print(">>> Удаляю старые вебхуки...")
    await bot.delete_webhook(drop_pending_updates=True)
    print(">>> Старые вебхуки удалены")
    
    print(">>> ЗАПУСК ПОЛЛИНГА...")
    print(">>> Бот готов к работе! Открой Telegram и нажми /start")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(">>> Бот остановлен вручную")
    except Exception as e:
        print(f"!!! ОШИБКА: {e}")
        import traceback
        traceback.print_exc()