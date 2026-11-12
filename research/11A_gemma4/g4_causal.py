# 11-B — Is Gemma 4's latent left/right signal real, and is it causal?
# usage: python g4_causal.py MODEL_ID OUT_DIR [--4bit]
#
# Checks, all on the identical V4 test set (egocentric lateral items unless stated):
#  1. Binary readout: does the model's own output prefer the right word when forced to choose ONLY
#     between "left" and "right"?  (4-way failures could just be the model saying "front".)
#  2. Shuffled-label probe baseline (5 seeds) at the best layer: rules out probe overfitting.
#  3. Unembedding alignment: cosine between the final-layer left/right direction and
#     W_U[right] - W_U[left].  Negative => the model encodes the answer but its output head reads it inverted.
#  4. Causal steering (2-fold cross-fit over object groups): add a * (mu_right - mu_left) at the best
#     layer's last token, measure the shift in logit(right) - logit(left) on held-out items.
#  5. Probe-guided correction: read the latent answer with a probe fit on the other fold, steer toward it,
#     and measure the model's OWN output accuracy before/after.  (The probe is a tiny supervised readout;
#     the language model's weights are never changed.)
import sys, json, re, time, os, numpy as np, torch
from huggingface_hub import hf_hub_download
import transformers
from transformers import AutoTokenizer, AutoProcessor
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

MODEL_ID, OUT = sys.argv[1], sys.argv[2]
FOUR_BIT = "--4bit" in sys.argv
os.makedirs(OUT, exist_ok=True)
t0 = time.time()
T = json.load(open(hf_hub_download("Platinum04/EgoSpatial-Gemma-data", "v4/test.json", repo_type="dataset")))
assert len(T) == 800

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
        print(cls, "failed:", str(e)[:160])
assert model is not None
model.eval()

def user_turn(text):
    return re.search(r"<start_of_turn>user\s*(.*?)<end_of_turn>", text, re.S).group(1).strip()
