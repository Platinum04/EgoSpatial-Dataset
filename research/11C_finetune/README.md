# 11-C — LoRA fine-tuning Gemma 4 on the V4 task

**Question.** Fine-tuning Gemma-2-2b-it on the V4 data (LoRA "V4") fixed front/behind but left lateral answers at chance: left 6%, right 95.5%, and no linear left/right signal in any layer (08D-6). 11-A and 11-B showed that Gemma 4 *already* encodes egocentric left/right internally:
* E2B probe 0.85; E4B probe 0.98;
* steering along that direction repairs E4B's binary left/right from 0.50 to 0.79.

So does the *same* fine-tuning recipe succeed on Gemma 4?

**Pre-registered hypothesis.** Because the information is present and only the readout is missing, a small LoRA should reach high accuracy on **all four directions**, including left and right, on the untouched test set. Two outcomes would falsify it:
* lateral accuracy stays near chance while front/behind is solved, which would repeat the Gemma-2 failure;
* lateral accuracy improves only on the training templates, which would show up as a large gap between validation and test.

**Setup** (`g4_finetune.py`)

| Item | Value |
|---|---|
| Model | `google/gemma-4-E2B-it`, 4-bit NF4 QLoRA (fits a free Colab T4) |
| LoRA placement | Language-model attention and MLP projections only (vision and audio towers excluded); r = 16, α = 32, dropout 0.05 |
| Training data | V4 train, 4,000 items, 1 epoch. Loss on the answer tokens only. |
| Optimiser | Batch 4 × accumulation 2; AdamW, lr 2e-4, 20-step warm-up, linear decay; seed 0 |
| Evaluation | V4 validation (800) and the **untouched V4 test (800)**, the same set every prior study used |

Evaluation uses the same first-token four-way readout as 11-A and 11-B. It also reports the binary left-vs-right readout and per-direction accuracy.

**Run:** the `# 11-C` cell in `EgoSpatial_Gemma_Prototype.ipynb`, or `python g4_finetune.py google/gemma-4-E2B-it OUT_DIR`.

## Results (run 2026-11-12, Colab T4, 3,281 s)

**The same LoRA recipe that left Gemma-2 at left 6% / right 95.5% solves the task on Gemma 4 E2B: 99.88% on the untouched V4 test, with left and right both at 100%.**

| Model + V4 LoRA (untouched V4 test, n = 800) | Overall | Front | Behind | Left | Right |
|---|---:|---:|---:|---:|---:|
| Gemma-2-2b-it (08D) | 75.38% | 100% | 100% | 6.0% | 95.5% |
| **Gemma 4 E2B (11-C)** | **99.88%** | 100% | 99.5% | **100%** | **100%** |

* Egocentric 99.75% (one *behind* item answered *left*); object-to-object 100%. Binary left/right readout 1.00 for both task types.
* Validation (800): 100% on every direction. Validation and test agree, so there is no validation/test gap.
* Training loss fell to ≈0 by step 225 of 500. 24.2 M trainable LoRA parameters.

**Reading.** The pre-registered prediction holds on this test set. Gemma-2 lacked a linear lateral signal and LoRA could not create a usable one. Gemma 4 already had one (probe 0.85), and a small adapter made the output read it.

**Caveat (important).** The V4 test reuses the training question *templates*. So 99.88% shows the lateral relation is learned for these templates, not that it generalises to new wording; the pre-registered template-overfitting check therefore remains open. Next: evaluate this adapter on the 240 freshly worded questions used for the hybrid engine (87.5%).

**Files.** `finetune_summary.json` (values transcribed from the run; SHA-256 of the raw `finetune_results.json` recorded inside). The raw JSON and the LoRA adapter (`adapter_model.safetensors`, 96.7 MB) are in the Colab runtime and go to HF `Platinum04/EgoSpatial-Gemma-v2/11_evaluation/11C_finetune/gemma-4-E2B-it_qlora/` once an `HF_TOKEN` secret exists in the running Colab account.

**Implementation note.** `peft.prepare_model_for_kbit_training` is not used: it upcasts Gemma 4's large embedding tables to fp32 and runs out of memory on a T4 (first attempt: OOM, 8.75 GiB).
