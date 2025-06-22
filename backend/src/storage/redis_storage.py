from typing import List, Optional, Set, Type, TypeVar

from pydantic import BaseModel
from redis.asyncio.client import Redis

T = TypeVar("T", bound=BaseModel)


class RedisStorageService:
    """
    A service for storing and retrieving Pydantic models in Redis.

    Handles serialization to JSON and deserialization back to Pydantic models.
    """

    def __init__(self, redis_client: Redis):
        self._redis = redis_client

    async def set_model(self, key: str, model: BaseModel, ttl: Optional[int] = None):
        """
        Stores a Pydantic model instance in Redis as a JSON string.
        :param key: The Redis key.
        :param model: The Pydantic model instance to store.
        :param ttl: Optional Time-To-Live for the key in seconds.
        """
        await self._redis.set(key, model.model_dump_json(by_alias=True), ex=ttl)

    async def delete_key(self, key: str) -> int:
        """Deletes a key from Redis."""
        return await self._redis.delete(key)

    async def set_value(self, key: str, value: str, ttl: Optional[int] = None):
        """Sets a simple string value in Redis."""
        await self._redis.set(key, value, ex=ttl)

    async def get(self, key: str) -> Optional[str]:
        """Gets a simple string value from Redis."""
        value = await self._redis.get(key)
        return value.decode('utf-8') if value else None

    async def add_to_set(self, key: str, value: str):
        """Adds a value to a Redis set."""
        await self._redis.sadd(key, value)

    async def get_set(self, key: str) -> Set[str]:
        """Gets all members of a Redis set."""
        members = await self._redis.smembers(key)
        return {member.decode('utf-8') for member in members}

    async def get_model(self, key: str, model_class: Type[T]) -> Optional[T]:
        """
        Gets a Pydantic model instance from Redis by key.
        :param key: The Redis key.
        :param model_class: The Pydantic model class to instantiate.
        :return: The model instance or None if not found.
        """
        data = await self._redis.get(key)
        if data:
            return model_class.model_validate_json(data)
        return None

    async def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """Returns a list of keys matching a pattern."""
        return [key.decode("utf-8") for key in await self._redis.keys(pattern)]
