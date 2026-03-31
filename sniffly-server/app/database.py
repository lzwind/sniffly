"""Database connections for MongoDB and Redis."""

import motor.motor_asyncio
import redis.asyncio as redis

from app.config import settings

# MongoDB client
mongo_client: motor.motor_asyncio.AsyncIOMotorClient | None = None

# Redis client
redis_client: redis.Redis | None = None


async def connect_mongodb():
    """Connect to MongoDB."""
    global mongo_client
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongodb_url)
    return mongo_client


async def disconnect_mongodb():
    """Disconnect from MongoDB."""
    global mongo_client
    if mongo_client:
        mongo_client.close()


async def connect_redis():
    """Connect to Redis."""
    global redis_client
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return redis_client


async def disconnect_redis():
    """Disconnect from Redis."""
    global redis_client
    if redis_client:
        await redis_client.close()


def get_mongodb():
    """Get MongoDB database."""
    if mongo_client is None:
        raise RuntimeError("MongoDB not connected")
    return mongo_client.get_default_database()


def get_redis():
    """Get Redis client."""
    if redis_client is None:
        raise RuntimeError("Redis not connected")
    return redis_client
