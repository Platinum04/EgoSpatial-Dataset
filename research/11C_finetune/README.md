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

**Results:** `finetune_results.json` and the LoRA adapter go to HF `Platinum04/EgoSpatial-Gemma-v2/11_evaluation/11C_finetune/`. A summary will be added here.
