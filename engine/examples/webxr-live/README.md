# EgoSpatial Live: mixed reality on Meta Quest 3 / 3S and Android XR

**Live demo:** https://platinum04-egospatial-webxr.static.hf.space/ (public Space: `Platinum04/EgoSpatial-WebXR`)

EgoSpatial Live answers the question "where is everything around me?" for the real furniture in your room, and it updates as you move.

* It reads semantic room data from WebXR `plane-detection` and `mesh-detection` (Quest **Space Setup** labels: table, couch, bed, door, storage…).
* It floats a label over each object, for example **TABLE · LEFT · 1.8 m**, with the label colour set by direction. The labels re-compute every 120 ms from the head pose.
* **Pinch or trigger** speaks a summary of where things are (Web Speech). **Grip** places your own object at the hit-test point.
* Every direction comes from the deterministic EgoSpatial engine (`egospatial.js`, the same file as `ports/js`). That engine is conformance-tested against the Python reference. **No language model guesses a direction**, which is the central finding of this project.
* A simulated top-down mode works in any browser.

## Run on Quest 3 / 3S
1. Settings → Physical space → **Space Setup** (label your furniture).
2. Open the demo URL in **Quest Browser** and press **Start Mixed Reality**. Allow spatial data when the headset asks.

## Files
| file | role |
|---|---|
| `index.html` | page, Quest instructions, importmap (`three` → vendored `three.module.min.js` r160) |
| `app.js` | three.js WebXR session (`immersive-ar`, `local-floor`; optional plane/mesh detection, hit-test, hand-tracking, anchors), labels, HUD, speech |
| `scene-logic.js` | pure logic: WebXR frame → canonical objects → relations (UMD, testable in Node) |
| `egospatial.js` | engine (identical to `engine/ports/js/egospatial.js`) |
| `scene-logic.test.js` | 13 tests with a fake WebXR frame (`node scene-logic.test.js`) |

The coordinate convention is that WebXR looks down −Z. The adapter maps that to the engine's canonical frame (+X East, +Z North, heading clockwise from North) with `z → −z`. The app was verified in an emulated Meta Quest 3 (IWER 2.8) with a synthetic labelled room. Facing −Z it reported table *left*, couch *behind*, storage *right* and door *front*. After a 90° left turn it reported table *front*, couch *left*, storage *behind* and door *right*.

To run it locally, serve the folder over HTTP and download `three.module.min.js` from `three@0.160.0/build/` into the folder.
