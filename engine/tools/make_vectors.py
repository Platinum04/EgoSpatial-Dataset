"""Generate cross-platform conformance vectors from the reference Python engine.
Ports (JS/WebXR, C#/Unity, Kotlin/Android XR) must reproduce every expected value."""
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import egospatial as es
from egospatial import adapters

rnd = random.Random(2026)
cases = []
for i in range(500):
    h = round(rnd.uniform(-400, 400), 3)
    ax, az = round(rnd.uniform(-5, 5), 3), round(rnd.uniform(-5, 5), 3)
    objs = []
    for k in range(3):
        while True:
            x, z = round(rnd.uniform(-8, 8), 3), round(rnd.uniform(-8, 8), 3)
            if math.hypot(x - ax, z - az) > 0.05:
                break
        objs.append({"id": f"o{k}", "label": "thing", "position": {"x": x, "y": round(rnd.uniform(0, 2), 3), "z": z}})
    st = es.SpatialState.from_dict({"agent": {"position": {"x": ax, "y": 0, "z": az}, "heading": h}, "objects": objs})
    exp = {"object_to_agent": {o["id"]: es.object_to_agent(st, o["id"])["direction"] for o in objs}}
    try:
        exp["reference_frame"] = es.reference_frame(st, "o0", "o1")["direction"]
        exp["object_to_object"] = es.object_to_object(st, "o0", "o1")["direction"]
    except es.SpatialStateError:
        pass
    exp["signed_angle_o0"] = es.object_to_agent(st, "o0")["signed_angle_deg"]
    cases.append({"state": {"agent": {"position": {"x": ax, "y": 0, "z": az}, "heading": h}, "objects": objs},
                  "expected": exp})

def yaw_q(deg):
    t = math.radians(deg) / 2
    return [0.0, math.sin(t), 0.0, math.cos(t)]

adapter_cases = []
for i in range(100):
    yaw = round(rnd.uniform(0, 360), 3); x, z = round(rnd.uniform(-5, 5), 3), round(rnd.uniform(-5, 5), 3)
    if math.hypot(x, z) < 0.05:
        continue
    q = yaw_q(yaw); o = [{"id": "o", "position": [x, 0.0, z]}]
    u = adapters.from_unity([0, 1.6, 0], q, o)
    w = adapters.from_webxr([0, 1.6, 0], q, o)
    adapter_cases.append({"quat": q, "object": [x, 0.0, z],
                          "unity": {"heading": round(u.agent_heading, 6), "direction": es.object_to_agent(u, "o")["direction"]},
                          "webxr": {"heading": round(w.agent_heading, 6), "direction": es.object_to_agent(w, "o")["direction"]}})

out = {"version": es.__version__, "convention": "+X East, +Y Up, +Z North, heading clockwise from North",
       "relations": cases, "adapters": adapter_cases}
Path(__file__).resolve().parents[1].joinpath("tests", "vectors.json").write_text(json.dumps(out, indent=0))
print(f"wrote {len(cases)} relation cases, {len(adapter_cases)} adapter cases")
