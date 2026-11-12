# EgoSpatial-Gemma — PROJECT STATUS

_Last updated: 2026-11-12 (11-C: Gemma 4 E2B + V4 LoRA reaches 99.88% on the untouched test, left/right 100%; 11-B: E4B steering repairs left/right 0.50 → 0.79)_

## Repositories
| Purpose | Location | Access |
|---|---|---|
| Code, docs, CI | [github.com/Platinum04/EgoSpatial-Dataset](https://github.com/Platinum04/EgoSpatial-Dataset) | Public |
| Model adapters + all experiment artifacts | [hf: Platinum04/EgoSpatial-Gemma-v2](https://huggingface.co/Platinum04/EgoSpatial-Gemma-v2) | Public |
| Datasets (v2, v3, v4) | [hf: datasets/Platinum04/EgoSpatial-Gemma-data](https://huggingface.co/datasets/Platinum04/EgoSpatial-Gemma-data) | Public |
| EgoSpatial Live: mixed reality for Quest 3/3S and Android XR (HTTPS) | [platinum04-egospatial-webxr.static.hf.space](https://platinum04-egospatial-webxr.static.hf.space/) (Space `Platinum04/EgoSpatial-WebXR`; code in `engine/examples/webxr-live/`) | Public |
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
| 10 | XR integration | ◐ EgoSpatial Live deployed. It reads real room semantics via WebXR plane/mesh detection and is verified in an emulated Quest 3 (IWER). A Quest 3S recording is pending | Space, `engine/examples/webxr-live/`, `engine/ports/` |
| 11-A | Gemma 4 replication (zero-shot + layer-wise probes) | ✓ E2B, E4B (NF4) and the Gemma-2 base control | `11_evaluation/11A_gemma4/` |
| 11-B | Readout, shuffled baseline, unembedding alignment, steering (causal); Gemma-2 permutation control | ✓ E2B, E4B (NF4) and the Gemma-2 control; E4B raw JSON still to upload from the runtime | `11_evaluation/11A_gemma4/gemma-4-E2B-it/causal/` |
| 11-C | Gemma 4 E2B LoRA fine-tune (V4 recipe, QLoRA on a T4) | ✓ 99.88% untouched test; fresh-wording eval pending; adapter upload to HF pending (needs HF token in the running Colab account) | GitHub `research/11C_finetune/`; HF `11_evaluation/11C_finetune/` |
| 13 | Native Android XR app (Jetpack Compose for XR) | ◐ Builds and tests in CI (APK artifact); emulator/device run pending | GitHub `android-xr/` |
| 11 | Evaluation (fresh phrasings, latency, invalid inputs, cross-platform) | ✓ | `11_evaluation/` |
| 12 | Documentation + release v1.0.1 | ✓ | GitHub `engine/docs/`, `engine/RELEASE_NOTES.md` |

## Key results
| System (untouched V4 test, n=800) | Overall | Front | Behind | Left | Right |
|---|---:|---:|---:|---:|---:|
| Gemma-2-2b-it + V4 LoRA | 75.38% | 100% | 100% | 6.0% | 95.5% |
| + 08D lateral intervention | 76.25% | 100% | 100% | 50.0% | 55.0% |
| Gemma 4 E2B + V4 LoRA (11-C) | 99.88% | 100% | 99.5% | 100% | 100% |
| Hybrid engine | 100% | 100% | 100% | 100% | 100% |

- **08D-6A:** 379/400 lateral test answers of V4 are exact bf16 ties (logits ≈29.75 near the 30.0 softcap) that decode as `right`. fp32 margins are uninformative (AUC 0.586).
- **08D-6B/C:** left/right is not linearly decodable at any of the 27 layers for either adapter (best 0.545, 95% CI 0.50–0.60). The front/behind control is 1.000 from layer 14.
- **Fresh phrasings (240 questions):** the hybrid with parser v2 scores 87.5% (v1: 73.8%). There were 28 confident mis-parses. Neural parse takes ≈1.5 s on a T4; the deterministic path takes 0.017 ms.

- **11-A Gemma 4 (zero-shot, n=800).**
  - Overall: E2B 39.3%, E4B-NF4 36.5%.
  - Egocentric left/right: E2B 34%, E4B 18% (E4B mostly answers "front"; random four-way = 25%).
  - Linear probes (GroupKFold by object pair) recover egocentric left/right from the late layers: E2B 0.852 @L32/35, E4B 0.983 @L41/42.
  - Front/behind reaches 1.000 by the middle layers.
  - So Gemma 4 computes the lateral relation internally but does not output it. See `11_evaluation/11A_gemma4/11A_REPORT.md`.

- **11-B.**
  - Base Gemma-2 lateral probe: 0.69 (layer-search null mean 0.55, max 0.62, p = 0.02 with 49 permutations), vs 0.85 for E2B and 0.98 for E4B. Layer-search null for Gemma 4: ≈0.61.
  - E2B binary left/right readout: 0.535. Shuffled probe baseline: 0.45–0.53. cos(latent direction, unembedding difference) = 0.03.
  - Steering is monotonic but weak: Δmargin ≈ +2.6 over α ∈ [−3, 3]. Probe-guided steering reaches 0.555. The probe readout alone reaches 0.81.
  - **E4B (NF4):** binary readout 0.50. Probe 0.983, probe readout 0.945. cos(latent, unembedding) = 0.11–0.16. Steering Δmargin ≈ +15.9. **Probe-guided steering takes binary accuracy from 0.50 to 0.79**; 4-way accuracy reaches only 0.27, because of the "front" prior.

- **11-C Gemma 4 E2B + V4 LoRA:** untouched test 99.88% (egocentric 99.75%, object-to-object 100%; left 100%, right 100%; one behind→left error). Validation 100%. Loss ≈0 by step 225/500. Same recipe on Gemma-2 gave left 6%. Caveat: V4 test shares training templates.

## Remaining work
1. **Quest 3S recording of EgoSpatial Live:** run Space Setup, open the demo in Quest Browser, Start Mixed Reality, turn around, pinch, and record 30–60 s.
2. **Android XR app:** built (GitHub `android-xr/`, APK from Actions). Still to do: run it on the Android XR emulator or a device and record it, then add live ARCore planes.
3. **Unity / Quest 3S** build using `engine/ports/unity/`.
4. **Research:**
   - Upload the E4B raw `causal_results.json` from the Colab runtime to HF (needs an HF token in that account).
   - Try stronger or multi-layer steering.
   - Do a matched probe rerun on the V4 adapter.
   - ~~Fine-tune Gemma 4 E2B with the V4 recipe~~ done (11-C). Next: evaluate the adapter on the 240 fresh phrasings; upload adapter + raw JSON to HF.
   - Write the paper.
5. **Parser:** constrained JSON decoding or a trained parser; show the parsed query in the UI.
6. **Real-world evaluation** with perception noise.

## Persistence rule
GENERATE → VERIFY → BACKUP → VERIFY REMOTE (re-download + SHA-256 match) → CONTINUE.
