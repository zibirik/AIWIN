from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from typing import Any, List

from fastapi import FastAPI

from ..event_bus import EventBus


@dataclass
class PluginContext:
    app: FastAPI
    bus: EventBus


def load_plugins(paths: list[str], ctx: PluginContext) -> List[Any]:
    loaded: List[Any] = []
    for base_path in paths:
        if not os.path.isdir(base_path):
            continue
        for entry in os.listdir(base_path):
            if entry.startswith("_"):
                continue
            full_path = os.path.join(base_path, entry)
            if os.path.isdir(full_path):
                module_path = os.path.join(full_path, "__init__.py")
                module_name = f"plugins.{entry}"
            elif entry.endswith(".py"):
                module_path = full_path
                module_name = f"plugins.{entry[:-3]}"
            else:
                continue

            if not os.path.exists(module_path):
                continue

            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                register = getattr(module, "register", None)
                if callable(register):
                    register(ctx)
                    loaded.append(module)
    return loaded

