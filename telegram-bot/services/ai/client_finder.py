import asyncio
import logging
from telethon import TelegramClient, events, errors
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
from instagrapi import Client
from database.crud import add_found_client, get_found_client_by_user_id
from config import TELEGRAM_API_ID, TELEGRAM_API_HASH, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD
import re

# ---- Telegram поиск потенциальных клиентов ----
class TelegramClientFinder:
    def __init__(self, api_id, api_hash):
        self.api_id = api_id
        self.api_hash = api_hash
        self.client = None

    async def start(self):
        self.client = TelegramClient('client_finder', self.api_id, self.api_hash)
        await self.client.start()
        # Требуется авторизация как пользователь, не бот
        logging.info("Telegram client started for searching")

    async def search_groups_by_keywords(self, keywords, limit=50):
        """Ищет группы по ключевым словам и возвращает список ссылок/ID"""
        if not self.client:
            await self.start()
        groups = []
        # Используем поиск по глобальному каталогу (доступно не во всех версиях)
        try:
            from telethon.tl.functions.contacts import SearchRequest
            result = await self.client(SearchRequest(
                q=' '.join(keywords),
                limit=limit
            ))
            for chat in result.chats:
                if hasattr(chat, 'username') and chat.username:
                    groups.append(f"https://t.me/{chat.username}")
        except Exception as e:
            logging.error(f"Ошибка поиска групп: {e}")
        return groups

    async def extract_users_from_group(self, group_link, max_users=100):
        """Парсит участников группы (только если вы участник)"""
        if not self.client:
            await self.start()
        try:
            entity = await self.client.get_entity(group_link)
            participants = []
            async for user in self.client.iter_participants(entity, limit=max_users):
                if not user.bot and user.username:
                    participants.append({
                        'user_id': user.id,
                        'username': user.username,
                        'first_name': user.first_name,
                        'last_name': user.last_name
                    })
            return participants
        except Exception as e:
            logging.error(f"Ошибка получения участников {group_link}: {e}")
            return []

    async def find_potential_clients(self, keywords, groups=None, max_users=500):
        """
        Основной метод: ищет группы по ключевым словам, затем собирает участников.
        Сохраняет найденных в БД.
        """
        if not groups:
            groups = await self.search_groups_by_keywords(keywords)
        all_users = []
        for group in groups[:5]:  # ограничимся первыми 5 группами
            users = await self.extract_users_from_group(group, max_users=100)
            for user in users:
                # Проверяем, не сохранён ли уже
                existing = await get_found_client_by_user_id(user['user_id'], source='telegram')
                if not existing:
                    await add_found_client(
                        source='telegram',
                        username=user['username'],
                        user_id=str(user['user_id']),
                        metadata={'first_name': user['first_name'], 'last_name': user['last_name']}
                    )
                    all_users.append(user)
        return all_users

# ---- Instagram поиск (через instagrapi) ----
class InstagramFinder:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.client = None

    def login(self):
        self.client = Client()
        self.client.login(self.username, self.password)
        logging.info("Instagram client logged in")

    def search_hashtags(self, hashtag, amount=50):
        """Ищет медиа по хештегу и собирает авторов"""
        if not self.client:
            self.login()
        medias = self.client.hashtag_medias_recent(hashtag, amount)
        users = []
        for media in medias:
            user = media.user
            if user.username:
                users.append({
                    'user_id': user.pk,
                    'username': user.username,
                    'full_name': user.full_name
                })
        return users

    def search_location(self, location_id, amount=50):
        """Ищет медиа по локации"""
        if not self.client:
            self.login()
        medias = self.client.location_medias_recent(location_id, amount)
        users = []
        for media in medias:
            user = media.user
            if user.username:
                users.append({
                    'user_id': user.pk,
                    'username': user.username,
                    'full_name': user.full_name
                })
        return users

    def save_found_users(self, users, source='instagram'):
        for u in users:
            # Асинхронный вызов БД – но здесь синхронный код, поэтому нужно использовать asyncio.run или передать в очередь
            # Для простоты сделаем синхронный вызов (но лучше через asyncio)
            import asyncio
            asyncio.create_task(add_found_client(
                source=source,
                username=u['username'],
                user_id=str(u['user_id']),
                metadata={'full_name': u.get('full_name')}
            ))