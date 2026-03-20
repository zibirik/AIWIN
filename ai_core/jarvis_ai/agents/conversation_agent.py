from __future__ import annotations

from typing import Iterable

from ..event_bus import Event, EventBus, EventType
from ..intents.detector import detect_intent
from .base import Agent


class ConversationAgent(Agent):
    name = "conversation-agent"

    @property
    def subscriptions(self) -> Iterable[EventType]:
        return [EventType.VOICE_INPUT, EventType.TEXT_INPUT]

    async def on_event(self, event: Event) -> None:
        text = (event.payload or {}).get("text", "").strip()
        if not text:
            return
        intent = detect_intent(text)
        goal = text
        await self.bus.publish(
            Event.new(
                type=EventType.INTENT_DETECTED,
                source=self.name,
                payload={
                    "text": text,
                    "goal": goal,
                    "intent": intent.name,
                    "slots": intent.slots,
                },
                correlation_id=event.correlation_id,
            )
        )

