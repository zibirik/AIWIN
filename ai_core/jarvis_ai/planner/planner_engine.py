from __future__ import annotations

import os
from typing import Any, Dict, Optional

from .task_graph import Task, TaskGraph

# Пути по умолчанию для типичных приложений. Для браузера проверяем несколько вариантов.
def _edge_path() -> str:
    for p in (
        "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    ):
        if os.path.isfile(p):
            return p
    return "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"


def _steam_path() -> str:
    for p in (
        "C:\\Program Files (x86)\\Steam\\steam.exe",
        "C:\\Program Files\\Steam\\steam.exe",
    ):
        if os.path.isfile(p):
            return p
    return "C:\\Program Files (x86)\\Steam\\steam.exe"


DEFAULT_APP_PATHS = {
    "браузер": _edge_path(),
    "browser": _edge_path(),
    "блокнот": "notepad.exe",
    "notepad": "notepad.exe",
    "калькулятор": "calc.exe",
    "calculator": "calc.exe",
    "стим": _steam_path(),
    "steam": _steam_path(),
}

# Опечатки и варианты названий -> каноническое имя приложения
APP_NAME_ALIASES = {
    "браусер": "браузер",
    "браус": "браузер",
    "броузер": "браузер",
    "бравзер": "браузер",
    "брузер": "браузер",
    "блакнот": "блокнот",
    "калькултор": "калькулятор",
}


class PlannerEngine:
    def __init__(self, get_app_path_callback: Optional[Any] = None) -> None:
        self._get_app_path = get_app_path_callback

    def build_simple_plan(self, goal: str) -> TaskGraph:
        graph = TaskGraph()
        graph.add_task(
            Task(id="task-1", description=goal, command={"type": "NOOP", "params": {}})
        )
        return graph

    def build_plan_from_intent(self, intent: str, slots: Dict[str, Any], goal: str = "") -> Optional[TaskGraph]:
        """Строит граф задач по интенту и слотам. Для read_screen возвращает None (обрабатывает ScreenReaderAgent)."""
        if intent in ("read_screen", "screen_reader_next", "screen_reader_prev", "screen_reader_stop", "screen_reader_repeat"):
            return None
        if intent == "skill_time":
            g = TaskGraph()
            g.add_task(
                Task(
                    id="skill-time",
                    description="Узнать время",
                    command={"type": "SKILL_ANSWER", "params": {"skill": "time"}},
                )
            )
            return g
        if intent == "skill_math":
            expr = (slots.get("expression") or "").strip()
            if not expr:
                expr = (goal or "").strip()
            g = TaskGraph()
            g.add_task(
                Task(
                    id="skill-math",
                    description=f"Посчитать: {expr}",
                    command={"type": "SKILL_ANSWER", "params": {"skill": "math", "expression": expr}},
                )
            )
            return g
        if intent == "skill_weather":
            city = slots.get("city", "")
            if isinstance(city, str):
                city = city.strip()
            g = TaskGraph()
            g.add_task(
                Task(
                    id="skill-weather",
                    description=f"Погода: {city or 'по умолчанию'}",
                    command={"type": "SKILL_ANSWER", "params": {"skill": "weather", "city": city}},
                )
            )
            return g
        if intent == "create_folder":
            raw = (slots.get("folder_name") or "").strip()
            if not raw:
                return None
            g = TaskGraph()
            g.add_task(
                Task(
                    id="mkdir-1",
                    description=f"Создать папку «{raw}»",
                    command={
                        "type": "CREATE_FOLDER",
                        "params": {"folder_name": raw, "where": "desktop"},
                    },
                )
            )
            return g
        if intent == "click_button":
            text = slots.get("text", "").strip()
            if not text:
                return None
            graph = TaskGraph()
            graph.add_task(
                Task(
                    id="click-1",
                    description=f"Клик по «{text}»",
                    command={"type": "CLICK_BY_TEXT", "params": {"text": text}},
                )
            )
            return graph
        if intent == "open_app":
            raw = (slots.get("app_name") or "").strip().rstrip(".,!?;:") or goal
            if not raw:
                return None
            raw_lower = raw.lower().strip()
            if raw_lower.startswith("и "):
                raw = raw[2:].strip()
            app_names = [a.strip() for a in raw.replace(" и ", ",").split(",") if a.strip()][:3]
            graph = TaskGraph()
            for i, app_name in enumerate(app_names):
                app_name_lower = app_name.lower()
                app_name = APP_NAME_ALIASES.get(app_name_lower, app_name)
                path = None
                if self._get_app_path:
                    try:
                        path = self._get_app_path(app_name)
                    except Exception:
                        pass
                if not path:
                    path = DEFAULT_APP_PATHS.get(app_name.lower(), app_name)
                graph.add_task(
                    Task(
                        id=f"open-{i+1}",
                        description=f"Открыть {app_name}",
                        command={"type": "OPEN_APPLICATION", "params": {"path": path, "app_name": app_name}},
                    )
                )
            return graph
        if intent == "scroll":
            direction = (slots.get("direction") or "вниз").strip().lower()
            graph = TaskGraph()
            graph.add_task(
                Task(
                    id="scroll-1",
                    description=f"Прокрутить {direction}",
                    command={"type": "SCROLL", "params": {"direction": direction}},
                )
            )
            return graph
        if intent == "type_text":
            text = slots.get("text", "").strip()
            if not text:
                return None
            graph = TaskGraph()
            graph.add_task(
                Task(
                    id="type-1",
                    description="Ввод текста",
                    command={"type": "TYPE_TEXT", "params": {"text": text}},
                )
            )
            return graph
        if intent in ("confirm", "cancel"):
            return None
        return self.build_simple_plan(goal or intent)

    def build_plan_from_decomposition(self, goal: str, steps: Dict[str, Any]) -> TaskGraph:
        graph = TaskGraph()
        _ = (goal, steps)
        return graph
