from __future__ import annotations

import os
from typing import Any, Dict

import yaml


def load_config() -> Dict[str, Any]:
    # Сначала ищем config в корне проекта (родитель ai_core)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    config_path = os.path.join(base_dir, "config", "config.yaml")
    if not os.path.exists(config_path):
        # Затем в ai_core/config (если запуск из репозитория без корневого config)
        alt = os.path.join(os.path.dirname(__file__), "..", "config", "config.yaml")
        config_path = os.path.abspath(alt) if os.path.exists(alt) else config_path
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

