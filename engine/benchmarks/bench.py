"""Latency / memory benchmark for the deterministic engine (CPU, pure Python)."""
import json
import platform
import random
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import egospatial as es

rnd = random.Random(0)


def make_state(n):
    return {"agent": {"position": {"x": 0, "y": 0, "z": 0}, "heading": rnd.uniform(0, 360)},
            "objects": [{"id": f"obj_{i}", "label": "thing",
                         "position": {"x": rnd.uniform(-10, 10), "y": 0, "z": rnd.uniform(-10, 10)}} for i in range(n)]}


def timeit(fn, reps):
    ts = []
    for _ in range(reps):
        t = time.perf_counter(); fn(); ts.append((time.perf_counter() - t) * 1e6)
    return {"median_us": round(statistics.median(ts), 2), "p95_us": round(sorted(ts)[int(0.95 * len(ts))], 2)}


res = {"python": platform.python_version(), "machine": platform.machine(), "processor": platform.processor() or "n/a"}
engine = es.SpatialEngine()
for n in (2, 10, 100):
    d = make_state(n); st = es.SpatialState.from_dict(d)
    res[f"objects={n}"] = {
        "parse_validate_state": timeit(lambda: es.SpatialState.from_dict(d), 2000),
        "object_to_agent": timeit(lambda: es.object_to_agent(st, "obj_1"), 5000),
        "all_relations": timeit(lambda: es.all_relations(st), 500),
        "ask(template question)": timeit(lambda: engine.ask(st, "Where is the obj_1 relative to me?"), 2000),
    }
tracemalloc.start()
st = es.SpatialState.from_dict(make_state(100)); es.all_relations(st)
cur, peak = tracemalloc.get_traced_memory()
res["memory_peak_kib_100_objects_all_relations"] = round(peak / 1024, 1)
print(json.dumps(res, indent=1))
