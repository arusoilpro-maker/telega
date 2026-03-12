from yookassa import Configuration, Payment
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY

Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

async def create_yookassa_payment(amount, description, return_url, metadata=None):
    """
    Создаёт платёж в ЮKassa.
    Возвращает URL для оплаты.
    """
    payment = Payment.create({
        "amount": {
            "value": f"{amount:.2f}",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": return_url
        },
        "capture": True,
        "description": description,
        "metadata": metadata or {}
    })
    return payment.confirmation.confirmation_url, payment.id

async def check_yookassa_payment(payment_id):
    """Проверяет статус платежа"""
    payment = Payment.find_one(payment_id)
    return payment.status  # 'succeeded', 'pending', 'canceled'

# DonationAlerts (пример)
import requests

async def send_donation_alert(message, amount):
    headers = {
        "Authorization": f"Bearer {DONATION_ALERTS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "external_id": "123",
        "amount": amount,
        "currency": "RUB",
        "message": message
    }
    response = requests.post("https://www.donationalerts.com/api/v1/alerts/donation", json=data, headers=headers)
    return response.json()

from yookassa import Payment
import uuid

async def create_yookassa_payment(amount, description, return_url, metadata=None):
    payment = Payment.create({
        "amount": {
            "value": f"{amount:.2f}",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": return_url
        },
        "capture": True,
        "description": description,
        "metadata": metadata or {}
    }, uuid.uuid4())
    return payment.confirmation.confirmation_url, payment.id

async def check_yookassa_payment(payment_id):
    payment = Payment.find_one(payment_id)
    return payment.status