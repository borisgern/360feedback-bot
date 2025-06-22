import json
from typing import List, Optional, Type, TypeVar

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

    async def set_model(
        self, key: str, model: BaseModel, ttl: Optional[int] = None
    ) -> None:
        """
        Serializes a Pydantic model to JSON and stores it in Redis.

        :param key: The Redis key.
        :param model: The Pydantic model instance to store.
        :param ttl: Optional Time-To-Live for the key in seconds.
        """
        await self._redis.set(key, model.model_dump_json(by_alias=True), ex=ttl)

    async def get_model(self, key: str, model_class: Type[T]) -> T | None:
        """
        Retrieves a Pydantic model from Redis by key.
        :param key: The key to retrieve.
        :param model_class: The Pydantic model class to validate against.
        :return: An instance of the model class, or None if the key does not exist.
        """
        data = await self._redis.get(key)
        if not data:
            return None
        return model_class.model_validate_json(data)

    async def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """Returns a list of keys matching a pattern."""
        return [key.decode("utf-8") for key in await self._redis.keys(pattern)]
