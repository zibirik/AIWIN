from __future__ import annotations

import ast
import operator as op
import re
from datetime import datetime
from typing import Any, Optional

import requests

# --- Безопасное вычисление арифметики (только числа и + - * / ** % и скобки) ---

_ALLOWED_BINOPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}
_ALLOWED_UNARY = {ast.UAdd: op.pos, ast.USub: op.neg}


def _eval_ast(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("только числа")
    if isinstance(node, ast.BinOp):
        if type(node.op) not in _ALLOWED_BINOPS:
            raise ValueError("операция не разрешена")
        return _ALLOWED_BINOPS[type(node.op)](_eval_ast(node.left), _eval_ast(node.right))
    if isinstance(node, ast.UnaryOp):
        if type(node.op) not in _ALLOWED_UNARY:
            raise ValueError("унарная операция не разрешена")
        return _ALLOWED_UNARY[type(node.op)](_eval_ast(node.operand))
    raise ValueError("выражение не поддерживается")


_WORDS_NUM: list[tuple[str, str]] = [
    ("одиннадцать", "11"),
    ("двенадцать", "12"),
    ("тринадцать", "13"),
    ("четырнадцать", "14"),
    ("пятнадцать", "15"),
    ("шестнадцать", "16"),
    ("семнадцать", "17"),
    ("восемнадцать", "18"),
    ("девятнадцать", "19"),
    ("двадцать", "20"),
    ("тридцать", "30"),
    ("сорок", "40"),
    ("пятьдесят", "50"),
    ("сто", "100"),
    ("ноль", "0"),
    ("один", "1"),
    ("одна", "1"),
    ("одно", "1"),
    ("два", "2"),
    ("две", "2"),
    ("три", "3"),
    ("четыре", "4"),
    ("пять", "5"),
    ("шесть", "6"),
    ("семь", "7"),
    ("восемь", "8"),
    ("девять", "9"),
    ("десять", "10"),
]


def _words_to_digits_expr(s: str) -> str:
    """«один плюс один» → «1+1» (простые случаи для ASR)."""
    t = s.lower()
    for w, d in _WORDS_NUM:
        t = re.sub(rf"\b{re.escape(w)}\b", d, t)
    t = re.sub(r"\bплюс\b", "+", t)
    t = re.sub(r"\bминус\b", "-", t)
    t = re.sub(r"\bумножить\s+на\b", "*", t)
    t = re.sub(r"\bразделить\s+на\b", "/", t)
    t = re.sub(r"\bна\b", "*", t)  # «два на три» как 2*3
    return re.sub(r"\s+", "", t)


def _normalize_math_expr(raw: str) -> str:
    s = (raw or "").strip()
    s = re.sub(r"^(сколько\s+будет|сколько\s+это|посчитай|вычисли)\s+", "", s, flags=re.IGNORECASE)
    s = s.replace(",", ".").replace("×", "*").replace("х", "*").replace("÷", "/")
    s = s.rstrip(".,!?;:")
    for tail in (" пожалуйста", " плиз"):
        if s.lower().endswith(tail):
            s = s[: -len(tail)].strip()
    # если есть русские слова чисел — конвертируем
    if re.search(r"[а-яё]{2,}", s, re.IGNORECASE):
        s = _words_to_digits_expr(s)
    return s


def run_skill_math(expression: str) -> tuple[bool, str]:
    expr = _normalize_math_expr(expression)
    if not expr:
        return False, "Скажите выражение, например: сколько будет два плюс два — или используйте цифры."
    try:
        tree = ast.parse(expr, mode="eval")
        value = _eval_ast(tree)
        if abs(value - round(value)) < 1e-9:
            pretty = str(int(round(value)))
        else:
            pretty = f"{value:.6g}"
        return True, f"Получится {pretty}."
    except Exception as e:
        return False, f"Не смог посчитать «{expression}». Попробуйте цифры и знаки плюс, минус, умножить, разделить."


def run_skill_time() -> tuple[bool, str]:
    now = datetime.now()
    # Локальная зона уже в now
    wd = [
        "понедельник",
        "вторник",
        "среда",
        "четверг",
        "пятница",
        "суббота",
        "воскресенье",
    ][now.weekday()]
    text = now.strftime(f"Сейчас %H:%M, {wd}, %d.%m.%Y.")
    return True, text


_GEO = "https://geocoding-api.open-meteo.com/v1/search"
_WEATHER = "https://api.open-meteo.com/v1/forecast"


def run_skill_weather(city: Optional[str]) -> tuple[bool, str]:
    place = (city or "").strip() or "Москва"
    try:
        gr = requests.get(
            _GEO,
            params={"name": place, "count": 1, "language": "ru", "format": "json"},
            timeout=12,
        )
        gr.raise_for_status()
        gdata = gr.json()
        results = gdata.get("results") or []
        if not results:
            return False, f"Не нашёл город «{place}». Уточните название."
        lat = results[0]["latitude"]
        lon = results[0]["longitude"]
        label = results[0].get("name") or place
        country = results[0].get("country") or ""
        wr = requests.get(
            _WEATHER,
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true",
                "timezone": "auto",
            },
            timeout=12,
        )
        wr.raise_for_status()
        wdata = wr.json()
        cw = wdata.get("current_weather") or {}
        temp = cw.get("temperature")
        code = cw.get("weathercode")
        wind = cw.get("windspeed")
        desc = _weathercode_ru(code)
        parts = [f"В {label}" + (f", {country}" if country else "") + ":"]
        if temp is not None:
            parts.append(f"около {temp:g} градусов")
        if desc:
            parts.append(desc)
        if wind is not None:
            parts.append(f"ветер примерно {wind:g} км/ч")
        return True, ", ".join(parts) + "."
    except requests.RequestException as e:
        return False, f"Не удалось получить погоду: {e}"


def _weathercode_ru(code: Any) -> str:
    try:
        c = int(code)
    except (TypeError, ValueError):
        return ""
    # WMO Weather interpretation codes (упрощённо)
    if c == 0:
        return "ясно"
    if c in (1, 2, 3):
        return "переменная облачность"
    if c in (45, 48):
        return "туман"
    if c in (51, 53, 55, 56, 57):
        return "морось"
    if c in (61, 63, 65, 80, 81, 82):
        return "дождь"
    if c in (71, 73, 75, 77, 85, 86):
        return "снег"
    if c in (95, 96, 99):
        return "гроза"
    return ""
