"""
Модуль авторассылки прогрева и сбора обратной связи.
Сохраняет прогресс в базу данных, чтобы не сбрасываться при перезапуске.
"""

import asyncio
import logging
import os
from datetime import datetime

from aiogram.types import FSInputFile

from bot import bot
from database import (
    get_users_with_free_guide_not_bought,
    get_users_who_bought_499,
    get_users_who_bought_999,
)

logger = logging.getLogger(__name__)

IMAGES_DIR = "images"

# Сообщения прогрева
WARMUP_DATA = [
    {
        "image": "warmup_day1.jpeg",
        "text": (
            "🎁 <b>Гайд у тебя. Не откладывай его в «потом».</b>\n\n"
            "15 минут сегодня = понимание, что именно блокирует твои деньги. "
            "Это не марафон желаний. Это диагностика. Как МРТ для кошелька.\n\n"
            "Пройди тест. Найди свой архетип. А завтра я расскажу, что с ним делать дальше."
        )
    },
    {
        "image": "warmup_day2.jpeg",
        "text": (
            "👋 <b>Это снова я. Твой «менеджер по перепрошивке».</b>\n\n"
            "Ты уже знаешь свой архетип? Самозванец, Спасатель, Аскет или Фаталист?\n\n"
            "Вот в чём прикол: узнать — мало. Это как поставить диагноз и не лечиться. "
            "Большинство на этом и останавливаются.\n\n"
            "А дальше нужна <b>СИСТЕМА</b>. Конкретные ритуалы. Каждый день.\n\n"
            "Завтра расскажу про 3 счёта — это база, которая убирает хаос из кошелька за один вечер."
        )
    },
    {
        "image": "warmup_day3.jpeg",
        "text": (
            "🏗 <b>Архитектура безопасности. Звучит скучно. Работает — зверски.</b>\n\n"
            "У тебя есть 3 счёта? Бункер, Командный центр, Шлюз удовольствий?\n\n"
            "Скорее всего, нет. Скорее всего, все деньги в одной куче. Поэтому тревога.\n\n"
            "Я расписал всю архитектуру в методичке «Система финансовых ритуалов». "
            "Это 30-дневный протокол. 10 ритуалов в день.\n\n"
            "Завтра расскажу про главный предохранитель от срывов. Про Шлюз."
        )
    },
    {
        "image": "warmup_day4.jpeg",
        "text": (
            "🎈 <b>Шлюз удовольствий. Это 10% дохода на любую хрень. Без вины. Без отчётов.</b>\n\n"
            "Звучит безответственно? На самом деле — это единственное, что спасает от срывов.\n\n"
            "Когда ты запрещаешь себе ВСЁ, психика взрывается.\n\n"
            "В методичке «Система финансовых ритуалов» я даю не только теорию, но и чек-лист на 30 дней.\n\n"
            "Завтра — последнее сообщение. О деньгах."
        )
    },
    {
        "image": "warmup_day5.jpeg",
        "text": (
            "💳 <b>Сколько ты уже потратил(а) на импульсные покупки за этот месяц?</b>\n\n"
            "Доставка еды, такси, курс, который не прошёл(ла).\n\n"
            "А теперь представь: ты мог(ла) бы вообще не париться о деньгах. "
            "Не потому что их «много». А потому что есть <b>СИСТЕМА</b>.\n\n"
            "Она стоит 499₽ — это меньше одного похода в суши. "
            "Просто нажми кнопку «📚 Купить методички» внизу."
        )
    },
]

FOLLOWUP_IMAGE = "warmup_followup.jpeg"
FOLLOWUP_TEXT = (
    "🤔 <b>Слушай, ты проходил(а) бесплатный гайд. Значит, тема денег для тебя важна.</b> "
    "Но ты не пошёл(ла) дальше.\n\n"
    "Это не упрёк. Мне правда интересно: что остановило?\n\n"
    "— Цена?\n— Недоверие?\n— «Я сам(а) разберусь»?\n— Что-то другое?\n\n"
    "Напиши честно. Я не буду переубеждать. Просто хочу понять, что не так."
)

