from __future__ import annotations

from typing import Any, Dict, Optional

_pending: Optional[Dict[str, Any]] = None


def set_pending(command: Dict[str, Any], task_id: str = "") -> None:
    global _pending
    _pending = {"command": command, "task_id": task_id}


def get_pending() -> Optional[Dict[str, Any]]:
    return _pending


def clear_pending() -> None:
    global _pending
    _pending = None
