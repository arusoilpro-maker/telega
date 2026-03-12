"""
Automated Telegram advertising system
"""
import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import aiohttp
from telethon import TelegramClient
from telethon.errors import FloodWaitError
import json
import hashlib

from core.database import Database
from core.redis_client import RedisCache
from config.settings import config

logger = logging.getLogger(__name__)

class AutoAdvertiser:
    """Automatic advertising in Telegram groups"""
    
    def __init__(self, client: TelegramClient):
        self.client = client
        self.db = Database()
        self.cache = RedisCache()
        self.api_id = config.TELEGRAM_API_ID
        self.api_hash = config.TELEGRAM_API_HASH
        
        # Limits to avoid ban
        self.daily_limit = 50
        self.sent_today = 0
        self.last_reset = datetime.now()
        
        # Proxy rotation
        self.proxies = self.load_proxies()
        self.current_proxy = 0
    
    def load_proxies(self) -> List[Dict]:
        """Load proxies from file"""
        try:
            with open('promotion/proxies.txt', 'r') as f:
                proxies = []
                for line in f:
                    if line.strip():
                        parts = line.strip().split(':')
                        if len(parts) == 4:
                            proxies.append({
                                'ip': parts[0],
                                'port': int(parts[1]),
                                'username': parts[2],
                                'password': parts[3]
                            })
                return proxies
        except Exception as e:
            logger.error(f"Error loading proxies: {e}")
            return []
    
    async def get_target_groups(self) -> List[Dict]:
        """Get groups for advertising"""
        
        # Try cache first
        cached = await self.cache.get('ad_groups')
        if cached:
            return json.loads(cached)
        
        # Get from database
        groups = await self.db.execute("""
            SELECT 
                g.*,
                COUNT(DISTINCT m.id) as message_count,
                MAX(m.date) as last_message
            FROM target_groups g
            LEFT JOIN group_messages m ON g.id = m.group_id
            WHERE g.is_active = 1 
                AND g.members_count >= 100
                AND (g.last_ad_date IS NULL OR g.last_ad_date < DATE_SUB(NOW(), INTERVAL 7 DAY))
            GROUP BY g.id
            ORDER BY g.priority DESC, g.members_count DESC
            LIMIT 200
        """)
        
        # Cache for 1 hour
        await self.cache.set('ad_groups', json.dumps(groups), 3600)
        
        return groups
    
    async def get_ad_content(self) -> List[Dict]:
        """Get advertising content"""
        
        campaigns = await self.db.execute("""
            SELECT * FROM ad_campaigns 
            WHERE status = 'active' 
                AND (start_date <= NOW() OR start_date IS NULL)
                AND (end_date >= NOW() OR end_date IS NULL)
            ORDER BY priority DESC
        """)
        
        return campaigns
    
    async def send_ad_to_group(self, group: Dict, ad: Dict) -> bool:
        """Send advertisement to group"""
        
        # Check daily limit
        if self.sent_today >= self.daily_limit:
            logger.warning("Daily limit reached")
            return False
        
        # Reset counter if new day
        now = datetime.now()
        if now.date() > self.last_reset.date