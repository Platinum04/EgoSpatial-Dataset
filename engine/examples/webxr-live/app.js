// EgoSpatial Live — app: simulated top-down mode + WebXR mixed reality (Quest 3S, Android XR Chrome).
import * as THREE from "three";

const ES = window.EgoSpatial;
const L = window.EgoSpatialLive;
const COLORS = { front: "#3ddc84", behind: "#ff6b6b", left: "#ffb84d", right: "#c77dff" };
const $ = (id) => document.getElementById(id);

// ------------------------------------------------------------------ SIMULATED (any browser)
const LABELS = ["chair", "table", "lamp", "door", "plant", "sofa", "desk", "shelf"];
const sim = {
  source: "simulated",
  agent: { position: { x: 0, y: 0, z: 0 }, heading: 0 },
  objects: [
    { id: "chair", label: "chair", position: { x: 1.2, y: 0, z: -0.8 } },
    { id: "table", label: "table", position: { x: -0.5, y: 0, z: -1.4 } },
    { id: "lamp", label: "lamp", position: { x: 0.3, y: 0, z: 2.0 } },
  ],
};
const row = (r) => `<tr><td>${r.target}</td><td style="color:${COLORS[r.direction]}"><b>${r.direction}</b></td>` +
  `<td>${r.signed_angle_deg.toFixed(0)}°</td><td>${Math.hypot(r.world_displacement.x, r.world_displacement.z).toFixed(2)} m</td></tr>`;
function renderTable(state) {
  try { $("rel").innerHTML = Object.values(ES.allRelations(state)).map(row).join(""); }
  catch (e) { $("rel").innerHTML = `<tr><td colspan=4>${e.message}</td></tr>`; }
}
const cv = $("map"), cx = cv.getContext("2d"), S = 60;
const toPx = (p) => [cv.width / 2 + p.x * S, cv.height / 2 - p.z * S];
const toW = (px, py) => ({ x: (px - cv.width / 2) / S, y: 0, z: (cv.height / 2 - py) / S });
function draw() {
  cx.clearRect(0, 0, cv.width, cv.height);
  cx.strokeStyle = getComputedStyle(document.body).getPropertyValue("--grid") || "#262a33";
  for (let i = -5; i <= 5; i++) {
    const [a] = toPx({ x: i, z: 0 }); const [, b] = toPx({ x: 0, z: i });
    cx.beginPath(); cx.moveTo(a, 0); cx.lineTo(a, cv.height); cx.stroke();
    cx.beginPath(); cx.moveTo(0, b); cx.lineTo(cv.width, b); cx.stroke();
  }
  cx.fillStyle = "#9aa3b2"; cx.font = "14px system-ui"; cx.fillText("N", cv.width / 2 - 4, 16);
  const [ax, ay] = toPx(sim.agent.position), t = sim.agent.heading * Math.PI / 180;
  cx.save(); cx.translate(ax, ay); cx.rotate(t); cx.fillStyle = "#5aa9ff";
  cx.beginPath(); cx.moveTo(0, -18); cx.lineTo(11, 12); cx.lineTo(-11, 12); cx.closePath(); cx.fill(); cx.restore();
  const rels = ES.allRelations(sim);
  for (const o of sim.objects) {
    const [x, y] = toPx(o.position); cx.fillStyle = COLORS[rels[o.id].direction];
    cx.beginPath(); cx.arc(x, y, 10, 0, 7); cx.fill();
    cx.fillStyle = "#e8eaf0"; cx.fillText(`${o.id} (${rels[o.id].direction})`, x + 14, y + 5);
  }
  renderTable(sim);
}
let drag = null;
cv.addEventListener("pointerdown", (e) => {
  const r = cv.getBoundingClientRect(), k = cv.width / r.width, px = (e.clientX - r.left) * k, py = (e.clientY - r.top) * k;
  drag = sim.objects.find((o) => { const [x, y] = toPx(o.position); return Math.hypot(x - px, y - py) < 18; });
});
cv.addEventListener("pointermove", (e) => {
  if (!drag) return;
  const r = cv.getBoundingClientRect(), k = cv.width / r.width, w = toW((e.clientX - r.left) * k, (e.clientY - r.top) * k);
  if (Math.hypot(w.x, w.z) > 0.05) { drag.position = w; draw(); }
});
addEventListener("pointerup", () => (drag = null));
$("heading").oninput = (e) => { sim.agent.heading = +e.target.value; $("hval").textContent = e.target.value + "°"; draw(); };
$("add").onclick = () => {
  const n = sim.objects.length, l = LABELS[n % LABELS.length];
  sim.objects.push({ id: `${l}_${n}`, label: l, position: { x: Math.cos(n) * 2, y: 0, z: Math.sin(n) * 2 } }); draw();
};
$("speakSim").onclick = () => {
  // Same pipeline as live mode: canonical sim scene -> WebXR frame (z flipped, yaw negated) -> relations -> sentence.
  const half = -sim.agent.heading * Math.PI / 360, q = [0, Math.sin(half), 0, Math.cos(half)];
  const objs = sim.objects.map((o) => ({ id: o.id, label: o.label, position: [o.position.x, 0, -o.position.z] }));
  speak(L.summarySentence(L.relationsFor([0, 0, 0], q, objs).relations));
};
draw();