def prompt(ex):
    m = [{"role": "user", "content": user_turn(ex["text"])}]
    try:
        return tok.apply_chat_template(m, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    except TypeError:
        return tok.apply_chat_template(m, tokenize=False, add_generation_prompt=True)
P = [prompt(ex) for ex in T]
DIRS = ["front", "behind", "left", "right"]
cand = {}
for d in DIRS:
    ids = set()
    for v in [d, " " + d, d.capitalize(), " " + d.capitalize()]:
        e = tok(v, add_special_tokens=False).input_ids
        if e: ids.add(e[0])
    cand[d] = sorted(ids)
gold = np.array([ex["answer"] for ex in T]); tt = np.array([ex["task_type"] for ex in T])
groups = np.array([f'{ex["target_object"]}|{ex["reference_object"]}' for ex in T])

def enc(idx):
    return tok([P[i] for i in idx], return_tensors="pt", padding=True, add_special_tokens=False).to("cuda:0")
def scores(logits):  # [b, V] -> [b, 4] max over token variants
    return torch.stack([logits[:, cand[d]].max(-1).values for d in DIRS], -1).float().cpu().numpy()

# ---- decoder layer list matching hidden_states indexing (hidden_states[k] = output of layers[k-1])
with torch.no_grad():
    nhs = len(model(**enc([0]), output_hidden_states=True).hidden_states)
layers = None
for name, m in model.named_modules():
    if isinstance(m, torch.nn.ModuleList) and len(m) == nhs - 1 and name.endswith("layers"):
        layers, lname = m, name
assert layers is not None, "decoder layers not found"
print("decoder layers:", lname, len(layers))

state = {"vec": None, "cap": None}
def hook(mod, inp, out):
    hs = out[0] if isinstance(out, tuple) else out
    if state["cap"] is not None: state["cap"].append(hs[:, -1].float().cpu())
    if state["vec"] is None: return out
    hs = hs.clone(); hs[:, -1, :] += state["vec"].to(hs.dtype).to(hs.device)
    return (hs,) + tuple(out[1:]) if isinstance(out, tuple) else hs

# ---- pass 1: 4-way scores + last-token hidden states at all layers
S, H = [], []
B = 8
with torch.no_grad():
    for i in range(0, 800, B):
        o = model(**enc(range(i, min(i + B, 800))), output_hidden_states=True)
        S.append(scores(o.logits[:, -1]))
        H.append(torch.stack([h[:, -1].float() for h in o.hidden_states], 1).cpu().numpy().astype(np.float32))
S = np.concatenate(S); H = np.concatenate(H)
print(f"pass 1 done {time.time()-t0:.0f}s, H {H.shape}")
R = {"model": MODEL_ID, "four_bit": FOUR_BIT, "transformers": transformers.__version__}

ego_lat = np.where((tt == "egocentric") & np.isin(gold, ["left", "right"]))[0]
o2o_lat = np.where((tt == "object_to_object") & np.isin(gold, ["left", "right"]))[0]
def binacc(idx, sc):
    return round(float(np.mean(np.where(sc[idx, 3] > sc[idx, 2], "right", "left") == gold[idx])), 4)
four = np.array(DIRS)[S.argmax(1)]
R["readout"] = {
    "ego_lateral_4way": round(float(np.mean(four[ego_lat] == gold[ego_lat])), 4),
    "ego_lateral_binary_left_vs_right": binacc(ego_lat, S),
    "o2o_lateral_4way": round(float(np.mean(four[o2o_lat] == gold[o2o_lat])), 4),
    "o2o_lateral_binary_left_vs_right": binacc(o2o_lat, S),
    "ego_lateral_4way_pred_dist": {d: int(np.sum(four[ego_lat] == d)) for d in DIRS},
}
print("readout", R["readout"])

# ---- probes (ego lateral) per layer + shuffled baseline at best layer
y = (gold[ego_lat] == "right").astype(int); g = groups[ego_lat]
def probe_acc(X, yy, gg):
    s = []
    for tr, te in GroupKFold(n_splits=min(5, len(set(gg)))).split(X, yy, gg):
        c = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=0.1)).fit(X[tr], yy[tr]); s.append(c.score(X[te], yy[te]))
    return float(np.mean(s))
per_layer = [round(probe_acc(H[ego_lat, L], y, g), 4) for L in range(H.shape[1])]
Lb = max(1, int(np.argmax(per_layer)))
rng = np.random.default_rng(0)
shuf = [round(probe_acc(H[ego_lat, Lb], rng.permutation(y), g), 4) for _ in range(5)]
R["probe"] = {"per_layer": per_layer, "best_layer": Lb, "best": per_layer[Lb], "shuffled_at_best": shuf}
print("probe best", per_layer[Lb], "@L", Lb, "shuffled", shuf)

# ---- unembedding alignment
W = model.get_output_embeddings().weight
def urow(d): return W[cand[d]].float().mean(0).detach().cpu().numpy()
dU = urow("right") - urow("left")
cos = []
for L in range(H.shape[1]):
    dm = H[ego_lat][y == 1, L].mean(0) - H[ego_lat][y == 0, L].mean(0)
    cos.append(round(float(dm @ dU / (np.linalg.norm(dm) * np.linalg.norm(dU) + 1e-9)), 4))
R["unembed_cos_per_layer"] = cos
print("cos(mu_R-mu_L, W_R-W_L) final", cos[-1], "best-layer", cos[Lb])

# ---- sanity: hook at layers[Lb-1] captures hidden_states[Lb]
hk = layers[Lb - 1].register_forward_hook(hook)
state["cap"] = []
with torch.no_grad(): model(**enc(ego_lat[:8]))
cap = torch.cat(state["cap"]).numpy(); state["cap"] = None
R["hook_check_maxabs"] = float(np.abs(cap - H[ego_lat[:8], Lb]).max())
print("hook check max|diff|", R["hook_check_maxabs"])

