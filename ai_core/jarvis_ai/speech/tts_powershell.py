"""
Озвучка: PowerShell генерирует WAV через System.Speech.
Воспроизведение: открываем WAV в программе по умолчанию (Музыка, проигрыватель) — так звук точно слышно.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
import sys
import time


def _safe_print(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()


def _speak_powershell_sync(text: str) -> bool:
    if not text or not text.strip():
        return True
    wav_path = None
    played_with_winsound = False
    try:
        # 1) Текст во временный файл
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(text.strip())
            txt_path = f.name
        # 2) Временный путь для WAV (PowerShell создаст файл)
        wav_fd, wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(wav_fd)
        # Файл пустой — PowerShell перезапишет его через SetOutputToWaveFile

        script = r"""
$txtPath = $env:JARVIS_TTS_TXT
$wavPath = $env:JARVIS_TTS_WAV
if (-not $txtPath -or -not $wavPath) { exit 1 }
$t = [System.IO.File]::ReadAllText($txtPath, [System.Text.Encoding]::UTF8)
if ([string]::IsNullOrWhiteSpace($t)) { exit 0 }
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SetOutputToWaveFile($wavPath)
$s.Rate = 0
$s.Volume = 100
$s.Speak($t)
$s.Dispose()
exit 0
"""
        env = os.environ.copy()
        env["JARVIS_TTS_TXT"] = txt_path
        env["JARVIS_TTS_WAV"] = wav_path
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-Command", script,
            ],
            env=env,
            capture_output=True,
            timeout=60,
            encoding="utf-8",
            errors="replace",
        )
        try:
            os.unlink(txt_path)
        except Exception:
            pass
        if proc.returncode != 0:
            if proc.stderr:
                _safe_print(f"[JARVIS] PowerShell TTS stderr: {proc.stderr[:300]}")
                return False
        if not os.path.isfile(wav_path) or os.path.getsize(wav_path) == 0:
            _safe_print("[JARVIS] WAV file not created or empty")
            return False
        wav_size = os.path.getsize(wav_path)
        if wav_size < 1000:
            _safe_print(f"[JARVIS] WAV too small ({wav_size} bytes), synthesis may have failed")
            return False
        # 3) Воспроизведение: сначала startfile (открыть в плеере по умолчанию — всегда слышно)
        played = False
        duration = max(3.0, len(text) * 0.07)
        try:
            os.startfile(wav_path)
            time.sleep(duration)
            played = True
        except Exception as e:
            _safe_print(f"[JARVIS] startfile(WAV): {e}")
        if not played:
            try:
                import winsound
                winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
                played = True
                played_with_winsound = True
            except Exception as e2:
                _safe_print(f"[JARVIS] winsound: {e2}")
        return played
    except Exception:
        return False
    finally:
        # Удаляем WAV только если воспроизведение было через winsound (оно синхронное).
        # При startfile не удаляем — плеер может ещё читать файл.
        if wav_path and os.path.isfile(wav_path) and played_with_winsound:
            try:
                os.unlink(wav_path)
            except Exception:
                pass


def is_available() -> bool:
    try:
        proc = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "Add-Type -AssemblyName System.Speech; exit 0",
            ],
            capture_output=True,
            timeout=5,
        )
        return proc.returncode == 0
    except Exception:
        return False


async def speak_via_powershell(text: str) -> bool:
    if not text or not text.strip():
        return True
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _speak_powershell_sync, text)
