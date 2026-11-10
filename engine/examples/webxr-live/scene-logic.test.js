// node scene-logic.test.js — exercises EgoSpatial Live logic with a fake WebXR frame.
const L = require("./scene-logic.js");
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) pass++; else { fail++; console.error("FAIL", m); } };

// identity rotation matrix with translation
const mat = (x, y, z) => new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, x,y,z,1]);
const poseAt = (x, y, z) => ({ transform: { position: { x, y, z }, matrix: mat(x, y, z) } });
const yawQ = (deg) => { const t = deg * Math.PI / 360; return [0, Math.sin(t), 0, Math.cos(t)]; };

// Fake room: viewer at origin facing -Z (WebXR forward).
const table = { semanticLabel: "table", planeSpace: { p: [-2, 0.75, 0] } };     // to the viewer's left (-X)
const couch = { semanticLabel: "couch", planeSpace: { p: [0, 0.4, 3] } };       // behind (+Z)
const floor = { semanticLabel: "floor", planeSpace: { p: [0, 0, 0] } };         // skipped
const door  = { semanticLabel: "door frame", planeSpace: { p: [0, 1, -4] } };   // in front (-Z)
const box   = { semanticLabel: "storage", meshSpace: { p: [3, 0, 0] }, vertices: new Float32Array([-0.2,0,-0.2, 0.2,0.8,0.2]) }; // right
const frame = {
  detectedPlanes: new Set([table, couch, floor, door]),
  detectedMeshes: new Set([box, { meshSpace: { p: [9, 9, 9] }, vertices: new Float32Array(3) }]),   // unlabelled mesh skipped
  getPose: (space) => poseAt(...space.p),
};
const idFor = L.createRegistry();
const objs = L.collectObjects(frame, {}, idFor, [{ id: "mug", label: "mug", position: [0.5, 1, -0.5] }]);
ok(objs.length === 5, "collected 5 objects (floor + unlabelled mesh skipped): " + objs.map(o => o.id));
ok(objs.find(o => o.id === "door").label === "door", "door frame -> door");
const st = objs.find(o => o.id === "storage");
ok(Math.abs(st.position[0] - 3) < 1e-6 && Math.abs(st.position[1] - 0.4) < 1e-6, "mesh centroid transformed");
// stable ids across frames
const again = L.collectObjects(frame, {}, idFor, []);
ok(again.find(o => o.label === "table").id === "table", "stable id");

let R = L.relationsFor([0, 1.6, 0], [0, 0, 0, 1], objs);
const dir = Object.fromEntries(R.relations.map(r => [r.id, r.direction]));
ok(dir.table === "left" && dir.couch === "behind" && dir.door === "front" && dir.storage === "right", "facing -Z: " + JSON.stringify(dir));
ok(R.relations[0].id === "mug", "sorted by distance");
ok(Math.abs(R.heading) < 1e-9, "heading 0");

// Turn left 90 degrees (right-handed +Y): table should now be in front, door on the right.
R = L.relationsFor([0, 1.6, 0], yawQ(90), objs);
const d2 = Object.fromEntries(R.relations.map(r => [r.id, r.direction]));
ok(d2.table === "front" && d2.door === "right" && d2.couch === "left" && d2.storage === "behind", "after left turn: " + JSON.stringify(d2));

const s = L.summarySentence(R.relations, 3);
ok(/Mug/.test(s) && /metres|centimetres/.test(s), "summary: " + s);
ok(L.summarySentence([]).startsWith("I don't see"), "empty summary");
ok(/table is in front of you/.test(L.answerFor(R.relations, "where is the table?")), "answer table");
ok(L.answerFor(R.relations, "where is the piano") === null, "unknown object");

// Object exactly at the viewer is dropped instead of throwing.
R = L.relationsFor([0, 1.6, 0], [0, 0, 0, 1], [{ id: "x", label: "x", position: [0, 0, 0] }]);
ok(R.relations.length === 0, "object at viewer dropped");

console.log(`EgoSpatial Live logic: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
