/*
 * EgoSpatial Live — perception-to-relations logic (no rendering).
 * Turns WebXR scene understanding (Quest Space Setup planes/meshes with semantic labels,
 * or user-placed hit-test anchors) into labelled objects, then asks the deterministic
 * EgoSpatial engine where each one is relative to the viewer.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory(require("./egospatial.js"));
  else root.EgoSpatialLive = factory(root.EgoSpatial);
})(typeof self !== "undefined" ? self : this, function (ES) {
  "use strict";

  // Labels that describe room structure rather than objects you'd ask about.
  const SKIP = new Set(["floor", "ceiling", "wall", "wall face", "invisible wall face", "global mesh", "inner wall face"]);
  const PRETTY = { "door frame": "door", "window frame": "window", "wall art": "wall art", "other": "object", "screen": "screen" };

  function prettyLabel(raw) {
    const l = String(raw || "object").trim().toLowerCase();
    return PRETTY[l] || l;
  }

  /** Multiply a column-major 4x4 matrix by a point. */
  function transformPoint(m, x, y, z) {
    return [m[0] * x + m[4] * y + m[8] * z + m[12],
            m[1] * x + m[5] * y + m[9] * z + m[13],
            m[2] * x + m[6] * y + m[10] * z + m[14]];
  }

  /** Centroid of a vertex buffer (x,y,z,x,y,z,...) in its own space. */
  function centroid(vertices) {
    let sx = 0, sy = 0, sz = 0; const n = Math.floor(vertices.length / 3);
    if (!n) return [0, 0, 0];
    for (let i = 0; i < n * 3; i += 3) { sx += vertices[i]; sy += vertices[i + 1]; sz += vertices[i + 2]; }
    return [sx / n, sy / n, sz / n];
  }

  /**
   * Stable object registry: each XRPlane / XRMesh keeps the same id across frames.
   */
  function createRegistry() {
    const ids = new WeakMap(); const counts = {};
    return function idFor(entity, label) {
      if (!ids.has(entity)) { counts[label] = (counts[label] || 0) + 1; ids.set(entity, counts[label] > 1 ? `${label} ${counts[label]}` : label); }
      return ids.get(entity);
    };
  }

  /**
   * Collect labelled objects from a WebXR frame.
   * @returns {{id,label,position:[x,y,z],source:'plane'|'mesh'|'placed'}[]}
   */
  function collectObjects(frame, refSpace, idFor, placed) {
    const out = [];
    const take = (entity, space, label, local) => {
      if (SKIP.has(String(label || "").toLowerCase())) return;
      const pose = frame.getPose(space, refSpace); if (!pose) return;
      const nice = prettyLabel(label);
      const p = local ? transformPoint(pose.transform.matrix, local[0], local[1], local[2])
                      : [pose.transform.position.x, pose.transform.position.y, pose.transform.position.z];
      out.push({ id: idFor(entity, nice), label: nice, position: p });
    };
    if (frame.detectedPlanes) for (const pl of frame.detectedPlanes) take(pl, pl.planeSpace, pl.semanticLabel, null);
    if (frame.detectedMeshes) for (const me of frame.detectedMeshes) {
      if (!me.semanticLabel) continue;                 // unlabelled room mesh: skip
      take(me, me.meshSpace, me.semanticLabel, me.vertices ? centroid(me.vertices) : null);
    }
    for (const p of placed || []) out.push({ id: p.id, label: p.label, position: p.position.slice(), source: "placed" });
    return out;
  }

  /** Relations for every object from the current viewer pose. Objects at the viewer's own spot are dropped. */
  function relationsFor(viewerPosition, viewerOrientation, objects) {
    const usable = objects.filter((o) => Math.hypot(o.position[0] - viewerPosition[0], o.position[2] - viewerPosition[2]) > 0.05);
    if (!usable.length) return { heading: null, relations: [] };
    const st = ES.fromWebXR(viewerPosition, viewerOrientation, usable, "live");
    const rel = ES.allRelations(st);
    const relations = Object.values(rel).map((r) => {
      const o = usable.find((u) => u.id === r.target);
      return { id: r.target, label: o.label, direction: r.direction, angle: r.signed_angle_deg,
               distance: Math.hypot(r.world_displacement.x, r.world_displacement.z), position: o.position };
    }).sort((a, b) => a.distance - b.distance);
    return { heading: st.agent.heading, relations };
  }

  const PHRASE = { front: "in front of you", behind: "behind you", left: "on your left", right: "on your right" };

  /** A short spoken summary, nearest first. */
  function summarySentence(relations, max = 5) {
    if (!relations.length) return "I don't see any objects yet. Pinch or pull the trigger at a surface to place one.";
    const parts = relations.slice(0, max).map((r) => {
      const d = r.distance < 1 ? `${Math.round(r.distance * 100)} centimetres` : `${r.distance.toFixed(1)} metres`;
      const name = r.label.charAt(0).toUpperCase() + r.label.slice(1);
      return `${name} ${PHRASE[r.direction]}, ${d}`;
    });
    return parts.join(". ") + ".";
  }

  /** Answer "where is the X" against current relations (simple label match). */
  function answerFor(relations, query) {
    const q = String(query || "").toLowerCase();
    const hit = relations.find((r) => q.includes(r.label) || q.includes(r.id));
    if (!hit) return null;
    return `The ${hit.label} is ${PHRASE[hit.direction]}, about ${hit.distance.toFixed(1)} metres away.`;
  }

  return { collectObjects, relationsFor, summarySentence, answerFor, createRegistry, prettyLabel, transformPoint, centroid, PHRASE };
});