// ------------------------------------------------------------------ SPEECH
function speak(text) {
  $("said").textContent = text;
  try {
    if (!("speechSynthesis" in window)) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text); u.rate = 1.0; speechSynthesis.speak(u);
  } catch (e) { /* speech unavailable: text is still shown */ }
}

// ------------------------------------------------------------------ LIVE MIXED REALITY
const xrBtn = $("xrBtn");
(async () => {
  const ok = navigator.xr && (await navigator.xr.isSessionSupported("immersive-ar").catch(() => false));
  xrBtn.disabled = !ok;
  xrBtn.textContent = ok ? "Start Mixed Reality" : "Mixed reality needs Quest Browser or Chrome on an AR device";
})();

function makeLabelSprite() {
  const canvas = document.createElement("canvas"); canvas.width = 1024; canvas.height = 256;
  const tex = new THREE.CanvasTexture(canvas); tex.colorSpace = THREE.SRGBColorSpace;
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false, depthWrite: false });
  const sprite = new THREE.Sprite(mat); sprite.renderOrder = 999; sprite.userData = { canvas, tex, text: "" };
  return sprite;
}
function setLabel(sprite, title, sub, color) {
  const key = title + "|" + sub + "|" + color;
  if (sprite.userData.text === key) return;
  sprite.userData.text = key;
  const { canvas, tex } = sprite.userData, g = canvas.getContext("2d");
  g.clearRect(0, 0, canvas.width, canvas.height);
  g.fillStyle = "rgba(12,14,18,0.82)"; g.beginPath(); g.roundRect(8, 8, canvas.width - 16, canvas.height - 16, 48); g.fill();
  g.fillStyle = color; g.beginPath(); g.roundRect(8, 8, 28, canvas.height - 16, 14); g.fill();
  g.fillStyle = "#ffffff"; g.font = "bold 92px system-ui, sans-serif"; g.textBaseline = "middle";
  g.fillText(title, 72, 92);
  g.fillStyle = color; g.font = "bold 72px system-ui, sans-serif"; g.fillText(sub, 72, 184);
  tex.needsUpdate = true;
}

