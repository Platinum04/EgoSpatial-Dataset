# EgoSpatial-Gemma

**Diagnosing why a fine-tuned small language model fails at egocentric left/right reasoning, and building a reliable hybrid spatial reasoning engine for XR.**

[![ci](https://github.com/Platinum04/EgoSpatial-Dataset/actions/workflows/ci.yml/badge.svg)](https://github.com/Platinum04/EgoSpatial-Dataset/actions/workflows/ci.yml)
· Model and experiment artifacts: [huggingface.co/Platinum04/EgoSpatial-Gemma-v2](https://huggingface.co/Platinum04/EgoSpatial-Gemma-v2)
· Datasets: [huggingface.co/datasets/Platinum04/EgoSpatial-Gemma-data](https://huggingface.co/datasets/Platinum04/EgoSpatial-Gemma-data)
· Live WebXR demo: [huggingface.co/spaces/Platinum04/EgoSpatial-WebXR](https://huggingface.co/spaces/Platinum04/EgoSpatial-WebXR)

## Findings
We fine-tuned Gemma-2-2b-it with LoRA ("V4") to answer egocentric spatial questions such as "Where is the lamp relative to me?" from a structured scene description.

1. **Behaviour.** V4 reaches 100% on *front/behind* but stays at chance on *left/right*. On the untouched 800-question test set it scores 75.38% overall: left 6%, right 95.5%. A targeted intervention with 4,000 extra lateral examples moved left/right to 50% / 55%, which is still chance (lateral 52.5%).
2. **Output layer.** The apparent "right bias" is a numerical artifact. Gemma-2 caps its output scores at 30, and on lateral questions both `left` and `right` sit at about 29.75. In bf16 they become **exact ties in 379 of 400 cases**, and greedy decoding picks the lower token id, `right`. Recomputed in fp32, the model weakly prefers `left` every time and still does not discriminate (AUC 0.59).
3. **Hidden states.** We ran linear probes at all 27 layers, using scene-grouped cross-validation on the validation split. Left/right is **not linearly decodable at any layer** of either fine-tuned model (best 0.545, 95% CI 0.50–0.60). Front/behind reaches **1.000 from layer 14** under the identical method, which serves as the positive control.
4. **Interpretation.** Front/behind reduces to an equality test (same or opposite of the heading). Left/right requires *handedness* (+90° vs −90°), which the models never represented. More fine-tuning of the answer token is not justified by this evidence.
5. **Architecture decision.** Geometry is computed by a deterministic engine. The language model is used only to turn free-form questions into a structured query, its output is validated, and the engine abstains instead of guessing.

| System (untouched V4 test, n = 800) | Overall | Front | Behind | Left | Right |
|---|---:|---:|---:|---:|---:|
| Gemma-2-2b-it + V4 LoRA | 75.38% | 100% | 100% | 6.0% | 95.5% |
| + targeted lateral intervention | 76.25% | 100% | 100% | 50.0% | 55.0% |
| Hybrid engine (this repo) | 100% | 100% | 100% | 100% | 100% |

The V4 test reuses the training question templates, so the hybrid's 100% reflects correct template parsing plus exact geometry. Language robustness is measured separately on **240 freshly worded questions**: the hybrid with the Gemma parser scores **87.5%** (egocentric 98.3%, object-relative 76.9%). Every error is a question-parsing error, never a geometry error.

Full write-up: [`engine/docs/RESEARCH_REPORT.md`](engine/docs/RESEARCH_REPORT.md) and the decision record [`engine/docs/08D-7_REPORT.md`](engine/docs/08D-7_REPORT.md).

## Repository layout
| Path | Contents |
|---|---|
| [`engine/`](engine/) | `egospatial`: a dependency-free Python package with a CLI and HTTP API, plus JS (WebXR), C# (Unity) and Kotlin (Android XR) ports, tests and benchmarks |
| [`engine/docs/`](engine/docs/) | Research report, architecture, API, XR integration guide, datasets, model training, reproducibility |
| [`engine/examples/webxr/`](engine/examples/webxr/) | WebXR demo: simulated mode, plus live `immersive-ar` with hit-test |
| [`notebooks/`](notebooks/), `EgoSpatial_Gemma_Prototype.ipynb` | The Colab research notebook (experiments 01–12) |
| `v1_balanced_*_scannetv2.json` | SQA3D-style balanced question and annotation files (ScanNet scenes) from the project's early data exploration. Their use is subject to the original SQA3D/ScanNet terms. |
| [`PROJECT_STATUS.md`](PROJECT_STATUS.md) | Milestone tracker with every artifact location |

## Quick start
```bash
cd engine
pip install .                                   # Python >= 3.9, no dependencies
egospatial --state examples/scene.json --question "Where is the chair_01 relative to me?"   # -> front
python -m unittest discover -s tests            # 23 tests
node ports/js/conformance.test.js               # JS port: 3204/3204 checks against the Python reference
egospatial-server --port 8765                   # HTTP JSON API for Unity / WebXR / Android XR clients
```

## Status
| Component | Status |
|---|---|
| Deterministic engine (Python) | Tested. Parity with the original 08B engine on 20,000 random scenes; 100% on V4 validation and test. |
| JavaScript / WebXR | 3,204/3,204 conformance checks. Demo hosted over HTTPS. **Live on-device run pending.** |
| Unity (C#) and Android XR (Kotlin) ports | Written, formulas numerically cross-checked. **Not yet compiled or run on device.** |
| Gemma semantic parser | 87.5% on fresh phrasings. 28/240 questions are mis-parsed and answered confidently wrong. Main open weakness. |
| Real-world evaluation (perception noise) | Not yet done |

## Limitations
- The data is synthetic: four cardinal directions, two objects per scene, a 12-word object vocabulary.
- Probe results are linear and correlational. We do not claim causal erasure.
- Results come from one model family (Gemma-2-2b-it). We do not claim general spatial intelligence.

## Citation
```bibtex
@misc{awodi2026egospatial,
  title  = {EgoSpatial-Gemma: Diagnosing Egocentric Left/Right Failure in a Fine-Tuned Small Language Model and a Hybrid Spatial Reasoning Engine for XR},
  author = {Awodi, Abdulmujeeb},
  year   = {2026},
  howpublished = {\url{https://github.com/Platinum04/EgoSpatial-Dataset}},
  note   = {Technical report, not peer reviewed}
}
```
