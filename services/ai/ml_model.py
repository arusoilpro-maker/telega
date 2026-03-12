import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from database.crud import get_historical_orders, get_all_masters, get_all_services
import os
import asyncio
from datetime import datetime
import logging

MODEL_PATH = "models/repair_time_model.pkl"
MODEL_METADATA_PATH = "models/model_metadata.json"

def train_model():
    """Обучает модель предсказания времени ремонта на основе исторических данных"""
    orders = get_historical_orders()  # [(service_id, master_id, duration_minutes, ...)]
    if len(orders) < 20:
        logging.warning("Недостаточно данных для обучения модели (нужно минимум 20 заказов)")
        return None

    # Преобразуем в DataFrame
    df = pd.DataFrame(orders, columns=['service_id', 'master_id', 'duration_minutes', 'client_id', 'created_at'])
    
    # Добавим признаки: день недели, час, и т.д.
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['day_of_week'] = df['created_at'].dt.dayofweek
    df['hour'] = df['created_at'].dt.hour

    # Признаки: service_id, master_id, day_of_week, hour
    feature_columns = ['service_id', 'master_id', 'day_of_week', 'hour']
    X = df[feature_columns]
    y = df['duration_minutes']

    # Разделение на обучающую и тестовую выборки
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Модель: Random Forest
    model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X_train, y_train)

    # Оценка
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    logging.info(f"MAE модели: {mae:.2f} минут")

    # Сохраняем модель и метаданные
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    # Сохраняем важность признаков и прочее
    import json
    metadata = {
        "mae": mae,
        "features": feature_columns,
        "train_date": datetime.now().isoformat(),
        "n_samples": len(orders)
    }
    with open(MODEL_METADATA_PATH, 'w') as f:
        json.dump(metadata, f)

    return model

def load_model():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None

def predict_repair_time(service_id, master_id, day_of_week=None, hour=None):
    """Предсказывает время ремонта в минутах"""
    model = load_model()
    if model is None:
        # Если модель не обучена, возвращаем среднее или дефолт
        return 60  # 1 час по умолчанию

    if day_of_week is None or hour is None:
        # Если время не указано, используем текущие
        now = datetime.now()
        day_of_week = now.weekday()
        hour = now.hour

    X = np.array([[service_id, master_id, day_of_week, hour]])
    pred = model.predict(X)[0]
    return int(max(pred, 10))  # минимум 10 минут

# Функция для автоматического переобучения (запускать по расписанию)
async def retrain_model_periodically():
    while True:
        # Переобучаем раз в неделю (можно настроить)
        await asyncio.sleep(7 * 24 * 60 * 60)  # 7 дней
        train_model()

# Рекомендация мастера на основе ML (простейший вариант)
def recommend_master(service_id, client_lat=None, client_lon=None):
    from database.crud import get_masters_by_service_with_stats
    masters = get_masters_by_service_with_stats(service_id)
    if not masters:
        return None

    # Загружаем модель (если есть)
    model = load_model()
    if model:
        # Используем предсказание времени для каждого мастера и выбираем того, у кого меньше время
        best_master = None
        best_time = float('inf')
        for master in masters:
            pred_time = predict_repair_time(service_id, master.id)
            if pred_time < best_time:
                best_time = pred_time
                best_master = master
        return best_master.id
    else:
        # Иначе выбираем по рейтингу
        return max(masters, key=lambda m: m.rating).id