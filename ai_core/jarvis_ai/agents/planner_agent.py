from __future__ import annotations

from typing import Iterable

from ..event_bus import Event, EventBus, EventType
from ..planner.planner_engine import PlannerEngine
from ..planner.task_graph import TaskGraph
from .base import Agent


class PlannerAgent(Agent):
    name = "planner-agent"

    def __init__(self, bus: EventBus) -> None:
        super().__init__(bus)
        self.planner = PlannerEngine()

    @property
    def subscriptions(self) -> Iterable[EventType]:
        return [EventType.INTENT_DETECTED]

    async def on_event(self, event: Event) -> None:
        payload = event.payload or {}
        goal = payload.get("goal") or payload.get("text", "")
        intent = payload.get("intent", "")
        slots = payload.get("slots") or {}
        if intent in ("read_screen", "screen_reader_next", "screen_reader_prev", "screen_reader_stop", "screen_reader_repeat"):
            return
        graph = self.planner.build_plan_from_intent(intent, slots, goal)
        if graph is None:
            graph = self.planner.build_simple_plan(goal)
        try:
            print(f"[JARVIS] План: intent={intent}, задач={len(graph.tasks)}", flush=True)
        except Exception:
            pass
        await self.bus.publish(
            Event.new(
                type=EventType.TASK_GRAPH_READY,
                source=self.name,
                payload={"goal": goal, "intent": intent, "task_graph": graph.model_dump()},
                correlation_id=event.correlation_id,
            )
        )
