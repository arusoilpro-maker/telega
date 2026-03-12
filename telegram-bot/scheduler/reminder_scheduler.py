"""
Модуль планировщика напоминаний для сервиса онлайн-записи.
Отвечает за отправку уведомлений о предстоящих заказах клиентам и мастерам.
Использует APScheduler для фоновых задач.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.base import JobLookupError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from database.models import Order, User, MasterProfile, Notification
from services.notification_service import NotificationService
from services.order_service import OrderService
from core.logging import logger
from core.config import config

class ReminderScheduler:
    """
    Планировщик напоминаний о заказах.
    """
    
    def __init__(self, db_session_factory, notification_service: NotificationService):
        self.scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)
        self.db_session_factory = db_session_factory
        self.notification_service = notification_service
        self.order_service = OrderService(db_session_factory, notification_service)
        
    async def start(self):
        """Запуск планировщика и добавление периодических задач."""
        # Каждые 10 минут проверяем приближающиеся заказы
        self.scheduler.add_job(
            self.check_upcoming_orders,
            trigger=IntervalTrigger(minutes=10),
            id='check_upcoming_orders',
            replace_existing=True
        )
        
        # Каждый час чистим старые задачи
        self.scheduler.add_job(
            self.cleanup_old_jobs,
            trigger=IntervalTrigger(hours=1),
            id='cleanup_old_jobs',
            replace_existing=True
        )
        
        # При старте сразу проверяем на ближайшие напоминания
        await self.check_upcoming_orders()
        
        self.scheduler.start()
        logger.info("Reminder scheduler started")
    
    async def stop(self):
        """Остановка планировщика."""
        self.scheduler.shutdown()
        logger.info("Reminder scheduler stopped")
    
    async def check_upcoming_orders(self):
        """
        Проверяет все предстоящие заказы и планирует напоминания,
        если они ещё не запланированы.
        """
        async with self.db_session_factory() as session:
            # Ищем заказы со статусом confirmed или in_progress, запланированные на ближайшие 48 часов
            now = datetime.now()
            time_48h = now + timedelta(hours=48)
            
            stmt = select(Order).where(
                and_(
                    Order.status.in_(['confirmed', 'in_progress']),
                    Order.scheduled_datetime >= now,
                    Order.scheduled_datetime <= time_48h
                )
            )
            result = await session.execute(stmt)
            orders = result.scalars().all()
            
            for order in orders:
                await self.schedule_reminders_for_order(order.id, order.scheduled_datetime)
    
    async def schedule_reminders_for_order(self, order_id: int, scheduled_datetime: datetime):
        """
        Планирует напоминания для конкретного заказа (за 24 часа и за 2 часа).
        Если напоминания уже существуют, не дублирует.
        """
        # За 24 часа
        remind_24h = scheduled_datetime - timedelta(hours=24)
        if remind_24h > datetime.now():
            job_id = f"remind_24h_order_{order_id}"
            try:
                self.scheduler.get_job(job_id)
                logger.debug(f"Job {job_id} already exists")
            except JobLookupError:
                self.scheduler.add_job(
                    self.send_reminder,
                    trigger=DateTrigger(run_date=remind_24h),
                    args=[order_id, '24h'],
                    id=job_id,
                    replace_existing=False
                )
                logger.info(f"Scheduled 24h reminder for order {order_id}")
        
        # За 2 часа
        remind_2h = scheduled_datetime - timedelta(hours=2)
        if remind_2h > datetime.now():
            job_id = f"remind_2h_order_{order_id}"
            try:
                self.scheduler.get_job(job_id)
            except JobLookupError:
                self.scheduler.add_job(
                    self.send_reminder,
                    trigger=DateTrigger(run_date=remind_2h),
                    args=[order_id, '2h'],
                    id=job_id,
                    replace_existing=False
                )
                logger.info(f"Scheduled 2h reminder for order {order_id}")
    
    async def send_reminder(self, order_id: int, reminder_type: str):
        """
        Отправляет напоминание клиенту и мастеру.
        reminder_type: '24h' или '2h'
        """
        logger.info(f"Sending {reminder_type} reminder for order {order_id}")
        async with self.db_session_factory() as session:
            # Получаем заказ с пользователями
            stmt = select(Order).where(Order.id == order_id)
            result = await session.execute(stmt)
            order = result.scalar_one_or_none()
            if not order:
                logger.error(f"Order {order_id} not found for reminder")
                return
            
            # Проверяем, не отменён ли заказ
            if order.status in ['cancelled', 'completed']:
                logger.info(f"Order {order_id} status {order.status}, skipping reminder")
                return
            
            # Формируем текст в зависимости от типа
            if reminder_type == '24h':
                client_text = (
                    f"🔔 Напоминаем, что завтра в {order.scheduled_datetime.strftime('%H:%M')} "
                    f"у вас запланирован визит мастера {order.master.name}. "
                    f"Пожалуйста, подготовьте доступ к оборудованию."
                )
                master_text = (
                    f"🔔 Напоминание: завтра в {order.scheduled_datetime.strftime('%H:%M')} "
                    f"у вас заказ №{order.id} у клиента {order.client.full_name}. "
                    f"Адрес: {order.address}"
                )
            else:  # 2h
                client_text = (
                    f"⏰ Через 2 часа, в {order.scheduled_datetime.strftime('%H:%M')}, "
                    f"приедет мастер {order.master.name}. Будьте на связи!"
                )
                master_text = (
                    f"⏰ Через 2 часа у вас заказ №{order.id} по адресу {order.address}. "
                    f"Клиент: {order.client.full_name}, тел: {order.client.phone}"
                )
            
            # Отправляем клиенту
            await self.notification_service.send_to_user(
                user_id=order.client_id,
                message=client_text,
                channel='telegram'  # или другой канал по настройкам пользователя
            )
            
            # Отправляем мастеру
            await self.notification_service.send_to_user(
                user_id=order.master.user_id,
                message=master_text,
                channel='telegram'
            )
            
            # Логируем в БД (опционально)
            await self._log_notification(order.client_id, order_id, 'reminder', client_text)
            await self._log_notification(order.master.user_id, order_id, 'reminder', master_text)
    
    async def schedule_order_confirmation_reminder(self, order_id: int):
        """
        Если заказ не подтверждён мастером в течение N часов, отправить напоминание мастеру.
        """
        async with self.db_session_factory() as session:
            order = await session.get(Order, order_id)
            if not order:
                return
            # Если заказ в статусе 'pending' уже 2 часа
            remind_time = order.created_at + timedelta(hours=2)
            if remind_time > datetime.now():
                job_id = f"confirm_remind_{order_id}"
                self.scheduler.add_job(
                    self.send_confirmation_reminder,
                    trigger=DateTrigger(run_date=remind_time),
                    args=[order_id],
                    id=job_id,
                    replace_existing=False
                )
    
    async def send_confirmation_reminder(self, order_id: int):
        """Напоминание мастеру о неподтверждённом заказе."""
        async with self.db_session_factory() as session:
            order = await session.get(Order, order_id)
            if order and order.status == 'pending':
                master_text = (
                    f"⏳ У вас есть неподтверждённый заказ №{order.id} "
                    f"от {order.client.full_name} на {order.scheduled_datetime.strftime('%d.%m.%Y %H:%M')}. "
                    f"Пожалуйста, подтвердите или отклоните его."
                )
                await self.notification_service.send_to_user(
                    user_id=order.master.user_id,
                    message=master_text,
                    channel='telegram'
                )
    
    async def cleanup_old_jobs(self):
        """Удаляет задачи для заказов, которые уже прошли или отменены."""
        async with self.db_session_factory() as session:
            # Находим все запланированные job_id (они хранятся в БД или в памяти планировщика)
            # В данном примере мы просто удаляем задачи для заказов, которые завершены.
            # Для более точного подхода нужно хранить связь job_id - order_id.
            # Здесь упрощённо: получаем все jobs и проверяем соответствующие заказы.
            jobs = self.scheduler.get_jobs()
            for job in jobs:
                if job.id.startswith(('remind_24h_order_', 'remind_2h_order_')):
                    order_id = int(job.id.split('_')[-1])
                    order = await session.get(Order, order_id)
                    if not order or order.status in ['completed', 'cancelled']:
                        job.remove()
                        logger.info(f"Removed obsolete job {job.id}")
    
    async def _log_notification(self, user_id: int, order_id: int, notif_type: str, message: str):
        """Сохраняет запись об отправленном уведомлении в БД (опционально)."""
        async with self.db_session_factory() as session:
            notif = Notification(
                user_id=user_id,
                order_id=order_id,
                type=notif_type,
                message=message,
                status='sent'
            )
            session.add(notif)
            await session.commit()