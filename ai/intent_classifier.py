"""
AI-powered intent classification for user messages
"""
import numpy as np
import pickle
import logging
from typing import Dict, Any, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import re
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class IntentClassifier:
    """Classify user intents from messages"""
    
    def __init__(self, model_path: str = "ai/models/intent_model.pkl"):
        self.model_path = model_path
        self.model = None
        self.vectorizer = None
        self.intents = {
            'search_master': ['найти', 'ищу', 'нужен', 'требуется', 'починить', 'ремонт'],
            'booking': ['записаться', 'заказать', 'запись', 'время', 'приехать'],
            'price': ['цена', 'сколько', 'стоимость', 'дорого', 'дешево', 'прайс'],
            'review': ['отзыв', 'оценка', 'рейтинг', 'качество', 'хороший'],
            'support': ['помощь', 'поддержка', 'проблема', 'вопрос', 'не работает'],
            'profile': ['профиль', 'аккаунт', 'данные', 'регистрация'],
            'payment': ['оплата', 'платеж', 'деньги', 'перевод', 'карта'],
            'greeting': ['привет', 'здравствуй', 'добрый', 'хай'],
            'farewell': ['пока', 'до свидания', 'спасибо', 'до связи'],
            'unknown': []
        }
        
        # Load or train model
        self.load_or_train_model()
    
    def load_or_train_model(self):
        """Load existing model or train new one"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                logger.info("Intent model loaded successfully")
            else:
                self.train_model()
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.train_model()
    
    def train_model(self):
        """Train intent classification model"""
        try:
            # Training data
            X_train = []
            y_train = []
            
            for intent, keywords in self.intents.items():
                for keyword in keywords:
                    X_train.append(keyword)
                    y_train.append(intent)
                    
                # Add variations
                if intent != 'unknown':
                    for _ in range(5):
                        X_train.append(f"нужно {np.random.choice(keywords)}")
                        X_train.append(f"хочу {np.random.choice(keywords)}")
                        y_train.extend([intent, intent])
            
            # Create pipeline
            self.model = Pipeline([
                ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=1000)),
                ('clf', MultinomialNB())
            ])
            
            # Train
            self.model.fit(X_train, y_train)
            
            # Save model
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.model, f)
            
            logger.info("Intent model trained and saved")
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
    
    def predict_intent(self, message: str) -> Tuple[str, float]:
        """Predict intent of message"""
        try:
            # Clean message
            message = self.clean_text(message)
            
            # Predict
            if self.model:
                intent = self.model.predict([message])[0]
                probabilities = self.model.predict_proba([message])[0]
                confidence = float(max(probabilities))
                
                if confidence < 0.3:
                    return 'unknown', confidence
                
                return intent, confidence
            else:
                # Rule-based fallback
                return self.rule_based_classify(message), 0.5
                
        except Exception as e:
            logger.error(f"Error predicting intent: {e}")
            return 'unknown', 0.0
    
    def rule_based_classify(self, message: str) -> str:
        """Rule-based classification fallback"""
        message = message.lower()
        
        for intent, keywords in self.intents.items():
            for keyword in keywords:
                if keyword in message:
                    return intent
        
        return 'unknown'
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove special characters
        text = re.sub(r'[^\w\s]', ' ', text)
        # Remove extra spaces
        text = ' '.join(text.split())
        # Convert to lowercase
        text = text.lower()
        return text
    
    def get_response_template(self, intent: str, context: Dict[str, Any] = None) -> str:
        """Get response template based on intent"""
        
        templates = {
            'search_master': (
                "🔍 Я помогу найти мастера!\n\n"
                "Скажите, какая услуга вам нужна и в каком районе?"
            ),
            'booking': (
                "📅 Отлично! Для записи мне нужно знать:\n"
                "• Какую услугу вы хотите?\n"
                "• Удобное время?\n"
                "• Ваш адрес?"
            ),
            'price': (
                "💰 Цены зависят от сложности работы.\n\n"
                "Вы можете посмотреть примерные цены в каталоге: /services\n"
                "Или скажите, что именно нужно починить?"
            ),
            'review': (
                "⭐ Отзывы очень важны!\n\n"
                "Вы можете:\n"
                "• Посмотреть отзывы о мастере\n"
                "• Оставить свой отзыв после заказа\n"
                "• Оценить качество работы"
            ),
            'support': (
                "💬 Чем я могу помочь?\n\n"
                "Если у вас проблема с заказом или вопросы по работе платформы - "
                "напишите подробнее, и я подключу специалиста поддержки."
            ),
            'profile': (
                "👤 Раздел профиля\n\n"
                "Вы можете:\n"
                "• Посмотреть /profile\n"
                "• Редактировать данные\n"
                "• Настроить уведомления"
            ),
            'payment': (
                "💳 Принимаем различные способы оплаты:\n"
                "• Банковские карты\n"
                "• Apple Pay / Google Pay\n"
                "• Наличные\n"
                "• Перевод на карту\n\n"
                "Все платежи защищены!"
            ),
            'greeting': (
                "👋 Здравствуйте! Чем могу помочь?\n\n"
                "Я помогу найти мастера, записаться на ремонт или ответить на вопросы."
            ),
            'farewell': (
                "👋 Всего доброго! Буду рад помочь снова!\n\n"
                "Если появятся вопросы - обращайтесь!"
            ),
            'unknown': (
                "🤔 Извините, я не совсем понял.\n\n"
                "Можете уточнить:\n"
                "• /search - найти мастера\n"
                "• /help - помощь\n"
                "• Или просто напишите подробнее о вашей проблеме"
            )
        }
        
        return templates.get(intent, templates['unknown'])