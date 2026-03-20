from __future__ import annotations

import asyncio
import sys
from typing import Optional


def _safe_print(msg: str) -> None:
    """Print to stdout without failing on encoding (e.g. Windows cp1252 vs Russian text)."""
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()


try:
    import pyttsx3
    _HAS_PYTTSX = True
except ImportError:
    _HAS_PYTTSX = False


def _sapi_available() -> bool:
    try:
        from .tts_sapi import is_available
        return is_available()
    except Exception:
        return False


def _powershell_available() -> bool:
    try:
        from .tts_powershell import is_available
        return is_available()
    except Exception:
        return False


class TTS:
    """Озвучка: 1) SAPI (Windows), 2) PowerShell WAV, 3) pyttsx3 subprocess, 4) in-process pyttsx3."""
    def __init__(self, voice: Optional[str] = None) -> None:
        self.voice_id = voice
        self._engine = None
        self._use_sapi = _sapi_available()
        if not self._use_sapi and _HAS_PYTTSX:
            try:
                self._engine = pyttsx3.init()
                if voice:
                    self._engine.setProperty("voice", voice)
                self._engine.setProperty("rate", 150)
            except Exception:
                self._engine = None
        if _HAS_PYTTSX:
            _safe_print("[JARVIS] TTS: pyttsx3 WAV + winsound (same device as beep), then SAPI.")
        elif self._use_sapi:
            _safe_print("[JARVIS] TTS: SAPI (Windows) ready.")
        else:
            _safe_print("[JARVIS] TTS: SAPI/pyttsx3 will be used.")

    def _ensure_engine(self) -> bool:
        return (self._use_sapi or _powershell_available() or _HAS_PYTTSX or self._engine is not None)

    async def speak(self, text: str) -> None:
        if not text or not text.strip():
            return
        loop = asyncio.get_event_loop()

        def _beep() -> None:
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

        try:
            await asyncio.wait_for(loop.run_in_executor(None, _beep), 2.0)
        except Exception:
            pass

        # 1) SAPI → WAV (SpFileStream) + winsound — тот же вывод, что и бип
        if self._use_sapi:
            try:
                from .tts_sapi import speak_to_wav_then_play_sync
                ok = await loop.run_in_executor(None, speak_to_wav_then_play_sync, text)
                if ok:
                    return
                _safe_print("[JARVIS] TTS: SAPI WAV + winsound failed.")
            except Exception as e:
                _safe_print(f"[JARVIS] TTS SAPI WAV: {e}")
        # 2) pyttsx3 → WAV в subprocess, воспроизведение через winsound
        if _HAS_PYTTSX:
            try:
                from .tts_subprocess import speak_via_wav_and_winsound
                ok = await speak_via_wav_and_winsound(text)
                if ok:
                    return
                _safe_print("[JARVIS] TTS: pyttsx3 WAV + winsound failed.")
            except Exception as e:
                _safe_print(f"[JARVIS] TTS pyttsx3 WAV: {e}")
        # 3) pyttsx3 в subprocess (прямое воспроизведение)
        if _HAS_PYTTSX:
            try:
                from .tts_subprocess import speak_via_subprocess
                ok = await speak_via_subprocess(text)
                if ok:
                    return
                _safe_print("[JARVIS] TTS: pyttsx3 subprocess failed.")
            except Exception as e:
                _safe_print(f"[JARVIS] TTS pyttsx3 subprocess: {e}")
        # 4) SAPI в отдельном процессе
        if self._use_sapi:
            try:
                from .tts_sapi import speak_via_subprocess_sync
                ok = await loop.run_in_executor(None, speak_via_subprocess_sync, text)
                if ok:
                    return
                _safe_print("[JARVIS] TTS SAPI subprocess failed.")
            except Exception as e:
                _safe_print(f"[JARVIS] TTS SAPI subprocess: {e}")
        # 5) SAPI в потоке
        if self._use_sapi:
            try:
                from .tts_sapi import speak_sync
                ok = await loop.run_in_executor(None, speak_sync, text)
                if ok:
                    return
                _safe_print("[JARVIS] TTS SAPI in-thread failed.")
            except Exception as e:
                _safe_print(f"[JARVIS] TTS SAPI: {e}")
        # 6) PowerShell (WAV) — часто даёт пустой WAV если нет русского голоса
        try:
            from .tts_powershell import speak_via_powershell
            ok = await speak_via_powershell(text)
            if ok:
                return
            _safe_print("[JARVIS] TTS: PowerShell failed.")
        except Exception as e:
            _safe_print(f"[JARVIS] TTS PowerShell: {e}")
        # 7) pyttsx3 in-process
        if self._engine is not None:
            try:
                def _say() -> None:
                    if self._engine:
                        self._engine.say(text)
                        self._engine.runAndWait()
                await loop.run_in_executor(None, _say)
                return
            except Exception as e:
                _safe_print(f"[JARVIS] TTS pyttsx3: {e}")
        _safe_print("[JARVIS] TTS: no method worked. Check volume and output device.")
