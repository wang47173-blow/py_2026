from __future__ import annotations

import os
import time
from collections import defaultdict, deque

try:
    from app.config import settings
except ModuleNotFoundError:  # test/runtime fallback in minimal env
    class _Settings:
        enable_rate_limit = True
        rate_limit_requests_per_minute = 60

    settings = _Settings()  # type: ignore

try:
    import redis
except Exception:  # noqa: BLE001
    redis = None

_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_REDIS_CLIENT = None


def _get_redis_client():
    global _REDIS_CLIENT
    redis_url = os.getenv("EKA_REDIS_URL", "")
    if not redis_url or redis is None:
        return None
    if _REDIS_CLIENT is None:
        _REDIS_CLIENT = redis.Redis.from_url(redis_url, decode_responses=True)
    return _REDIS_CLIENT


def _allow_request_memory(identity: str) -> bool:
    now = time.time()
    dq = _BUCKETS[identity]
    window_start = now - 60
    while dq and dq[0] < window_start:
        dq.popleft()
    if len(dq) >= settings.rate_limit_requests_per_minute:
        return False
    dq.append(now)
    return True


def _allow_request_redis(identity: str) -> bool:
    client = _get_redis_client()
    if client is None:
        return _allow_request_memory(identity)

    limit = int(settings.rate_limit_requests_per_minute)
    key = f"eka:rl:{identity}"
    now_ms = int(time.time() * 1000)
    window_start = now_ms - 60000

    pipe = client.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    _, count = pipe.execute()

    if int(count) >= limit:
        return False

    pipe = client.pipeline()
    pipe.zadd(key, {str(now_ms): now_ms})
    pipe.expire(key, 61)
    pipe.execute()
    return True


def allow_request(identity: str) -> bool:
    if not settings.enable_rate_limit:
        return True
    return _allow_request_redis(identity)
