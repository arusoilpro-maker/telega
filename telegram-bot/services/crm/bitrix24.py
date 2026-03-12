import requests
import logging
from typing import Dict, Any, Optional
from urllib.parse import urljoin
from config import BITRIX24_WEBHOOK_URL

logger = logging.getLogger(__name__)

class Bitrix24Client:
    """Клиент для работы с Bitrix24 REST API через входящий вебхук"""
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or BITRIX24_WEBHOOK_URL
        if not self.webhook_url:
            raise ValueError("Не указан webhook_url для Bitrix24")

    def _call_method(self, method: str, params: Dict = None) -> Optional[Dict]:
        """Вызывает метод REST API"""
        url = urljoin(self.webhook_url, method)
        try:
            response = requests.post(url, json=params or {})
            response.raise_for_status()
            result = response.json()
            if 'error' in result:
                logger.error(f"Ошибка Bitrix24 API: {result['error_description']} (код {result['error']})")
                return None
            return result.get('result')
        except Exception as e:
            logger.error(f"Ошибка при вызове {method}: {e}")
            return None

    def create_lead(self, order_data: Dict[str, Any]) -> Optional[int]:
        """
        Создаёт лид в Битрикс24.
        order_data:
            - TITLE: название лида
            - NAME: имя клиента
            - PHONE: телефон
            - COMMENTS: описание
            - SOURCE_ID: источник (опционально)
            - ASSIGNED_BY_ID: ответственный (опционально)
        """
        fields = {
            'TITLE': order_data.get('TITLE', 'Новый заказ'),
            'NAME': order_data.get('NAME', ''),
            'PHONE': [{'VALUE': order_data.get('PHONE', ''), 'VALUE_TYPE': 'WORK'}],
            'COMMENTS': order_data.get('COMMENTS', ''),
            'SOURCE_ID': order_data.get('SOURCE_ID', 'WEB'),
        }
        if 'ASSIGNED_BY_ID' in order_data:
            fields['ASSIGNED_BY_ID'] = order_data['ASSIGNED_BY_ID']

        result = self._call_method('crm.lead.add', {'fields': fields})
        if result:
            return result  # ID лида
        return None

    def update_lead(self, lead_id: int, fields: Dict) -> bool:
        """Обновляет поля лида"""
        params = {
            'id': lead_id,
            'fields': fields
        }
        result = self._call_method('crm.lead.update', params)
        return result is not None

    def get_lead(self, lead_id: int) -> Optional[Dict]:
        """Получает информацию о лиде"""
        result = self._call_method('crm.lead.get', {'id': lead_id})
        return result

    def create_deal(self, order_data: Dict[str, Any]) -> Optional[int]:
        """Создаёт сделку в Битрикс24 (если используется воронка продаж)"""
        fields = {
            'TITLE': order_data.get('TITLE', 'Новая сделка'),
            'OPPORTUNITY': order_data.get('OPPORTUNITY', 0),
            'CURRENCY_ID': order_data.get('CURRENCY_ID', 'RUB'),
            'CONTACT_ID': order_data.get('CONTACT_ID'),  # ID контакта, если есть
            'COMMENTS': order_data.get('COMMENTS', ''),
            'STAGE_ID': order_data.get('STAGE_ID', 'NEW'),
        }
        result = self._call_method('crm.deal.add', {'fields': fields})
        return result

    def add_comment(self, entity_type: str, entity_id: int, comment: str) -> bool:
        """Добавляет комментарий к лиду или сделке"""
        # В Битрикс24 комментарии добавляются через crm.timeline.comment.add
        params = {
            'fields': {
                'ENTITY_ID': entity_id,
                'ENTITY_TYPE': entity_type.upper(),  # 'LEAD' или 'DEAL'
                'COMMENT': comment
            }
        }
        result = self._call_method('crm.timeline.comment.add', params)
        return result is not None