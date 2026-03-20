from __future__ import annotations

import asyncio
from typing import Any, Iterable

from ..event_bus import Event, EventBus, EventType
from ..executor.executor_engine import ExecutionEngine, is_dangerous_command
from ..executor.command_schema import Command, CommandType
from ..executor.confirmation_store import clear_pending, get_pending, set_pending
from ..vision.screen_vision import ScreenVision
from .base import Agent


class ExecutorAgent(Agent):
    name = "executor-agent"

    def __init__(self, bus: EventBus, rust_client: Any) -> None:
        super().__init__(bus)
        vision = ScreenVision(rust_client) if rust_client else None
        self.engine = ExecutionEngine(rust_client, vision=vision)

    @property
    def subscriptions(self) -> Iterable[EventType]:
        return [EventType.TASK_GRAPH_READY, EventType.CONFIRMATION_YES]

    async def _execute_task(self, task_id: str, cmd: dict, correlation_id: str | None) -> dict:
        cmd_type = cmd.get("type", "NOOP")
        params = cmd.get("params", {})
        command = Command(type=CommandType(cmd_type), params=params)
        result = await self.engine.execute(command)
        await self.bus.publish(
            Event.new(
                type=EventType.COMMAND_EXECUTED,
                source=self.name,
                payload={"task_id": task_id, "result": result},
                correlation_id=correlation_id,
            )
        )
        return result

    async def on_event(self, event: Event) -> None:
        if event.type == EventType.CONFIRMATION_YES:
            pending = event.payload or {}
            cmd = pending.get("command", {})
            task_id = pending.get("task_id", "confirmed")
            if cmd:
                await self._execute_task(task_id, cmd, event.correlation_id)
            clear_pending()
            return

        payload = event.payload or {}
        graph_data = payload.get("task_graph", {})
        tasks = graph_data.get("tasks", {})
        correlation_id = event.correlation_id
        if not tasks:
            return
        try:
            print(f"[JARVIS] Выполняю задач: {len(tasks)}", flush=True)
        except Exception:
            pass

        for tid, t in tasks.items():
            cmd = (t or {}).get("command")
            if not cmd:
                continue
            cmd_type = cmd.get("type", "NOOP")
            params = cmd.get("params", {})
            command = Command(type=CommandType(cmd_type), params=params)

            if is_dangerous_command(command):
                set_pending(cmd, tid)
                desc = (t or {}).get("description", cmd_type)
                await self.bus.publish(
                    Event.new(
                        type=EventType.CONFIRMATION_REQUIRED,
                        source=self.name,
                        payload={
                            "task_id": tid,
                            "command": cmd,
                            "description": desc,
                            "prompt": f"Подтвердите: {desc}. Скажите «Да» или «Отмена».",
                        },
                        correlation_id=correlation_id,
                    )
                )
                try:
                    from ..speech.tts import TTS
                    tts = TTS()
                    await tts.speak(f"Подтвердите действие: {desc}. Скажите «Да» или «Отмена».")
                except Exception:
                    pass
                return
            result = await self._execute_task(tid, cmd, correlation_id)
            if cmd_type == "OPEN_APPLICATION":
                try:
                    from ..speech.tts import TTS
                    tts = TTS()
                    if result.get("success"):
                        app = (cmd.get("params") or {}).get("app_name", "")
                        await tts.speak(f"Открыто. {app}" if app else "Готово.")
                    else:
                        await tts.speak("Не удалось открыть.")
                except Exception:
                    pass
            elif cmd_type in ("SKILL_ANSWER", "CREATE_FOLDER"):
                try:
                    from ..speech.tts import TTS

                    tts = TTS()
                    msg = (result.get("speak") or result.get("message") or "").strip()
                    if msg:
                        await tts.speak(msg)
                    elif not result.get("success"):
                        await tts.speak((result.get("error") or "Не получилось.")[:300])
                except Exception:
                    pass

        intent = payload.get("intent", "")
        if intent == "unknown" and len(tasks) == 1:
            try:
                from ..speech.tts import TTS
                from ..llm_client import ask_llm_sync

                loop = asyncio.get_running_loop()
                prompt = payload.get("goal") or payload.get("text") or ""
                print(f"[JARVIS][LLM] intent=unknown prompt_len={len(str(prompt))}", flush=True)
                answer = await loop.run_in_executor(None, ask_llm_sync, str(prompt))
                answer = (answer or "").strip()
                print(f"[JARVIS][LLM] answer_len={len(answer)}", flush=True)

                tts = TTS()
                if answer:
                    # TTS не любит слишком длинные ответы
                    if len(answer) > 400:
                        answer = answer[:400]
                    await tts.speak(answer)
                else:
                    await tts.speak(
                        "Не удалось получить ответ от ИИ. Скажите: открой браузер, открой блокнот, открой стим. Или задайте вопрос."
                    )
            except Exception as e:
                print(f"[JARVIS][LLM] executor unknown block error: {e}", flush=True)
                try:
                    from ..speech.tts import TTS
                    tts = TTS()
                    await tts.speak(
                        "Не понял вопрос. Скажите: открой браузер, открой блокнот, открой стим. Или задайте вопрос."
                    )
                except Exception:
                    pass

        await self.bus.publish(
            Event.new(
                type=EventType.TASK_COMPLETED,
                source=self.name,
                payload={"task_graph": graph_data},
                correlation_id=correlation_id,
            )
        )
