from __future__ import annotations

from typing import Iterable

from ..event_bus import Event, EventBus, EventType
from .base import Agent


class MemoryAgent(Agent):
    name = "memory-agent"

    @property
    def subscriptions(self) -> Iterable[EventType]:
        return [
            EventType.VOICE_INPUT,
            EventType.TEXT_INPUT,
            EventType.INTENT_DETECTED,
            EventType.TASK_COMPLETED,
            EventType.COMMAND_EXECUTED,
        ]

    async def on_event(self, event: Event) -> None:
        try:
            from ..memory.db import MemoryDB
            from .. import config as cfg_mod
            cfg = cfg_mod.load_config()
            path = cfg.get("memory", {}).get("sqlite_path", "jarvis_memory.db")
            db = MemoryDB(path)
            conn = await db.connect()
            await conn.execute(
                "INSERT INTO conversations (timestamp, role, content, correlation_id, tags) VALUES (?, ?, ?, ?, ?)",
                (event.timestamp.isoformat(), "event", str(event.payload), event.correlation_id or "", str(event.type)),
            )
            await conn.commit()
        except Exception:
            pass
