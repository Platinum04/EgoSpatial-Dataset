# 11-B — Does Gemma 4 *use* its internal left/right signal? (control, readout, causal tests)

**Date:** 2026-11-11 (E4B: 2026-11-12) · **Script:** `g4_causal.py` (this folder) · **Raw outputs:**
* HF: `11_evaluation/11A_gemma4/gemma-4-E2B-it/causal/causal_results.json`
* HF: `11_evaluation/11A_gemma4/gemma-2-2b-it_control/`
* E4B: key fields in `e4b_causal_summary.json` (this folder). The raw file (sha256 `af5305fd3b361744…`) still needs uploading from the Colab runtime.

All numbers are on the identical V4 test set (n = 800). Unless stated, they use the **200 egocentric left/right items**. Probes are standardised logistic regression with 5-fold GroupKFold by object pair. Chance is 0.50.

## 1. Control: base Gemma 2 under the identical protocol

| model | zero-shot ego lateral | best lateral-ego probe | best sagittal-ego probe |
|---|---|---|---|
| gemma-2-2b-it (base) | 0.210 | **0.690** @L20/26 | 0.995 @L15 |
| gemma-4-E2B-it (bf16) | 0.340 | **0.852** @L32/35 | 1.000 @L20 |
| gemma-4-E4B-it (NF4) | 0.180 | **0.983** @L41/42 | 1.000 @L24 |

**Under this protocol** the best-layer lateral score rises with model generation and size (0.69 → 0.85 → 0.98). Zero-shot four-way accuracy stays at or below the 0.25 random-guess level in all three models.

**Two caveats on the best-layer numbers.**
1. A best-layer score is a maximum over layers, so its proper null also searches over layers. The layer-search permutation control in `11A_REPORT.md` (`probe_control.py`, nine-permutation smoke check) put the highest shuffled maximum at 0.608 (E2B) and 0.622 (E4B). Both Gemma 4 models clear that comfortably. For base Gemma 2, a 49-permutation layer-search run (`gemma-2-2b-it_control/probe_control_49.json` on HF) gives an observed maximum of 0.690 against a null mean of 0.553 (null maximum 0.616), p = 0.02, the minimum possible with 49 permutations. So base Gemma 2 carries a real but much weaker lateral signal.
2. 08D-6 used a different protocol: ridge probes on the V4 validation split, covering base and fine-tuned Gemma 2. Absolute scores should only be compared within one protocol.

## 2. Gemma 4 E2B: readout, baseline, alignment, causality

| check | result | reading |
|---|---|---|
| 4-way answer on lateral items | 0.330 (pred: left 99, right 46, behind 41, front 14) | fails |
| **binary readout** (logit right vs left only) | **0.535** | the output head itself does not separate left from right; this is not just "front"/"behind" leakage |
| object-relative lateral, binary | 0.505 | fails |
| probe at L32 | **0.852** | signal present |
| **shuffled-label probe**, fixed layer L32 (5 seeds) | 0.453–0.529 | the probe is not overfitting at that layer; the layer-search null is ≈0.61 (11A) |
| cos(μ_right − μ_left, W_right − W_left), final layer | **+0.027** | the latent direction is almost orthogonal to the unembedding difference |
| cos(μ_right − μ_left, W_right − W_left), L32 | +0.066 | same |
| hook check | max \|Δ\| = 0.0 | the intervention site is correct |

**Steering.** We add α·(μ_right − μ_left) at L32, last token, with 2-fold cross-fit over object groups (held-out items).

| α | −3 | −2 | −1 | −0.5 | 0 | +0.5 | +1 | +2 | +3 |
|---|---|---|---|---|---|---|---|---|---|
| mean logit(right) − logit(left) | −3.08 | −3.04 | −2.87 | −2.75 | −2.56 | −2.33 | −2.06 | −1.37 | −0.52 |
| fraction answering "right" | 0.26 | 0.25 | 0.23 | 0.23 | 0.23 | 0.24 | 0.24 | 0.25 | 0.24 |

**Probe-guided correction.** A probe trained on the other fold reads the latent answer, and the model is steered toward it. The model's weights are unchanged.

| | baseline | probe alone | steer 0.5 | steer 1.0 | steer 2.0 |
|---|---|---|---|---|---|
| binary accuracy | 0.535 | **0.81** | 0.545 | 0.545 | 0.555 |
| 4-way accuracy | 0.33 | — | 0.345 | 0.35 | 0.38 |

