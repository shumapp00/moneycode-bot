"""
Запуск бота в режиме вебхука для Render.com.
"""

import asyncio
import logging
import os
import sys

from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update, FSInputFile
from aiogram.client.default import DefaultBotProperties

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import BOT_TOKEN, ADMIN_ID, PDF_499, PDF_999
from database import init_db, mark_payment_success
from bot import dp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "")
TELEGRAM_WEBHOOK_PATH = "/webhook/telegram"
YOOKASSA_WEBHOOK_PATH = "/webhook/yookassa"

IMAGES_DIR = "images"


def get_image(image_name):
    """Безопасно получает картинку."""
    path = os.path.join(IMAGES_DIR, image_name)
    if os.path.exists(path):
        return FSInputFile(path)
    return None


app = web.Application()


async def on_startup(app):
    logger.info("=" * 50)
    logger.info("ЗАПУСК БОТА MONEY CODE НА RENDER")
    logger.info("=" * 50)
    logger.info("Шаг 1: Инициализация базы данных...")
    await init_db()
    logger.info("✅ База данных готова")
    if RENDER_URL:
        webhook_url = f"{RENDER_URL}{TELEGRAM_WEBHOOK_PATH}"
        logger.info(f"Шаг 2: Установка вебхука Telegram: {webhook_url}")
        await bot.set_webhook(url=webhook_url, allowed_updates=dp.resolve_used_update_types(), drop_pending_updates=True)
        logger.info("✅ Вебхук Telegram установлен")
    else:
        logger.warning("⚠️ RENDER_URL не задан")
    logger.info("Шаг 3: Отправка уведомления админу...")
    try:
        await bot.send_message(ADMIN_ID, "🚀 <b>Бот Money Code запущен!</b>\n\nСервер работает, вебхуки настроены.\nБот готов принимать заказы.")
        logger.info("✅ Уведомление админу отправлено")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось отправить уведомление админу: {e}")
    logger.info("=" * 50)
    logger.info("БОТ ГОТОВ К РАБОТЕ")
    logger.info("=" * 50)


async def on_shutdown(app):
    logger.info("Остановка бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()
    logger.info("Бот остановлен")


async def telegram_webhook_handler(request: web.Request):
    try:
        json_data = await request.json()
        update = Update.model_validate(json_data)
        await dp.feed_update(bot, update)
        return web.Response(status=200)
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука Telegram: {e}", exc_info=True)
        return web.Response(status=500)


async def yookassa_webhook_handler(request: web.Request):
    try:
        event = await request.json()
        logger.info(f"Получен вебхук от ЮKassa: {event.get('event', 'unknown event')}")
        if event.get("event") == "payment.succeeded":
            payment_data = event.get("object", {})
            payment_id = payment_data.get("id")
            metadata = payment_data.get("metadata", {})
            user_id = metadata.get("user_id")
            product_type = metadata.get("product_type")
            logger.info(f"💰 ПЛАТЕЖ УСПЕШЕН! ID: {payment_id}, Пользователь: {user_id}, Продукт: {product_type}")
            await mark_payment_success(payment_id)

            if product_type == "499":
                pdf_file = FSInputFile(PDF_499)
                await bot.send_document(chat_id=int(user_id), document=pdf_file, caption="✅ <b>Оплата прошла успешно!</b>\n\nТвоя методичка <b>«Система финансовых ритуалов»</b> готова.\n\nСпасибо за покупку! 🚀")
                photo = get_image("method_499.jpeg")
                if photo:
                    await bot.send_photo(chat_id=int(user_id), photo=photo, caption="📘 Методичка у тебя. Это 30-дневный протокол. Внедряй по одному ритуалу в день.")
                try:
                    await bot.send_message(ADMIN_ID, f"💰 <b>Новая продажа!</b>\n\nПродукт: <b>Система ритуалов</b>\nСумма: <b>499₽</b>\nПользователь: <code>{user_id}</code>\nID платежа: <code>{payment_id}</code>")
                except:
                    pass

            elif product_type == "999":
                pdf_file = FSInputFile(PDF_999)
                await bot.send_document(chat_id=int(user_id), document=pdf_file, caption="✅ <b>Оплата прошла успешно!</b>\n\nТвоя методичка <b>«Код личности: Перепрошивка»</b> готова.\n\nСпасибо за покупку! 🚀")
                photo = get_image("method_999.jpeg")
                if photo:
                    await bot.send_photo(chat_id=int(user_id), photo=photo, caption="🧬 «Код личности» у тебя. Это глубокая работа. Не спеши. Дай себе время.")
                try:
                    await bot.send_message(ADMIN_ID, f"💰💰 <b>Новая продажа!</b>\n\nПродукт: <b>Код личности</b>\nСумма: <b>999₽</b>\nПользователь: <code>{user_id}</code>\nID платежа: <code>{payment_id}</code>")
                except:
                    pass

        return web.Response(status=200)
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука ЮKassa: {e}", exc_info=True)
        return web.Response(status=500)


async def index_handler(request: web.Request):
    return web.Response(text="✅ Money Code Bot is running!", content_type="text/plain")


async def health_handler(request: web.Request):
    return web.Response(text="OK", status=200)


app.router.add_get("/", index_handler)
app.router.add_get("/health", health_handler)
app.router.add_post(TELEGRAM_WEBHOOK_PATH, telegram_webhook_handler)
app.router.add_post(YOOKASSA_WEBHOOK_PATH, yookassa_webhook_handler)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Запуск сервера на порту {port}...")
    web.run_app(app, port=port)