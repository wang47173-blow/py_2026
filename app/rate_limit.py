from __future__ import annotations

import time
from collections import defaultdict, deque

from app.config import settings

_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def allow_request(identity: str) -> bool:
    if not settings.enable_rate_limit:
        return True
    now = time.time()
    dq = _BUCKETS[identity]
    window_start = now - 60
    while dq and dq[0] < window_start:
        dq.popleft()
    if len(dq) >= settings.rate_limit_requests_per_minute:
        return False
    dq.append(now)
    return True
