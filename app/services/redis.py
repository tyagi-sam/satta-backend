from redis.asyncio import Redis
from typing import Optional, AsyncGenerator
from ..core.config import settings

class RedisService:
    def __init__(self):
        self.redis: Optional[Redis] = None
        self.pubsub = None

    async def init(self):
        if not self.redis:
            self.redis = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )
            self.pubsub = self.redis.pubsub()

    async def publish(self, channel: str, message: str):
        """Publish a message to a channel"""
        if not self.redis:
            await self.init()
        await self.redis.publish(channel, message)

    async def subscribe(self, channel: str) -> AsyncGenerator[str, None]:
        """Subscribe to a channel and yield messages"""
        if not self.redis:
            await self.init()
        
        async with self.redis.pubsub() as pubsub:
            await pubsub.subscribe(channel)
            
            while True:
                try:
                    message = await pubsub.get_message(ignore_subscribe_messages=True)
                    if message and message["type"] == "message":
                        yield message["data"]
                except Exception as e:
                    print(f"Redis subscription error: {e}")
                    break

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            self.redis = None
            self.pubsub = None

redis_service = RedisService() 