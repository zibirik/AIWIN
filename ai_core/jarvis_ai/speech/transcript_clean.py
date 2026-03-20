"""
Очистка текста от типичных «галлюцинаций» Whisper на фоне музыки/субтитров YouTube и т.п.
"""

from __future__ import annotations

import re


# Фразы из субтитров, тишины и фоновой музыки (часто попадают в лог)
_GARBAGE_PATTERNS = [
    re.compile(
        r"опряжен\w*\s+звонок|динамич\w*\s+музык\w*|фонов\w*\s+музык\w*",
        re.IGNORECASE,
    ),
    re.compile(
        r"редактор\s+субтитров[^.]*|корректор\s+[^.]+|субтитр\w*\s+[^.]{0,80}",
        re.IGNORECASE,
    ),
    re.compile(r"подписывайтесь\s+на\s+канал[^.]*", re.IGNORECASE),
    re.compile(r"\bмузык\w*\s+из\s+[^.]+", re.IGNORECASE),
    re.compile(r"\bсмотрите\s+также[^.]*", re.IGNORECASE),
]


def clean_transcript(text: str) -> str:
    if not text or not text.strip():
        return ""
    t = text.strip()
    for pat in _GARBAGE_PATTERNS:
        t = pat.sub(" ", t)
    # повторяющиеся короткие фрагменты (ASR-заикание)
    t = re.sub(r"(\b\w{2,20}\b)(\s+\1){2,}", r"\1", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip(" ,.;:—-")
    return t


def merge_tail_safely(main: str, tail: str, *, max_tail_len: int = 220) -> str:
    """Склеивает основной текст и хвост; отбрасывает слишком длинный/подозрительный хвост."""
    main = (main or "").strip()
    tail = clean_transcript(tail or "")
    if not tail or len(tail) < 2:
        return main
    if len(tail) > max_tail_len:
        return main
    # если хвост почти полностью уже есть в начале — не дублировать
    low_m, low_t = main.lower(), tail.lower()
    if low_t in low_m or low_m.endswith(low_t[: min(20, len(low_t))]):
        return main
    return f"{main} {tail}".strip()
