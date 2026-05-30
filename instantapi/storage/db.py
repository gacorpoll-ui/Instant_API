"""SQLite storage for saving scraped API configurations."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from instantapi.ai.detector import DetectionResult, EndpointSchema, FieldSchema
from instantapi.config import DB_FILE, APP_DIR


async def init_db() -> None:
    """Initialize the database schema."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS apis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                site_description TEXT DEFAULT '',
                endpoints_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)
        await db.commit()


async def save_api(result: DetectionResult) -> int:
    """Save a detection result to the database.

    Returns:
        The ID of the saved record.
    """
    await init_db()
    now = datetime.now(timezone.utc).isoformat()

    # Serialize endpoints
    endpoints_data = []
    for ep in result.endpoints:
        endpoints_data.append({
            "name": ep.name,
            "description": ep.description,
            "method": ep.method,
            "item_count": ep.item_count,
            "schema_fields": {
                k: {"type": v.type, "description": v.description, "example": v.example}
                for k, v in ep.schema_fields.items()
            },
            "sample_data": ep.sample_data,
        })

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            """INSERT INTO apis (url, site_description, endpoints_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (result.source_url, result.site_description, json.dumps(endpoints_data), now, now),
        )
        await db.commit()
        return cursor.lastrowid or 0


async def list_apis() -> list[dict[str, Any]]:
    """List all saved APIs."""
    await init_db()
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, url, site_description, created_at, is_active FROM apis ORDER BY id DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_api(api_id: int) -> DetectionResult | None:
    """Load a saved API by ID."""
    await init_db()
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM apis WHERE id = ?", (api_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None

            row_dict = dict(row)
            endpoints_data = json.loads(row_dict["endpoints_json"])

            endpoints = []
            for ep_data in endpoints_data:
                schema_fields = {}
                for k, v in ep_data.get("schema_fields", {}).items():
                    schema_fields[k] = FieldSchema(**v)
                endpoints.append(
                    EndpointSchema(
                        name=ep_data["name"],
                        description=ep_data.get("description", ""),
                        method=ep_data.get("method", "GET"),
                        item_count=ep_data.get("item_count", 0),
                        schema_fields=schema_fields,
                        sample_data=ep_data.get("sample_data", []),
                    )
                )

            return DetectionResult(
                endpoints=endpoints,
                site_description=row_dict.get("site_description", ""),
                source_url=row_dict["url"],
            )


async def delete_api(api_id: int) -> bool:
    """Delete a saved API."""
    await init_db()
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("DELETE FROM apis WHERE id = ?", (api_id,))
        await db.commit()
        return (cursor.rowcount or 0) > 0
