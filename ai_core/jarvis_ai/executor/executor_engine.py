from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from ..skills.local_skills import run_skill_math, run_skill_time, run_skill_weather
from .command_schema import Command, CommandType

# Команды, требующие голосового подтверждения.
DANGEROUS_PATTERNS = [
    r"setup\.exe",
    r"install\.exe",
    r"installer",
    r"unins\d*\.exe",
    r"del\.exe",
    r"format\b",
    r"rmdir\b",
    r"remove\b",
]


def _safe_folder_name(raw: str) -> str:
    s = (raw or "").strip().strip("\"'")
    s = re.sub(r"\s+на\s+рабочем\s+столе\s*$", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "", s)
    return (s[:200] or "").strip()


def _desktop_path() -> Path:
    home = Path.home()
    for name in ("Desktop", "Рабочий стол"):
        d = home / name
        if d.is_dir():
            return d
    return home / "Desktop"


def is_dangerous_command(command: Command) -> bool:
    if command.type == CommandType.OPEN_APPLICATION:
        path = (command.params or {}).get("path") or (command.params or {}).get("app_path", "")
        path_lower = (path or "").lower()
        for pat in DANGEROUS_PATTERNS:
            if re.search(pat, path_lower):
                return True
    return False


class ExecutionEngine:
    def __init__(self, rust_client: Any, vision: Any = None) -> None:
        self.rust_client = rust_client
        self.vision = vision

    async def execute(self, command: Command) -> Dict[str, Any]:
        if command.type == CommandType.NOOP:
            return {"success": True, "message": "NOOP"}
        if command.type == CommandType.READ_SCREEN:
            return {"success": True, "message": "Handled by ScreenReaderAgent"}
        if command.type == CommandType.SKILL_ANSWER:
            return self._execute_skill(command.params or {})
        if command.type == CommandType.CREATE_FOLDER:
            return self._execute_create_folder(command.params or {})
        params = command.params or {}
        try:
            if command.type == CommandType.OPEN_APPLICATION:
                path = (params.get("path") or params.get("app_path", "") or "").strip()
                args = params.get("args", [])
                working_dir = params.get("working_dir", "") or ""
                if self.rust_client is not None:
                    r = await self.rust_client.launch_application(path, args=args, working_dir=working_dir)
                    ok = getattr(r, "success", False)
                    err = getattr(r, "error_message", "") or ""
                    return {"success": ok, "error": err}
                try:
                    if not path:
                        return {"success": False, "error": "path empty"}
                    app_name = params.get("app_name", path)
                    launched = False
                    if os.path.isfile(path):
                        subprocess.Popen(
                            [path] + list(args),
                            cwd=working_dir or None,
                            shell=False,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        launched = True
                    if not launched and (path.lower().endswith(".exe") or "\\" in path or "/" in path):
                        try:
                            subprocess.Popen(
                                f'start "" "{path}"',
                                shell=True,
                                stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                            launched = True
                        except Exception:
                            pass
                    if not launched:
                        subprocess.Popen(path, shell=True)
                        launched = True
                    print(f"[JARVIS] Opened: {app_name}", flush=True)
                    return {"success": True}
                except Exception as e:
                    print(f"[JARVIS] Launch error ({params.get('app_name', path)}): {e}", flush=True)
                    return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

        if self.rust_client is None and command.type not in (CommandType.NOOP, CommandType.READ_SCREEN):
            return {"success": False, "error": "Rust core client not available"}

        try:
            if command.type == CommandType.TYPE_TEXT:
                text = params.get("text", "")
                await self.rust_client.type_text(text)
                return {"success": True}
            if command.type == CommandType.CLICK:
                x, y = params.get("x", 0), params.get("y", 0)
                await self.rust_client.click_mouse(x, y)
                return {"success": True}
            if command.type == CommandType.CLICK_BY_TEXT:
                text = params.get("text", "").strip()
                if not text or not self.vision:
                    return {"success": False, "error": "CLICK_BY_TEXT requires vision and text"}
                coords = await self.vision.find_click_for_text(text)
                if not coords:
                    return {"success": False, "error": f"Текст «{text}» не найден на экране"}
                x, y = coords
                await self.rust_client.click_mouse(x, y)
                return {"success": True}
            if command.type == CommandType.SCROLL:
                direction = (params.get("direction") or "вниз").strip().lower()
                if hasattr(self.rust_client, "scroll"):
                    await self.rust_client.scroll(direction)
                    return {"success": True}
                return {"success": False, "error": "Прокрутка пока не поддерживается"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "Unknown command type"}

    def _execute_skill(self, params: Dict[str, Any]) -> Dict[str, Any]:
        skill = (params.get("skill") or "").strip().lower()
        if skill == "time":
            ok, text = run_skill_time()
            return {"success": ok, "message": text, "speak": text}
        if skill == "math":
            expr = params.get("expression") or params.get("text") or ""
            ok, text = run_skill_math(str(expr))
            return {"success": ok, "message": text, "speak": text}
        if skill == "weather":
            city = params.get("city")
            if isinstance(city, str):
                city = city.strip() or None
            ok, text = run_skill_weather(city)
            return {"success": ok, "message": text, "speak": text}
        return {"success": False, "error": f"Неизвестный навык: {skill}", "speak": "Неизвестный навык."}

    def _execute_create_folder(self, params: Dict[str, Any]) -> Dict[str, Any]:
        raw_name = params.get("folder_name") or params.get("name") or ""
        name = _safe_folder_name(str(raw_name))
        if not name:
            return {"success": False, "error": "empty name", "speak": "Скажите имя папки."}
        where = (params.get("where") or "desktop").strip().lower()
        try:
            if where in ("desktop", "рабочий стол", "рабочем столе"):
                base = _desktop_path()
            else:
                base = Path.home()
            target = (base / name).resolve()
            base_res = base.resolve()
            if not str(target).startswith(str(base_res)):
                return {"success": False, "error": "Недопустимый путь", "speak": "Не могу создать папку в этом месте."}
            target.mkdir(parents=False, exist_ok=True)
            msg = f"Папка «{name}» создана на рабочем столе." if where in ("desktop", "рабочий стол", "рабочем столе") else f"Папка «{name}» создана."
            return {"success": True, "message": msg, "speak": msg, "path": str(target)}
        except OSError as e:
            err = f"Ошибка: {e}"
            return {"success": False, "error": err, "speak": "Не удалось создать папку."}
