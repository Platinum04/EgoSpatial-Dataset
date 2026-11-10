# Reproducibility guide

## Deterministic engine (CPU, no GPU or network needed)
```bash
pip install .                          # Python >= 3.9, no dependencies
python -m unittest discover -s tests   # 23 tests
python tools/make_vectors.py           # regenerate tests/vectors.json (seed 2026)
node ports/js/conformance.test.js      # JS port: expect 3204 passed, 0 failed
python benchmarks/bench.py             # latency / memory
```

## Neural experiments (GPU; reference hardware was a Colab Tesla T4)
| Step | Artifact (model repo `Platinum04/EgoSpatial-Gemma-v2`) | Script in the same folder |
|---|---|---|
| 08D-5 original vs intervention on the untouched test | `08_spatial_state_builder/08D/test_eval/08d5_v1/` | `08d5v2_eval.py`, `08d5v2b_continue.py` |
| 08D-6A inference / token / tie verification | `08D/08D-6/6A/` | `08d6a_verify.py` |
| 08D-6B/6C hidden states and probes | `08D/08D-6/6BC/` (includes `hidden_states/*.npz`) | `08d6bc_probes.py` |
| 08D-7 decision report | `08D/08D-7/08D-7_REPORT.md` | — |
| 08E hybrid orchestrator evaluation | `08_spatial_state_builder/08E/` | `08e_hybrid_orchestrator.py` |
| 11 parser evaluation on fresh phrasings | `11_evaluation/` | `11_parser_eval.py` |

The scripts are the exact cell sources that produced each result. They expect a Colab-style session:
- `google/gemma-2-2b-it` loaded in bf16, with PEFT adapters attached as `original_v4` and `intervention`.
- V4 data from `hf://datasets/Platinum04/EgoSpatial-Gemma-data`.
- The `torchao` package uninstalled (the installed version is incompatible with PEFT).

## Known sources of run-to-run variation
- **GPU numerics.** Lateral logits for the original V4 adapter are near-ties in bf16, so different GPUs can flip a few lateral predictions. On the T4, 08C-10's 10/193 left/right counts reproduced as 12/191, with overall accuracy unchanged at 603/800.
- **Seeds.** Probe CV, bootstrap: 42. Paraphrase stress: 7. Fresh phrasings: 2027. Vectors: 2026.

## Software (08D-5 session)
Recorded in `08d5_reproducibility.json`: Python, torch, transformers and peft versions, plus the GPU name.
