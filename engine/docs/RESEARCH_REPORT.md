# EgoSpatial-Gemma research report

_Status: internal technical report. Not peer reviewed and not published._

## 1. Summary
EgoSpatial-Gemma set out to make Gemma-2-2b-it a spatial reasoning engine for XR. Fine-tuning (V4 LoRA) reached 75% on a balanced four-way egocentric benchmark: 100% on front/behind but **chance on left/right**.

We diagnosed the failure at three levels:

- **Behaviour.** The original V4 and a targeted intervention both score about 51–53% on left/right questions in the untouched test set.
- **Output layer.** V4's apparent right bias is a bf16 tie-break artifact near Gemma-2's logit softcap.
- **Hidden states.** Layer-wise linear probes find no left/right signal at any layer of either adapter, while front/behind is perfectly decodable.

Based on this evidence, the final system assigns **all geometry to a deterministic engine** and uses Gemma only as an optional language-to-query parser whose output is validated. The hybrid scores 100% on the untouched V4 test (800/800). On unseen phrasings it scores 87.5% with the improved parser (73.8% with the original), and it abstains instead of guessing when it cannot parse. The engine is packaged as dependency-free Python with JS, C# and Kotlin ports, an HTTP API, and a hosted WebXR demo.

## 2. Methodology
- **Controlled splits.** V4 train, validation and test are deduplicated and leakage-checked. No training or tuning used the test set. Probes were trained on validation with scene-grouped cross-validation.
- **Same-session comparisons.** Both adapters were evaluated in one session on the same GPU, with an identical prompt contract and a reproduction gate against the 08C-10 baseline.
- **Controls.** The probes used a positive control (front/behind), a majority-class baseline, shuffled labels, and bootstrap 95% CIs. The hybrid was evaluated with a dev check on validation before touching test. Parser changes were evaluated only on fresh phrasings.
- **Persistence.** Every artifact was uploaded to Hugging Face and verified by re-downloading it and matching SHA-256.

## 3. Experiment history (this phase)
| ID | Question | Result |
|---|---|---|
| 08A | Canonical spatial state | Schema, frames, validation; tests passed (historical) |
| 08B | Deterministic relations | Object→agent and object→object; tests passed (historical) |
| 08C-10 | Frozen V4 on the untouched test | 603/800 = 75.38%; left 10/200, right 193/200 |
| 08C-16 | Final-layer probe (n=100) | 0.50, too small to be conclusive |
| 08D-1..3 | Targeted lateral LoRA intervention | Trained: 6,000 examples, 750 steps |
| 08D-4 | Intervention on validation (fp16) | 75.50%; left 65%, right 37% |
| 08D-5 | Original vs intervention on test (bf16, same session) | 75.38% vs 76.25%; lateral 50.75% vs 52.5% |
| 08D-6A | Token / dtype / tie audit | Answer tokens left=1672, right=1331. V4 has 379/400 exact bf16 ties, all decoded as `right`. fp32 margins are uninformative (AUC 0.59). |
| 08D-6B/6C | Layer-wise probes on 27 layers × 3 models | Left/right at chance for both adapters at every layer (best 0.545). Base model reaches 0.67 at L23. Front/behind control is 1.000 from L14. |
| 08D-7 | Decision | No further LoRA work. Geometry goes to the deterministic engine; Gemma is a parser only. |
| 08E | Hybrid orchestrator | Test 100% (800/800). Paraphrase stress 88.5% vs V4 direct 61.0%. All errors are parsing errors. |
| 09 | Portable package | 23 tests, 3,204/3,204 JS conformance checks, 20,000/20,000 parity with 08B-2 |
| 10 | XR integration | WebXR demo hosted over HTTPS. Unity and Android ports written. Device runs pending. |
| 11 | Fresh-phrasing parser evaluation | Parser v1 73.8%, v2 87.5%. Neural parse latency median 1.48 s (p95 1.81 s) (T4). Deterministic path 0.017 ms median. |

## 4. What the model learned and what it did not
- **Learned:** the output format, front/behind (an equality test between heading and direction), and the task templates.
- **Not learned:** handedness, i.e. whether a direction is +90° or −90° from the heading. Left and right collapsed into one undifferentiated "lateral" state.
- **What the intervention changed:** the tie-break balance (fewer exact ties, a slight left preference), not the representation.
- **Caveat:** probes are linear, read only the answer position, and are correlational. We do not claim causal erasure.

## 5. Final system evaluation (untouched V4 test, n=800)
| System | Overall | Front | Behind | Left | Right | Egocentric | Object→object |
|---|---:|---:|---:|---:|---:|---:|---:|
| Original V4 | 75.38% | 100% | 100% | 6.0% | 95.5% | 75.8% | 75.0% |
| Intervention | 76.25% | 100% | 100% | 50.0% | 55.0% | 77.0% | 75.5% |
| Deterministic engine | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| Hybrid | 100% | 100% | 100% | 100% | 100% | 100% | 100% |

**Interpretation.** The V4 test reuses the training templates, so 100% here shows correct template parsing plus exact geometry. It does not show language understanding, which is measured separately in the paraphrase sets (08E and 11).

**Robustness** (invalid input cases in 08E and the Python tests):
- Malformed JSON, a bad heading, duplicate IDs and an empty scene each produce a structured error.
- An unknown object produces an abstention ("unresolved").
- Self-reference produces an error.
- No case produces a fabricated direction.

## 6. Demonstrated vs. not yet demonstrated
| Capability | Status |
|---|---|
| Exact four-way egocentric and object-relative relations from coordinates | Demonstrated (tests, parity, V4) |
| Cross-platform numerical consistency (Python ↔ JS) | Demonstrated (3,204 checks) |
| Question parsing with Gemma on unseen phrasings | 87.5% on fresh phrasings (egocentric 98.3%, object→object 76.9%). 28/240 confidently wrong answers come from mis-parses, so this is the main open weakness. |
| WebXR simulated mode | Demonstrated (headless browser) |
| WebXR **live** device perception | **Not yet demonstrated.** Hosted and ready for an on-device test. |
| Unity / Quest 3S, Android XR | **Code only.** Not compiled or run. |
| Real-world evaluation with perception noise | **Not done** |
| General spatial intelligence | **Not claimed** |

## 7. Limitations and future work
- The benchmark is synthetic and narrow: four cardinal directions, two objects, 12 names.
- Finer relations (diagonals, near/far, above/below, containment) and uncertainty handling are not implemented.
- Real perception noise needs to be measured: label errors, pose drift, anchor jitter.
- Parsing should be trained or constrained (for example, grammar-constrained JSON decoding) rather than prompt-only.
- Any return to neural spatial reasoning should supervise an intermediate signed-angle representation rather than answer tokens, and should be validated with causal methods.

## 8. Artifact index
- **Model repo** `Platinum04/EgoSpatial-Gemma-v2`:
  - `v4_final_run/`
  - `08_spatial_state_builder/08A…08E/`
  - `11_evaluation/`
  - `engine/egospatial-1.0.0/`
  - `PROJECT_STATUS.md`
  - `github_staging/` (mirror of code and docs for GitHub)
- **Dataset repo** `datasets/Platinum04/EgoSpatial-Gemma-data`: `v2/`, `v3/`, `v4/`
- **WebXR Space:** `spaces/Platinum04/EgoSpatial-WebXR`
