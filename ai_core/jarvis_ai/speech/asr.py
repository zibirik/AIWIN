from __future__ import annotations

import asyncio
import os
from typing import AsyncIterator

import numpy as np

# На части сетей XET-скачивание Hugging Face «висит»; классический HTTP стабильнее.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

try:
    from faster_whisper import WhisperModel
    _HAS_WHISPER = True
except ImportError:
    _HAS_WHISPER = False
    WhisperModel = None


_RU_PROMPT = (
    "Русская речь. Команды ассистенту: открой блокнот, какая погода, сколько будет, "
    "который час, создай папку, нажми кнопку."
)


class ASR:
    def __init__(self, model_size: str = "base") -> None:
        # Важно: не вызывать WhisperModel здесь — скачивание с HF Hub блокирует весь asyncio.
        # Загрузка только в _ensure_model(), из executor в always_listen.
        self.model_size = model_size
        self._model = None

    def _ensure_model(self) -> bool:
        if self._model is None and _HAS_WHISPER and WhisperModel is not None:
            try:
                self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            except Exception:
                pass
        return self._model is not None

    def transcribe_bytes(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        *,
        vad_filter: bool = True,
    ) -> str:
        if not self._ensure_model():
            return ""
        audio = np.frombuffer(audio_bytes, dtype=np.int16)
        audio = audio.astype(np.float32) / 32768.0
        # condition_on_previous_text=False снижает «нарастающие» галлюцинации на шуме
        segments, _ = self._model.transcribe(
            audio,
            language="ru",
            vad_filter=vad_filter,
            initial_prompt=_RU_PROMPT,
            beam_size=5,
            condition_on_previous_text=False,
        )
        return " ".join(s.text for s in segments if s.text).strip()

    async def transcribe_stream(self, audio_stream: AsyncIterator[bytes]) -> str:
        chunks = []
        async for chunk in audio_stream:
            chunks.append(chunk)
        if not chunks:
            return ""
        return self.transcribe_bytes(b"".join(chunks))

    async def transcribe_from_mic(self, duration_sec: float = 5.0, sample_rate: int = 16000) -> str:
        try:
            import sounddevice as sd
        except ImportError:
            return ""
        loop = asyncio.get_event_loop()

        def record() -> np.ndarray:
            return sd.rec(
                int(duration_sec * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype=np.int16,
                blocking=True,
            )

        data = await loop.run_in_executor(None, record)
        return self.transcribe_bytes(data.tobytes(), sample_rate)
