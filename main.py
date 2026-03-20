"""
Запуск JARVIS из корня репозитория (AIWin).
Основной код лежит в папке ai_core — здесь только перенаправление.
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
_AI_CORE = os.path.join(_ROOT, "ai_core")
if not os.path.isdir(_AI_CORE):
    raise SystemExit(f"Не найдена папка ai_core: {_AI_CORE}")

os.chdir(_AI_CORE)
if _AI_CORE not in sys.path:
    sys.path.insert(0, _AI_CORE)

# Зависимости ставятся в ai_core\.venv — py/другой Python их не видит.
try:
    import fastapi  # noqa: F401
except ModuleNotFoundError:
    _venv_py = os.path.join(_AI_CORE, ".venv", "Scripts", "python.exe")
    _req = os.path.join(_AI_CORE, "requirements.txt")
    print(
        "Не найден fastapi. Сейчас используется:\n"
        f"  {sys.executable}\n"
        "Установите зависимости и запускайте интерпретатором из venv:\n"
        f'  "{_venv_py}" -m pip install -r "{_req}"\n'
        f'  "{_venv_py}" "{os.path.join(_ROOT, "main.py")}"',
        file=sys.stderr,
    )
    raise SystemExit(1)

from jarvis_ai.server import create_app, run_app  # noqa: E402


def main() -> None:
    app = create_app()
    run_app(app)


if __name__ == "__main__":
    main()
