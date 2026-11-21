# EgoSpatial — Unity demo (desktop; Quest 3S build not done yet)

A Unity 6 (6000.6.9f1) project around the C# engine in `engine/ports/unity/`.

## What works (verified 2026-11-21, Unity 6000.6.9f1, Windows)
- **Conformance:** the C# engine passes 3,103/3,103 checks against `engine/tests/vectors.json`
  (relations, reference frames, Unity quaternion adapter, invalid-state rejection).
- **Demo scene** `Assets/Scenes/EgoSpatialDemo.unity`: camera at the origin, a table, couch, storage unit and door,
  each with a live label (`TABLE · LEFT · 2.0 m`) and a HUD list. The camera turns slowly so the labels change.
- **Rendered check** at four headings (`Screenshots/`, `Screenshots/relations.txt`):
  facing N: table left, couch behind, storage right, door front; facing E: table behind, couch right, storage front, door left.

## Not done yet
- No XR packages (OpenXR / Meta XR SDK) and no Quest 3S build or headset run.
- No live room data (MRUK scene anchors); objects are placed by hand (`source = "simulated"`).

## Run it
Open this folder in Unity Hub (Unity 6000.6.9f1), open `Assets/Scenes/EgoSpatialDemo.unity`, press Play.
Menu **EgoSpatial → Run conformance** / **Build demo scene**.

Batch mode:
```
Unity -batchmode -quit -projectPath . -executeMethod EgoSpatial.EditorTools.RunConformanceBatch
Unity -batchmode -quit -projectPath . -executeMethod EgoSpatial.EditorTools.RenderHeadingsBatch
```
