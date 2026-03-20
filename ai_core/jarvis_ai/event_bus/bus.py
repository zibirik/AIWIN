from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Awaitable, Callable, Dict, List

from .events import Event, EventType

EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """
    Асинхронная шина событий JARVIS.
    """

    def __init__(self) -> None:
        self._subscribers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        async with self._lock:
            self._subscribers[event_type].append(handler)

    async def publish(self, event: Event) -> None:
        async with self._lock:
            handlers = list(self._subscribers.get(event.type, []))

        for handler in handlers:
            # Не блокируем основной поток, ошибки логируем отдельно.
            asyncio.create_task(self._safe_call(handler, event))

    async def _safe_call(self, handler: EventHandler, event: Event) -> None:
        try:
            await handler(event)
        except Exception as exc:  # noqa: BLE001
            # TODO: интеграция с логированием
            print(f"[EventBus] Ошибка в обработчике {handler}: {exc}")

