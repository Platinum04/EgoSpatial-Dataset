# EgoSpatial XR: native Android XR app (Jetpack Compose for XR)

[![android-xr](https://github.com/Platinum04/EgoSpatial-Dataset/actions/workflows/android-xr.yml/badge.svg)](https://github.com/Platinum04/EgoSpatial-Dataset/actions/workflows/android-xr.yml)

EgoSpatial XR answers "where is everything around me?" in a native Android XR app.

* **On Android XR (Full Space)**, two spatial panels float around you. Both are movable and resizable:
  * a top-down room map, with North up and the user as the arrow;
  * a relations panel listing each object's direction, front / behind / left / right, and its distance.
* **On a phone or tablet**, the same UI is shown side by side.
* **Ask "Where is the table?"** and the app answers out loud.
* **For an unknown object it refuses instead of guessing.** That's the design rule this project's research supports: directions come from the deterministic `EgoSpatial` engine (`app/src/main/java/dev/egospatial/EgoSpatial.kt`, the Kotlin port of the Python reference), never from a language model.
* **Turn with the heading slider**, and tap the map to place a mug.

## Get the app without installing Android Studio
Every push builds the app on GitHub Actions:
1. Open the **Actions** tab, then the latest **android-xr** run.
2. Download the **egospatial-xr-debug-apk** artifact.

The run also executes the unit tests in `app/src/test`.

## Build it yourself
To build locally you need **JDK 17** (the project toolchain; Android Studio's bundled JDK 25 alone fails with "Cannot find a Java installation ... languageVersion=17").

- **Command line:** `gradlew testDebugUnitTest assembleDebug` (Gradle 9.6.0 wrapper included), with `JAVA_HOME` pointing at a JDK 17.
- **Android Studio:** File → Open → this `android-xr` folder; set Settings → Build Tools → Gradle → Gradle JDK to a JDK 17; run configuration **app**.

It is designed to run on the Android XR emulator, XR headsets and Android phones (2D fallback). It has been run in 2D on a real Android phone and on a phone emulator (Pixel 8, API 36): see `../docs/android-xr-emulator.png` and `../docs/android-xr-emulator-demo.mp4`. Not yet tested in XR.

Build versions mirror Google's official sample [android/xr-samples](https://github.com/android/xr-samples):

| Component | Version |
|---|---|
| AGP | 9.4.1 |
| Kotlin | 2.4.21 |
| Jetpack Compose for XR | 1.0.0-beta02 |
| compileSdk | 37 |

## Files
| Path | Purpose |
|---|---|
| `app/src/main/java/dev/egospatial/EgoSpatial.kt` | Deterministic engine (canonical frame +X East, +Z North, heading clockwise from North) |
| `app/src/main/java/dev/egospatial/Logic.kt` | Room model, relations, spoken answers, abstention |
| `app/src/main/java/dev/egospatial/xr/EgoSpatialApp.kt` | Compose UI: `Subspace` → `SpatialRow` → two `SpatialPanel`s, with a 2D fallback |
| `app/src/test/java/dev/egospatial/LogicTest.kt` | JVM unit tests (turning, distance order, abstention, convention parity) |

**Next step:** replace the hand-placed room with live data from ARCore for Jetpack XR (planes and anchors) via `EgoSpatial.fromArPose(...)`, the same way EgoSpatial Live uses WebXR plane detection on Quest.
