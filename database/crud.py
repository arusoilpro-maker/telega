# Добавьте в существующий crud.py:

from sqlalchemy import select, update, delete
from database.db import get_session
from database.models import Service, Master, User, Order, FoundClient

# Для услуг
async def add_service(name, description, price, category, is_product=False, stock_quantity=0):
    async with get_session() as session:
        service = Service(
            name=name,
            description=description,
            price=price,
            category=category,
            is_product=is_product,
            stock_quantity=stock_quantity
        )
        session.add(service)
        await session.commit()
        return service

async def get_services(only_services=False):
    async with get_session() as session:
        query = select(Service.id, Service.name, Service.price)
        if only_services:
            query = query.where(Service.is_product == False)
        result = await session.execute(query)
        return result.all()

async def get_service_by_id(service_id):
    async with get_session() as session:
        return await session.get(Service, service_id)

# Для мастеров
async def add_master(user_id, specialty, rating, location_lat, location_lon, experience_years, is_available):
    async with get_session() as session:
        master = Master(
            user_id=user_id,
            specialty=specialty,
            rating=rating,
            location_lat=location_lat,
            location_lon=location_lon,
            experience_years=experience_years,
            is_available=is_available
        )
        session.add(master)
        await session.commit()
        return master

async def get_masters_by_service(service_id):
    async with get_session() as session:
        result = await session.execute(
            select(Master.id, User.full_name, Master.rating)
            .join(User)
            .where(Master.is_available == True, Master.specialty == service_id)  # упрощённо
        )
        return result.all()

async def get_master_by_id(master_id):
    async with get_session() as session:
        return await session.get(Master, master_id)

async def get_masters_by_service_with_stats(service_id):
    async with get_session() as session:
        result = await session.execute(
            select(Master).where(Master.is_available == True, Master.specialty == service_id)
        )
        return result.scalars().all()

# Для найденных клиентов
async def add_found_client(source, username, user_id, metadata=None):
    async with get_session() as session:
        client = FoundClient(
            source=source,
            username=username,
            user_id=user_id,
            metadata=metadata
        )
        session.add(client)
        await session.commit()
        return client

async def get_found_client_by_user_id(user_id, source):
    async with get_session() as session:
        result = await session.execute(
            select(FoundClient).where(FoundClient.user_id == str(user_id), FoundClient.source == source)
        )
        return result.scalar_one_or_none()
    
# Добавить в модель Order поле photos (JSON) и payment_id
# В models.py:
# photos = Column(JSON, nullable=True)  # список file_id
# payment_id = Column(String, nullable=True)
# payment_status = Column(String, default="pending")

async def create_order(client_id, master_id, service_id, scheduled_time, address, total_price,
                       payment_status="pending", payment_id=None, photos=None):
    async with get_session() as session:
        order = Order(
            client_id=client_id,
            master_id=master_id,
            service_id=service_id,
            scheduled_time=scheduled_time,
            address=address,
            total_price=total_price,
            payment_status=payment_status,
            payment_id=payment_id,
            photos=photos or []
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
        return order

async def update_order_payment_id(order_id, payment_id):
    async with get_session() as session:
        await session.execute(
            update(Order).where(Order.id == order_id).values(payment_id=payment_id)
        )
        await session.commit()

async def get_order_by_id(order_id):
    async with get_session() as session:
        return await session.get(Order, order_id)
    
async def create_order(client_id, master_id, service_ids, scheduled_time, address, total_price,
                       payment_status="pending", payment_id=None, photos=None):
    async with get_session() as session:
        order = Order(
            client_id=client_id,
            master_id=master_id,
            scheduled_time=scheduled_time,
            address=address,
            total_price=total_price,
            payment_status=payment_status,
            payment_id=payment_id,
            photos=photos or []
        )
        # Добавляем услуги
        for sid in service_ids:
            service = await session.get(Service, sid)
            if service:
                order.services.append(service)
        session.add(order)
        await session.commit()
        await session.refresh(order)
        return order

# Вспомогательная функция для получения заказов клиента с услугами
async def get_client_orders(telegram_id):
    async with get_session() as session:
        user = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = user.scalar_one_or_none()
        if not user:
            return []
        result = await session.execute(
            select(Order)
            .where(Order.client_id == user.id)
            .order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()
        # Явно загружаем услуги для каждого заказа (если нужно)
        for order in orders:
            await session.refresh(order, ['services'])
        return orders
    
async def is_master_available(master_id, start_time, end_time):
    """Проверяет, свободен ли мастер в указанный интервал"""
    async with get_session() as session:
        # Ищем пересекающиеся интервалы
        stmt = select(MasterSchedule).where(
            MasterSchedule.master_id == master_id,
            MasterSchedule.start_time < end_time,
            MasterSchedule.end_time > start_time
        )
        result = await session.execute(stmt)
        return result.first() is None  # если нет записей, значит свободен

async def add_master_busy_slot(master_id, start_time, end_time, order_id=None):
    async with get_session() as session:
        slot = MasterSchedule(
            master_id=master_id,
            start_time=start_time,
            end_time=end_time,
            is_busy=True,
            order_id=order_id
        )
        session.add(slot)
        await session.commit()
        
async def update_order_status(order_id, status, completed_at=None):
    async with get_session() as session:
        stmt = update(Order).where(Order.id == order_id).values(status=status)
        if completed_at:
            stmt = stmt.values(completed_at=completed_at)
        await session.execute(stmt)
        await session.commit()

async def update_order_review(order_id, rating, text=None):
    async with get_session() as session:
        values = {"review_rating": rating}
        if text:
            values["review_text"] = text
        await session.execute(update(Order).where(Order.id == order_id).values(**values))
        await session.commit()