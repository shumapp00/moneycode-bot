"""
Модуль базы данных для бота Money Code.
Хранит информацию о пользователях и платежах.
"""

import aiosqlite
import asyncio
from datetime import datetime

# Название файла базы данных
DB_NAME = "moneycode.db"


async def init_db():
    """
    Создает таблицы в базе данных, если их еще нет.
    Вызывается ОДИН раз при запуске бота.
    """
    # Подключаемся к базе (или создаем её, если файла нет)
    async with aiosqlite.connect(DB_NAME) as db:
        
        # Таблица USERS — информация о пользователях
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,       -- Telegram ID пользователя
                username TEXT,                       -- @username
                first_name TEXT,                     -- Имя в Telegram
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP,  -- Когда первый раз зашел
                got_free_guide INTEGER DEFAULT 0,   -- 0 = не получал, 1 = получал бесплатный гайд
                bought_499 INTEGER DEFAULT 0,       -- 0 = не покупал, 1 = купил методичку за 499
                bought_999 INTEGER DEFAULT 0        -- 0 = не покупал, 1 = купил методичку за 999
            )
        """)
        
        # Таблица PAYMENTS — история всех платежей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Уникальный ID записи
                user_id INTEGER,                        -- Кто оплатил (Telegram ID)
                payment_id TEXT UNIQUE,                 -- ID платежа в ЮKassa
                amount REAL,                            -- Сумма в рублях
                product_type TEXT,                      -- Тип продукта: "499" или "999"
                status TEXT,                            -- Статус: "pending", "succeeded", "canceled"
                created_at TEXT DEFAULT CURRENT_TIMESTAMP  -- Когда создан платеж
            )
        """)
        
        # Сохраняем изменения
        await db.commit()
    
    # Выводим в консоль, чтобы знать, что база готова
    print("✅ База данных готова")


# ============================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ
# ============================================================

async def add_user(user_id: int, username: str = None, first_name: str = None):
    """
    Добавляет нового пользователя в базу.
    Если пользователь уже есть — обновляет его username и имя.
    Вызывается при КАЖДОМ нажатии /start.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        # Пытаемся вставить нового пользователя
        # INSERT OR IGNORE — если такой user_id уже есть, пропускаем вставку
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
        """, (user_id, username, first_name))
        
        # Обновляем username и имя (могли измениться с прошлого захода)
        await db.execute("""
            UPDATE users SET username = ?, first_name = ? WHERE user_id = ?
        """, (username, first_name, user_id))
        
        await db.commit()


async def mark_free_guide_sent(user_id: int):
    """
    Отмечает, что пользователь получил бесплатный гайд.
    Ставит got_free_guide = 1.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE users SET got_free_guide = 1 WHERE user_id = ?
        """, (user_id,))
        await db.commit()


async def has_free_guide(user_id: int) -> bool:
    """
    Проверяет, получал ли пользователь бесплатный гайд.
    Возвращает True (получал) или False (не получал).
    """
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT got_free_guide FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            # Если пользователь есть в базе и у него got_free_guide == 1
            return row is not None and row[0] == 1


# ============================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ПЛАТЕЖАМИ
# ============================================================

async def save_payment(user_id: int, payment_id: str, amount: float, product_type: str, status: str = "pending"):
    """
    Сохраняет информацию о новом платеже в базу.
    Вызывается, когда пользователь нажал «Купить» и мы создали платеж в ЮKassa.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT OR REPLACE INTO payments (user_id, payment_id, amount, product_type, status)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, payment_id, amount, product_type, status))
        await db.commit()


async def mark_payment_success(payment_id: str):
    """
    Отмечает платеж как успешный (status = 'succeeded').
    И обновляет флаг bought_499 или bought_999 у пользователя.
    Вызывается, когда ЮKassa присылает webhook об успешной оплате.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        # Обновляем статус платежа
        await db.execute("""
            UPDATE payments SET status = 'succeeded' WHERE payment_id = ?
        """, (payment_id,))
        
        # Узнаем, кто оплатил и какой продукт
        async with db.execute(
            "SELECT user_id, product_type FROM payments WHERE payment_id = ?",
            (payment_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                user_id, product_type = row
                # Обновляем соответствующий флаг у пользователя
                if product_type == "499":
                    await db.execute(
                        "UPDATE users SET bought_499 = 1 WHERE user_id = ?",
                        (user_id,)
                    )
                elif product_type == "999":
                    await db.execute(
                        "UPDATE users SET bought_999 = 1 WHERE user_id = ?",
                        (user_id,)
                    )
        await db.commit()


async def get_payment_info(payment_id: str):
    """
    Возвращает информацию о платеже по его ID.
    Нужно для проверки статуса.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT user_id, product_type, status FROM payments WHERE payment_id = ?",
            (payment_id,)
        ) as cursor:
            return await cursor.fetchone()


async def get_all_users_count() -> int:
    """
    Возвращает общее количество пользователей бота.
    Для статистики (можешь потом вывести админу).
    """
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


# ============================================================
# ЗАПУСК ПРИ ИМПОРТЕ
# ============================================================

# Эта строчка гарантирует, что при первом импорте database.py
# таблицы автоматически создадутся
asyncio.run(init_db())