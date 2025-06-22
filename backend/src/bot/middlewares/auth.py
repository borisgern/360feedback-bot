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
        # This is a simplified example.
        # In a real app, you'd apply this middleware only to admin handlers.
        if event.from_user.id not in self.admin_ids:
            # You can ignore the update or send a message.
            # For admin commands, ignoring is often better.
            return
        return await handler(event, data)
