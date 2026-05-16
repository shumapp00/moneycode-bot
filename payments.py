"""
Модуль работы с ЮKassa.
Создает платежи и проверяет их статус.
"""

import uuid
from yookassa import Configuration, Payment
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY

# Настраиваем ЮKassa
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY


async def create_payment(user_id: int, amount: float, product_type: str, description: str) -> tuple[str, str]:
    """
    Создает платеж в ЮKassa.
    
    Аргументы:
        user_id: Telegram ID пользователя
        amount: сумма в рублях
        product_type: тип продукта ("499" или "999")
        description: описание товара
    
    Возвращает:
        (payment_id, payment_url) — ID платежа и ссылку на оплату
    """
    idempotency_key = str(uuid.uuid4())  # Уникальный ключ для защиты от повторов
    
    payment = Payment.create({
        "amount": {
            "value": str(amount),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/moneey_code_bot"  # Ссылка на бота
        },
        "capture": True,  # Автоматически списывать
        "description": description,
        "metadata": {
            "user_id": user_id,
            "product_type": product_type
        }
    }, idempotency_key)
    
    payment_id = payment.id
    payment_url = payment.confirmation.confirmation_url
    
    return payment_id, payment_url


async def get_payment_status(payment_id: str) -> str:
    """
    Проверяет статус платежа.
    Возвращает: 'pending', 'waiting_for_capture', 'succeeded', 'canceled'
    """
    payment = Payment.find_one(payment_id)
    return payment.status