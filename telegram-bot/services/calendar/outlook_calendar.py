import msal
import requests
from config import OUTLOOK_CLIENT_ID, OUTLOOK_CLIENT_SECRET, OUTLOOK_TENANT_ID

def get_outlook_token():
    """Получает токен для Microsoft Graph API через client credentials (или device code)"""
    authority = f"https://login.microsoftonline.com/{OUTLOOK_TENANT_ID}"
    app = msal.ConfidentialClientApplication(
        client_id=OUTLOOK_CLIENT_ID,
        client_credential=OUTLOOK_CLIENT_SECRET,
        authority=authority
    )
    # Для демо используем client credentials (не подходит для пользовательских календарей)
    # В реальном проекте нужен поток с согласием пользователя (например, device code flow)
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" in result:
        return result['access_token']
    else:
        raise Exception("Не удалось получить токен Outlook")

async def add_outlook_event(summary, description, start_time, end_time, attendees_emails=None):
    token = get_outlook_token()
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    event = {
        "subject": summary,
        "body": {
            "contentType": "HTML",
            "content": description
        },
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "Europe/Moscow"
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "Europe/Moscow"
        },
        "attendees": [
            {
                "emailAddress": {
                    "address": email
                },
                "type": "required"
            } for email in (attendees_emails or [])
        ]
    }
    response = requests.post(
        "https://graph.microsoft.com/v1.0/me/calendar/events",
        headers=headers,
        json=event
    )
    response.raise_for_status()
    return response.json().get('webLink')