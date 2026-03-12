import requests

class AmoCRMService:
    def __init__(self, subdomain, access_token):
        self.base_url = f"https://{subdomain}.amocrm.ru/api/v4"
        self.headers = {"Authorization": f"Bearer {access_token}"}

    def create_lead(self, name, price, contact_id=None):
        data = [{"name": name, "price": price}]
        response = requests.post(f"{self.base_url}/leads", headers=self.headers, json=data)
        return response.json()