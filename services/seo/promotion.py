import requests
from bs4 import BeautifulSoup
import random
import time
import logging
from urllib.parse import urlparse, quote

# ---- SEO инструменты ----
def generate_seo_keywords(service_type, location=None):
    """Генерирует ключевые слова для SEO на основе услуги и локации"""
    base_keywords = [
        f"ремонт {service_type}",
        f"{service_type} мастер на дом",
        f"вызов {service_type}",
        f"услуги {service_type} цена",
        f"частный мастер {service_type}"
    ]
    if location:
        location_keywords = [f"{kw} {location}" for kw in base_keywords]
        return base_keywords + location_keywords
    return base_keywords

def generate_meta_tags(service_name, description, keywords):
    """Генерирует HTML мета-теги для страницы"""
    meta = f"""
    <meta name="description" content="{description[:150]}">
    <meta name="keywords" content="{', '.join(keywords)}">
    <title>Ремонт {service_name} | Сервис КАЧЕСТВЕННО ВЫГОДНО</title>
    """
    return meta

def check_search_engine_index(url):
    """Проверяет, проиндексирована ли страница в Google (упрощённо)"""
    try:
        response = requests.get(f"https://www.google.com/search?q=site:{url}")
        if "По запросу" in response.text and "не найдено" not in response.text:
            return True
        else:
            return False
    except:
        return False

def analyze_competitors(keyword):
    """Анализирует конкурентов в выдаче Google (заглушка)"""
    # В реальности можно парсить выдачу, но это сложно и может быть заблокировано
    return [
        {"url": "https://example.com/remont", "title": "Пример сайта", "description": "Описание..."}
    ]

# ---- Поиск групп в Telegram (улучшенный) ----
def search_telegram_channels_public(query):
    """
    Использует публичные каталоги Telegram (tgstat.ru, telemetr.me) для поиска групп.
    Это веб-скрапинг, может нарушать правила.
    """
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        # Пример: поиск на tgstat.ru
        url = f"https://tgstat.ru/search?q={quote(query)}"
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        # Здесь нужен парсинг конкретного сайта, зависит от структуры
        # Для примера просто вернём заглушку
        return ["https://t.me/example_channel"]
    except Exception as e:
        logging.error(f"Ошибка поиска групп: {e}")
        return []

def search_instagram_hashtag_posts(hashtag, count=20):
    """
    Ищет посты по хештегу в Instagram (через публичный API без авторизации, если доступно)
    """
    # Используем альтернативный способ через requests (без instagrapi)
    # Это нестабильно, лучше использовать официальный API
    try:
        url = f"https://www.instagram.com/explore/tags/{hashtag}/?__a=1&__d=dis"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = response.json()
        posts = data['graphql']['hashtag']['edge_hashtag_to_media']['edges']
        users = []
        for post in posts[:count]:
            node = post['node']
            username = node['owner']['username']
            users.append(username)
        return users
    except Exception as e:
        logging.error(f"Ошибка поиска Instagram: {e}")
        return []

# ---- Автоматическое размещение объявлений (осторожно, спам) ----
def post_to_telegram_group(group_link, message, api_id, api_hash):
    """Размещает сообщение в Telegram группе (требуется быть участником)"""
    # Используем Telethon
    from telethon import TelegramClient
    import asyncio

    async def post():
        client = TelegramClient('promo_session', api_id, api_hash)
        await client.start()
        entity = await client.get_entity(group_link)
        await client.send_message(entity, message)
        await client.disconnect()

    asyncio.run(post())