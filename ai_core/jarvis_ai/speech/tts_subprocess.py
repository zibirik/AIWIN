"""
Озвучка через запуск pyttsx3 в отдельном процессе — нет конфликта «run loop already started».
Текст передаётся через временный файл (UTF-8), чтобы на Windows не ломалась кодировка.
Вариант to_wav: pyttsx3 сохраняет в WAV, воспроизведение через winsound (тот же вывод, что и бип).
"""
from __future__ import annotations

import asyncio
import os
import sys
import subprocess
import tempfile
from pathlib import Path


def _log(msg: str) -> None:
    try:
        print(f"[JARVIS] {msg}", flush=True)
    except Exception:
        pass


def _run_pyttsx3_to_wav_then_play_sync(text: str) -> bool:
    """Сгенерировать WAV через pyttsx3 в subprocess, воспроизвести через winsound (тот же вывод, что бип)."""
    if not text or not text.strip():
        return True
    text = text.strip()
    txt_path = None
    wav_path = None
    try:
        fd_txt, txt_path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd_txt, "w", encoding="utf-8") as f:
            f.write(text)
        fd_wav, wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd_wav)
        code = r"""
import sys
txt_path = sys.argv[1]
wav_path = sys.argv[2]
with open(txt_path, encoding='utf-8') as f:
    text = f.read().strip()
if not text:
    sys.exit(0)
import pyttsx3
e = pyttsx3.init()
e.setProperty("rate", 150)
voices = e.getProperty("voices")
for v in voices:
    langs = str(getattr(v, "languages", "") or "").lower()
    name = str(getattr(v, "name", "") or "").lower()
    if "ru" in langs or "ru" in name or "0419" in langs:
        e.setProperty("voice", v.id)
        break
else:
    if voices:
        e.setProperty("voice", voices[0].id)
e.save_to_file(text, wav_path)
e.runAndWait()
sys.exit(0)
"""
        proc = subprocess.run(
            [sys.executable, "-c", code, txt_path, wav_path],
            capture_output=True,
            timeout=60,
            cwd=str(Path(__file__).resolve().parent.parent.parent.parent),
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            _log(f"pyttsx3 to WAV: subprocess exit {proc.returncode} stderr={(proc.stderr or '')[:200]}")
            return False
        wav_size = os.path.getsize(wav_path) if (wav_path and os.path.isfile(wav_path)) else 0
        if wav_size < 1000:
            _log(f"pyttsx3 to WAV: file too small ({wav_size} bytes)")
            return False
        import winsound
        winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
        return True
    except Exception as e:
        _log(f"pyttsx3 to WAV: {e}")
        return False
    finally:
        for p in (txt_path, wav_path):
            if p and os.path.isfile(p):
                try:
                    os.unlink(p)
                except Exception:
                    pass


def _run_pyttsx3_subprocess_sync(text: str) -> bool:
    """Синхронно: запустить дочерний процесс, в нём только pyttsx3."""
    if not text or not text.strip():
        return True
    text = text.strip()
    tmp_path = None
    try:
        # Текст в файл UTF-8 — иначе в subprocess на Windows stdin читается в cp1251 и «Слушаю» превращается в мусор
        fd, tmp_path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        code = r"""
import sys
path = sys.argv[1]
with open(path, encoding='utf-8') as f:
    text = f.read().strip()
if not text:
    sys.exit(0)
import pyttsx3
e = pyttsx3.init()
e.setProperty("rate", 150)
e.say(text)
e.runAndWait()
"""
        proc = subprocess.run(
            [sys.executable, "-c", code, tmp_path],
            capture_output=True,
            timeout=60,
            cwd=str(Path(__file__).resolve().parent.parent.parent.parent),
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0 and (proc.stderr or proc.stdout):
            import logging
            logging.getLogger("jarvis.tts").warning(
                "pyttsx3 subprocess: returncode=%s stderr=%s",
                proc.returncode, (proc.stderr or "")[:300]
            )
        return proc.returncode == 0
    except subprocess.TimeoutExpired:
        import logging
        logging.getLogger("jarvis.tts").warning("pyttsx3 subprocess: таймаут 60 сек (озвучка не воспроизведена)")
        return False
    except Exception as e:
        import logging
        logging.getLogger("jarvis.tts").warning("pyttsx3 subprocess: %s", e)
        return False
    finally:
        if tmp_path and os.path.isfile(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


async def speak_via_subprocess(text: str) -> bool:
    """Асинхронно озвучить через subprocess (pyttsx3 в отдельном процессе)."""
    if not text or not text.strip():
        return True
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_pyttsx3_subprocess_sync, text)


async def speak_via_wav_and_winsound(text: str) -> bool:
    """pyttsx3 → WAV в subprocess, воспроизведение через winsound (тот же вывод, что и бип)."""
    if not text or not text.strip():
        return True
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_pyttsx3_to_wav_then_play_sync, text)


if __name__ == "__main__":
    # Вызов из командной строки: текст из stdin или argv
    if len(sys.argv) > 1:
        t = " ".join(sys.argv[1:])
    else:
        t = sys.stdin.read().strip()
    if t:
        _run_pyttsx3_subprocess_sync(t)
