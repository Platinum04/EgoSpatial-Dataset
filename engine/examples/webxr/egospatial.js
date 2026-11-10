/*
 * EgoSpatial deterministic engine — JavaScript port (WebXR / browser / Node).
 * Conformance: must reproduce tests/vectors.json produced by the Python reference engine.
 * Canonical frame: +X East, +Y Up, +Z North; heading clockwise from North (degrees).
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.EgoSpatial = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  const DEG = Math.PI / 180;

  class SpatialStateError extends Error {}

  function normalizeHeading(d) {
    if (!Number.isFinite(d)) throw new SpatialStateError("heading must be finite");
    let h = d % 360;
    if (h < 0) h += 360;
    return h === 360 ? 0 : h;
  }

  function worldToEgocentric(v, heading) {
    const t = normalizeHeading(heading) * DEG;
    return {
      x: v.x * Math.cos(t) - v.z * Math.sin(t),
      y: v.y || 0,
      z: v.x * Math.sin(t) + v.z * Math.cos(t),
    };
  }

  function bearing(v) {
    if (v.x === 0 && v.z === 0) throw new SpatialStateError("bearing of zero vector is undefined");
    return normalizeHeading(Math.atan2(v.x, v.z) / DEG);
  }

  function classify(ego, tol = 1e-9) {
    if (Math.abs(ego.x) < tol && Math.abs(ego.z) < tol)
      throw new SpatialStateError("cannot classify a zero-length horizontal vector");
    if (Math.abs(ego.z) >= Math.abs(ego.x)) return ego.z > 0 ? "front" : "behind";
    return ego.x > 0 ? "right" : "left";
  }

  function signedAngle(ego) {
    const a = Math.atan2(ego.x, ego.z) / DEG;
    return a === -180 ? 180 : a;
  }

  const sub = (a, b) => ({ x: b.x - a.x, y: (b.y || 0) - (a.y || 0), z: b.z - a.z });

  function validate(state) {
    if (!state || !state.agent) throw new SpatialStateError("state.agent is required");
    const h = state.agent.heading;
    if (typeof h !== "number" || !Number.isFinite(h)) throw new SpatialStateError("agent.heading must be finite");
    if (!Array.isArray(state.objects) || state.objects.length === 0)
      throw new SpatialStateError("state.objects must be a non-empty list");
    const seen = new Set();
    for (const o of state.objects) {
      if (!o || typeof o.id !== "string" || !o.id) throw new SpatialStateError("object id required");
      if (seen.has(o.id)) throw new SpatialStateError("duplicate object id: " + o.id);
      seen.add(o.id);
      const p = o.position || {};
      for (const k of ["x", "z"]) if (typeof p[k] !== "number" || !Number.isFinite(p[k]))
        throw new SpatialStateError(`objects[${o.id}].position.${k} must be finite`);
    }
    return state;
  }

  function obj(state, id) {
    const o = state.objects.find((o) => o.id === id);
    if (!o) throw new SpatialStateError("unknown object: " + id);
    return o;
  }
  const agentPos = (s) => s.agent.position || { x: 0, y: 0, z: 0 };

  function result(kind, target, reference, world, heading) {
    const ego = worldToEgocentric(world, heading);
    return { relation: kind, target, reference, direction: classify(ego), signed_angle_deg: signedAngle(ego),
             world_displacement: world, ego_displacement: ego, frame_heading_deg: normalizeHeading(heading) };
  }

  function objectToAgent(state, target) {
    validate(state);
    return result("object_to_agent", target, "agent", sub(agentPos(state), obj(state, target).position), state.agent.heading);
  }

  function objectToObject(state, reference, target) {
    validate(state);
    if (reference === target) throw new SpatialStateError("reference and target must differ");
    return result("object_to_object", target, reference,
      sub(obj(state, reference).position, obj(state, target).position), state.agent.heading);
  }

  function referenceFrame(state, reference, target) {
    validate(state);
    if (reference === target) throw new SpatialStateError("reference and target must differ");
    const a = agentPos(state);
    const h = bearing(sub(a, obj(state, reference).position));
    return result("reference_frame", target, reference, sub(a, obj(state, target).position), h);
  }

  // ---- adapters --------------------------------------------------------
  function quatRotate(q, v) {
    let [x, y, z, w] = q; const n = Math.hypot(x, y, z, w);
    if (!(n > 0)) throw new SpatialStateError("invalid quaternion");
    x /= n; y /= n; z /= n; w /= n;
    const [vx, vy, vz] = v;
    const tx = 2 * (y * vz - z * vy), ty = 2 * (z * vx - x * vz), tz = 2 * (x * vy - y * vx);
    return [vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx)];
  }

  /** WebXR / OpenXR pose (right-handed, -Z forward) -> canonical state. */
  function fromWebXR(viewerPos, viewerQuat, objects, source = "live") {
    const [fx, , fz] = quatRotate(viewerQuat, [0, 0, -1]);
    const cx = fx, cz = -fz;
    if (Math.abs(cx) < 1e-12 && Math.abs(cz) < 1e-12) throw new SpatialStateError("heading undefined (looking up/down)");
    return validate({
      source,
      agent: { position: { x: viewerPos[0], y: viewerPos[1], z: -viewerPos[2] }, heading: normalizeHeading(Math.atan2(cx, cz) / DEG) },
      objects: objects.map((o) => ({ id: o.id, label: o.label || o.id,
        position: { x: o.position[0], y: o.position[1], z: -o.position[2] } })),
    });
  }

  /** Unity pose (left-handed, +Z forward) -> canonical state. */
  function fromUnity(camPos, camQuat, objects, source = "simulated") {
    const [fx, , fz] = quatRotate(camQuat, [0, 0, 1]);
    if (Math.abs(fx) < 1e-12 && Math.abs(fz) < 1e-12) throw new SpatialStateError("heading undefined (looking up/down)");
    return validate({
      source,
      agent: { position: { x: camPos[0], y: camPos[1], z: camPos[2] }, heading: normalizeHeading(Math.atan2(fx, fz) / DEG) },
      objects: objects.map((o) => ({ id: o.id, label: o.label || o.id,
        position: { x: o.position[0], y: o.position[1], z: o.position[2] } })),
    });
  }

  function allRelations(state) {
    const out = {};
    for (const o of validate(state).objects) out[o.id] = objectToAgent(state, o.id);
    return out;
  }

  return { SpatialStateError, normalizeHeading, worldToEgocentric, bearing, classify, objectToAgent,
           objectToObject, referenceFrame, allRelations, fromWebXR, fromUnity, quatRotate, version: "1.0.0" };
});
