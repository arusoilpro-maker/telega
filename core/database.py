"""
Database connection pool and ORM
"""
import aiomysql
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from config.settings import config

logger = logging.getLogger(__name__)

class Database:
    """Database connection pool manager"""
    
    _instance = None
    _pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self):
        """Create database connection pool"""
        try:
            self._pool = await aiomysql.create_pool(
                host=config.DB_HOST,
                port=config.DB_PORT,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                db=config.DB_NAME,
                charset='utf8mb4',
                autocommit=False,
                maxsize=config.DB_POOL_SIZE,
                minsize=5,
                pool_recycle=config.DB_POOL_RECYCLE
            )
            logger.info("Database pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection pool"""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            logger.info("Database pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool"""
        if not self._pool:
            raise Exception("Database not connected")
        
        async with self._pool.acquire() as conn:
            yield conn
    
    @asynccontextmanager
    async def transaction(self):
        """Database transaction context manager"""
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                try:
                    await conn.begin()
                    yield cursor
                    await conn.commit()
                except Exception as e:
                    await conn.rollback()
                    logger.error(f"Transaction failed: {e}")
                    raise
    
    async def execute(self, query: str, *args) -> List[Dict]:
        """Execute query and return results"""
        async with self.transaction() as cursor:
            await cursor.execute(query, args)
            return await cursor.fetchall()
    
    async def execute_one(self, query: str, *args) -> Optional[Dict]:
        """Execute query and return one result"""
        results = await self.execute(query, *args)
        return results[0] if results else None
    
    async def insert(self, query: str, *args) -> int:
        """Insert data and return last insert id"""
        async with self.transaction() as cursor:
            await cursor.execute(query, args)
            return cursor.lastrowid
    
    async def update(self, query: str, *args) -> int:
        """Update data and return affected rows"""
        async with self.transaction() as cursor:
            await cursor.execute(query, args)
            return cursor.rowcount
    
    async def delete(self, query: str, *args) -> int:
        """Delete data and return affected rows"""
        async with self.transaction() as cursor:
            await cursor.execute(query, args)
            return cursor.rowcount