FEEDBACK_499 = (
    "🔍 <b>Привет! Ты уже сутки с методичкой «Система финансовых ритуалов». Как ощущения?</b>\n\n"
    "Напиши честно:\n🟢 Уже внедрил(а) первые ритуалы, нравится\n🟡 Читаю, пока осмысляю\n🔴 Что-то непонятно или не заходит"
)

FEEDBACK_999 = (
    "🧬 <b>Привет! Ты открыл(а) «Код личности». Это самая глубокая методичка из всех.</b>\n\n"
    "Там есть техники, которые могут вскрыть неприятные вещи. Это нормально.\n\n"
    "Напиши, как идёт:\n🟢 Погрузился(лась), идёт работа\n🟡 Читаю, пока осмысляю\n🔴 Что-то непонятно или «не моё»"
)


def get_image(image_name):
    """Безопасно получает картинку из папки images."""
    path = os.path.join(IMAGES_DIR, image_name)
    if os.path.exists(path):
        return FSInputFile(path)
    return None


async def get_warmup_day(user_id: int) -> int:
    """Получает текущий день прогрева пользователя."""
    import aiosqlite
    async with aiosqlite.connect("moneycode.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warmup_progress (
                user_id INTEGER PRIMARY KEY,
                current_day INTEGER DEFAULT 0,
                followup_sent INTEGER DEFAULT 0,
                feedback_499_sent INTEGER DEFAULT 0,
                feedback_999_sent INTEGER DEFAULT 0,
                last_message_at TEXT
            )
        """)
        await db.commit()
        
        async with db.execute(
            "SELECT current_day FROM warmup_progress WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
            else:
                await db.execute(
                    "INSERT OR IGNORE INTO warmup_progress (user_id, current_day) VALUES (?, 0)",
                    (user_id,)
                )
                await db.commit()
                return 0


async def set_warmup_day(user_id: int, day: int):
    """Сохраняет текущий день прогрева."""
    import aiosqlite
    async with aiosqlite.connect("moneycode.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warmup_progress (
                user_id INTEGER PRIMARY KEY,
                current_day INTEGER DEFAULT 0,
                followup_sent INTEGER DEFAULT 0,
                feedback_499_sent INTEGER DEFAULT 0,
                feedback_999_sent INTEGER DEFAULT 0,
                last_message_at TEXT
            )
        """)
        await db.execute(
            "UPDATE warmup_progress SET current_day = ?, last_message_at = ? WHERE user_id = ?",
            (day, datetime.now().isoformat(), user_id)
        )
        await db.commit()


