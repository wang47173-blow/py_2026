from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

BASE = "http://localhost:8080"
TENANT = "11111111-1111-1111-1111-111111111111"
USER = "22222222-2222-2222-2222-222222222222"


def call_rag(question: str) -> dict:
    payload = {
        "question": question,
        "tenant_id": TENANT,
        "user_id": USER,
        "top_k": 3,
        "filters": {},
    }
    req = urllib.request.Request(
        f"{BASE}/mcp/tools/rag_query",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> None:
    rows = [json.loads(x) for x in Path("eval/golden.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]

    hit = 0
    citation_ok = 0
    refusal_ok = 0
    latencies = []

    for row in rows:
        t0 = time.perf_counter()
        resp = call_rag(row["question"])
        dt = int((time.perf_counter() - t0) * 1000)
        latencies.append(resp.get("latency_ms", dt))

        ans = (resp.get("answer") or "").lower()
        if row["should_refuse"]:
            if ("不能" in ans) or ("拒绝" in ans) or ("insufficient" in ans):
                refusal_ok += 1
        else:
            if any(k.lower() in ans for k in row["expected_keywords"]):
                hit += 1

        cits = resp.get("citations", [])
        if cits and all(c.get("chunk_id") and c.get("source") and c.get("snippet") for c in cits):
            citation_ok += 1

    total_non_refuse = sum(1 for r in rows if not r["should_refuse"])
    total_refuse = sum(1 for r in rows if r["should_refuse"])

    metrics = {
        "hit_rate": round(hit / max(total_non_refuse, 1), 4),
        "citation_coverage": round(citation_ok / len(rows), 4),
        "refusal_rate": round(refusal_ok / max(total_refuse, 1), 4),
        "avg_latency_ms": round(sum(latencies) / max(len(latencies), 1), 2),
        "samples": len(rows),
    }
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