## 2b. Gemma 4 E4B (NF4): the same tests

| check | E2B | **E4B** |
|---|---|---|
| 4-way answer on lateral items | 0.330 | 0.185 (pred: front 118, right 42, left 31, behind 9) |
| binary readout (logit right vs left only) | 0.535 | **0.500** |
| object-relative lateral, binary | 0.505 | 0.555 |
| best probe | 0.852 @L32 | **0.983 @L41** |
| shuffled-label probe, fixed best layer | 0.453–0.529 | 0.399–0.544 |
| cos(μ_right − μ_left, W_right − W_left), final layer | +0.027 | **+0.108** |
| cos, best layer | +0.066 | +0.158 |
| hook check | 0.0 | 0.0 |

**Steering in E4B** (α·(μ_right − μ_left) at L41, last token, 2-fold cross-fit over object groups):

| α | −3 | −2 | −1 | −0.5 | 0 | +0.5 | +1 | +2 | +3 |
|---|---|---|---|---|---|---|---|---|---|
| mean logit(right) − logit(left) | −8.13 | −5.47 | −2.83 | −1.51 | −0.20 | +1.11 | +2.43 | +5.10 | **+7.81** |
| fraction answering "right" | 0.17 | 0.20 | 0.21 | 0.21 | 0.21 | 0.23 | 0.25 | 0.33 | **0.51** |
| fraction answering "left" | 0.19 | 0.16 | 0.16 | 0.16 | 0.15 | 0.16 | 0.15 | 0.13 | 0.12 |

**Probe-guided correction in E4B** (the model's weights are unchanged):

| | baseline | probe alone | steer 0.5 | steer 1.0 | steer 2.0 |
|---|---|---|---|---|---|
| binary accuracy | 0.500 | **0.945** | 0.615 | 0.685 | **0.790** |
| 4-way accuracy | 0.185 | — | 0.18 | 0.195 | 0.27 |

## 3. Interpretation
1. **Gemma 4 computes egocentric left/right internally but does not read it out.** The answer is linearly decodable (0.85) from layers that sit just before the output. They are well above both the fixed-layer shuffled baseline and the layer-search null (≈0.61). The model's own left-vs-right logit comparison is still at chance (0.535).
2. **The reason is geometric.** The direction carrying the answer is nearly orthogonal to the output head's right-minus-left direction (cos ≈ 0.03). The information exists but points where the unembedding does not look.
3. **Causal coupling grows with the model.**
   * **E2B:** pushing along the latent direction moves the right-vs-left margin monotonically, but only by about +2.6 logits over α = −3…+3. Probe-guided steering improves binary accuracy only from 0.535 to 0.555.
   * **E4B:** the same intervention moves the margin by about **+15.9 logits**, and probe-guided steering raises binary accuracy from **0.50 to 0.79**. Its latent direction is also better aligned with the unembedding (cos 0.11–0.16, versus 0.03–0.07).
   * So in the larger model the signal is not just decodable. It is causally connected to the output, and injecting it repairs most left/right decisions without any training.
4. **What remains broken.** Four-way accuracy stays low, at most 0.27, because E4B answers "front" for most lateral items. Lateral steering does not remove that prior. Correcting lateral answers inside a free four-way choice would also need the sagittal decision handled, for example by steering or reading out both axes.
5. **Consequence.** In E2B the only working readout is a tiny external probe (0.81). In E4B the probe reads 0.945, and steering with it repairs the model's own binary output (0.79). For a product, reading the latent answer, or computing geometry explicitly, is still more reliable than trusting the generated word.

## 4. Limitations and next steps
* E4B ran in 4-bit NF4. A bf16 run on a larger GPU would remove that caveat.
* The probe used for correction is a supervised readout trained on the other fold of object groups. "No training" refers to the language model's weights only.
* Steering was single-layer, last-token and diff-of-means, with |α| ≤ 3. Still to try:
  * stronger or multi-layer steering;
  * steering at earlier layers or all positions;
  * a direction learned to maximise the output-margin shift.
* Still to run: the full 99-permutation layer-search control for Gemma 4 E2B and E4B. Base Gemma 2 is done (49 permutations, p = 0.02).
* The setting is synthetic: four cardinal directions and a templated scene description.
