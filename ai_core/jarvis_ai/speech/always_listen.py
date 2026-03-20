from __future__ import annotations

import asyncio
import logging
import sys
from typing import Optional

from ..event_bus import EventBus, Event, EventType
from .asr import ASR
from .transcript_clean import clean_transcript, merge_tail_safely
from .wakeword import WakeWordDetector
from .tts import TTS

logger = logging.getLogger("jarvis.voice")


def _safe_print(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()


def _log(msg: str) -> None:
    """Печатает в консоль и в лог (без падения на кодировке консоли)."""
    _safe_print(f"[JARVIS] {msg}")
    logger.info(msg)


async def run_always_listen(
    bus: EventBus,
    *,
    chunk_seconds: float = 6.0,
    tail_seconds: float = 3.0,
    command_extra_seconds: float = 3.0,
    asr_model: str = "base",
    asr_load_timeout_sec: float = 900.0,
    ack_tts: bool = False,
    greeting: str = "Слушаю",
    enabled: bool = True,
    wake_phrases: list[str] | None = None,
) -> None:
    """
    Бесконечный цикл: запись с микрофона -> распознавание -> при фразе активации
    публикует команду в шину и опционально произносит «Слушаю».
    """
    if not enabled:
        return
    try:
        import sounddevice as sd
    except ImportError:
        _log("sounddevice не установлен — постоянное прослушивание отключено")
        return

    _log(
        f"Скачивание/загрузка Whisper («{asr_model}») в фоне — до {int(asr_load_timeout_sec)} с при первом запуске. "
        "Сервер уже отвечает; HF_TOKEN ускоряет загрузку с Hugging Face."
    )
    loop = asyncio.get_event_loop()
    asr = ASR(model_size=asr_model)
    # Только в отдельном потоке — не блокируем event loop
    try:
        asr_ok = await asyncio.wait_for(
            loop.run_in_executor(None, asr._ensure_model),
            timeout=float(asr_load_timeout_sec),
        )
    except asyncio.TimeoutError:
        asr_ok = False
        _log(
            f"ОШИБКА: таймаут загрузки Whisper ({int(asr_load_timeout_sec)} с). "
            "Увеличьте voice.asr_load_timeout_sec в config или задайте HF_TOKEN, проверьте интернет."
        )
    except Exception as e:
        asr_ok = False
        _log(f"ОШИБКА загрузки Whisper: {e}. Проверьте интернет при первом запуске.")
    if not asr_ok:
        _log("Распознавание голоса отключено. Остальные команды (текст, API) работают.")
    else:
        _log("Модель распознавания речи загружена.")

    wake = WakeWordDetector(wake_phrases=wake_phrases)
    tts = TTS()
    tts_ok = tts._ensure_engine()
    if not tts_ok:
        _log("Предупреждение: TTS (озвучка) недоступен. Ответы не будут озвучиваться.")
    else:
        _log("Озвучка (TTS) готова.")

    sample_rate = 16000

    def record(sec: float) -> bytes:
        data = sd.rec(
            int(sec * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            blocking=True,
        )
        return data.tobytes()

    _log('Фоновое прослушивание включено. Скажи: «Привет, Джарвис» или «Джарвис».')

    # Один раз озвучить приветствие при старте (с таймаутом, чтобы не зависнуть)
    if tts_ok:
        try:
            _log("Озвучиваю приветствие...")
            await asyncio.wait_for(
                tts.speak("Готов к работе. Скажи: Привет, Джарвис."),
                timeout=25.0,
            )
            _log("Приветствие озвучено.")
        except asyncio.TimeoutError:
            _log("Приветствие не озвучено: таймаут 25 сек. Проверь громкость и устройство вывода.")
        except Exception as e:
            _log(f"Ошибка TTS при старте: {e}")

    while True:
        try:
            audio_bytes = await loop.run_in_executor(None, record, chunk_seconds)
            if not asr_ok:
                continue
            text = await loop.run_in_executor(
                None,
                lambda: asr.transcribe_bytes(audio_bytes, sample_rate, vad_filter=True),
            )
            text = clean_transcript(text)
            if not text or not text.strip():
                continue
            # Показывать в консоли, что услышали (чтобы проверить микрофон)
            _log(f"Услышано: «{text.strip()}»")
            found, command = wake.detect_and_extract_command(text)
            if not found:
                continue

            # Дожимаем фразу: VAD отсекает тишину; хвост — только если речь продолжается.
            full_text = text
            if tail_seconds and tail_seconds > 0:
                try:
                    tail_audio_bytes = await loop.run_in_executor(None, record, tail_seconds)
                    tail_text = await loop.run_in_executor(
                        None,
                        lambda: asr.transcribe_bytes(tail_audio_bytes, sample_rate, vad_filter=True),
                    )
                    tail_text = clean_transcript(tail_text)
                    merged = merge_tail_safely(text, tail_text)
                    if merged != text.strip():
                        full_text = merged
                        _, command2 = wake.detect_and_extract_command(full_text)
                        if command2 is not None and command2.strip():
                            command = command2
                except Exception:
                    pass

            # Доп. буфер только если команда короткая/пустая — иначе лишняя задержка.
            cmd_len = len((command or "").strip())
            need_extra = command_extra_seconds and command_extra_seconds > 0 and cmd_len < 28
            if need_extra:
                try:
                    extra_audio = await loop.run_in_executor(None, record, command_extra_seconds)
                    extra_text = await loop.run_in_executor(
                        None,
                        lambda: asr.transcribe_bytes(extra_audio, sample_rate, vad_filter=True),
                    )
                    extra_text = clean_transcript(extra_text)
                    if extra_text:
                        merged2 = merge_tail_safely(full_text, extra_text)
                        if merged2 != full_text.strip():
                            full_text = merged2
                            _, command3 = wake.detect_and_extract_command(full_text)
                            if command3 is not None and command3.strip():
                                command = command3
                except Exception:
                    pass

            full_text = clean_transcript(full_text)
            _log(f"Фраза активации! Команда: «{command or '(нет)'}»")
            if command and command.strip():
                await bus.publish(
                    Event.new(
                        type=EventType.VOICE_INPUT,
                        source="always_listen",
                        payload={"text": command.strip(), "full_text": full_text},
                    )
                )
                if ack_tts:
                    try:
                        await tts.speak("Выполняю.")
                    except Exception as e:
                        logger.debug("TTS: %s", e)
            else:
                await bus.publish(
                    Event.new(
                        type=EventType.VOICE_INPUT,
                        source="always_listen",
                        payload={"text": full_text, "full_text": full_text},
                    )
                )
                try:
                    await tts.speak(greeting)
                except Exception as e:
                    logger.debug("TTS greeting: %s", e)
        except asyncio.CancelledError:
            logger.info("Прослушивание остановлено")
            break
        except Exception as e:
            logger.exception("Ошибка в цикле прослушивания: %s", e)
            await asyncio.sleep(1.0)
