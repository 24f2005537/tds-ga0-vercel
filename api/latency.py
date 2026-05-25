from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import statistics

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Access-Control-Allow-Origin"],
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "q-vercel-latency.json")
with open(DATA_PATH, "r", encoding="utf-8") as f:
    DATA = json.load(f)

class Payload(BaseModel):
    regions: list[str]
    threshold_ms: float

def p95(values):
    if not values:
        return None
    values = sorted(values)
    n = len(values)
    if n == 1:
        return values[0]
    k = (n - 1) * 0.95
    f = int(k)
    c = min(f + 1, n - 1)
    if f == c:
        return values[f]
    return values[f] + (values[c] - values[f]) * (k - f)

@app.post("/api/latency")
def latency(payload: Payload):
    result = {}
    for region in payload.regions:
        rows = [r for r in DATA if r.get("region") == region]
        latencies = [r["latency_ms"] for r in rows if "latency_ms" in r]
        uptimes = [r["uptime_pct"] for r in rows if "uptime_pct" in r]

        result[region] = {
            "avg_latency": round(statistics.mean(latencies), 2) if latencies else None,
            "p95_latency": round(p95(latencies), 2) if latencies else None,
            "avg_uptime": round(statistics.mean(uptimes), 2) if uptimes else None,
            "breaches": sum(1 for x in latencies if x > payload.threshold_ms),
        }
    return result