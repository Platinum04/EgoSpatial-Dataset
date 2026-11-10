"""Coordinate frames and transforms for the EgoSpatial canonical convention.

Canonical world frame (08A-2):
    +X = East, -X = West, +Z = North, -Z = South, +Y = Up
    Heading in degrees, clockwise seen from above: 0 = North, 90 = East,
    180 = South, 270 = West.

Egocentric frame (agent-relative):
    +x = agent's right, +z = agent's forward, +y = up.

This module is pure Python and has no dependencies.
"""
from __future__ import annotations

import math
from typing import Dict

Vec3 = Dict[str, float]

CARDINAL_HEADINGS = {"north": 0.0, "east": 90.0, "south": 180.0, "west": 270.0}
CARDINAL_VECTORS = {
    "north": (0.0, 1.0),
    "east": (1.0, 0.0),
    "south": (0.0, -1.0),
    "west": (-1.0, 0.0),
}


def normalize_heading(degrees: float) -> float:
    """Wrap any finite heading into [0, 360)."""
    if not math.isfinite(degrees):
        raise ValueError(f"heading must be finite, got {degrees!r}")
    h = math.fmod(float(degrees), 360.0)
    if h < 0:
        h += 360.0
    return 0.0 if h == 360.0 else h


def vec(x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Vec3:
    return {"x": float(x), "y": float(y), "z": float(z)}


def displacement(source: Vec3, target: Vec3) -> Vec3:
    """World-space vector from source to target."""
    return vec(target["x"] - source["x"], target["y"] - source["y"], target["z"] - source["z"])


def world_to_egocentric(world_vector: Vec3, heading_degrees: float) -> Vec3:
    """Rotate a world-space vector into the agent's egocentric frame.

    With heading theta (clockwise from North):
        forward unit = ( sin theta, cos theta)  in (x, z)
        right   unit = ( cos theta, -sin theta)
    """
    t = math.radians(normalize_heading(heading_degrees))
    x, z = float(world_vector["x"]), float(world_vector["z"])
    right = x * math.cos(t) - z * math.sin(t)
    forward = x * math.sin(t) + z * math.cos(t)
    return vec(right, float(world_vector.get("y", 0.0)), forward)


def egocentric_to_world(ego_vector: Vec3, heading_degrees: float) -> Vec3:
    """Inverse of :func:`world_to_egocentric`."""
    t = math.radians(normalize_heading(heading_degrees))
    r, f = float(ego_vector["x"]), float(ego_vector["z"])
    x = r * math.cos(t) + f * math.sin(t)
    z = -r * math.sin(t) + f * math.cos(t)
    return vec(x, float(ego_vector.get("y", 0.0)), z)


def bearing_degrees(world_vector: Vec3) -> float:
    """Compass bearing (clockwise from North) of a horizontal world vector."""
    x, z = float(world_vector["x"]), float(world_vector["z"])
    if x == 0.0 and z == 0.0:
        raise ValueError("bearing of a zero-length horizontal vector is undefined")
    return normalize_heading(math.degrees(math.atan2(x, z)))


def horizontal_distance(a: Vec3, b: Vec3) -> float:
    return math.hypot(b["x"] - a["x"], b["z"] - a["z"])


def distance_3d(a: Vec3, b: Vec3) -> float:
    return math.sqrt((b["x"] - a["x"]) ** 2 + (b["y"] - a["y"]) ** 2 + (b["z"] - a["z"]) ** 2)