async def is_followup_sent(user_id: int) -> bool:
    """Проверяет, отправлен ли фоллоу-ап."""
    import aiosqlite
    async with aiosqlite.connect("moneycode.db") as db:
        async with db.execute(
            "SELECT followup_sent FROM warmup_progress WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None and row[0] == 1


async def mark_followup_sent(user_id: int):
    """Отмечает фоллоу-ап как отправленный."""
    import aiosqlite
    async with aiosqlite.connect("moneycode.db") as db:
        await db.execute(
            "UPDATE warmup_progress SET followup_sent = 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def is_feedback_sent(user_id: int, product_type: str) -> bool:
    """Проверяет, отправлен ли запрос обратной связи."""
    import aiosqlite
    async with aiosqlite.connect("moneycode.db") as db:
        column = f"feedback_{product_type}_sent"
        async with db.execute(
            f"SELECT {column} FROM warmup_progress WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None and row[0] == 1


async def mark_feedback_sent(user_id: int, product_type: str):
    """Отмечает запрос обратной связи как отправленный."""
    import aiosqlite
    async with aiosqlite.connect("moneycode.db") as db:
        column = f"feedback_{product_type}_sent"
        await db.execute(
            f"UPDATE warmup_progress SET {column} = 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def send_warmup_cycle():
    """Основной цикл прогрева — проверяет всех пользователей каждые 5 минут."""
    while True:
        try:
            users = await get_users_with_free_guide_not_bought()
            
            for user in users:
                user_id = user[0]
                current_day = await get_warmup_day(user_id)
                
                # Если все 5 дней пройдены и фоллоу-ап не отправлен — ждём 2 дня и шлём
                if current_day >= 5 and not await is_followup_sent(user_id):
                    last_msg = await get_last_message_time(user_id)
                    if last_msg:
                        last_time = datetime.fromisoformat(last_msg)
                        if (datetime.now() - last_time).days >= 2:
                            photo = get_image(FOLLOWUP_IMAGE)
                            try:
                                if photo:
                                    await bot.send_photo(chat_id=user_id, photo=photo, caption=FOLLOWUP_TEXT)
                                else:
                                    await bot.send_message(user_id, FOLLOWUP_TEXT)
                                await mark_followup_sent(user_id)
                                logger.info(f"Фоллоу-ап отправлен пользователю {user_id}")
                            except Exception as e:
                                logger.error(f"Ошибка отправки фоллоу-апа {user_id}: {e}")
                
                # Если ещё не все дни пройдены — проверяем, пора ли слать следующий
                elif current_day < 5:
                    last_msg = await get_last_message_time(user_id)
                    if last_msg:
                        last_time = datetime.fromisoformat(last_msg)
                        if (datetime.now() - last_time).days >= 1:
                            # Отправляем следующий день
                            data = WARMUP_DATA[current_day]
                            photo = get_image(data["image"])
                            try:
                                if photo:
                                    await bot.send_photo(chat_id=user_id, photo=photo, caption=data["text"])
                                else:
                                    await bot.send_message(user_id, data["text"])
                                await set_warmup_day(user_id, current_day + 1)
                                logger.info(f"Прогрев день {current_day + 1} отправлен пользователю {user_id}")
                            except Exception as e:
                                logger.error(f"Ошибка отправки прогрева {user_id}: {e}")
                    else:
                        # Первый запуск — отправляем день 1 сразу
                        data = WARMUP_DATA[0]
                        photo = get_image(data["image"])
                        try:
                            if photo:
                                await bot.send_photo(chat_id=user_id, photo=photo, caption=data["text"])
                            else:
                                await bot.send_message(user_id, data["text"])
                            await set_warmup_day(user_id, 1)
                            logger.info(f"Прогрев день 1 отправлен пользователю {user_id}")
                        except Exception as e:
                            logger.error(f"Ошибка отправки прогрева {user_id}: {e}")
        
        except Exception as e:
            logger.error(f"Ошибка в цикле прогрева: {e}")
        
        await asyncio.sleep(300)  # Проверяем каждые 5 минут


async def get_last_message_time(user_id: int) -> str | None:
    """Получает время последнего отправленного сообщения."""
    import aiosqlite
    async with aiosqlite.connect("moneycode.db") as db:
        async with db.execute(
            "SELECT last_message_at FROM warmup_progress WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
    return None


async def send_feedback_cycle():
    """Проверяет покупателей и отправляет запросы обратной связи."""
    await asyncio.sleep(60)  # Ждём минуту после запуска
    
    while True:
        try:
            # Обратная связь для покупателей 499
            users_499 = await get_users_who_bought_499()
            for user in users_499:
                user_id = user[0]
                if not await is_feedback_sent(user_id, "499"):
                    try:
                        await bot.send_message(user_id, FEEDBACK_499)
                        await mark_feedback_sent(user_id, "499")
                        logger.info(f"Обратная связь (499) отправлена пользователю {user_id}")
                    except Exception as e:
                        logger.error(f"Ошибка отправки обратной связи {user_id}: {e}")
            
            # Обратная связь для покупателей 999
            users_999 = await get_users_who_bought_999()
            for user in users_999:
                user_id = user[0]
                if not await is_feedback_sent(user_id, "999"):
                    try:
                        await bot.send_message(user_id, FEEDBACK_999)
                        await mark_feedback_sent(user_id, "999")
                        logger.info(f"Обратная связь (999) отправлена пользователю {user_id}")
                    except Exception as e:
                        logger.error(f"Ошибка отправки обратной связи {user_id}: {e}")
        
        except Exception as e:
            logger.error(f"Ошибка в цикле обратной связи: {e}")
        
        await asyncio.sleep(3600)  # Проверяем каждый час


async def start_scheduler():
    """Запускает все задачи авторассылки."""
    asyncio.create_task(send_warmup_cycle())
    asyncio.create_task(send_feedback_cycle())
    logger.info("Планировщик авторассылки запущен (с сохранением в БД)")