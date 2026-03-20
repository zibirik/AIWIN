from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel


class CommandType(str, Enum):
    OPEN_APPLICATION = "OPEN_APPLICATION"
    CLICK = "CLICK"
    CLICK_BY_TEXT = "CLICK_BY_TEXT"
    TYPE_TEXT = "TYPE_TEXT"
    SCROLL = "SCROLL"
    READ_SCREEN = "READ_SCREEN"
    RUN_TERMINAL = "RUN_TERMINAL"
    FILE_WRITE = "FILE_WRITE"
    SKILL_ANSWER = "SKILL_ANSWER"
    CREATE_FOLDER = "CREATE_FOLDER"
    NOOP = "NOOP"


class Command(BaseModel):
    type: CommandType
    params: Dict[str, Any]
    description: Optional[str] = None

