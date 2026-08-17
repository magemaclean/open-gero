from __future__ import annotations

import json
import time
import uuid
from typing import Any

from ..config import get_settings

TTL_SECONDS = 15 * 60
_memory: dict[str, tuple[float, str]] = {}
_downloads: dict[str, tuple[float, dict[str, Any]]] = {}


def _now() -> float:
    return time.time()


def _purge(store: dict[str, tuple[float, Any]]) -> None:
    cutoff = _now() - TTL_SECONDS
    for key in [k for k, (ts, _) in store.items() if ts < cutoff]:
        store.pop(key, None)


def _redis():
    settings = get_settings()
    try:
        from redis import Redis

        client = Redis.from_url(settings.redis_url)
        client.ping()
        return client
    except Exception:
        return None


def put_pending(user_id: str, payload: dict[str, Any]) -> str:
    confirm_id = str(uuid.uuid4())
    body = json.dumps(payload)
    key = f"opengero:assistant:pending:{user_id}:{confirm_id}"
    client = _redis()
    if client is not None:
        client.setex(key, TTL_SECONDS, body)
        return confirm_id
    _purge(_memory)
    _memory[key] = (_now(), body)
    return confirm_id


def pop_pending(user_id: str, confirm_id: str) -> dict[str, Any] | None:
    key = f"opengero:assistant:pending:{user_id}:{confirm_id}"
    client = _redis()
    raw = None
    if client is not None:
        raw = client.get(key)
        if raw is not None:
            client.delete(key)
            return json.loads(raw)
        return None
    _purge(_memory)
    item = _memory.pop(key, None)
    if item is None:
        return None
    return json.loads(item[1])


def put_download(user_id: str, filename: str, content: bytes, media_type: str) -> str:
    download_id = str(uuid.uuid4())
    payload = {
        "user_id": user_id,
        "filename": filename,
        "media_type": media_type,
        "content": content,
    }
    client = _redis()
    if client is not None:
        meta = json.dumps({"user_id": user_id, "filename": filename, "media_type": media_type})
        client.setex(f"opengero:assistant:dlmeta:{download_id}", TTL_SECONDS, meta)
        client.setex(f"opengero:assistant:dl:{download_id}", TTL_SECONDS, content)
        return download_id
    _purge(_downloads)
    _downloads[download_id] = (_now(), payload)
    return download_id


def get_download(user_id: str, download_id: str) -> dict[str, Any] | None:
    client = _redis()
    if client is not None:
        meta_raw = client.get(f"opengero:assistant:dlmeta:{download_id}")
        body = client.get(f"opengero:assistant:dl:{download_id}")
        if not meta_raw or body is None:
            return None
        meta = json.loads(meta_raw)
        if meta.get("user_id") != user_id:
            return None
        return {**meta, "content": body}
    _purge(_downloads)
    item = _downloads.get(download_id)
    if item is None:
        return None
    payload = item[1]
    if payload.get("user_id") != user_id:
        return None
    return payload
