async def get_plan_fact_report(period: str):
    # Здесь будет логика сбора данных из БД и сравнения с плановыми показателями
    return {"plan": 100, "fact": 85, "difference": -15}

async def get_cash_report(period: str):
    # Сумма всех оплаченных заказов
    return {"total": 150000, "orders_count": 30}