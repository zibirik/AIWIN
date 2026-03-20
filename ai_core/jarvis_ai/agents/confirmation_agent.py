from __future__ import annotations

from typing import Iterable

from ..event_bus import Event, EventBus, EventType
from ..intents.detector import detect_intent
from ..executor.confirmation_store import clear_pending, get_pending, set_pending
from .base import Agent


class ConfirmationAgent(Agent):
    name = "confirmation-agent"

    @property
    def subscriptions(self) -> Iterable[EventType]:
        return [EventType.VOICE_INPUT, EventType.TEXT_INPUT]

    async def on_event(self, event: Event) -> None:
        pending = get_pending()
        if not pending:
            return
        text = (event.payload or {}).get("text", "").strip()
        if not text:
            return
        intent = detect_intent(text)
        if intent.name == "confirm":
            await self.bus.publish(
                Event.new(
                    type=EventType.CONFIRMATION_YES,
                    source=self.name,
                    payload=pending,
                    correlation_id=event.correlation_id,
                )
            )
            clear_pending()
        elif intent.name == "cancel":
            await self.bus.publish(
                Event.new(
                    type=EventType.CONFIRMATION_NO,
                    source=self.name,
                    payload=pending,
                    correlation_id=event.correlation_id,
                )
            )
            clear_pending()
