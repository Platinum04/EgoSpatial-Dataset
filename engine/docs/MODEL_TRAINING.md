# Model training documentation

| Model | Base | Where | Training data | Status |
|---|---|---|---|---|
| V2 / V3 adapters | google/gemma-2-2b-it | `v2_clean_run/`, `v3_verified_run/` (+ checkpoints) | v2 / v3 | Historical |
| **V4 adapter** | google/gemma-2-2b-it | `v4_final_run/` (`adapter_config.json`, `adapter_model.safetensors`) | v4 train (4,000) | Authoritative behavioural baseline. Hyperparameters are recorded in the adapter config and the 08D-4A training-metadata artifacts. |
| **08D intervention** | google/gemma-2-2b-it | `08_spatial_state_builder/08D/intervention/v1/adapter` | 08D-1 targeted lateral set (6,000) | LoRA r=16, α=32, dropout 0.05, targets q/k/v/o/gate/up/down, lr 1e-4, 750 steps, effective batch 8. Metadata in `08d3_training_metadata.json`. |

## Inference contract (used for every number in this release)
1. Take the user turn from `example["text"]` (the part before `<start_of_turn>model`).
2. Apply `tokenizer.apply_chat_template(..., add_generation_prompt=True)`.
3. Tokenize with the default call. This yields **2 BOS tokens**, matching 08C-10.
4. Decode greedily with `max_new_tokens=4`, then exact-match the stripped, lowercased output.
5. Use bf16 weights (LoRA weights stay fp32).

Answer tokens are the bare `front`=10573, `behind`=53020, `left`=1672, `right`=1331.

## Precision caveat (08D-6A)
Gemma-2 applies a final-logit softcap of 30. For lateral questions, both the `left` and `right` logits sit at about 29.75, where bf16 resolution is 0.125. In 379 of 400 cases they become exact ties, and greedy decoding picks `right` because it has the lower token id. Any classification read-out should compare logits in fp32. The 08D-4 validation run used fp16, so its numbers are not directly comparable with the bf16 runs.

## Why there is no further fine-tuning (08D-7)
Probes trained on V4 validation found no linearly decodable left/right signal at any layer of either adapter, while front/behind was perfectly decodable. The 08D intervention, which supplied 4,000 extra lateral examples, changed the tie-break behaviour but not the representation. Exact geometry is therefore handled by the deterministic engine, and Gemma is used only as an optional question parser (base model, no adapter).
