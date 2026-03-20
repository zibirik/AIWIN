from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, List

from ..event_bus import Event, EventBus, EventType


class Agent(ABC):
    """
    Базовый класс агента JARVIS.
    """

    name: str = "base-agent"

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus

    @property
    @abstractmethod
    def subscriptions(self):  # -> Iterable[EventType]
        ...

    async def start(self) -> None:
        # Подписка на интересующие события.
        for etype in self.subscriptions:
            await self.bus.subscribe(etype, self.on_event)

    @abstractmethod
    async def on_event(self, event: Event) -> None:
        ...


def build_default_agents(bus: EventBus, rust_client: Any = None) -> List[Agent]:
    from .conversation_agent import ConversationAgent
    from .planner_agent import PlannerAgent
    from .research_agent import ResearchAgent
    from .memory_agent import MemoryAgent
    from .system_agent import SystemAgent
    from .executor_agent import ExecutorAgent
    from .confirmation_agent import ConfirmationAgent

    agents: List[Agent] = [
        ConversationAgent(bus=bus),
        PlannerAgent(bus=bus),
        ResearchAgent(bus=bus),
        MemoryAgent(bus=bus),
        SystemAgent(bus=bus),
        ConfirmationAgent(bus=bus),
    ]
    if rust_client is not None:
        agents.append(ExecutorAgent(bus=bus, rust_client=rust_client))
        from .screen_reader_agent import ScreenReaderAgent
        agents.append(ScreenReaderAgent(bus=bus, rust_client=rust_client))
    return agents

