# XR integration guide

Every integration has three steps:

1. Read the platform pose and object positions.
2. Convert them to the canonical frame with the adapter or port.
3. Compute relations with the deterministic engine, either on-device through a port or by calling the HTTP API.

**Always label the data source.** `simulated` means hand-placed scene objects. `recorded` means replayed perception logs. `live` means real device perception at runtime.

| Platform | Axes | Heading from | Code | Verification status |
|---|---|---|---|---|
| Unity / Meta Quest 3S | Left-handed, +Z forward | `camera.rotation * Vector3.forward` | `ports/unity/EgoSpatialEngine.cs`, `EgoSpatialSceneBridge.cs` | Formulas cross-checked numerically. **Not compiled or run in Unity yet.** |
| WebXR (Quest Browser, Chrome Android ARCore) | Right-handed, −Z forward | `XRViewerPose.transform.orientation` | `ports/js/egospatial.js`, `examples/webxr/` | JS port passes 3,204 conformance checks. Simulated mode verified headless. **Live AR not yet run on a device.** |
| Android XR (Jetpack XR / ARCore for Jetpack XR) | Right-handed, −Z forward (OpenXR) | Session / ARCore `Pose` rotation | `ports/android/EgoSpatial.kt` | Formulas cross-checked numerically. **Not compiled or run on device yet.** |
| Any platform | — | — | `egospatial-server` HTTP API | Tested (Python integration test) |

## Unity / Meta Quest 3S
1. Copy `ports/unity/*.cs` into `Assets/EgoSpatial/`.
2. Add `EgoSpatialSceneBridge` to a GameObject. Set `xrCamera` to `CenterEyeAnchor` (OVRCameraRig) or `Main Camera`.
3. **Simulated:** drag scene objects into `objects` and set `source = simulated`.
4. **Live on Quest 3S:** use Meta MR Utility Kit (MRUK) scene anchors (TABLE, COUCH, DOOR_FRAME, …) or user-placed spatial anchors. Add their transforms at runtime and set `source = live`.
5. Optionally assign a world-space `TextMesh` to `debugLabel` to see relations in the headset.

Unity's +yaw turns right (clockwise), which matches the canonical heading directly.

## WebXR
- Serve `examples/webxr/` over **HTTPS**. WebXR requires a secure context, and `localhost` also works for desktop testing.
- **Simulated mode** works in any browser: drag objects and turn the agent.
- **Live mode** (`immersive-ar` with `hit-test`): tap real surfaces to place objects. The viewer pose updates the relations every frame. Canonical North is the session's initial forward direction.

## Android XR
- Two options:
  - Embed `EgoSpatial.kt` and call `EgoSpatial.fromArPose(...)` with the head pose, plus anchor or plane-centre poses from the same session.
  - Call the HTTP API from the device.
- Perception differs between devices. Plane detection, scene meshing and semantic labels are not uniformly available on all Android XR hardware, so check capabilities at runtime and record them with each logged scene.

## Cross-platform consistency
`tools/make_vectors.py` generates `tests/vectors.json` from the Python reference. Every port must reproduce every expected direction and heading. The JS runner is `node ports/js/conformance.test.js`. Equivalent runners for C# and Kotlin are a TODO, to be added when those toolchains are available.
