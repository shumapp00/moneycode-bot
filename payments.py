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


async def create_payment(user_id: int, amount: float, product_type: str, description: str):
    """
    Создает платеж в ЮKassa.
    Возвращает (payment_id, payment_url).
    """
    idempotency_key = str(uuid.uuid4())

    payment = Payment.create({
        "amount": {
            "value": str(amount),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/moneey_code_bot"
        },
        "capture": True,
        "description": description,
        "metadata": {
            "user_id": user_id,
            "product_type": product_type
        }
    }, idempotency_key)

    return payment.id, payment.confirmation.confirmation_url


async def get_payment_status(payment_id: str):
    """Проверяет статус платежа."""
    payment = Payment.find_one(payment_id)
    return payment.status