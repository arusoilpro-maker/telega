"""
Модуль планировщика маркетинговых воронок.
Отвечает за автоматические рассылки по сегментам пользователей на разных стадиях воронки.
"""
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from database.models import User, Funnel, FunnelStep, UserFunnelStep, Order, Notification
from services.notification_service import NotificationService
from services.analytics_service import AnalyticsService
from core.logging import logger
from core.config import config

class FunnelScheduler:
    """
    Планировщик маркетинговых воронок.
    Позволяет создавать последовательности сообщений для разных сегментов пользователей.
    """
    
    def __init__(self, db_session_factory, notification_service: NotificationService):
        self.scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)
        self.db_session_factory = db_session_factory
        self.notification_service = notification_service
        self.analytics = AnalyticsService(db_session_factory)
        
    async def start(self):
        """Запуск планировщика и периодических задач."""
        # Каждые 15 минут проверяем, кому отправить следующие шаги воронок
        self.scheduler.add_job(
            self.process_funnels,
            trigger=IntervalTrigger(minutes=15),
            id='process_funnels',
            replace_existing=True
        )
        
        # Раз в сутки анализируем эффективность воронок
        self.scheduler.add_job(
            self.analyze_funnel_performance,
            trigger=IntervalTrigger(hours=24),
            id='analyze_funnel_performance',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Funnel scheduler started")
    
    async def stop(self):
        self.scheduler.shutdown()
        logger.info("Funnel scheduler stopped")
    
    async def process_funnels(self):
        """
        Основной метод: для каждого активного пользователя проверяет,
        нужно ли отправить следующий шаг воронки.
        """
        async with self.db_session_factory() as session:
            # Получаем все активные воронки
            funnels = await self._get_active_funnels(session)
            
            for funnel in funnels:
                await self._process_funnel(session, funnel)
    
    async def _get_active_funnels(self, session: AsyncSession) -> List[Funnel]:
        """Возвращает список активных воронок."""
        stmt = select(Funnel).where(Funnel.is_active == True)
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def _process_funnel(self, session: AsyncSession, funnel: Funnel):
        """Обрабатывает одну воронку: ищет пользователей для следующего шага."""
        # Получаем шаги воронки, отсортированные по порядку
        steps = sorted(funnel.steps, key=lambda s: s.step_order)
        if not steps:
            return
        
        # Для каждого шага, кроме первого, проверяем, кто прошёл предыдущий шаг и ожидает текущий
        for i, step in enumerate(steps):
            # Пропускаем первый шаг – он запускается по триггеру (например, регистрация)
            if i == 0:
                continue
            
            prev_step = steps[i-1]
            
            # Находим пользователей, которые выполнили предыдущий шаг, но ещё не начинали текущий
            # и у которых прошло достаточно времени с момента выполнения prev_step
            subquery = select(UserFunnelStep.user_id).where(
                and_(
                    UserFunnelStep.funnel_id == funnel.id,
                    UserFunnelStep.step_id == prev_step.id,
                    UserFunnelStep.completed_at.isnot(None),
                    ~UserFunnelStep.user_id.in_(
                        select(UserFunnelStep.user_id).where(
                            UserFunnelStep.funnel_id == funnel.id,
                            UserFunnelStep.step_id == step.id
                        )
                    )
                )
            ).subquery()
            
            # Учитываем задержку step.delay_hours
            now = datetime.now()
            time_threshold = now - timedelta(hours=step.delay_hours)
            
            stmt = select(User).where(
                and_(
                    User.id.in_(subquery),
                    # Убедимся, что предыдущий шаг был завершён достаточно давно
                    UserFunnelStep.completed_at <= time_threshold
                )
            ).join(UserFunnelStep, User.id == UserFunnelStep.user_id).where(
                UserFunnelStep.step_id == prev_step.id
            )
            
            result = await session.execute(stmt)
            users = result.scalars().all()
            
            for user in users:
                await self._send_funnel_step(user.id, funnel.id, step.id, step)
    
    async def _send_funnel_step(self, user_id: int, funnel_id: int, step_id: int, step: FunnelStep):
        """Отправляет сообщение шага воронки пользователю и фиксирует начало шага."""
        # Отправляем через notification_service
        success = await self.notification_service.send_to_user(
            user_id=user_id,
            message=step.message_text,
            channel='telegram',  # или другой канал
            funnel_step_id=step_id
        )
        
        if success:
            async with self.db_session_factory() as session:
                # Записываем, что шаг начат
                user_step = UserFunnelStep(
                    user_id=user_id,
                    funnel_id=funnel_id,
                    step_id=step_id,
                    started_at=datetime.now(),
                    status='sent'
                )
                session.add(user_step)
                await session.commit()
                
                # Планируем проверку нажатия/конверсии через некоторое время (если step.track_conversion)
                if step.track_conversion:
                    await self._schedule_conversion_check(user_id, funnel_id, step_id, step.conversion_window_hours)
    
    async def _schedule_conversion_check(self, user_id: int, funnel_id: int, step_id: int, window_hours: int):
        """Планирует задачу для проверки конверсии шага (например, совершил ли пользователь целевое действие)."""
        run_date = datetime.now() + timedelta(hours=window_hours)
        job_id = f"conv_check_{funnel_id}_{step_id}_{user_id}"
        self.scheduler.add_job(
            self.check_conversion,
            trigger=DateTrigger(run_date=run_date),
            args=[user_id, funnel_id, step_id],
            id=job_id,
            replace_existing=False
        )
    
    async def check_conversion(self, user_id: int, funnel_id: int, step_id: int):
        """Проверяет, выполнил ли пользователь целевое действие после получения шага."""
        async with self.db_session_factory() as session:
            # Получаем шаг, чтобы узнать, какое действие считать конверсией (например, оформление заказа)
            step = await session.get(FunnelStep, step_id)
            if not step:
                return
            
            # Проверяем по целевым событиям (например, создан заказ после получения сообщения)
            # Здесь можно определить логику в зависимости от step.conversion_event
            converted = False
            if step.conversion_event == 'order_created':
                # Проверяем, создал ли пользователь заказ после времени отправки шага
                # Находим UserFunnelStep
                ufs = await session.execute(
                    select(UserFunnelStep).where(
                        UserFunnelStep.user_id == user_id,
                        UserFunnelStep.funnel_id == funnel_id,
                        UserFunnelStep.step_id == step_id
                    )
                )
                ufs = ufs.scalar_one_or_none()
                if ufs:
                    # Проверяем заказы после started_at
                    orders_after = await session.execute(
                        select(Order).where(
                            Order.client_id == user_id,
                            Order.created_at >= ufs.started_at
                        )
                    )
                    converted = orders_after.first() is not None
            
            # Обновляем статус шага
            if ufs:
                ufs.converted = converted
                if converted:
                    ufs.completed_at = datetime.now()
                    ufs.status = 'converted'
                else:
                    ufs.status = 'no_conversion'
                await session.commit()
                
                # Если есть следующий шаг и конверсия не произошла, возможно, не отправляем дальше?
                # Обычно воронка продолжается независимо, но можно настроить.
    
    async def trigger_funnel_for_user(self, user_id: int, funnel_id: int, trigger_event: str = 'registration'):
        """
        Запускает воронку для конкретного пользователя по событию (например, регистрация).
        Отправляет первый шаг и планирует последующие.
        """
        async with self.db_session_factory() as session:
            funnel = await session.get(Funnel, funnel_id)
            if not funnel or not funnel.is_active:
                return
            
            # Получаем первый шаг
            first_step = await session.execute(
                select(FunnelStep).where(
                    FunnelStep.funnel_id == funnel_id,
                    FunnelStep.step_order == 1
                )
            )
            first_step = first_step.scalar_one_or_none()
            if not first_step:
                return
            
            # Отправляем первый шаг
            await self._send_funnel_step(user_id, funnel_id, first_step.id, first_step)
            
            # Логируем запуск воронки
            logger.info(f"Funnel {funnel_id} triggered for user {user_id} by event {trigger_event}")
    
    async def add_user_to_funnel(self, user_id: int, funnel_id: int):
        """Добавляет пользователя в воронку (без отправки первого шага, если он уже был отправлен)."""
        async with self.db_session_factory() as session:
            # Проверяем, не был ли пользователь уже добавлен
            existing = await session.execute(
                select(UserFunnelStep).where(
                    UserFunnelStep.user_id == user_id,
                    UserFunnelStep.funnel_id == funnel_id
                )
            )
            if not existing.first():
                # Создаём запись, но без шага
                # Обычно первый шаг отправляется при триггере
                pass
    
    async def analyze_funnel_performance(self):
        """Анализирует эффективность воронок и обновляет статистику."""
        async with self.db_session_factory() as session:
            funnels = await self._get_active_funnels(session)
            for funnel in funnels:
                # Считаем общее количество пользователей, вошедших в воронку
                total_users = await session.scalar(
                    select(func.count(func.distinct(UserFunnelStep.user_id))).where(
                        UserFunnelStep.funnel_id == funnel.id
                    )
                )
                
                # Считаем конверсию на каждом шаге
                steps = sorted(funnel.steps, key=lambda s: s.step_order)
                step_stats = []
                for i, step in enumerate(steps):
                    step_users = await session.scalar(
                        select(func.count(UserFunnelStep.user_id)).where(
                            UserFunnelStep.funnel_id == funnel.id,
                            UserFunnelStep.step_id == step.id
                        )
                    )
                    converted = await session.scalar(
                        select(func.count(UserFunnelStep.user_id)).where(
                            UserFunnelStep.funnel_id == funnel.id,
                            UserFunnelStep.step_id == step.id,
                            UserFunnelStep.converted == True
                        )
                    )
                    step_stats.append({
                        'step': step.id,
                        'name': step.name,
                        'users': step_users,
                        'converted': converted,
                        'conversion_rate': (converted / step_users * 100) if step_users else 0
                    })
                
                # Сохраняем в аналитику
                await self.analytics.save_funnel_stats(funnel.id, total_users, step_stats)
                
                # Корректируем задержки на основе конверсии (пример AI-оптимизации)
                if funnel.ai_optimization_enabled:
                    await self._optimize_funnel_delays(funnel, step_stats)
    
    async def _optimize_funnel_delays(self, funnel: Funnel, step_stats: List[Dict]):
        """
        Простая оптимизация задержек: если конверсия низкая, увеличиваем интервал,
        если высокая – уменьшаем.
        """
        async with self.db_session_factory() as session:
            steps = await session.execute(
                select(FunnelStep).where(FunnelStep.funnel_id == funnel.id).order_by(FunnelStep.step_order)
            )
            steps = steps.scalars().all()
            for i, step in enumerate(steps):
                if i == 0:
                    continue  # первый шаг не оптимизируем
                stat = step_stats[i]
                current_delay = step.delay_hours
                target_conversion = step.target_conversion_rate
                actual = stat['conversion_rate']
                if actual < target_conversion * 0.8:
                    # конверсия низкая – увеличиваем задержку
                    new_delay = min(current_delay * 1.2, 168)  # не больше недели
                elif actual > target_conversion * 1.2:
                    # конверсия высокая – уменьшаем
                    new_delay = max(current_delay * 0.8, 1)
                else:
                    continue
                
                step.delay_hours = new_delay
                session.add(step)
            await session.commit()