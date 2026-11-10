// node ports/js/conformance.test.js  — checks the JS port against tests/vectors.json
const fs = require("fs");
const path = require("path");
const ES = require("./egospatial.js");
const V = JSON.parse(fs.readFileSync(path.join(__dirname, "../../tests/vectors.json"), "utf8"));
let pass = 0, fail = 0;
const check = (ok, msg) => { if (ok) pass++; else { fail++; if (fail < 10) console.error("FAIL", msg); } };
for (const c of V.relations) {
  for (const [id, d] of Object.entries(c.expected.object_to_agent))
    check(ES.objectToAgent(c.state, id).direction === d, `o2a ${id}`);
  if (c.expected.reference_frame) check(ES.referenceFrame(c.state, "o0", "o1").direction === c.expected.reference_frame, "rf");
  if (c.expected.object_to_object) check(ES.objectToObject(c.state, "o0", "o1").direction === c.expected.object_to_object, "o2o");
  check(Math.abs(ES.objectToAgent(c.state, "o0").signed_angle_deg - c.expected.signed_angle_o0) < 1e-5, "angle");
}
for (const a of V.adapters) {
  const u = ES.fromUnity([0, 1.6, 0], a.quat, [{ id: "o", position: a.object }]);
  const w = ES.fromWebXR([0, 1.6, 0], a.quat, [{ id: "o", position: a.object }]);
  check(Math.abs(u.agent.heading - a.unity.heading) < 1e-5 && ES.objectToAgent(u, "o").direction === a.unity.direction, "unity");
  check(Math.abs(w.agent.heading - a.webxr.heading) < 1e-5 && ES.objectToAgent(w, "o").direction === a.webxr.direction, "webxr");
}
for (const bad of [{}, { agent: { heading: NaN }, objects: [{ id: "a", position: { x: 1, z: 0 } }] },
                   { agent: { heading: 0 }, objects: [] },
                   { agent: { heading: 0 }, objects: [{ id: "a", position: { x: 1, z: 0 } }, { id: "a", position: { x: 2, z: 0 } }] }]) {
  let threw = false; try { ES.objectToAgent(bad, "a"); } catch (e) { threw = e instanceof ES.SpatialStateError; }
  check(threw, "validation " + JSON.stringify(bad));
}
console.log(`JS conformance: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
