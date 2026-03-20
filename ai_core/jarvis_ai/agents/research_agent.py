from __future__ import annotations

from typing import Iterable

from ..event_bus import Event, EventBus, EventType
from .base import Agent


class ResearchAgent(Agent):
    name = "research-agent"

    @property
    def subscriptions(self) -> Iterable[EventType]:
        return [EventType.RESEARCH_REQUESTED]

    async def on_event(self, event: Event) -> None:
        query = (event.payload or {}).get("query", "")
        if not query:
            return
        try:
            from ..research.deepseek_client import DeepSeekClient
            from .. import config as cfg_mod
            cfg = cfg_mod.load_config()
            ds_cfg = cfg.get("deepseek", {})
            if not ds_cfg.get("enabled") or not ds_cfg.get("api_key"):
                await self.bus.publish(
                    Event.new(
                        type=EventType.RESEARCH_RESULT,
                        source=self.name,
                        payload={"query": query, "result": "DeepSeek disabled or no API key"},
                        correlation_id=event.correlation_id,
                    )
                )
                return
            client = DeepSeekClient(ds_cfg.get("base_url", "https://api.deepseek.com"), ds_cfg.get("api_key", ""))
            out = await client.ask(query)
            await self.bus.publish(
                Event.new(
                    type=EventType.RESEARCH_RESULT,
                    source=self.name,
                    payload={"query": query, "result": out},
                    correlation_id=event.correlation_id,
                )
            )
        except Exception as e:
            await self.bus.publish(
                Event.new(
                    type=EventType.ERROR,
                    source=self.name,
                    payload={"error": str(e), "query": query},
                    correlation_id=event.correlation_id,
                )
            )
