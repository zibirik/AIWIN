from __future__ import annotations

from typing import Iterable

from ..event_bus import Event, EventBus, EventType
from .base import Agent


class SystemAgent(Agent):
    name = "system-agent"

    @property
    def subscriptions(self) -> Iterable[EventType]:
        return [EventType.ERROR, EventType.SYSTEM_STATUS_UPDATED]

    async def on_event(self, event: Event) -> None:
        if event.type == EventType.ERROR:
            pass
        elif event.type == EventType.SYSTEM_STATUS_UPDATED:
            pass