# ---- 2-fold cross-fit over object groups: steering sweep + probe-guided correction
ug = sorted(set(g)); half = set(ug[::2])
foldA = np.array([gi in half for gi in g])
alphas = [-3, -2, -1, -0.5, 0, 0.5, 1, 2, 3]
sweep = {a: [] for a in alphas}; fix = {s: [] for s in [0.5, 1.0, 2.0]}; base_bin, base_4, probe_hits = [], [], []
def run(idx, vecs):
    out = []
    with torch.no_grad():
        for i in range(0, len(idx), B):
            state["vec"] = None if vecs is None else torch.tensor(vecs[i:i + B])[:, :]  # [b, h]
            out.append(scores(model(**enc(idx[i:i + B])).logits[:, -1]))
    state["vec"] = None
    return np.concatenate(out)
for fit_mask in [foldA, ~foldA]:
    fi, ei = ego_lat[fit_mask], ego_lat[~fit_mask]
    yf = y[fit_mask]
    mu = H[fi][yf == 1, Lb].mean(0) - H[fi][yf == 0, Lb].mean(0)
    for a in alphas:
        sc = run(ei, np.tile(a * mu, (len(ei), 1)).astype(np.float32))
        sweep[a].append(np.c_[sc[:, 3] - sc[:, 2], sc.argmax(1)])
    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=0.1)).fit(H[fi, Lb], yf)
    lat = clf.predict(H[ei, Lb]); probe_hits += list(lat == y[~fit_mask])
    sign = np.where(lat == 1, 1.0, -1.0)[:, None]
    for s in fix:
        sc = run(ei, (s * sign * mu[None, :]).astype(np.float32))
        fix[s].append(np.c_[(np.where(sc[:, 3] > sc[:, 2], 1, 0) == y[~fit_mask]), np.array(DIRS)[sc.argmax(1)] == gold[ei]])
    base_bin += list(np.where(S[ei, 3] > S[ei, 2], 1, 0) == y[~fit_mask]); base_4 += list(four[ei] == gold[ei])
hk.remove()
R["steering"] = {str(a): {"mean_logit_R_minus_L": round(float(np.concatenate(v)[:, 0].mean()), 3),
                          "frac_says_right_4way": round(float(np.mean(np.concatenate(v)[:, 1] == 3)), 4),
                          "frac_says_left_4way": round(float(np.mean(np.concatenate(v)[:, 1] == 2)), 4)} for a, v in sweep.items()}
R["correction"] = {"baseline_binary": round(float(np.mean(base_bin)), 4), "baseline_4way": round(float(np.mean(base_4)), 4),
                   "probe_readout_acc": round(float(np.mean(probe_hits)), 4),
                   **{f"steer_{s}": {"binary": round(float(np.concatenate(v)[:, 0].mean()), 4), "4way": round(float(np.concatenate(v)[:, 1].mean()), 4)} for s, v in fix.items()}}
R["seconds"] = round(time.time() - t0)
json.dump(R, open(f"{OUT}/causal_results.json", "w"), indent=1)
print("\n==== 11-B SUMMARY", MODEL_ID, "4bit" if FOUR_BIT else "bf16", "====")
print("readout   ", R["readout"])
print(f"probe     best {R['probe']['best']:.3f} @L{Lb}/{H.shape[1]-1}   shuffled {shuf}")
print(f"unembed   cos final {cos[-1]:+.3f}   cos @best {cos[Lb]:+.3f}   hook check {R['hook_check_maxabs']:.2e}")
for a, v in R["steering"].items(): print(f"steer a={a:>5}  dlogit(R-L) {v['mean_logit_R_minus_L']:+7.3f}  says right {v['frac_says_right_4way']:.2f}  says left {v['frac_says_left_4way']:.2f}")
print("correction", R["correction"])
print("seconds", R["seconds"])
