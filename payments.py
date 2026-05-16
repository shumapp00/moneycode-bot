"""
Модуль работы с ЮKassa.
Создает платежи с данными для чека (54-ФЗ).
"""

import uuid
from yookassa import Configuration, Payment
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY

# Настраиваем ЮKassa
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY


async def create_payment(user_id: int, amount: float, product_type: str, description: str):
    """
    Создает платеж в ЮKassa с данными для чека.
    Возвращает (payment_id, payment_url).
    """
    idempotency_key = str(uuid.uuid4())
    
    # Определяем название товара для чека
    if product_type == "499":
        product_name = "Методичка «Система финансовых ритуалов»"
    elif product_type == "999":
        product_name = "Методичка «Код личности: Перепрошивка»"
    else:
        product_name = "Методичка Money Code"
    
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
        "receipt": {
            "customer": {
                "email": f"user{user_id}@moneycode.ru"
            },
            "items": [
                {
                    "description": product_name,
                    "quantity": "1.00",
                    "amount": {
                        "value": str(amount),
                        "currency": "RUB"
                    },
                    "vat_code": 1,
                    "payment_mode": "full_prepayment",
                    "payment_subject": "service"
                }
            ]
        },
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