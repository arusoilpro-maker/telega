import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from config import (
    AMOCRM_SUBDOMAIN,
    AMOCRM_ACCESS_TOKEN,
    AMOCRM_CLIENT_ID,
    AMOCRM_CLIENT_SECRET,
    AMOCRM_REDIRECT_URI,
    AMOCRM_REFRESH_TOKEN
)

logger = logging.getLogger(__name__)

class AmoCrmClient:
    """Клиент для работы с amoCRM API"""
    BASE_URL = "https://{subdomain}.amocrm.ru/api/v4"

    def __init__(self):
        self.subdomain = AMOCRM_SUBDOMAIN
        self.access_token = AMOCRM_ACCESS_TOKEN
        self.refresh_token = AMOCRM_REFRESH_TOKEN
        self.client_id = AMOCRM_CLIENT_ID
        self.client_secret = AMOCRM_CLIENT_SECRET
        self.redirect_uri = AMOCRM_REDIRECT_URI
        self._session = requests.Session()
        self._session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        })

    def _make_url(self, path: str) -> str:
        return self.BASE_URL.format(subdomain=self.subdomain) + path

    def refresh_access_token(self) -> bool:
        """Обновление access_token по refresh_token"""
        if not all([self.client_id, self.client_secret, self.refresh_token, self.redirect_uri]):
            logger.error("Не хватает данных для обновления токена amoCRM")
            return False
        url = f"https://{self.subdomain}.amocrm.ru/oauth2/access_token"
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'redirect_uri': self.redirect_uri
        }
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.refresh_token = token_data.get('refresh_token', self.refresh_token)
            # Обновляем заголовок авторизации
            self._session.headers.update({'Authorization': f'Bearer {self.access_token}'})
            logger.info("Токен amoCRM успешно обновлён")
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления токена amoCRM: {e}")
            return False

    def _request(self, method: str, path: str, **kwargs):
        """Выполнить запрос с автоматическим обновлением токена при 401"""
        url = self._make_url(path)
        for attempt in range(2):
            try:
                response = self._session.request(method, url, **kwargs)
                if response.status_code == 401 and attempt == 0:
                    # Попробуем обновить токен и повторить
                    if self.refresh_access_token():
                        continue
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"Ошибка запроса к amoCRM: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Ответ: {e.response.text}")
                raise
        return None

    def create_lead(self, order_data: Dict[str, Any]) -> Optional[int]:
        """
        Создаёт сделку в amoCRM по данным заказа.
        Возвращает ID сделки или None.
        order_data должен содержать:
            - name: название сделки (например, "Заказ #123")
            - price: сумма
            - client_name: имя клиента
            - client_phone: телефон
            - description: описание (услуга, адрес, время)
            - pipeline_id: ID воронки (по умолчанию 0)
            - status_id: ID статуса (по умолчанию 0)
        """
        lead = {
            "name": order_data.get("name", "Новый заказ"),
            "price": order_data.get("price", 0),
            "_embedded": {
                "contacts": [
                    {
                        "first_name": order_data.get("client_name", ""),
                        "custom_fields_values": [
                            {
                                "field_code": "PHONE",
                                "values": [{"value": order_data.get("client_phone", "")}]
                            }
                        ]
                    }
                ]
            },
            "custom_fields_values": [
                {
                    "field_code": "DESCRIPTION",
                    "values": [{"value": order_data.get("description", "")}]
                }
            ]
        }
        if "pipeline_id" in order_data:
            lead["pipeline_id"] = order_data["pipeline_id"]
        if "status_id" in order_data:
            lead["status_id"] = order_data["status_id"]

        try:
            result = self._request('POST', '/leads', json=[lead])
            if result and '_embedded' in result and 'leads' in result['_embedded']:
                return result['_embedded']['leads'][0]['id']
        except Exception:
            return None

    def update_lead_status(self, lead_id: int, status_id: int, pipeline_id: int = None) -> bool:
        """Обновляет статус сделки"""
        data = [{"id": lead_id, "status_id": status_id}]
        if pipeline_id:
            data[0]["pipeline_id"] = pipeline_id
        try:
            self._request('PATCH', '/leads', json=data)
            return True
        except Exception:
            return False

    def get_lead(self, lead_id: int) -> Optional[Dict]:
        """Получает информацию о сделке"""
        try:
            return self._request('GET', f'/leads/{lead_id}')
        except Exception:
            return None

    def add_note(self, lead_id: int, note_text: str) -> bool:
        """Добавляет примечание к сделке"""
        note = {
            "entity_id": lead_id,
            "note_type": "common",
            "params": {
                "text": note_text
            }
        }
        try:
            self._request('POST', '/notes', json=[note])
            return True
        except Exception:
            return False