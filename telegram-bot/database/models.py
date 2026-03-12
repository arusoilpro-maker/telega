from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    full_name = Column(String)
    phone = Column(String)
    role = Column(String, default="client")  # client, master, admin
    created_at = Column(DateTime, default=datetime.utcnow)

class Master(Base):
    __tablename__ = "masters"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User")
    specialty = Column(String)  # электрик, сантехник и т.д.
    rating = Column(Float, default=0.0)
    location_lat = Column(Float)   # координаты для карты
    location_lon = Column(Float)
    is_available = Column(Boolean, default=True)

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(Text)
    price = Column(Float)
    category = Column(String)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("users.id"))
    master_id = Column(Integer, ForeignKey("masters.id"), nullable=True)
    service_id = Column(Integer, ForeignKey("services.id"))
    status = Column(String, default="new")  # new, assigned, done, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_time = Column(DateTime)   # запланированное время
    address = Column(String)
    total_price = Column(Float)
    
    class Order(Base):
        # ... существующие поля
    amocrm_lead_id = Column(Integer, nullable=True)
    bitrix24_lead_id = Column(Integer, nullable=True)
    
    from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    full_name = Column(String)
    phone = Column(String)
    role = Column(String, default="client")  # client, master, admin
    created_at = Column(DateTime, default=datetime.utcnow)

class Master(Base):
    __tablename__ = "masters"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User")
    specialty = Column(String)  # электрик, сантехник и т.д.
    rating = Column(Float, default=0.0)
    location_lat = Column(Float)   # координаты для карты
    location_lon = Column(Float)
    is_available = Column(Boolean, default=True)
    # Дополнительные поля для загрузки мастеров
    experience_years = Column(Integer, default=0)
    photo_url = Column(String, nullable=True)
    documents_verified = Column(Boolean, default=False)

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    price = Column(Float)
    category = Column(String)
    # Для товаров (если есть)
    is_product = Column(Boolean, default=False)  # если это товар, а не услуга
    stock_quantity = Column(Integer, default=0)  # остаток на складе
    photo_url = Column(String, nullable=True)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("users.id"))
    master_id = Column(Integer, ForeignKey("masters.id"), nullable=True)
    service_id = Column(Integer, ForeignKey("services.id"))
    status = Column(String, default="new")  # new, assigned, done, cancelled, paid
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_time = Column(DateTime)   # запланированное время
    address = Column(String)
    total_price = Column(Float)
    # Поля для платежей
    payment_status = Column(String, default="pending")  # pending, paid, failed
    payment_id = Column(String, nullable=True)
    # Поля для ML (фактическое время выполнения)
    duration_minutes = Column(Integer, nullable=True)  # сколько минут занял ремонт
    completed_at = Column(DateTime, nullable=True)

# Модель для хранения данных о клиентах, найденных автоматически
class FoundClient(Base):
    __tablename__ = "found_clients"
    id = Column(Integer, primary_key=True)
    source = Column(String)  # telegram, instagram
    username = Column(String)
    user_id = Column(String, unique=True)  # telegram_id или instagram_id
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_contacted = Column(DateTime, nullable=True)
    status = Column(String, default="new")  # new, contacted, converted
    metadata = Column(JSON, nullable=True)  # дополнительная информация
    
    # Таблица связи заказа и услуг (многие ко многим)
order_services = Table(
    'order_services',
    Base.metadata,
    Column('order_id', Integer, ForeignKey('orders.id'), primary_key=True),
    Column('service_id', Integer, ForeignKey('services.id'), primary_key=True),
    Column('quantity', Integer, default=1)  # если услуга может повторяться
)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("users.id"))
    master_id = Column(Integer, ForeignKey("masters.id"), nullable=True)
    # Убираем service_id, заменяем на relationship
    services = relationship("Service", secondary=order_services, lazy="selectin")
    status = Column(String, default="new")  # new, assigned, done, cancelled, paid
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_time = Column(DateTime)
    address = Column(String)
    total_price = Column(Float)
    payment_status = Column(String, default="pending")
    payment_id = Column(String, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    photos = Column(JSON, nullable=True)
    # Добавляем поле для отзыва
    review_text = Column(Text, nullable=True)
    review_rating = Column(Integer, nullable=True)  # 1-5
    
class MasterSchedule(Base):
    __tablename__ = "master_schedule"
    id = Column(Integer, primary_key=True)
    master_id = Column(Integer, ForeignKey("masters.id"))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_busy = Column(Boolean, default=True)  # занят (заказ) или заблокировано (личное)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)