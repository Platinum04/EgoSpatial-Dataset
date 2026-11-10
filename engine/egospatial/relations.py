"""Deterministic spatial relationship engine (port of the verified 08B engine).

All geometric answers in EgoSpatial come from this module. Classification rule
(identical to 08B-2): compare |forward| and |right| of the egocentric vector;
ties go to front/behind; a zero-length horizontal vector is an error.
"""
from __future__ import annotations

import math
from typing import Any, Dict

from .frames import Vec3, bearing_degrees, displacement, distance_3d, horizontal_distance, world_to_egocentric
from .state import SpatialState, SpatialStateError

DIRECTIONS = ("front", "behind", "left", "right")


def classify_egocentric_direction(ego: Vec3, tolerance: float = 1e-9) -> str:
    x, z = float(ego["x"]), float(ego["z"])
    if abs(x) < tolerance and abs(z) < tolerance:
        raise SpatialStateError("cannot classify a zero-length horizontal vector (objects coincide horizontally)")
    if abs(z) >= abs(x):
        return "front" if z > 0 else "behind"
    return "right" if x > 0 else "left"


def signed_angle_degrees(ego: Vec3) -> float:
    """Angle of an egocentric vector, clockwise from forward, in (-180, 180]. Right = +90, left = -90."""
    a = math.degrees(math.atan2(float(ego["x"]), float(ego["z"])))
    return 180.0 if a == -180.0 else a


def _result(kind: str, state: SpatialState, target: str, reference: str, world: Vec3, frame_heading: float,
            **extra: Any) -> Dict[str, Any]:
    ego = world_to_egocentric(world, frame_heading)
    return {
        "relation": kind,
        "target": target,
        "reference": reference,
        "direction": classify_egocentric_direction(ego),
        "signed_angle_deg": round(signed_angle_degrees(ego), 6),
        "world_displacement": world,
        "ego_displacement": ego,
        "frame_heading_deg": frame_heading,
        **extra,
    }


def object_to_agent(state: SpatialState, target: str) -> Dict[str, Any]:
    """Where is `target` relative to the agent (egocentric)."""
    t = state.object(target)
    w = displacement(state.agent_position, t.position)
    return _result("object_to_agent", state, target, "agent", w, state.agent_heading,
                   distance_m=horizontal_distance(state.agent_position, t.position))


def object_to_object(state: SpatialState, reference: str, target: str) -> Dict[str, Any]:
    """08B-3 semantics: displacement reference->target, expressed in the AGENT's egocentric frame
    ("from my point of view, is the target left/right/in front of/behind the reference?")."""
    if reference == target:
        raise SpatialStateError("reference and target must be different objects")
    r, t = state.object(reference), state.object(target)
    w = displacement(r.position, t.position)
    return _result("object_to_object", state, target, reference, w, state.agent_heading,
                   distance_m=horizontal_distance(r.position, t.position))


def reference_frame(state: SpatialState, reference: str, target: str) -> Dict[str, Any]:
    """V4 semantics: 'if I face the reference, where is the target?'. Forward := bearing agent->reference;
    the target is classified by its direction from the agent in that frame."""
    if reference == target:
        raise SpatialStateError("reference and target must be different objects")
    r, t = state.object(reference), state.object(target)
    heading = bearing_degrees(displacement(state.agent_position, r.position))
    w = displacement(state.agent_position, t.position)
    return _result("reference_frame", state, target, reference, w, heading,
                   distance_m=horizontal_distance(state.agent_position, t.position))


def distance(state: SpatialState, a: str, b: str = "agent", horizontal: bool = True) -> Dict[str, Any]:
    pa = state.agent_position if a == "agent" else state.object(a).position
    pb = state.agent_position if b == "agent" else state.object(b).position
    d = horizontal_distance(pa, pb) if horizontal else distance_3d(pa, pb)
    return {"relation": "distance", "a": a, "b": b, "horizontal": horizontal, "distance_m": d}


def all_relations(state: SpatialState) -> Dict[str, Any]:
    """Every object-to-agent relation for the scene (useful for XR overlays)."""
    return {o.id: object_to_agent(state, o.id) for o in state.objects}
