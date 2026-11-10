# 11-A — Gemma 4 replication of the EgoSpatial left/right study.
# usage: python g4_study.py MODEL_ID OUT_DIR [--4bit]
# 1) zero-shot accuracy on the identical V4 test set (800 items, 200 per direction)
#    - free generation (thinking off) and constrained 4-way choice from next-token logits
# 2) layer-wise linear probes on the last prompt token, GroupKFold by (target, reference) pair,
#    separately for lateral (left vs right) and sagittal (front vs behind) — same protocol as 08D-6.
import sys, json, re, time, os, numpy as np, torch
from collections import Counter, defaultdict
from huggingface_hub import hf_hub_download
from transformers import AutoTokenizer, AutoProcessor
import transformers

MODEL_ID, OUT = sys.argv[1], sys.argv[2]
FOUR_BIT = "--4bit" in sys.argv
os.makedirs(OUT, exist_ok=True)
T = json.load(open(hf_hub_download("Platinum04/EgoSpatial-Gemma-data", "v4/test.json", repo_type="dataset")))
assert len(T) == 800

def user_turn(text):
    m = re.search(r"<start_of_turn>user\s*(.*?)<end_of_turn>", text, re.S)
    return m.group(1).strip()

t0 = time.time()
try:
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
except Exception:
    tok = AutoProcessor.from_pretrained(MODEL_ID).tokenizer
tok.padding_side = "left"
kw = dict(dtype=torch.bfloat16, device_map="cuda:0")
if FOUR_BIT:
    from transformers import BitsAndBytesConfig
    kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_quant_type="nf4")
model = None
for cls in ["AutoModelForCausalLM", "AutoModelForImageTextToText", "AutoModelForMultimodalLM"]:
    try:
        model = getattr(transformers, cls).from_pretrained(MODEL_ID, **kw); print("loaded with", cls); break
    except Exception as e:
        print(cls, "failed:", str(e)[:200])
assert model is not None
model.eval()
print(f"load {time.time()-t0:.0f}s  transformers {transformers.__version__}  gpu mem {torch.cuda.memory_allocated()/2**30:.1f} GiB")

def prompt(ex):
    msgs = [{"role": "user", "content": user_turn(ex["text"])}]
    try:
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    except TypeError:
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

P = [prompt(ex) for ex in T]
print("PROMPT SAMPLE >>>", P[0][-260:].replace("\n", "\\n"))
DIRS = ["front", "behind", "left", "right"]
# candidate first tokens for each direction (with/without leading space, capitalised)
cand = {}
for d in DIRS:
    ids = set()
    for v in [d, " " + d, d.capitalize(), " " + d.capitalize()]:
        e = tok(v, add_special_tokens=False).input_ids
        if e: ids.add(e[0])
    cand[d] = sorted(ids)
print("candidate token ids", cand)

gen, choice, H = [], [], []
B = 8
with torch.no_grad():
    for i in range(0, len(P), B):
        enc = tok(P[i:i+B], return_tensors="pt", padding=True, add_special_tokens=False).to("cuda:0")
        out = model(**enc, output_hidden_states=True)
        logits = out.logits[:, -1].float()
        for row in logits:
            sc = {d: max(row[j].item() for j in cand[d]) for d in DIRS}
            choice.append(max(sc, key=sc.get))
        hs = out.hidden_states  # tuple(layers+1) of [b, seq, h]
        H.append(torch.stack([h[:, -1].float() for h in hs], 1).cpu().numpy().astype(np.float16))
        g = model.generate(**enc, max_new_tokens=12, do_sample=False)
        for row in g[:, enc.input_ids.shape[1]:]:
            gen.append(tok.decode(row, skip_special_tokens=True))
        if i % 160 == 0: print(f"{i}/{len(P)}  {time.time()-t0:.0f}s  e.g. {gen[-1]!r}")
H = np.concatenate(H)  # [800, L+1, h]

