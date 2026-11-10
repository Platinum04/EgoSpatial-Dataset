"""Canonical spatial state: construction, validation and deterministic serialization (08A)."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from .frames import Vec3, normalize_heading, vec

SCHEMA_VERSION = "egospatial.state/1"


class SpatialStateError(ValueError):
    """Raised for any invalid or incomplete spatial observation."""


def _finite(v: Any, name: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise SpatialStateError(f"{name} must be a finite number, got {v!r}")
    return float(v)


def _position(p: Any, name: str) -> Vec3:
    if not isinstance(p, dict):
        raise SpatialStateError(f"{name} must be an object with x, y, z")
    missing = [k for k in ("x", "z") if k not in p]
    if missing:
        raise SpatialStateError(f"{name} is missing {missing}")
    return vec(_finite(p["x"], f"{name}.x"), _finite(p.get("y", 0.0), f"{name}.y"), _finite(p["z"], f"{name}.z"))


@dataclass(frozen=True)
class SpatialObject:
    id: str
    label: str
    position: Vec3
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {"id": self.id, "label": self.label, "position": dict(self.position)}
        if self.attributes:
            d["attributes"] = dict(sorted(self.attributes.items()))
        return d


@dataclass(frozen=True)
class SpatialState:
    agent_position: Vec3
    agent_heading: float
    objects: tuple
    source: str = "unspecified"  # "simulated" | "recorded" | "live" | "unspecified"

    # ---- construction -------------------------------------------------
    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SpatialState":
        if not isinstance(d, dict):
            raise SpatialStateError("state must be a JSON object")
        agent = d.get("agent")
        if not isinstance(agent, dict):
            raise SpatialStateError("state.agent is required")
        pos = _position(agent.get("position", {"x": 0, "y": 0, "z": 0}), "agent.position")
        heading = normalize_heading(_finite(agent.get("heading"), "agent.heading"))
        raw = d.get("objects")
        if not isinstance(raw, list) or not raw:
            raise SpatialStateError("state.objects must be a non-empty list")
        seen, objs = set(), []
        for i, o in enumerate(raw):
            if not isinstance(o, dict):
                raise SpatialStateError(f"objects[{i}] must be an object")
            oid = o.get("id")
            if not isinstance(oid, str) or not oid.strip():
                raise SpatialStateError(f"objects[{i}].id must be a non-empty string")
            if oid in seen:
                raise SpatialStateError(f"duplicate object id: {oid}")
            seen.add(oid)
            label = o.get("label", oid)
            if not isinstance(label, str) or not label.strip():
                raise SpatialStateError(f"objects[{i}].label must be a non-empty string")
            objs.append(SpatialObject(oid, label, _position(o.get("position"), f"objects[{oid}].position"),
                                      dict(o.get("attributes", {}))))
        objs.sort(key=lambda o: o.id)  # canonical order
        src = d.get("source", "unspecified")
        if src not in ("simulated", "recorded", "live", "unspecified"):
            raise SpatialStateError(f"unknown source {src!r}")
        return SpatialState(pos, heading, tuple(objs), src)

    @staticmethod
    def from_json(s: str) -> "SpatialState":
        try:
            return SpatialState.from_dict(json.loads(s))
        except json.JSONDecodeError as e:
            raise SpatialStateError(f"invalid JSON: {e}") from None

    # ---- access ---------------------------------------------------------
    def object(self, object_id: str) -> SpatialObject:
        for o in self.objects:
            if o.id == object_id:
                return o
        raise SpatialStateError(f"unknown object: {object_id}")

    @property
    def ids(self) -> List[str]:
        return [o.id for o in self.objects]

    def with_heading(self, heading: float) -> "SpatialState":
        return SpatialState(self.agent_position, normalize_heading(heading), self.objects, self.source)

    # ---- serialization --------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": SCHEMA_VERSION,
            "source": self.source,
            "agent": {"position": dict(self.agent_position), "heading": self.agent_heading},
            "objects": [o.to_dict() for o in self.objects],
        }

    def to_json(self) -> str:
        """Deterministic serialization: sorted keys, canonical object order, compact separators."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