async function startXR() {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(window.devicePixelRatio); renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.xr.enabled = true; renderer.xr.setReferenceSpaceType("local-floor");
  renderer.domElement.style.display = "none"; document.body.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.01, 50); scene.add(camera);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x444444, 2.0));

  const session = await navigator.xr.requestSession("immersive-ar", {
    requiredFeatures: ["local-floor"],
    optionalFeatures: ["plane-detection", "mesh-detection", "hit-test", "hand-tracking", "anchors"],
  });
  await renderer.xr.setSession(session);
  const refSpace = renderer.xr.getReferenceSpace();
  let hitSource = null;
  try { hitSource = await session.requestHitTestSource({ space: await session.requestReferenceSpace("viewer") }); } catch (e) { /* no hit-test */ }

  // reticle where the user is looking (for placing objects)
  const reticle = new THREE.Mesh(new THREE.RingGeometry(0.06, 0.08, 32).rotateX(-Math.PI / 2),
    new THREE.MeshBasicMaterial({ color: 0x5aa9ff, transparent: true, opacity: 0.9 }));
  reticle.matrixAutoUpdate = false; reticle.visible = false; scene.add(reticle);

  // heads-up panel that follows the view
  const hud = makeLabelSprite(); hud.scale.set(0.48, 0.12, 1); hud.position.set(0, -0.32, -1.1); camera.add(hud);

  const idFor = L.createRegistry(); const placed = []; const sprites = new Map(); const dots = new Map();
  let lastHit = null, latest = { relations: [] }, lastUpdate = 0, startedAt = performance.now(), sawRoomData = false;

  session.addEventListener("select", () => {
    const fromRoom = latest.relations.some((r) => !placed.find((p) => p.id === r.id));
    if (!fromRoom && lastHit) placeAtHit(); else speak(L.summarySentence(latest.relations));
  });
  session.addEventListener("squeeze", () => { if (lastHit) placeAtHit(); });
  function placeAtHit() {
    const p = lastHit.transform.position, label = LABELS[placed.length % LABELS.length];
    placed.push({ id: `${label} ${placed.length + 1}`, label, position: [p.x, p.y, p.z] });
    speak(`Placed ${label}.`);
  }

  renderer.setAnimationLoop((t, frame) => {
    if (frame) {
      const pose = frame.getViewerPose(refSpace);
      if (hitSource) {
        const hits = frame.getHitTestResults(hitSource);
        lastHit = hits.length ? hits[0].getPose(refSpace) : null;
        reticle.visible = !!lastHit; if (lastHit) reticle.matrix.fromArray(lastHit.transform.matrix);
      }
      if (pose && t - lastUpdate > 120) {
        lastUpdate = t;
        const objs = L.collectObjects(frame, refSpace, idFor, placed);
        if (frame.detectedPlanes || frame.detectedMeshes) sawRoomData = sawRoomData || objs.some((o) => !o.source);
        const p = pose.transform.position, o = pose.transform.orientation;
        try { latest = L.relationsFor([p.x, p.y, p.z], [o.x, o.y, o.z, o.w], objs); } catch (e) { latest = { relations: [] }; }
        window.__egoLive = latest;  // read-only debug hook (used by automated tests)
        const seen = new Set();
        for (const r of latest.relations) {
          seen.add(r.id);
          let s = sprites.get(r.id), d = dots.get(r.id);
          if (!s) {
            s = makeLabelSprite(); scene.add(s); sprites.set(r.id, s);
            d = new THREE.Mesh(new THREE.SphereGeometry(0.035, 16, 12), new THREE.MeshBasicMaterial({ color: 0xffffff }));
            scene.add(d); dots.set(r.id, d);
          }
          const k = Math.max(1, r.distance / 2);
          s.scale.set(0.4 * k, 0.1 * k, 1);
          s.position.set(r.position[0], r.position[1] + 0.25 * k, r.position[2]);
          d.position.set(r.position[0], r.position[1], r.position[2]); d.material.color.set(COLORS[r.direction]);
          setLabel(s, r.label.toUpperCase(), `${r.direction.toUpperCase()} · ${r.distance.toFixed(1)} m`, COLORS[r.direction]);
        }
        for (const [id, s] of sprites) if (!seen.has(id)) { scene.remove(s); scene.remove(dots.get(id)); sprites.delete(id); dots.delete(id); }
        const n = latest.relations.length;
        const waiting = !sawRoomData && performance.now() - startedAt > 4000;
        setLabel(hud, `EgoSpatial Live · ${n} object${n === 1 ? "" : "s"}`,
          n ? "Pinch / trigger: hear where things are" : (waiting ? "No room data: pinch at a surface to place" : "Scanning your room…"), "#5aa9ff");
      }
    }
    renderer.render(scene, camera);
  });

  session.addEventListener("end", () => {
    renderer.setAnimationLoop(null); renderer.dispose(); renderer.domElement.remove();
    $("mode").className = "badge sim"; $("mode").textContent = "SIMULATED";
  });
  $("mode").className = "badge live"; $("mode").textContent = "LIVE DEVICE PERCEPTION";
  speak("EgoSpatial Live started. Pinch or pull the trigger to hear where things are.");
}
xrBtn.onclick = () => startXR().catch((e) => { $("said").textContent = "Could not start mixed reality: " + e.message; });
