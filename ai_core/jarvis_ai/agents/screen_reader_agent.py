from __future__ import annotations

from typing import Any, Iterable

from ..event_bus import Event, EventBus, EventType
from ..vision.screen_vision import ScreenVision
from ..vision.screen_reader import ScreenReaderService
from ..intents.detector import detect_intent
from .base import Agent


class ScreenReaderAgent(Agent):
    name = "screen-reader-agent"

    def __init__(self, bus: EventBus, rust_client: Any) -> None:
        super().__init__(bus)
        vision = ScreenVision(rust_client)
        self.reader = ScreenReaderService(vision)

    @property
    def subscriptions(self) -> Iterable[EventType]:
        return [EventType.INTENT_DETECTED, EventType.VOICE_INPUT]

    async def on_event(self, event: Event) -> None:
        if event.type == EventType.INTENT_DETECTED:
            intent_name = (event.payload or {}).get("intent") or (event.payload or {}).get("goal", "")
            if isinstance(intent_name, dict):
                intent_name = intent_name.get("name", "")
            if intent_name == "read_screen":
                await self.reader.start()
            return
        if event.type == EventType.VOICE_INPUT and self.reader.is_reading:
            text = (event.payload or {}).get("text", "").strip()
            if not text:
                return
            intent = detect_intent(text)
            if intent.name == "screen_reader_next":
                await self.reader.next()
            elif intent.name == "screen_reader_prev":
                await self.reader.prev()
            elif intent.name == "screen_reader_stop":
                await self.reader.stop()
            elif intent.name == "screen_reader_repeat":
                await self.reader.repeat()
