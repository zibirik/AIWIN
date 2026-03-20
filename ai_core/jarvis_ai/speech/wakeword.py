from __future__ import annotations

import re
from typing import List, Tuple

# Фразы активации: как Whisper часто распознаёт «джарвис» (джавис, джервес и т.д.)
DEFAULT_WAKE_PHRASES = [
    "привет джарвис",
    "привет, джарвис",
    "привет джервес",
    "привет, джервес",
    "привет джавис",
    "привет, джавис",
    "джарвис",
    "джервес",
    "джавис",
    "дарвис",
    "джарвиз",
    "джавиз",
    "jarvis",
    "hello jarvis",
    "hey jarvis",
]


class WakeWordDetector:
    def __init__(self, wake_word: str = "джарвис", wake_phrases: List[str] | None = None) -> None:
        self.wake_word = wake_word.lower()
        self.wake_phrases = [p.lower().strip() for p in (wake_phrases or DEFAULT_WAKE_PHRASES)]
        self.wake_phrases = sorted(set(self.wake_phrases), key=len, reverse=True)

    def is_wake_word(self, text: str) -> bool:
        return self.wake_word in text.lower()

    def _normalize_for_match(self, s: str) -> str:
        """Убираем повторы букв и лишние пробелы — Whisper может выдать «джаарвис»."""
        s = re.sub(r"\s+", " ", s.strip().lower())
        return re.sub(r"(.)\1+", r"\1", s)

    def detect_and_extract_command(self, text: str) -> Tuple[bool, str]:
        """
        Проверяет, есть ли фраза активации в тексте.
        Возвращает (найдено, команда) — команда это остаток текста после фразы активации.
        """
        if not text or not text.strip():
            return False, ""
        t = text.strip().lower()
        t_norm = self._normalize_for_match(t)
        for phrase in self.wake_phrases:
            if not phrase:
                continue
            pos = t.find(phrase)
            if pos == -1:
                # Поиск в нормализованной строке (напр. «джаарвис» → «джавис»)
                phrase_norm = self._normalize_for_match(phrase)
                pos_norm = t_norm.find(phrase_norm)
                if pos_norm != -1:
                    after = t_norm[pos_norm + len(phrase_norm):].strip()
                    after = re.sub(r"^\s*[,\-—:]\s*", "", after).strip()
                    return True, after or text.strip()
                continue
            after = text[pos + len(phrase):].strip()
            after = re.sub(r"^\s*[,\-—:]\s*", "", after).strip()
            return True, after or text.strip()
        # Похоже на «джарвис» одной буквой (джавис, дарвис, джарвиз)
        if self.wake_word in t:
            parts = re.split(re.escape(self.wake_word), t, maxsplit=1, flags=re.IGNORECASE)
            after = (parts[1].strip() if len(parts) > 1 else "").strip()
            after = re.sub(r"^\s*[,\-—:]\s*", "", after).strip()
            return True, after or text.strip()
        if "джавис" in t or "джервес" in t or "дарвис" in t or "джарвиз" in t or "джавиз" in t or "jarvis" in t_norm:
            for variant in ["джавис", "джервес", "дарвис", "джарвиз", "джавиз", "jarvis"]:
                pos = t.find(variant)
                if pos == -1:
                    pos = t_norm.find(variant)
                if pos != -1:
                    after = text[pos + len(variant):].strip()
                    after = re.sub(r"^\s*[,\-—:]\s*", "", after).strip()
                    return True, after or text.strip()
        # Слово начинается на «джа» или «джер» — считаем обращением к Джарвису (мало таких слов)
        for m in re.finditer(r"\b(джа\w*|джер\w*)\b", t):
            word = m.group(1)
            pos = m.start()
            after = text[pos + len(word):].strip()
            after = re.sub(r"^\s*[,\-—:]\s*", "", after).strip()
            return True, after or text.strip()
        return False, ""
