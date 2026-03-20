"""
Озвучка через Windows SAPI (Speech API) — без конфликта «run loop already started».
Используется как запасной вариант вместо pyttsx3 в том же процессе.
"""

from __future__ import annotations

import os
import sys
import tempfile


def _safe_print(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()


def speak_sync(text: str) -> bool:
    """Синхронно озвучить текст через Windows SAPI. Возвращает True при успехе."""
    if not text or not text.strip():
        return True
    try:
        import pythoncom  # COM must be initialized in thread when called from run_in_executor
        import win32com.client
        pythoncom.CoInitialize()
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        voice.Speak(text.strip(), 0)  # 0 = synchronous
        return True
    except ImportError as e:
        _safe_print(f"[JARVIS] SAPI: pywin32 missing — {e}")
        return False
    except Exception as e:
        _safe_print(f"[JARVIS] SAPI speak_sync: {e}")
        return False


def is_available() -> bool:
    """Проверка: доступен ли Windows SAPI (только Windows)."""
    try:
        import win32com.client
        win32com.client.Dispatch("SAPI.SpVoice")
        return True
    except Exception:
        return False


def _select_voice_sapi(voice_obj) -> None:
    """Выбрать голос с поддержкой русского (0419) или любой доступный."""
    try:
        voices = voice_obj.GetVoices()
        if voices is None or voices.Count == 0:
            return
        for i in range(voices.Count):
            token = voices.Item(i)
            try:
                desc = (token.GetDescription() or "").lower()
                vid = (token.Id or "").lower()
                if "ru" in desc or "ru" in vid or "0419" in vid or "419" in desc:
                    voice_obj.Voice = token
                    return
            except Exception:
                continue
        voice_obj.Voice = voices.Item(0)
    except Exception:
        pass


def speak_to_wav_then_play_sync(text: str) -> bool:
    """SAPI пишет в WAV через SpFileStream, воспроизведение через winsound (тот же вывод, что и бип)."""
    if not text or not text.strip():
        return True
    text = text.strip()
    wav_path = None
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        fd, wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        _select_voice_sapi(voice)
        filestream = win32com.client.Dispatch("SAPI.SpFileStream")
        filestream.Open(wav_path, 3, False)  # 3 = SSFMCreateForWrite
        voice.AudioOutputStream = filestream
        voice.Speak(text, 0)
        filestream.Close()
        del voice
        del filestream
        wav_size = os.path.getsize(wav_path) if os.path.isfile(wav_path) else 0
        if wav_size < 1000:
            if wav_size <= 46:
                _safe_print("[JARVIS] SAPI: no audio (install Russian voice: Settings -> Time & language -> Speech)")
            return False
        import winsound
        winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
        return True
    except Exception as e:
        _safe_print(f"[JARVIS] SAPI to WAV: {e}")
        return False
    finally:
        if wav_path and os.path.isfile(wav_path):
            try:
                os.unlink(wav_path)
            except Exception:
                pass


def speak_via_subprocess_sync(text: str) -> bool:
    """Озвучка через SAPI в отдельном процессе (главный поток — часто надёжнее для COM/звука)."""
    if not text or not text.strip():
        return True
    import os
    import subprocess
    import tempfile
    text = text.strip()
    fd, path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        code = (
            "import sys\n"
            "path = sys.argv[1]\n"
            "with open(path, encoding='utf-8') as f:\n"
            "    text = f.read().strip()\n"
            "if not text:\n"
            "    sys.exit(0)\n"
            "import pythoncom\n"
            "import win32com.client\n"
            "pythoncom.CoInitialize()\n"
            "v = win32com.client.Dispatch('SAPI.SpVoice')\n"
            "v.Speak(text, 0)\n"
            "sys.exit(0)\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code, path],
            capture_output=True,
            timeout=60,
            encoding="utf-8",
            errors="replace",
        )
        return proc.returncode == 0
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass
