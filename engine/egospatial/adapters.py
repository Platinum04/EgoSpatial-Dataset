"""Platform adapters: convert platform-native poses into the canonical spatial state.

Canonical frame: +X East, +Y Up, +Z North, heading clockwise from North (degrees).
"North" is whatever direction the platform frame is aligned to; XR runtimes do not
know true north, so by default canonical North = the platform's world/session forward
(+Z in Unity, -Z in WebXR/OpenXR/ARCore). Pass `north_offset_deg` to align with a
known compass bearing (north_offset_deg = true bearing of the platform forward axis).

Supported:
  * V4 dataset symbolic situations (cardinal world_direction strings)
  * Unity (left-handed, +X right, +Y up, +Z forward; yaw clockwise seen from above)
  * WebXR / OpenXR / Android XR (Jetpack XR / ARCore) (right-handed, +X right, +Y up, -Z forward)
"""
from __future__ import annotations

import json
import math
from typing import Any, Dict, Iterable, Optional, Sequence

from .frames import CARDINAL_HEADINGS, CARDINAL_VECTORS, normalize_heading
from .state import SpatialState, SpatialStateError

Quat = Sequence[float]  # (x, y, z, w)


def quat_rotate(q: Quat, v: Sequence[float]) -> tuple:
    """Rotate vector v by unit quaternion q = (x, y, z, w)."""
    x, y, z, w = (float(c) for c in q)
    n = math.sqrt(x * x + y * y + z * z + w * w)
    if n == 0 or not math.isfinite(n):
        raise SpatialStateError("invalid (zero/non-finite) quaternion")
    x, y, z, w = x / n, y / n, z / n, w / n
    vx, vy, vz = (float(c) for c in v)
    # t = 2 * cross(q.xyz, v); v' = v + w*t + cross(q.xyz, t)
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx))


def _rot_y(x: float, z: float, deg: float):
    """Rotate canonical (x, z) clockwise by deg (seen from above)."""
    t = math.radians(deg)
    return x * math.cos(t) + z * math.sin(t), -x * math.sin(t) + z * math.cos(t)


def _state(agent_xyz, heading, objects, source, north_offset_deg):
    ax, ay, az = agent_xyz
    # north_offset_deg = compass bearing of the platform's forward axis; rotate clockwise into true-north frame
    ax, az = _rot_y(ax, az, north_offset_deg) if north_offset_deg else (ax, az)
    objs = []
    for o in objects:
        x, y, z = o["xyz"]
        if north_offset_deg:
            x, z = _rot_y(x, z, north_offset_deg)
        objs.append({"id": o["id"], "label": o.get("label", o["id"]), "position": {"x": x, "y": y, "z": z},
                     "attributes": o.get("attributes", {})})
    return SpatialState.from_dict({"agent": {"position": {"x": ax, "y": ay, "z": az},
                                             "heading": normalize_heading(heading + north_offset_deg)},
                                   "objects": objs, "source": source})


# ---------------------------------------------------------------- V4 dataset
def from_v4_situation(situation: str) -> SpatialState:
    """V4 symbolic situation -> state (agent at origin, objects at unit distance)."""
    try:
        s = json.loads(situation)
    except json.JSONDecodeError as e:
        raise SpatialStateError(f"invalid situation JSON: {e}") from None
    h = (s.get("agent") or {}).get("heading")
    if h not in CARDINAL_HEADINGS:
        raise SpatialStateError(f"invalid heading: {h!r}")
    objs = []
    for o in s.get("objects") or []:
        d = o.get("world_direction")
        if d not in CARDINAL_VECTORS:
            raise SpatialStateError(f"invalid world_direction for {o.get('id')!r}: {d!r}")
        x, z = CARDINAL_VECTORS[d]
        objs.append({"id": o.get("id"), "label": o.get("id"), "position": {"x": x, "y": 0.0, "z": z}})
    return SpatialState.from_dict({"agent": {"position": {"x": 0, "y": 0, "z": 0}, "heading": CARDINAL_HEADINGS[h]},
                                   "objects": objs, "source": "simulated"})


# ---------------------------------------------------------------- Unity
def unity_heading_from_rotation(q: Quat) -> float:
    fx, _, fz = quat_rotate(q, (0.0, 0.0, 1.0))
    if abs(fx) < 1e-12 and abs(fz) < 1e-12:
        raise SpatialStateError("camera is looking straight up/down; heading undefined")
    return normalize_heading(math.degrees(math.atan2(fx, fz)))


def from_unity(camera_position: Sequence[float], camera_rotation: Quat, objects: Iterable[Dict[str, Any]],
               source: str = "simulated", north_offset_deg: float = 0.0) -> SpatialState:
    """objects: [{"id","label","position":[x,y,z]}] in Unity world coordinates."""
    heading = unity_heading_from_rotation(camera_rotation)
    objs = [{"id": o["id"], "label": o.get("label", o["id"]), "xyz": tuple(o["position"]),
             "attributes": o.get("attributes", {})} for o in objects]
    return _state(tuple(camera_position), heading, objs, source, north_offset_deg)


# ---------------------------------------------------------------- WebXR / OpenXR / Android XR
def xr_heading_from_orientation(q: Quat) -> float:
    fx, _, fz = quat_rotate(q, (0.0, 0.0, -1.0))  # viewer forward is -Z
    cx, cz = fx, -fz                               # canonical: x = x, z = -z
    if abs(cx) < 1e-12 and abs(cz) < 1e-12:
        raise SpatialStateError("viewer is looking straight up/down; heading undefined")
    return normalize_heading(math.degrees(math.atan2(cx, cz)))


def from_webxr(viewer_position: Sequence[float], viewer_orientation: Quat, objects: Iterable[Dict[str, Any]],
               source: str = "live", north_offset_deg: float = 0.0) -> SpatialState:
    """Right-handed -Z-forward frame (WebXR XRRigidTransform, OpenXR, ARCore/Jetpack XR Pose).
    objects: [{"id","label","position":[x,y,z]}] in the same reference space."""
    px, py, pz = (float(c) for c in viewer_position)
    heading = xr_heading_from_orientation(viewer_orientation)
    objs = [{"id": o["id"], "label": o.get("label", o["id"]),
             "xyz": (float(o["position"][0]), float(o["position"][1]), -float(o["position"][2])),
             "attributes": o.get("attributes", {})} for o in objects]
    return _state((px, py, -pz), heading, objs, source, north_offset_deg)


from_android_xr = from_webxr  # identical axis convention (OpenXR / ARCore Pose)
from_openxr = from_webxr
