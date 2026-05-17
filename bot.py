"""
Основной модуль Telegram-бота Money Code.
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

IMAGES_DIR = "images"


def get_image(image_name):
    """Безопасно получает картинку из папки images."""
    path = os.path.join(IMAGES_DIR, image_name)
    if os.path.exists(path):
        return FSInputFile(path)
    return None


@dp.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    await add_user(user.id, user.username, user.first_name)

    welcome_text = (
        f"👋 <b>Привет, {user.first_name}!</b>\n\n"
        f"Я — бот канала <b>Money Code</b>. "
        f"Здесь мы не мотивируем «зарабатывать больше». "
        f"Мы перепрошиваем денежное мышление на уровне кода.\n\n"
        f"<i>Выбери, с чего хочешь начать:</i>"
    )

    photo = get_image("welcome.jpeg")
    if photo:
        await message.answer_photo(photo=photo, caption=welcome_text, reply_markup=get_main_menu())
    else:
        await message.answer(welcome_text, reply_markup=get_main_menu())


@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📋 <b>Справка по боту Money Code</b>\n\n"
        "🎁 <b>Бесплатный гайд</b> — диагностика денежных блоков за 15 минут.\n"
        "📘 <b>Методичка за 499₽</b> — система финансовых ритуалов на 30 дней.\n"
        "📗 <b>Методичка за 999₽</b> — глубинная перепрошивка родовых сценариев.\n\n"
        "❓ <i>По вопросам пиши в Instagram:</i> @_mooney.code_"
    )
    await message.answer(help_text)


@dp.message(F.text == "🎁 Получить бесплатный гайд")
async def free_guide_start(message: Message):
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
    text = (
        "🆘 <b>Нужна помощь?</b>\n\n"
        "• Если не пришел файл после оплаты\n"
        "• Если потерял(а) методичку\n"
        "• Если есть вопросы по содержанию\n\n"
        "Напиши мне в Instagram: <b>@_mooney.code_</b>\n"
        "Отвечаю в течение 24 часов."
    )
    await message.answer(text)


@dp.callback_query(F.data == "check_subscription")
async def process_subscription_check(callback: CallbackQuery):
    user = callback.from_user

    try:
        file_path = os.path.join(os.path.dirname(__file__), PDF_FREE)

        if not os.path.exists(file_path):
            await callback.message.answer("😔 Файл временно недоступен. Напиши в поддержку: @_mooney.code_")
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

        photo = get_image("free_guide.jpeg")
        if photo:
            await callback.message.answer_photo(
                photo=photo,
                caption="🧠 Твой денежный блок найден. Что дальше? Следующий шаг — система. Жми «📚 Купить методички»."
            )

        try:
            await bot.send_message(ADMIN_ID, f"📥 Пользователь @{user.username or user.id} получил бесплатный гайд.")
        except:
            pass

    except Exception as e:
        logger.error(f"Ошибка отправки бесплатного гайда: {e}")
        await callback.message.answer("😔 Произошла ошибка. Напиши в поддержку: @_mooney.code_")

    await callback.answer()


@dp.callback_query(F.data == "buy_499")
async def process_buy_499(callback: CallbackQuery):
    user = callback.from_user
    await callback.message.answer("⏳ Создаю ссылку на оплату...")

    try:
        payment_id, payment_url = await create_payment(
            user_id=user.id, amount=499.0, product_type="499", description=PRODUCT_499_DESC
        )
        await save_payment(user.id, payment_id, 499.0, "499")
        await callback.message.answer(
            f"📘 <b>{PRODUCT_499_NAME}</b>\n\nСумма: <b>499 ₽</b>\n\nПосле оплаты методичка придет автоматически.",
            reply_markup=get_payment_button(payment_url, "499 ₽")
        )
    except Exception as e:
        logger.error(f"Ошибка создания платежа 499: {e}")
        await callback.message.answer(f"😔 Ошибка при создании платежа.\n\n<b>Код:</b>\n<code>{str(e)[:300]}</code>\n\nПришли этот текст админу: @_mooney.code_")

    await callback.answer()


@dp.callback_query(F.data == "buy_999")
async def process_buy_999(callback: CallbackQuery):
    user = callback.from_user
    await callback.message.answer("⏳ Создаю ссылку на оплату...")

    try:
        payment_id, payment_url = await create_payment(
            user_id=user.id, amount=999.0, product_type="999", description=PRODUCT_999_DESC
        )
        await save_payment(user.id, payment_id, 999.0, "999")
        await callback.message.answer(
            f"📗 <b>{PRODUCT_999_NAME}</b>\n\nСумма: <b>999 ₽</b>\n\nПосле оплаты методичка придет автоматически.",
            reply_markup=get_payment_button(payment_url, "999 ₽")
        )
    except Exception as e:
        logger.error(f"Ошибка создания платежа 999: {e}")
        await callback.message.answer(f"😔 Ошибка при создании платежа.\n\n<b>Код:</b>\n<code>{str(e)[:300]}</code>\n\nПришли этот текст админу: @_mooney.code_")

    await callback.answer()


@dp.callback_query(F.data == "want_free_first")
async def process_want_free_first(callback: CallbackQuery):
    await callback.message.answer("Хорошее решение! Нажми кнопку 🎁 Получить бесплатный гайд в главном меню.")
    await callback.answer()


@dp.callback_query(F.data == "back_to_catalog")
async def process_back_to_catalog(callback: CallbackQuery):
    text = "📚 <b>Методички Money Code</b>\n\n📘 <b>«Система финансовых ритуалов» — 499₽</b>\n📗 <b>«Код личности: Перепрошивка» — 999₽</b>"
    await callback.message.answer(text, reply_markup=get_catalog_menu())
    await callback.answer()


@dp.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery):
    await callback.message.answer("🏠 <b>Главное меню</b>\nВыбери действие:", reply_markup=get_main_menu())
    await callback.answer()


@dp.message(F.text.in_(["🟢", "🟢 Уже внедрил", "🟢 Погрузился(лась), идёт работа"]))
async def feedback_green(message: Message):
    await message.answer("🔥 Это лучшая новость за день! Если будут вопросы — просто пиши сюда. Я на связи.")


@dp.message(F.text.in_(["🟡", "🟡 Читаю, пока осмысляю"]))
async def feedback_yellow(message: Message):
    await message.answer("🤓 Без спешки. Главное, что процесс идёт. Если что-то будет непонятно — маякни.")


@dp.message(F.text.in_(["🔴", "🔴 Что-то непонятно или не заходит", "🔴 Что-то непонятно или «не моё»"]))
async def feedback_red(message: Message):
    await message.answer(
        "Понял(а). Спасибо за честность.\n\n"
        "Напиши, что именно не зашло или непонятно. Я либо помогу разобраться, либо верну деньги. "
        "Без проблем. Это не конвейер. Мне важно, чтобы ты получил(а) результат."
    )


async def main():
    logger.info("Инициализация базы данных...")
    await init_db()
    logger.info("База данных готова")
    logger.info("Удаление старых вебхуков...")
    await bot.delete_webhook(drop_pending_updates=True)
    from scheduler import start_scheduler
    await start_scheduler()
    logger.info("Запуск поллинга...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")