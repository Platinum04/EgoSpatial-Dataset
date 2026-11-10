# 11-A — Gemma 4 replication of the left/right study

**Date:** 2026-11-10 · **Script:** `11_evaluation/11A_gemma4/g4_study.py` · **Raw outputs:** `11_evaluation/11A_gemma4/<model>/` (results.json, records.json, hidden_last_token.npz)

## Setup
* **Data.** The identical V4 test set (`Platinum04/EgoSpatial-Gemma-data/v4/test.json`) has 800 items: 200 per direction, 400 egocentric and 400 object-to-object. The user turn is extracted from `text` and re-wrapped in each model's own chat template, with thinking off.
* **Zero-shot.** Two readouts:
  * free greedy generation, 12 tokens, where the first direction word counts as the answer;
  * constrained 4-way choice, the argmax over the first-token logits of the four direction words.
* **Probes.** Standardised logistic regression (C=0.1) on the last prompt token at every layer.
  * Cross-validation is 5-fold GroupKFold grouped by (target, reference) object pair, as in 08D-6. The earlier study used ridge probes on V4 validation, so the full protocols differ.
  * Lateral (left vs right) and sagittal (front vs behind) are probed separately. Chance is 0.50.
* **Hardware.** Colab T4.
  * E2B ran in bf16.
  * **E4B ran in 4-bit NF4** to fit memory, so its numbers are for the quantised model.

## Results

| model | zero-shot overall | ego lateral | ego sagittal | o2o lateral | o2o sagittal |
|---|---|---|---|---|---|
| gemma-4-E2B-it (generate) | 0.393 | 0.340 | 0.525 | 0.490 | 0.215 |
| gemma-4-E2B-it (choice) | 0.394 | 0.330 | 0.535 | 0.490 | 0.220 |
| gemma-4-E4B-it NF4 (generate) | 0.365 | **0.180** | 0.540 | 0.215 | 0.525 |
| gemma-4-E4B-it NF4 (choice) | 0.369 | 0.185 | 0.545 | 0.205 | 0.540 |

Linear probe, best layer (GroupKFold by object pair):

| model | lateral ego | lateral o2o | lateral all | sagittal ego | sagittal o2o | sagittal all |
|---|---|---|---|---|---|---|
| gemma-4-E2B-it (35 layers) | **0.852** @L32 | 0.625 @L33 | 0.748 @L34 | 1.000 @L20 | 1.000 @L9 | 0.995 @L21 |
| gemma-4-E4B-it NF4 (42 layers) | **0.983** @L41 | 0.790 @L39 | 0.915 @L40 | 1.000 @L24 | 1.000 @L14 | 0.998 @L24 |

Layer profile for lateral-egocentric:
* **E2B:** 0.46 at the embedding layer, 0.58 at the middle layer, 0.85 at layer 32.
* **E4B:** 0.46 at the embedding layer, 0.55 at the middle layer, 0.98 at layer 41.

Sagittal information is already near ceiling by the middle layers.

## Reading
1. **Zero-shot, Gemma 4 does not answer the task.** On egocentric left/right, E4B scores 0.18. With four allowed directions, a uniformly random four-way answer has expected accuracy of 0.25 on this subset. Recounting the 200 saved predictions shows that E4B answered `front` 115 times on this subset, so the low score cannot be attributed to a left/right swap alone.
2. **The left/right answer is linearly decodable from Gemma 4's late layers** for unseen object pairs: 0.85 (E2B) and 0.98 (E4B) on egocentric items. In the fine-tuned Gemma-2 V4 (08D-6), left/right was not decodable at any layer.
3. **Lateral information appears late**, only in the last ~15% of layers. Sagittal (front/behind) is encoded by the middle layers. This matches the asymmetry we saw behaviourally in Gemma 2.
4. **What this does and does not show.**
   * Decodability does not establish whether the output head uses the signal.
   * The probe target is a non-linear function of (heading, world direction), and the last prompt token is a fixed template token, so a high score shows that later representations predict the label under this split. Template or scene structure may still contribute. The layer-0 score of 0.46 is only a sanity check; it does not test leakage.
   * A matched Gemma 2 control and a layer-search permutation baseline are needed to interpret the cross-model difference.
   * Object-relative ("face the reference") lateral is weaker: 0.63 and 0.79.

## Open items (not yet run)
* **Control:** base `gemma-2-2b-it` through the identical script. It failed once because Gemma 2 is gated and the subprocess had no token; it was then blocked because the Colab GPU quota was exhausted. Until it runs, the Gemma 2 vs Gemma 4 comparison relies on the 08D-6 probes, which used ridge probes on validation and included both base and fine-tuned Gemma 2.
* E4B in bf16 on a larger GPU, to remove the 4-bit caveat.
* **Next experiments.**
  * A causal test (activation patching or steering along the probe direction at the best layer).
  * Fine-tuning Gemma 4 E2B with the V4 recipe, to see whether the readout gap closes.

## Replaying the egocentric lateral probe control

From this directory, with NumPy, scikit-learn and threadpoolctl installed:

```bash
python probe_control.py /path/to/hidden_last_token.npz --permutations 99 > probe_control.json
```

The control shuffles labels within object-pair groups, preserving each group's label counts and keeping the cross-validation folds fixed. It repeats the full layer search on each shuffle and compares the observed maximum with the shuffled maxima. The observed maximum is still a layer-selection statistic, so it should not be reported as independently held-out performance. The control does not test generalization to new templates or establish causal use.

### Archived activation replay

A nine-permutation smoke check (seed 2027) reproduced the best-layer scores on the archived egocentric lateral activations. The highest shuffled score was 60.8% for E2B and 62.2% for E4B NF4. Zero of nine shuffles matched either observed maximum (85.2% and 98.3%, respectively). This gives a Monte Carlo p-value of 0.10 for each model, the minimum possible with nine shuffles. Use the larger run above for a more informative estimate.
