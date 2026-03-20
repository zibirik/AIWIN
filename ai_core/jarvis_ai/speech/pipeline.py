from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional

from ..event_bus import EventBus, Event, EventType
from .asr import ASR
from .wakeword import WakeWordDetector


class VoicePipeline:
    def __init__(self, bus: EventBus, listen_seconds: float = 5.0) -> None:
        self.bus = bus
        self.asr = ASR()
        self.wake = WakeWordDetector()
        self.listen_seconds = listen_seconds

    async def run(self, audio_stream: AsyncIterator[bytes]) -> None:
        text = await self.asr.transcribe_stream(audio_stream)
        if not text:
            return
        if not self.wake.is_wake_word(text):
            return
        await self.bus.publish(
            Event.new(
                type=EventType.VOICE_INPUT,
                source="voice-pipeline",
                payload={"text": text},
            )
        )

    async def run_once_from_mic(self, duration_sec: Optional[float] = None) -> Optional[str]:
        sec = duration_sec or self.listen_seconds
        text = await self.asr.transcribe_from_mic(duration_sec=sec)
        if not text:
            return None
        if self.wake.is_wake_word(text):
            await self.bus.publish(
                Event.new(
                    type=EventType.VOICE_INPUT,
                    source="voice-pipeline",
                    payload={"text": text},
                )
            )
        return text
