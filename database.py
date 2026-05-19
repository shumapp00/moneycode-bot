"""
Модуль базы данных для бота Money Code.
Хранит информацию о пользователях и платежах.
"""

import aiosqlite
import asyncio

DB_NAME = "moneycode.db"


async def init_db():
    """Создает таблицы, если их нет."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                got_free_guide INTEGER DEFAULT 0,
                bought_499 INTEGER DEFAULT 0,
                bought_999 INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                payment_id TEXT UNIQUE,
                amount REAL,
                product_type TEXT,
                status TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    print("✅ База данных готова")


async def add_user(user_id: int, username: str = None, first_name: str = None):
    """Добавляет нового пользователя или обновляет информацию."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
        """, (user_id, username, first_name))
        await db.execute("""
            UPDATE users SET username = ?, first_name = ? WHERE user_id = ?
        """, (username, first_name, user_id))
        await db.commit()


async def mark_free_guide_sent(user_id: int):
    """Отмечает, что пользователь получил бесплатный гайд."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE users SET got_free_guide = 1 WHERE user_id = ?
        """, (user_id,))
        await db.commit()


async def has_free_guide(user_id: int) -> bool:
    """Проверяет, получал ли пользователь бесплатный гайд."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT got_free_guide FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None and row[0] == 1


async def save_payment(user_id: int, payment_id: str, amount: float, product_type: str, status: str = "pending"):
    """Сохраняет информацию о платеже."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT OR REPLACE INTO payments (user_id, payment_id, amount, product_type, status)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, payment_id, amount, product_type, status))
        await db.commit()


async def mark_payment_success(payment_id: str):
    """Отмечает платеж как успешный и обновляет флаг у пользователя."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE payments SET status = 'succeeded' WHERE payment_id = ?
        """, (payment_id,))

        async with db.execute(
            "SELECT user_id, product_type FROM payments WHERE payment_id = ?",
            (payment_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                user_id, product_type = row
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
    """Возвращает информацию о платеже по его ID."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT user_id, product_type, status FROM payments WHERE payment_id = ?",
            (payment_id,)
        ) as cursor:
            return await cursor.fetchone()


async def get_all_users_count() -> int:
    """Возвращает общее количество пользователей бота."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_users_with_free_guide_not_bought():
    """Получает пользователей, которые получили бесплатный гайд, но ничего не купили."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT user_id FROM users WHERE got_free_guide = 1 AND bought_499 = 0 AND bought_999 = 0"
        ) as cursor:
            return await cursor.fetchall()


async def get_users_who_bought_499():
    """Получает пользователей, купивших методичку за 499₽."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT user_id FROM users WHERE bought_499 = 1"
        ) as cursor:
            return await cursor.fetchall()


async def get_users_who_bought_999():
    """Получает пользователей, купивших методичку за 999₽."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT user_id FROM users WHERE bought_999 = 1"
        ) as cursor:
            return await cursor.fetchall()


# Запуск при импорте
asyncio.run(init_db())