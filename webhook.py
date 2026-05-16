"""
Запуск бота в режиме вебхука для Render.com.
Этот файл нужен ТОЛЬКО для работы на сервере Render.
"""

import asyncio
import logging
import os
import sys

from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update, FSInputFile
from aiogram.client.default import DefaultBotProperties

# Добавляем текущую папку в пути поиска модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import BOT_TOKEN, ADMIN_ID, PDF_499, PDF_999
from database import init_db, mark_payment_success
from bot import dp

# Настройка логирования (чтобы видеть, что происходит)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создаем бота
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

# Получаем URL приложения из переменной окружения Render
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "")

# Пути для вебхуков
TELEGRAM_WEBHOOK_PATH = "/webhook/telegram"
YOOKASSA_WEBHOOK_PATH = "/webhook/yookassa"

# Создаем aiohttp приложение
app = web.Application()


# ============================================================
# ДЕЙСТВИЯ ПРИ ЗАПУСКЕ СЕРВЕРА
# ============================================================

async def on_startup(app):
    """Выполняется при запуске сервера на Render."""
    logger.info("=" * 50)
    logger.info("ЗАПУСК БОТА MONEY CODE НА RENDER")
    logger.info("=" * 50)
    
    # 1. Инициализируем базу данных
    logger.info("Шаг 1: Инициализация базы данных...")
    await init_db()
    logger.info("✅ База данных готова")
    
    # 2. Устанавливаем вебхук Telegram
    if RENDER_URL:
        webhook_url = f"{RENDER_URL}{TELEGRAM_WEBHOOK_PATH}"
        logger.info(f"Шаг 2: Установка вебхука Telegram: {webhook_url}")
        
        await bot.set_webhook(
            url=webhook_url,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True
        )
        logger.info("✅ Вебхук Telegram установлен")
    else:
        logger.warning("⚠️ RENDER_URL не задан, вебхук Telegram не установлен")
    
    # 3. Уведомляем админа о запуске
    logger.info("Шаг 3: Отправка уведомления админу...")
    try:
        await bot.send_message(
            ADMIN_ID,
            "🚀 <b>Бот Money Code запущен!</b>\n\n"
            "Сервер работает, вебхуки настроены.\n"
            "Бот готов принимать заказы."
        )
        logger.info("✅ Уведомление админу отправлено")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось отправить уведомление админу: {e}")
        logger.warning("Возможно, админ еще не запускал бота (не нажимал /start)")
    
    logger.info("=" * 50)
    logger.info("БОТ ГОТОВ К РАБОТЕ")
    logger.info("=" * 50)


# ============================================================
# ДЕЙСТВИЯ ПРИ ОСТАНОВКЕ СЕРВЕРА
# ============================================================

async def on_shutdown(app):
    """Выполняется при остановке сервера."""
    logger.info("Остановка бота...")
    
    # Удаляем вебхук
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Вебхук Telegram удален")
    
    # Закрываем сессию
    await bot.session.close()
    logger.info("Бот остановлен")


# ============================================================
# ОБРАБОТЧИК ВЕБХУКОВ TELEGRAM
# ============================================================

async def telegram_webhook_handler(request: web.Request):
    """
    Принимает обновления от Telegram.
    Когда пользователь что-то пишет боту, Telegram отправляет
    POST-запрос на этот адрес.
    """
    try:
        # Получаем JSON из запроса
        json_data = await request.json()
        logger.info(f"Получено обновление от Telegram: {json_data.get('update_id', 'unknown')}")
        
        # Преобразуем в объект Update
        update = Update.model_validate(json_data)
        
        # Передаем в диспетчер aiogram для обработки
        await dp.feed_update(bot, update)
        
        return web.Response(status=200)
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука Telegram: {e}", exc_info=True)
        return web.Response(status=500)


# ============================================================
# ОБРАБОТЧИК ВЕБХУКОВ ЮKASSA
# ============================================================

