import json
import os
import statistics
from http.server import BaseHTTPRequestHandler

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "q-vercel-latency.json")
with open(DATA_FILE, "r", encoding="utf-8") as f:
    DATA = json.load(f)

def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    k = (len(values) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return values[f]
    return values[f] + (values[c] - values[f]) * (k - f)

class handler(BaseHTTPRequestHandler):
    def _send(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode("utf-8"))

    def do_OPTIONS(self):
        self._send(200, {})

    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", "0"))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(raw)
            regions = payload.get("regions", [])
            threshold = payload.get("threshold_ms", 180)

            if not isinstance(regions, list):
                raise ValueError("regions must be a list")

            out = {}
            for region in regions:
                rows = [r for r in DATA if r.get("region") == region]
                latencies = [r["latency_ms"] for r in rows if "latency_ms" in r]
                uptimes = [r["uptime"] for r in rows if "uptime" in r]

                out[region] = {
                    "avg_latency": round(statistics.mean(latencies), 2) if latencies else None,
                    "p95_latency": round(percentile(latencies, 95), 2) if latencies else None,
                    "avg_uptime": round(statistics.mean(uptimes), 2) if uptimes else None,
                    "breaches": sum(1 for x in latencies if x > threshold),
                }

            self._send(200, out)
        except Exception as e:
            self._send(400, {"error": str(e)})