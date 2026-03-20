from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from .db import MemoryDB


class PreferencesStore:
    def __init__(self, db: MemoryDB) -> None:
        self._db = db

    async def get(self, key: str) -> Optional[Any]:
        conn = await self._db.connect()
        cursor = await conn.execute("SELECT value_json FROM preferences WHERE key = ?", (key,))
        row = await cursor.fetchone()
        if not row:
            return None
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, IndexError):
            return None

    async def set(self, key: str, value: Any) -> None:
        conn = await self._db.connect()
        now = datetime.now(timezone.utc).isoformat()
        await conn.execute(
            """INSERT INTO preferences (key, value_json, updated_at) VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at""",
            (key, json.dumps(value) if not isinstance(value, str) else json.dumps({"value": value}), now),
        )
        await conn.commit()

    async def get_app_path(self, app_name: str) -> Optional[str]:
        key = f"app_path:{app_name.strip().lower()}"
        val = await self.get(key)
        if isinstance(val, dict) and "path" in val:
            return val["path"]
        if isinstance(val, str):
            return val
        return None

    async def set_app_path(self, app_name: str, path: str) -> None:
        await self.set(f"app_path:{app_name.strip().lower()}", {"path": path})