async def yookassa_webhook_handler(request: web.Request):
    """
    Принимает уведомления об оплате от ЮKassa.
    Когда пользователь оплачивает методичку, ЮKassa отправляет
    POST-запрос на этот адрес.
    """
    try:
        # Получаем JSON из запроса
        event = await request.json()
        logger.info(f"Получен вебхук от ЮKassa: {event.get('event', 'unknown event')}")
        
        # Проверяем тип события: нас интересует только успешная оплата
        if event.get("event") == "payment.succeeded":
            payment_data = event.get("object", {})
            payment_id = payment_data.get("id")
            metadata = payment_data.get("metadata", {})
            user_id = metadata.get("user_id")
            product_type = metadata.get("product_type")
            
            logger.info(f"💰 ПЛАТЕЖ УСПЕШЕН!")
            logger.info(f"   ID платежа: {payment_id}")
            logger.info(f"   Пользователь: {user_id}")
            logger.info(f"   Продукт: {product_type}")
            
            # Отмечаем платеж в базе данных
            await mark_payment_success(payment_id)
            logger.info("   Статус в базе обновлен")
            
            # Определяем, какой файл отправлять
            if product_type == "499":
                pdf_file = FSInputFile(PDF_499)
                caption = (
                    "✅ <b>Оплата прошла успешно!</b>\n\n"
                    "Твоя методичка <b>«Система финансовых ритуалов»</b> готова.\n\n"
                    "Это 30-дневный протокол пересборки денежного мышления. "
                    "Выполняй ритуалы каждый день, и через месяц ты заметишь, "
                    "как изменилось твое отношение к деньгам.\n\n"
                    "Спасибо за покупку! 🚀"
                )
            elif product_type == "999":
                pdf_file = FSInputFile(PDF_999)
                caption = (
                    "✅ <b>Оплата прошла успешно!</b>\n\n"
                    "Твоя методичка <b>«Код личности: Перепрошивка»</b> готова.\n\n"
                    "Это глубокая работа с родовыми сценариями. "
                    "Не торопись. Проходи её постепенно, давая себе время "
                    "на осознание и интеграцию.\n\n"
                    "Спасибо за покупку! 🚀"
                )
            else:
                logger.error(f"❌ Неизвестный тип продукта: {product_type}")
                return web.Response(status=400)
            
            # Отправляем файл пользователю
            try:
                await bot.send_document(
                    chat_id=int(user_id),
                    document=pdf_file,
                    caption=caption
                )
                logger.info(f"   Файл отправлен пользователю {user_id}")
            except Exception as send_error:
                logger.error(f"   Ошибка при отправке файла: {send_error}")
            
            # Отправляем уведомление админу о продаже
            try:
                product_name = "Система ритуалов" if product_type == "499" else "Код личности"
                price = "499₽" if product_type == "499" else "999₽"
                await bot.send_message(
                    ADMIN_ID,
                    f"💰 <b>Новая продажа!</b>\n\n"
                    f"Продукт: <b>{product_name}</b>\n"
                    f"Сумма: <b>{price}</b>\n"
                    f"Пользователь: <code>{user_id}</code>\n"
                    f"ID платежа: <code>{payment_id}</code>"
                )
                logger.info("   Уведомление админу отправлено")
            except Exception as admin_error:
                logger.warning(f"   Не удалось отправить уведомление админу: {admin_error}")
        
        elif event.get("event") == "payment.canceled":
            logger.info(f"❌ Платеж отменен: {event.get('object', {}).get('id')}")
        
        elif event.get("event") == "payment.waiting_for_capture":
            logger.info(f"⏳ Платеж ожидает подтверждения: {event.get('object', {}).get('id')}")
        
        return web.Response(status=200)
        
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука ЮKassa: {e}", exc_info=True)
        return web.Response(status=500)


# ============================================================
# СЛУЖЕБНЫЕ ОБРАБОТЧИКИ
# ============================================================

async def index_handler(request: web.Request):
    """Главная страница (просто проверка, что сервер жив)."""
    return web.Response(
        text="✅ Money Code Bot is running!\n\n"
             "Telegram: @moneycode_bot\n"
             "Instagram: @_mooney.code_",
        content_type="text/plain"
    )


async def health_handler(request: web.Request):
    """Эндпоинт для проверки здоровья (используется UptimeRobot)."""
    return web.Response(text="OK", status=200)


# ============================================================
# РЕГИСТРАЦИЯ МАРШРУТОВ
# ============================================================

# Главная страница
app.router.add_get("/", index_handler)
# Проверка здоровья
app.router.add_get("/health", health_handler)
# Вебхук Telegram (сюда Telegram отправляет сообщения)
app.router.add_post(TELEGRAM_WEBHOOK_PATH, telegram_webhook_handler)
# Вебхук ЮKassa (сюда ЮKassa отправляет уведомления об оплате)
app.router.add_post(YOOKASSA_WEBHOOK_PATH, yookassa_webhook_handler)

# Регистрируем функции запуска и остановки
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)


# ============================================================
# ТОЧКА ВХОДА
# ============================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Запуск сервера на порту {port}...")
    web.run_app(app, port=port)