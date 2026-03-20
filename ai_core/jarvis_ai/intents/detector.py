from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Паттерны интентов для доступности: экран, клик по тексту, приложения, прокрутка, ввод, подтверждение.
INTENT_PATTERNS = [
    # Локальные навыки (математика, время, погода) и создание папки — до общих шаблонов
    (r"(который\s+час|сколько\s+времени|какое\s+время|текущее\s+время|сколько\s+сейчас\s+времени)", "skill_time", {}),
    (r"(?:какая\s+)?(?:сейчас\s+)?погода\s+в\s+(.+)", "skill_weather", {"city": 1}),
    # «погода, Санкт-Петербург» (часто так выходит из ASR)
    (r"(?:какая\s+)?(?:сейчас\s+)?погода\s*,\s*(.+)", "skill_weather", {"city": 1}),
    (r"(какая\s+погода|погода\s+сейчас|погода\s+какая|погода\s+на\s+улице)", "skill_weather", {"city": ""}),
    (r"(сколько\s+будет|сколько\s+это|посчитай|вычисли)\s+(.+)", "skill_math", {"expression": 2}),
    (r"(создай|создать)\s+папку\s+(.+?)\s+на\s+рабочем\s+столе", "create_folder", {"folder_name": 2}),
    (r"(создай|создать)\s+на\s+рабочем\s+столе\s+папку\s+(.+)", "create_folder", {"folder_name": 2}),
    (r"(создай|создать)\s+папку\s+(.+)", "create_folder", {"folder_name": 2}),
    (r"(прочитай|читай|озвучь)\s*(экран|что\s+на\s+экране|текст\s+с\s+экрана)", "read_screen", {}),
    (r"(что\s+на\s+экране|прочитай\s+экран)", "read_screen", {}),
    (r"читалка|экранный\s+читал", "read_screen", {}),
    (r"(дальше|следующ|next)", "screen_reader_next", {}),
    (r"(назад|предыдущ|prev)", "screen_reader_prev", {}),
    (r"(стоп|останови|stop)", "screen_reader_stop", {}),
    (r"(повтори|ещё\s+раз|repeat)", "screen_reader_repeat", {}),
    (r"кликни\s+(по\s+)?(?:кнопке\s+)?[\"']?([^\"']+)[\"']?", "click_button", {"text": 2}),
    (r"нажми\s+(?:кнопку\s+)?[\"']?([^\"']+)[\"']?", "click_button", {"text": 1}),
    (r"выбери\s+[\"']?([^\"']+)[\"']?", "click_button", {"text": 1}),
    (r"нажми\s+([^\s]+)", "click_button", {"text": 1}),
    (r"(открой|запусти)\s+([^\s]+(?:\s+[^\s]+)*)", "open_app", {"app_name": 2}),
    (r"(открой|запусти)\s+браузер", "open_app", {"app_name": "браузер"}),
    (r"(открой|запусти)\s*стим", "open_app", {"app_name": "стим"}),
    (r"откройстим|открой\s*стим", "open_app", {"app_name": "стим"}),
    (r"(прокрути|скролль?)\s+(вниз|вверх|down|up)", "scroll", {"direction": 2}),
    (r"(введи|напиши|напечатай)\s+(?:текст\s+)?[\"']?([^\"']+)[\"']?", "type_text", {"text": 2}),
    (r"\b(да|подтверждаю|подтвердить|yes|ок|выполни)\b", "confirm", {}),
    (r"\b(нет|отмена|отменить|cancel|не\s+надо)\b", "cancel", {}),
]


@dataclass
class Intent:
    name: str
    slots: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""

    def get(self, key: str, default: Any = None) -> Any:
        return self.slots.get(key, default)


def _normalize_slot_value(val: str) -> str:
    if not val:
        return val
    return val.strip().rstrip(".,!?;:").strip()


def _extract_slots(text: str, pattern: re.Pattern, slot_indices: Dict[str, Any]) -> Dict[str, Any]:
    m = pattern.search(text)
    if not m:
        return {}
    slots = {}
    for key, idx in slot_indices.items():
        if isinstance(idx, int) and m.lastindex is not None and idx <= m.lastindex:
            slots[key] = _normalize_slot_value(m.group(idx))
        elif isinstance(idx, str):
            slots[key] = idx
    return slots


def detect_intent(text: str) -> Optional[Intent]:
    if not text or not text.strip():
        return None
    t = text.strip().lower()
    for pattern_str, intent_name, slot_indices in INTENT_PATTERNS:
        try:
            pattern = re.compile(pattern_str, re.IGNORECASE)
        except re.error:
            continue
        m = pattern.search(t)
        if not m:
            continue
        slots = _extract_slots(t, pattern, slot_indices)
        return Intent(name=intent_name, slots=slots, raw_text=text)
    return Intent(name="unknown", slots={"raw": text}, raw_text=text)


class IntentDetector:
    def __init__(self) -> None:
        pass

    def detect(self, text: str) -> Intent:
        return detect_intent(text) or Intent(name="unknown", slots={"raw": text}, raw_text=text)
