"""
Основной модуль Telegram-бота Money Code.
Обрабатывает команды, callback-запросы, платежи.
"""

import asyncio
import logging
import os
import traceback

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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
    print(">>> КОМАНДА /start ПОЛУЧЕНА <<<")
    user = message.from_user
    
    try:
        await add_user(user.id, user.username, user.first_name)
        print(f">>> Пользователь {user.id} добавлен в базу")
    except Exception as e:
        print(f">>> Ошибка добавления пользователя: {e}")
    
    welcome_text = (
        f"👋 <b>Привет, {user.first_name}!</b>\n\n"
        f"Я — бот канала <b>Money Code</b>. "
        f"Здесь мы не мотивируем «зарабатывать больше». "
        f"Мы перепрошиваем денежное мышление на уровне кода.\n\n"
        f"<i>Выбери, с чего хочешь начать:</i>"
    )
    
    try:
        await message.answer(welcome_text, reply_markup=get_main_menu())
        print(">>> Приветствие отправлено")
    except Exception as e:
        print(f">>> ОШИБКА отправки приветствия: {e}")


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
    print(">>> КНОПКА 'БЕСПЛАТНЫЙ ГАЙД' НАЖАТА <<<")
    user = message.from_user
    
    # Проверяем, получал ли уже
    try:
        already_has = await has_free_guide(user.id)
        if already_has:
            await message.answer(
                "✨ Ты уже получал(а) бесплатный гайд «Честный аудит».\n"
                "Если потерял(а) файл — напиши в поддержку: @moneycode"
            )
            return
    except Exception as e:
        print(f">>> Ошибка проверки has_free_guide: {e}")
    
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
    print(">>> КНОПКА 'КУПИТЬ МЕТОДИЧКИ' НАЖАТА <<<")
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
    print(">>> КНОПКА 'Я ПОДПИСАЛСЯ' НАЖАТА <<<")
    user = callback.from_user
    
    try:
        # Проверяем, существует ли файл
        print(f">>> Проверяю файл: {PDF_FREE}")
        print(f">>> Абсолютный путь: {os.path.abspath(PDF_FREE)}")
        print(f">>> Файл существует: {os.path.exists(PDF_FREE)}")
        
        # Пробуем другой способ указания пути
        file_path = os.path.join(os.path.dirname(__file__), PDF_FREE)
        print(f">>> Альтернативный путь: {file_path}")
        print(f">>> Файл существует (alt): {os.path.exists(file_path)}")
        
        if not os.path.exists(file_path):
            await callback.message.answer(
                f"❌ Файл не найден.\n"
                f"Путь: {file_path}\n"
                f"Напиши админу: @moneycode"
            )
            await callback.answer("Ошибка: файл не найден")
            return
        
        print(">>> Отправляю файл...")
        pdf_file = FSInputFile(file_path)
        
        await callback.message.answer_document(
            document=pdf_file,
            caption=(
                "✅ <b>Твой гайд «Честный аудит» готов!</b>\n\n"
                "Это первая ступень. Когда найдешь свои денежные блоки — "
                "загляни в платные методички. Они помогут их проработать."
            )
        )
        print(">>> Файл отправлен успешно!")
        
        await mark_free_guide_sent(user.id)
        print(">>> Статус в базе обновлен")
        
        # Уведомление админу
        try:
            await bot.send_message(
                ADMIN_ID,
                f"📥 Пользователь @{user.username or user.id} получил бесплатный гайд."
            )
        except:
            pass
        
    except Exception as e:
        print(f">>> ОШИБКА: {e}")
        print(traceback.format_exc())
        await callback.message.answer(
            f"❌ Произошла ошибка при отправке файла.\n"
            f"Ошибка: {e}\n"
            f"Напиши админу: @moneycode"
        )
    
    await callback.answer()


@dp.callback_query(F.data == "buy_499")
async def process_buy_499(callback: CallbackQuery):
    """Создает платеж на 499 рублей."""
    print(">>> КНОПКА 'КУПИТЬ 499' НАЖАТА <<<")
    user = callback.from_user
    
    await callback.message.answer("⏳ Создаю ссылку на оплату...")
    
    try:
        payment_id, payment_url = await create_payment(
            user_id=user.id,
            amount=499.0,
            product_type="499",
            description=PRODUCT_499_DESC
        )
        
        print(f">>> Платеж создан: {payment_id}")
        print(f">>> Ссылка: {payment_url}")
        
        await save_payment(user.id, payment_id, 499.0, "499")
        
        await callback.message.answer(
            f"📘 <b>{PRODUCT_499_NAME}</b>\n\n"
            f"Сумма: <b>499 ₽</b>\n\n"
            f"После оплаты методичка придет автоматически в этот чат.\n\n"
            f"<a href='{payment_url}'>💳 Нажми сюда для оплаты</a>",
            reply_markup=get_payment_button(payment_url, "499 ₽")
        )
        
    except Exception as e:
        print(f">>> ОШИБКА ПЛАТЕЖА 499: {e}")
        print(traceback.format_exc())
        await callback.message.answer(
            f"❌ Ошибка при создании платежа.\n"
            f"Ошибка: {e}\n"
            f"Попробуй позже или напиши админу: @moneycode"
        )
    
    await callback.answer()


@dp.callback_query(F.data == "buy_999")
async def process_buy_999(callback: CallbackQuery):
    """Создает платеж на 999 рублей."""
    print(">>> КНОПКА 'КУПИТЬ 999' НАЖАТА <<<")
    user = callback.from_user
    
    await callback.message.answer("⏳ Создаю ссылку на оплату...")
    
    try:
        payment_id, payment_url = await create_payment(
            user_id=user.id,
            amount=999.0,
            product_type="999",
            description=PRODUCT_999_DESC
        )
        
        print(f">>> Платеж создан: {payment_id}")
        print(f">>> Ссылка: {payment_url}")
        
        await save_payment(user.id, payment_id, 999.0, "999")
        
        await callback.message.answer(
            f"📗 <b>{PRODUCT_999_NAME}</b>\n\n"
            f"Сумма: <b>999 ₽</b>\n\n"
            f"После оплаты методичка придет автоматически в этот чат.\n\n"
            f"<a href='{payment_url}'>💳 Нажми сюда для оплаты</a>",
            reply_markup=get_payment_button(payment_url, "999 ₽")
        )
        
    except Exception as e:
        print(f">>> ОШИБКА ПЛАТЕЖА 999: {e}")
        print(traceback.format_exc())
        await callback.message.answer(
            f"❌ Ошибка при создании платежа.\n"
            f"Ошибка: {e}\n"
            f"Попробуй позже или напиши админу: @moneycode"
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
    print(">>> main() начал работу")
    try:
        print(">>> Инициализация базы данных...")
        await init_db()
        print(">>> База данных готова")
        
        print(">>> Удаляю старые вебхуки...")
        await bot.delete_webhook(drop_pending_updates=True)
        print(">>> Старые вебхуки удалены")
        
        print(">>> ЗАПУСК ПОЛЛИНГА...")
        print(">>> Бот готов к работе! Открой Telegram и нажми /start")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"!!! ОШИБКА В MAIN: {e}")
        print(traceback.format_exc())


if __name__ == "__main__":
    print(">>> Запуск asyncio.run(main())")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(">>> Бот остановлен вручную")
    except Exception as e:
        print(f"!!! КРИТИЧЕСКАЯ ОШИБКА: {e}")
        print(traceback.format_exc())