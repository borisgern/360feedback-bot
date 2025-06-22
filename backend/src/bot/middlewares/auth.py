from typing import Any, Awaitable, Callable, Dict, List

from aiogram import BaseMiddleware
from aiogram.types import Message


class AdminAuthMiddleware(BaseMiddleware):
    def __init__(self, admin_ids: List[int]):
        self.admin_ids = admin_ids

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if not event.from_user or event.from_user.id not in self.admin_ids:
            # If the user is not an admin, we simply stop processing the event.
            # The handler will not be called.
            return
        return await handler(event, data)