def parse(s):
    m = re.search(r"\b(front|behind|left|right)\b", s.lower())
    return m.group(1) if m else "none"
pred = [parse(s) for s in gen]
gold = [ex["answer"] for ex in T]
tt = [ex["task_type"] for ex in T]

def acc(p, mask=None):
    idx = [i for i in range(len(gold)) if mask is None or mask(i)]
    return round(sum(p[i] == gold[i] for i in idx) / len(idx), 4), len(idx)

R = {"model": MODEL_ID, "four_bit": FOUR_BIT, "transformers": transformers.__version__, "n": len(T)}
for name, p in [("generate", pred), ("choice", choice)]:
    r = {"overall": acc(p)}
    for t in ["egocentric", "object_to_object"]:
        r[t] = acc(p, lambda i, t=t: tt[i] == t)
        for d in DIRS:
            r[f"{t}/{d}"] = acc(p, lambda i, t=t, d=d: tt[i] == t and gold[i] == d)
        r[f"{t}/lateral"] = acc(p, lambda i, t=t: tt[i] == t and gold[i] in ("left", "right"))
        r[f"{t}/sagittal"] = acc(p, lambda i, t=t: tt[i] == t and gold[i] in ("front", "behind"))
    r["pred_dist"] = dict(Counter(p))
    conf = defaultdict(Counter)
    for g_, p_ in zip(gold, p): conf[g_][p_] += 1
    r["confusion"] = {g_: dict(c) for g_, c in conf.items()}
    R[name] = r

# ---- probes (same protocol as 08D-6: GroupKFold by object pair, standardised logistic regression)
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
groups = np.array([f'{ex["target_object"]}|{ex["reference_object"]}' for ex in T])
probe = {}
for axis, labs in [("lateral", ("left", "right")), ("sagittal", ("front", "behind"))]:
    for t in ["egocentric", "object_to_object", "all"]:
        idx = np.array([i for i in range(len(T)) if gold[i] in labs and (t == "all" or tt[i] == t)])
        y = np.array([labs.index(gold[i]) for i in idx]); g = groups[idx]
        k = min(5, len(set(g)))
        accs = []
        for L in range(H.shape[1]):
            X = H[idx, L].astype(np.float32)
            s = []
            for tr, te in GroupKFold(n_splits=k).split(X, y, g):
                clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=0.1))
                clf.fit(X[tr], y[tr]); s.append(clf.score(X[te], y[te]))
            accs.append(round(float(np.mean(s)), 4))
        probe[f"{axis}/{t}"] = {"best_layer": int(np.argmax(accs)), "best": max(accs), "per_layer": accs, "n": len(idx)}
R["probe"] = probe
R["seconds"] = round(time.time() - t0)
json.dump(R, open(f"{OUT}/results.json", "w"), indent=1)
json.dump([{"id": ex["id"], "gold": g_, "gen": s, "pred": p_, "choice": c} for ex, g_, s, p_, c in zip(T, gold, gen, pred, choice)],
          open(f"{OUT}/records.json", "w"))
np.savez_compressed(f"{OUT}/hidden_last_token.npz", H=H, gold=np.array(gold), task=np.array(tt), groups=groups)

print("\n==== SUMMARY", MODEL_ID, "====")
for name in ["generate", "choice"]:
    r = R[name]
    print(f"{name:9s} overall {r['overall'][0]:.3f} | ego {r['egocentric'][0]:.3f} (lat {r['egocentric/lateral'][0]:.3f}, sag {r['egocentric/sagittal'][0]:.3f})"
          f" | o2o {r['object_to_object'][0]:.3f} (lat {r['object_to_object/lateral'][0]:.3f}, sag {r['object_to_object/sagittal'][0]:.3f}) | dist {r['pred_dist']}")
for k, v in probe.items():
    print(f"probe {k:28s} best {v['best']:.3f} @L{v['best_layer']}/{H.shape[1]-1}  (n={v['n']})")
print("seconds", R["seconds"])
