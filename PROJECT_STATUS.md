# EgoSpatial-Gemma — PROJECT STATUS

_Last updated: 2026-11-10 (v1.0.1 released; GitHub + Hugging Face public)_

## Repositories
| Purpose | Location | Access |
|---|---|---|
| Code, docs, CI | [github.com/Platinum04/EgoSpatial-Dataset](https://github.com/Platinum04/EgoSpatial-Dataset) | Public |
| Model adapters + all experiment artifacts | [hf: Platinum04/EgoSpatial-Gemma-v2](https://huggingface.co/Platinum04/EgoSpatial-Gemma-v2) | Public |
| Datasets (v2, v3, v4) | [hf: datasets/Platinum04/EgoSpatial-Gemma-data](https://huggingface.co/datasets/Platinum04/EgoSpatial-Gemma-data) | Public |
| WebXR demo (HTTPS) | [hf: spaces/Platinum04/EgoSpatial-WebXR](https://huggingface.co/spaces/Platinum04/EgoSpatial-WebXR) | Public |
| Research notebook | `EgoSpatial_Gemma_Prototype.ipynb` (Colab / this repo) | Public |

## Milestones
| ID | Milestone | Status | Artifact (HF model repo unless noted) |
|---|---|---|---|
| 08A | Spatial state representation | ✓ | `08_spatial_state_builder/08A-*` |
| 08B | Deterministic relationship engine | ✓ | `08_spatial_state_builder/08B-*` |
| 08C | Frozen V4 diagnosis | ✓ | `08_spatial_state_builder/08C-*` |
| 08D-1..4 | Lateral intervention dataset, LoRA training, validation | ✓ | `08D/dataset`, `08D/intervention/v1/` |
| 08D-5 | Untouched-test comparison (original vs intervention) | ✓ | `08D/test_eval/08d5_v1/` |
| 08D-6A | Inference / tokenization / bf16-tie verification | ✓ | `08D/08D-6/6A/` |
| 08D-6B/C | Layer-wise hidden states + linear probes | ✓ | `08D/08D-6/6BC/` |
| 08D-7 | Interpretation + architecture decision | ✓ | `08D/08D-7/08D-7_REPORT.md` |
| 08E | Hybrid orchestrator (deterministic geometry + Gemma parsing) | ✓ | `08E/` |
| 09 | Portable engine package (Python + JS/C#/Kotlin ports, HTTP API) | ✓ | `engine/egospatial-1.0.1/`, GitHub `engine/` |
| 10 | XR integration | ◐ WebXR hosted; on-device runs pending | Space, `engine/ports/`, `engine/examples/webxr/` |
| 11 | Evaluation (fresh phrasings, latency, invalid inputs, cross-platform) | ✓ | `11_evaluation/` |
| 12 | Documentation + release v1.0.1 | ✓ | GitHub `engine/docs/`, `engine/RELEASE_NOTES.md` |

## Key results
| System (untouched V4 test, n=800) | Overall | Front | Behind | Left | Right |
|---|---:|---:|---:|---:|---:|
| Gemma-2-2b-it + V4 LoRA | 75.38% | 100% | 100% | 6.0% | 95.5% |
| + 08D lateral intervention | 76.25% | 100% | 100% | 50.0% | 55.0% |
| Hybrid engine | 100% | 100% | 100% | 100% | 100% |

- **08D-6A:** 379/400 lateral test answers of V4 are exact bf16 ties (logits ≈29.75 near the 30.0 softcap) that decode as `right`. fp32 margins are uninformative (AUC 0.586).
- **08D-6B/C:** left/right is not linearly decodable at any of the 27 layers for either adapter (best 0.545, 95% CI 0.50–0.60). The front/behind control is 1.000 from layer 14.
- **Fresh phrasings (240 questions):** the hybrid with parser v2 scores 87.5% (v1: 73.8%). There were 28 confident mis-parses. Neural parse takes ≈1.5 s on a T4; the deterministic path takes 0.017 ms.

## Remaining work
1. **WebXR on device:** open the Space in Quest Browser or Chrome on ARCore → Start LIVE AR → place objects → turn around → record a video.
2. **Android XR app** (Jetpack XR) built on `engine/ports/android/EgoSpatial.kt`. Run it on a device or the Android XR emulator and record.
3. **Unity / Quest 3S** build using `engine/ports/unity/`.
4. **Research strengthening:** replicate the probe study on 2–3 more models, add a causal (activation-patching) test, and write the paper.
5. **Parser:** constrained JSON decoding or a trained parser; show the parsed query in the UI.
6. **Real-world evaluation** with perception noise.

## Persistence rule
GENERATE → VERIFY → BACKUP → VERIFY REMOTE (re-download + SHA-256 match) → CONTINUE.
