# EgoSpatial API (v1.0.0)

## Input: canonical spatial state
```json
{
  "source": "live",
  "agent": {"position": {"x": 0, "y": 0, "z": 0}, "heading": 90},
  "objects": [
    {"id": "chair_01", "label": "chair", "position": {"x": 1.2, "y": 0, "z": -0.8}},
    {"id": "table_01", "label": "table", "position": {"x": -0.5, "y": 0, "z": -1.4}}
  ]
}
```
- Units are metres. +X = East, +Y = Up, +Z = North. `heading` is in degrees, clockwise from North, and any finite value is wrapped to [0, 360).
- `source` is one of `simulated`, `recorded`, `live` or `unspecified`. It is carried through to every response.
- Validation errors are reported as `status: "error"`: missing agent or heading, non-finite numbers, empty object list, duplicate ids, unknown source.

## Python
| Call | Returns |
|---|---|
| `SpatialState.from_dict(d)` / `.from_json(s)` | Validated state, objects sorted by id |
| `state.to_json()` | Deterministic JSON (sorted keys, canonical order) |
| `object_to_agent(state, target)` | `{direction, signed_angle_deg, distance_m, world_displacement, ego_displacement, frame_heading_deg, ...}` |
| `object_to_object(state, reference, target)` | Same fields, 08B-3 semantics |
| `reference_frame(state, reference, target)` | Same fields, V4 semantics |
| `distance(state, a, b="agent", horizontal=True)` | `{distance_m}` |
| `all_relations(state)` | `{id: object_to_agent(...)}` |
| `SpatialEngine(semantic_parser=None, object_relation="reference_frame").ask(state, question)` | `{status: ok/unresolved/error, answer, path, query, result, latency_ms, source}` |
| `SpatialEngine().evaluate(state, Query(op, target, reference))` | Relation dict |
| `adapters.from_unity(pos, quat, objects)` / `from_webxr` / `from_android_xr` / `from_v4_situation` | `SpatialState` |
| `neural.GemmaSemanticParser()` | Callable `(question, names) -> Query or None`. Requires `[neural]`. |

`signed_angle_deg` is measured clockwise from forward: right is +90, left is −90, behind is ±180.

## HTTP (`egospatial-server`)
| Method and path | Body | Response |
|---|---|---|
| `GET /health` | — | `{"status":"ok","version":"1.0.0"}` |
| `POST /ask` | `{"state": {...}, "question": "..."}` | Same as `SpatialEngine.ask` |
| `POST /evaluate` | `{"state": {...}, "query": {"op","target","reference"}}` | `{"status","result"}` |
| `POST /relations` | `{"state": {...}}` | `{"status","source","relations"}` |

Invalid input returns HTTP 400 with `{"status":"error","error": "..."}`. CORS is open for development. Put the server behind your own auth before exposing it on a network.

## Latency (deterministic engine, CPU, Python 3.13, x86-64; `benchmarks/bench.py`)
| Operation | 2 objects | 10 objects | 100 objects |
|---|---:|---:|---:|
| parse + validate state | 5.8 µs | 18 µs | 164 µs |
| `object_to_agent` | 2.2 µs | 2.1 µs | 2.0 µs |
| `ask` (template question) | 7.8 µs | 8.0 µs | 21 µs |
| `all_relations` | 4.3 µs | 21 µs | 366 µs |

Peak memory for 100-object `all_relations` is about 125 KiB. The optional Gemma parser needs a GPU-class device and roughly 5 GB of weights in bf16. Its latency was measured in 08E on a T4 (see the 08E results JSON).
