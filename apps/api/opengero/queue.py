"""Job queue. Uses Redis/RQ when available, otherwise an in-process fallback."""

from __future__ import annotations

import logging
from typing import Any

from .config import get_settings

log = logging.getLogger(__name__)
_memory_queue: list[tuple[str, tuple, dict]] = []


def enqueue(func_path: str, *args: Any, **kwargs: Any) -> None:
    settings = get_settings()
    try:
        from redis import Redis
        from rq import Queue

        redis = Redis.from_url(settings.redis_url)
        redis.ping()
        Queue("opengero", connection=redis).enqueue(func_path, *args, **kwargs)
        return
    except Exception as exc:
        log.info("Redis queue unavailable (%s); using in-process fallback", exc)
        _memory_queue.append((func_path, args, kwargs))


def drain_memory_queue() -> int:
    """Execute queued in-process jobs. Used by tests and sqlite/dev mode."""
    from importlib import import_module

    count = 0
    while _memory_queue:
        path, args, kwargs = _memory_queue.pop(0)
        module_name, _, func_name = path.rpartition(".")
        fn = getattr(import_module(module_name), func_name)
        fn(*args, **kwargs)
        count += 1
    return count


def publish_job_event(job_id: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    try:
        import json

        from redis import Redis

        redis = Redis.from_url(settings.redis_url)
        redis.publish(f"job:{job_id}", json.dumps(payload))
    except Exception:
        pass
