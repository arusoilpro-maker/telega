import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from config import GOOGLE_CALENDAR_CREDENTIALS, GOOGLE_CALENDAR_TOKEN

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """Возвращает авторизованный сервис Google Calendar"""
    creds = None
    if os.path.exists(GOOGLE_CALENDAR_TOKEN):
        creds = Credentials.from_authorized_user_file(GOOGLE_CALENDAR_TOKEN, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CALENDAR_CREDENTIALS, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(GOOGLE_CALENDAR_TOKEN, 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    return service

async def add_event_to_calendar(summary, description, start_time, end_time, attendees=None):
    """
    Добавляет событие в календарь.
    start_time, end_time: datetime objects.
    """
    service = get_calendar_service()
    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'Europe/Moscow',
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'Europe/Moscow',
        },
        'attendees': [{'email': email} for email in attendees] if attendees else [],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 30},
            ],
        },
    }
    event = service.events().insert(calendarId='primary', body=event).execute()
    return event.get('htmlLink')