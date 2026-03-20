from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from .screen_vision import ScreenVision, OCRBlock

logger = logging.getLogger("jarvis.screen_reader")


def _blocks_to_chunks(blocks: List[OCRBlock], words_per_chunk: int = 15) -> List[str]:
    """Собирает блоки в фразы для озвучки."""
    if not blocks:
        return []
    chunks: List[str] = []
    current: List[str] = []
    for b in blocks:
        current.append(b.text)
        if len(current) >= words_per_chunk:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return [c.strip() for c in chunks if c.strip()]


class ScreenReaderService:
    def __init__(self, vision: ScreenVision) -> None:
        self.vision = vision
        self._chunks: List[str] = []
        self._index: int = 0
        self._reading: bool = False
        self._tts = None

    def _get_tts(self):
        if self._tts is None:
            from ..speech.tts import TTS
            self._tts = TTS()
        return self._tts

    @property
    def is_reading(self) -> bool:
        return self._reading

    async def start(self) -> bool:
        blocks = await self.vision.ocr_blocks()
        self._chunks = _blocks_to_chunks(blocks)
        self._index = 0
        self._reading = bool(self._chunks)
        if not self._chunks:
            return False
        tts = self._get_tts()
        await tts.speak(f"На экране {len(self._chunks)} фрагментов. Начинаю чтение.")
        await tts.speak(self._chunks[0])
        return True

    async def next(self) -> bool:
        if not self._reading or self._index >= len(self._chunks) - 1:
            return False
        self._index += 1
        await self._get_tts().speak(self._chunks[self._index])
        return True

    async def prev(self) -> bool:
        if not self._reading or self._index <= 0:
            return False
        self._index -= 1
        await self._get_tts().speak(self._chunks[self._index])
        return True

    async def stop(self) -> bool:
        if not self._reading:
            return False
        self._reading = False
        await self._get_tts().speak("Остановлено.")
        return True

    async def repeat(self) -> bool:
        if not self._reading or not self._chunks:
            return False
        await self._get_tts().speak(self._chunks[self._index])
        return True
