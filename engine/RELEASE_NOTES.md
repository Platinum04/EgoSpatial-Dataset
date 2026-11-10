# EgoSpatial 1.0.0 release notes (2026-11-10)

## What's in this release
- **The `egospatial` Python package.** Deterministic egocentric, object-to-object, reference-frame and distance relations. It validates input states, serializes deterministically, abstains on unparseable questions, and ships a CLI and an HTTP API. It has no dependencies.
- **An optional Gemma-2-2b-it semantic parser** (`egospatial.neural`). Its JSON output is validated against the scene, and it never produces geometry itself.
- **Platform adapters** for Unity, WebXR / OpenXR / Android XR and the V4 dataset, with `north_offset_deg` alignment and a `source` tag (simulated / recorded / live).
- **Ports:**
  - JavaScript (`ports/js`): conformance-verified.
  - C# for Unity (`ports/unity`) and Kotlin for Android XR (`ports/android`): formulas cross-checked, not compiled here.
- **A WebXR demo** (`examples/webxr`) with simulated mode and live `immersive-ar` hit-test mode, hosted at `https://huggingface.co/spaces/Platinum04/EgoSpatial-WebXR`.
- **Research artifacts** for 08D-5 through 11 on Hugging Face, each backed up and verified by SHA-256.

## Verified
- 23 Python unit and integration tests pass.
- The JS port passes 3,204 of 3,204 conformance checks.
- 20,000 of 20,000 random scenes match the original 08B-2 engine.
- The engine scores 100% on V4 validation and 100% on the untouched V4 test.

## Not yet verified
- The live WebXR session on a device.
- Unity and Android builds.
- Real-world evaluation with perception noise.

## Breaking or semantic notes
- "X relative to Y" defaults to the **V4 reference-frame** meaning: face Y, then classify X. For the 08B-3 metric meaning (Y→X displacement seen from the agent), use `SpatialEngine(object_relation="object_to_object")`.
- Gemma-2 classification read-outs must use fp32 logits (see the 08D-6A softcap/bf16 tie issue).
