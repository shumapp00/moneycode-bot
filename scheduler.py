"""
Модуль авторассылки прогрева и сбора обратной связи.
Отправляет сообщения с картинками из папки images.
"""

import asyncio
import logging
import os

from aiogram.types import FSInputFile

from bot import bot
from database import (
    get_users_with_free_guide_not_bought,
    get_users_who_bought_499,
    get_users_who_bought_999,
)

logger = logging.getLogger(__name__)

IMAGES_DIR = "images"


def get_image(image_name):
    path = os.path.join(IMAGES_DIR, image_name)
    if os.path.exists(path):
        return FSInputFile(path)
    return None


WARMUP_DATA = [
    {
        "image": "warmup_day1.jpeg",
        "text": "🎁 <b>Гайд у тебя. Не откладывай его в «потом».</b>\n\n15 минут сегодня = понимание, что именно блокирует твои деньги. Это не марафон желаний. Это диагностика. Как МРТ для кошелька.\n\nПройди тест. Найди свой архетип. А завтра я расскажу, что с ним делать дальше."
    },
    {
        "image": "warmup_day2.jpeg",
        "text": "👋 <b>Это снова я. Твой «менеджер по перепрошивке».</b>\n\nТы уже знаешь свой архетип? Самозванец, Спасатель, Аскет или Фаталист?\n\nВот в чём прикол: узнать — мало. Это как поставить диагноз и не лечиться. Большинство на этом и останавливаются.\n\nА дальше нужна <b>СИСТЕМА</b>. Конкретные ритуалы. Каждый день.\n\nЗавтра расскажу про 3 счёта — это база, которая убирает хаос из кошелька за один вечер."
    },
    {
        "image": "warmup_day3.jpeg",
        "text": "🏗 <b>Архитектура безопасности. Звучит скучно. Работает — зверски.</b>\n\nУ тебя есть 3 счёта? Бункер, Командный центр, Шлюз удовольствий?\n\nСкорее всего, нет. Скорее всего, все деньги в одной куче. Поэтому тревога.\n\nЯ расписал всю архитектуру в методичке «Система финансовых ритуалов». Это 30-дневный протокол. 10 ритуалов в день.\n\nЗавтра расскажу про главный предохранитель от срывов. Про Шлюз."
    },
    {
        "image": "warmup_day4.jpeg",
        "text": "🎈 <b>Шлюз удовольствий. Это 10% дохода на любую хрень. Без вины. Без отчётов.</b>\n\nЗвучит безответственно? На самом деле — это единственное, что спасает от срывов.\n\nКогда ты запрещаешь себе ВСЁ, психика взрывается.\n\nВ методичке «Система финансовых ритуалов» я даю не только теорию, но и чек-лист на 30 дней.\n\nЗавтра — последнее сообщение. О деньгах."
    },
    {
        "image": "warmup_day5.jpeg",
        "text": "💳 <b>Сколько ты уже потратил(а) на импульсные покупки за этот месяц?</b>\n\nДоставка еды, такси, курс, который не прошёл(ла).\n\nА теперь представь: ты мог(ла) бы вообще не париться о деньгах. Не потому что их «много». А потому что есть <b>СИСТЕМА</b>.\n\nОна стоит 499₽ — это меньше одного похода в суши. Просто нажми кнопку «📚 Купить методички» внизу."
    },
]

FOLLOWUP_IMAGE = "warmup_followup.jpeg"
FOLLOWUP_TEXT = (
    "🤔 <b>Слушай, ты проходил(а) бесплатный гайд. Значит, тема денег для тебя важна.</b> Но ты не пошёл(ла) дальше.\n\n"
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


async def send_warmup_messages():
    for i, data in enumerate(WARMUP_DATA):
        await asyncio.sleep(i * 86400)
        users = await get_users_with_free_guide_not_bought()
        for user in users:
            user_id = user[0]
            photo = get_image(data["image"])
            try:
                if photo:
                    await bot.send_photo(chat_id=user_id, photo=photo, caption=data["text"])
                else:
                    await bot.send_message(user_id, data["text"])
            except Exception as e:
                logger.error(f"Ошибка отправки прогрева пользователю {user_id}: {e}")

    await asyncio.sleep(2 * 86400)
    users = await get_users_with_free_guide_not_bought()
    for user in users:
        user_id = user[0]
        photo = get_image(FOLLOWUP_IMAGE)
        try:
            if photo:
                await bot.send_photo(chat_id=user_id, photo=photo, caption=FOLLOWUP_TEXT)
            else:
                await bot.send_message(user_id, FOLLOWUP_TEXT)
        except Exception as e:
            logger.error(f"Ошибка отправки фоллоу-апа пользователю {user_id}: {e}")


async def send_feedback_requests():
    await asyncio.sleep(86400)
    for user in await get_users_who_bought_499():
        try:
            await bot.send_message(user[0], FEEDBACK_499)
        except:
            pass
    for user in await get_users_who_bought_999():
        try:
            await bot.send_message(user[0], FEEDBACK_999)
        except:
            pass


async def start_scheduler():
    asyncio.create_task(send_warmup_messages())
    asyncio.create_task(send_feedback_requests())
    logger.info("Планировщик авторассылки запущен")