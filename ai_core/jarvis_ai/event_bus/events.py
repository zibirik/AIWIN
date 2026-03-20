from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel
from datetime import datetime, timezone


class EventType(str, Enum):
    VOICE_INPUT = "VOICE_INPUT"
    TEXT_INPUT = "TEXT_INPUT"
    INTENT_DETECTED = "INTENT_DETECTED"
    TASK_CREATED = "TASK_CREATED"
    TASK_GRAPH_READY = "TASK_GRAPH_READY"
    TASK_UPDATED = "TASK_UPDATED"
    TASK_COMPLETED = "TASK_COMPLETED"
    COMMAND_SCHEDULED = "COMMAND_SCHEDULED"
    COMMAND_EXECUTED = "COMMAND_EXECUTED"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    CONFIRMATION_YES = "CONFIRMATION_YES"
    CONFIRMATION_NO = "CONFIRMATION_NO"
    SCREEN_READER_START = "SCREEN_READER_START"
    SCREEN_READER_CONTROL = "SCREEN_READER_CONTROL"
    SCREEN_UPDATED = "SCREEN_UPDATED"
    RESEARCH_REQUESTED = "RESEARCH_REQUESTED"
    RESEARCH_RESULT = "RESEARCH_RESULT"
    ERROR = "ERROR"
    SYSTEM_STATUS_UPDATED = "SYSTEM_STATUS_UPDATED"


class Event(BaseModel):
    type: EventType
    timestamp: datetime
    source: str
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None

    @classmethod
    def new(
        cls,
        type: EventType,
        source: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> "Event":
        return cls(
            type=type,
            timestamp=datetime.now(timezone.utc),
            source=source,
            payload=payload,
            correlation_id=correlation_id,
        )

