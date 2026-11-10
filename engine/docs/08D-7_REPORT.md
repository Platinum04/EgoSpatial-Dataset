# 08D-7 — Research Conclusion and Architecture Decision

_EgoSpatial-Gemma · 2026-11-10 · evidence: 08C-10, 08D-4, 08D-5, 08D-6A, 08D-6B/6C (all artifacts on `hf://Platinum04/EgoSpatial-Gemma-v2/08_spatial_state_builder/`)_

## 1. Question
Does fine-tuned Gemma-2-2B-it (V4 LoRA, and the 08D lateral intervention LoRA) represent LEFT vs RIGHT, and where does the distinction fail?

## 2. Evidence

### 2.1 Behaviour (08D-5, untouched V4 test, n=800, same session, T4, bf16)
| | Original V4 | Intervention |
|---|---:|---:|
| Front / Behind | 100% / 100% | 100% / 100% |
| Left / Right | 6.0% / 95.5% | 50.0% / 55.0% |
| Lateral (400) | 50.75% | 52.5% |
| Overall | 75.38% | 76.25% |

### 2.2 Output layer (08D-6A, 400 lateral test examples)
- Answer tokens verified: `left`=1672, `right`=1331 (bare tokens, as in training text). 2731 is `▁left` and is not the answer token.
- Original V4: **379/400 exact bf16 ties** between `left` and `right` (both ≈29.75, just under Gemma-2's 30.0 final-logit softcap, where bf16 resolution is 0.125). Greedy decoding chose `right` on all 379 ties, because the lower token id wins. Recomputing the head in fp32 gives a left−right margin that is positive on all 400 examples (0.005–0.022), so the unrounded model would answer `left` almost always. AUC(left vs right) = 0.586.
- **The "RIGHT bias" reported since 08C is a numerical artifact (bf16 rounding plus tie-breaking), not a learned preference.**
- Intervention: 130/400 ties, AUC 0.548.
- 08D-4 validation ran in float16 while 08C-10 and 08D-5 ran in bf16, so their lateral numbers are not directly comparable.

### 2.3 Hidden states (08D-6B/6C, V4 *validation*, GroupKFold(5) by scene object pair, ridge probes, last prompt token, 27 layers)
| Probe | Base Gemma | Original V4 | Intervention |
|---|---|---|---|
| LEFT vs RIGHT, best layer | 0.670 (L23, CI 0.63–0.72) | 0.545 (L2, CI 0.50–0.60) | 0.545 (L1, CI 0.50–0.60) |
| LEFT vs RIGHT, final layer | 0.630 | 0.453 | 0.480 |
| FRONT vs BEHIND (control), best | 0.98 (L17) | 1.000 (L14+) | 1.000 (L14+) |
| Logit-lens AUC front/behind, L18+ | ~0.7 | 1.000 | 1.000 |

The shuffled-label control was ≈0.5 everywhere. The majority baseline was ≈0.5.

## 3. Interpretation (against the five candidate explanations)
1. **Lateral information poorly encoded from early layers. Best supported for both fine-tuned models.** No layer gives above-chance linear decodability of LEFT/RIGHT at the answer position, while FRONT/BEHIND becomes perfectly decodable by layer 14 under the identical method. So the probe is sensitive enough, and the lateral distinction is simply not linearly present.
2. Available mid-network, then degraded. Not supported for V4 or the intervention: there is no mid-layer peak. Base Gemma shows the *opposite* profile, with chance until L20 and then a weak rise to 0.67.
3. Present but misaligned with the head. Not supported: there is nothing to misalign, since probes are at chance at L26.
4. Tokenization or output competition. Partly true for the *pattern* of errors (the RIGHT bias comes from bf16 ties and the softcap), but it is **not** the cause of failure. The fp32 head is also uninformative (AUC 0.59), and the hidden states lack the information.
5. Inconclusive. Not chosen. The positive control makes the negative result interpretable.

**Why front/behind works and left/right does not.** In this task, front and behind reduce to an equality test: is the object's direction the same as, or opposite to, the heading? Left and right require **handedness**, i.e. whether the object is a +90° or −90° rotation from the heading. The models learned the equality structure and collapsed the two ±90° cases into one undifferentiated "lateral" class.

**Caveats (not overclaimed).** Probes are linear and read only the final prompt position. Non-linear or other-position encodings are not excluded. Probe decodability is correlational: the drop from base (0.63–0.67 at L21–26) to fine-tuned (≈0.5) is consistent with fine-tuning *not preserving* the weak base signal, but it is not causal proof that fine-tuning erased it. n=400 per probe; CIs are reported.

## 4. Decisions
| Question | Decision |
|---|---|
| Is another LoRA intervention justified? | **No.** 08D-3 already supplied 2,000 left and 2,000 right examples and moved only the tie-break, not the representation. There is no specific, evidence-backed hypothesis that another LoRA run would create handedness. A future option, only with a new hypothesis, would be to supervise an intermediate representation (for example, signed angle) rather than the answer token. |
| Should exact spatial relations be deterministic? | **Yes.** The 08B engine computes all four relations exactly from coordinates. The task has no ambiguity a neural model is needed for. |
| What should Gemma do? | Language-side work only: map free-form questions to structured queries when templates fail, refer to objects by semantic description ("the thing I sit on"), explain results, and handle open-ended scene descriptions. It must **never be the source of truth** for a geometric relation. |
| Precision note for any Gemma inference | Gemma-2 lateral logits sit near the 30.0 softcap. Any classification read-out must compare logits in fp32 (or use the deterministic engine), not rely on bf16 argmax. |

## 5. Next milestone (08E)
Build and measure a hybrid **orchestrator**:
- **Deterministic layer** (08A/08B, unchanged) for all geometric relations.
- **Query router** that parses the structured state and the question. V4 `egocentric` maps to object-to-agent. V4 `object_to_object` maps to the *reference-direction frame*, which is distinct from 08B-3's displacement semantics.
- **Neural fallback** (Gemma) only for queries the router cannot parse, with output validation.

Evaluate on the untouched V4 test against the original V4, the intervention, and the deterministic engine alone, per task and per class. No claim of hybrid superiority before measurement.
