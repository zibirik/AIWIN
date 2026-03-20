from __future__ import annotations

from typing import Any, Dict

import httpx


class DeepSeekClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    async def ask(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Базовый запрос к DeepSeek. Подробный формат будет настроен позже.
        """
        if not self.api_key:
            return {"error": "DeepSeek API key is not configured"}

        payload: Dict[str, Any] = {"prompt": prompt}
        payload.update(kwargs)

        resp = await self._client.post(
            f"{self.base_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

