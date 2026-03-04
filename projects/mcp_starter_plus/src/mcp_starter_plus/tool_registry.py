from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolSpec:
    name: str
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    required_fields: set[str] = field(default_factory=set)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self._cache: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
        self.cache_ttl_s = 30.0
        self.hooks: dict[str, list[Callable[..., None]]] = {
            "before_call": [],
            "after_call": [],
            "on_error": [],
        }

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def on(self, event: str, fn: Callable[..., None]) -> None:
        if event in self.hooks:
            self.hooks[event].append(fn)

    def call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        spec = self._tools.get(name)
        if not spec:
            raise ValueError(f"unknown tool: {name}")

        missing = [f for f in spec.required_fields if f not in args]
        if missing:
            raise ValueError(f"missing required fields: {sorted(missing)}")

        idem = args.get("idempotency_key")
        if idem:
            key = (name, str(idem))
            cached = self._cache.get(key)
            now = time.time()
            if cached and now - cached[0] <= self.cache_ttl_s:
                return {"cached": True, **cached[1]}

        for h in self.hooks["before_call"]:
            h(name=name, args=args)

        try:
            result = spec.handler(args)
            for h in self.hooks["after_call"]:
                h(name=name, result=result)
            if idem:
                self._cache[(name, str(idem))] = (time.time(), result)
            return result
        except Exception as exc:  # noqa: BLE001
            for h in self.hooks["on_error"]:
                h(name=name, error=str(exc))
            # innovation: structured fallback
            return {
                "fallback": {
                    "reason": str(exc),
                    "recoverable": True,
                    "next_action": "retry_or_switch_tool",
                }
            }
