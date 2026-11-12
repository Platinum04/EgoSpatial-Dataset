# 11-C — Does LoRA fine-tuning fix left/right in Gemma 4, where it failed in Gemma 2?
# usage: python g4_finetune.py MODEL_ID OUT_DIR [--epochs 1] [--bf16]   (default: 4-bit NF4 QLoRA, fits a T4)
#
# Hypothesis (from 11-A/11-B): Gemma 4 already encodes egocentric left/right linearly (probe 0.85-0.98) but its
# output head does not read it out. A small LoRA on the same V4 training data should therefore reach high lateral
# accuracy — unlike Gemma-2 + V4 LoRA (left 6% / right 95.5%). Same data, same untouched test set as every prior study.
import sys, os, re, json, time, random, argparse, numpy as np, torch
from collections import Counter, defaultdict
from huggingface_hub import hf_hub_download
import transformers
from transformers import AutoTokenizer, AutoProcessor

ap = argparse.ArgumentParser()
ap.add_argument("model"); ap.add_argument("out")
ap.add_argument("--epochs", type=int, default=1); ap.add_argument("--bf16", action="store_true")
ap.add_argument("--lr", type=float, default=2e-4); ap.add_argument("--rank", type=int, default=16)
ap.add_argument("--bs", type=int, default=4); ap.add_argument("--accum", type=int, default=2); ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)
random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
t0 = time.time()

def load(split):
    return json.load(open(hf_hub_download("Platinum04/EgoSpatial-Gemma-data", f"v4/{split}.json", repo_type="dataset")))
TRAIN, VAL, TEST = load("train"), load("validation"), load("test")
assert (len(TRAIN), len(VAL), len(TEST)) == (4000, 800, 800)

try:
    tok = AutoTokenizer.from_pretrained(args.model)
except Exception:
    tok = AutoProcessor.from_pretrained(args.model).tokenizer
if tok.pad_token is None: tok.pad_token = tok.eos_token

kw = dict(dtype=torch.bfloat16, device_map="cuda:0")
if not args.bf16:
    from transformers import BitsAndBytesConfig
    kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_quant_type="nf4")
model = None
for cls in ["AutoModelForCausalLM", "AutoModelForImageTextToText"]:
    try:
        model = getattr(transformers, cls).from_pretrained(args.model, **kw); print("loaded with", cls); break
    except Exception as e:
        print(cls, "failed:", str(e)[:160])
assert model is not None

def user_turn(text):
    return re.search(r"<start_of_turn>user\s*(.*?)<end_of_turn>", text, re.S).group(1).strip()
def prompt(ex):
    m = [{"role": "user", "content": user_turn(ex["text"])}]
    try:
        return tok.apply_chat_template(m, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    except TypeError:
        return tok.apply_chat_template(m, tokenize=False, add_generation_prompt=True)
def full(ex):
    p = prompt(ex)
    m = [{"role": "user", "content": user_turn(ex["text"])}, {"role": "assistant", "content": ex["answer"]}]
    try:
        f = tok.apply_chat_template(m, tokenize=False, enable_thinking=False)
    except TypeError:
        f = tok.apply_chat_template(m, tokenize=False)
    if not f.startswith(p):  # template renders the assistant turn differently: fall back to prompt + answer + eos
        f = p + ex["answer"] + (tok.eos_token or "")
    return p, f
p0, f0 = full(TRAIN[0]); print("TRAIN SAMPLE target >>>", repr(f0[len(p0):]))

def encode(ex):
    p, f = full(ex)
    pi = tok(p, add_special_tokens=False).input_ids; fi = tok(f, add_special_tokens=False).input_ids
    return fi, [-100] * len(pi) + fi[len(pi):]
ENC = [encode(ex) for ex in TRAIN]
print("answer tokens per example:", Counter(sum(1 for l in lab if l != -100) for _, lab in ENC).most_common(3))

# ---- LoRA on the language model only (never the vision/audio towers)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
if not args.bf16:
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
else:
    model.gradient_checkpointing_enable()
target = r"^(?!.*(vision|audio)).*layers\.\d+\.(self_attn\.(q|k|v|o)_proj|mlp\.(gate|up|down)_proj)$"
model = get_peft_model(model, LoraConfig(r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.05, target_modules=target, task_type="CAUSAL_LM"))
trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"trainable params {trainable:,}  load+setup {time.time()-t0:.0f}s")

def forward_logits(ids, att):
    try:
        return model(input_ids=ids, attention_mask=att).logits
    except Exception as e:
        if "token_type_ids" not in str(e): raise
        return model(input_ids=ids, attention_mask=att, token_type_ids=torch.zeros_like(ids)).logits

def batch(items):
    L = max(len(i) for i, _ in items)
    ids = torch.full((len(items), L), tok.pad_token_id); lab = torch.full((len(items), L), -100); att = torch.zeros((len(items), L), dtype=torch.long)
    for k, (i, l) in enumerate(items):
        ids[k, :len(i)] = torch.tensor(i); lab[k, :len(l)] = torch.tensor(l); att[k, :len(i)] = 1
    return ids.cuda(), lab.cuda(), att.cuda()

opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr, weight_decay=0.0)
steps_total = args.epochs * len(ENC) // (args.bs * args.accum)
sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / 20) * max(0.0, 1 - s / max(1, steps_total)))
log = []; step = 0; model.train()
for ep in range(args.epochs):
    order = list(range(len(ENC))); random.shuffle(order)
    for b0 in range(0, len(order), args.bs):
        ids, lab, att = batch([ENC[j] for j in order[b0:b0 + args.bs]])
        logits = forward_logits(ids, att)[:, :-1].float()
        loss = torch.nn.functional.cross_entropy(logits.reshape(-1, logits.size(-1)), lab[:, 1:].reshape(-1), ignore_index=-100) / args.accum
        loss.backward()
        if (b0 // args.bs + 1) % args.accum == 0:
            torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
            opt.step(); sched.step(); opt.zero_grad(); step += 1
            if step % 25 == 0:
                log.append({"step": step, "loss": round(loss.item() * args.accum, 4), "s": round(time.time() - t0)})
                print(f"step {step}/{steps_total} loss {loss.item()*args.accum:.4f} {time.time()-t0:.0f}s", flush=True)
model.eval()

# ---- evaluation: identical readouts to 11-A/11-B (first-token logits over the 4 direction words)
tok.padding_side = "left"
DIRS = ["front", "behind", "left", "right"]
cand = {d: sorted({tok(v, add_special_tokens=False).input_ids[0] for v in [d, " " + d, d.capitalize(), " " + d.capitalize()]}) for d in DIRS}
def evaluate(DATA, name):
    P = [prompt(ex) for ex in DATA]; S = []
    with torch.no_grad():
        for i in range(0, len(P), 8):
            enc = tok(P[i:i + 8], return_tensors="pt", padding=True, add_special_tokens=False).to("cuda:0")
            lg = forward_logits(enc.input_ids, enc.attention_mask)[:, -1].float()
            S.append(torch.stack([lg[:, cand[d]].max(-1).values for d in DIRS], -1).cpu().numpy())
    S = np.concatenate(S); gold = np.array([ex["answer"] for ex in DATA]); tt = np.array([ex["task_type"] for ex in DATA])
    pred = np.array(DIRS)[S.argmax(1)]
    def acc(m): return round(float(np.mean(pred[m] == gold[m])), 4)
    r = {"overall": acc(np.ones(len(DATA), bool))}
    for t in ["egocentric", "object_to_object"]:
        r[t] = acc(tt == t)
        for d in DIRS: r[f"{t}/{d}"] = acc((tt == t) & (gold == d))
        lat = (tt == t) & np.isin(gold, ["left", "right"])
        r[f"{t}/lateral_binary"] = round(float(np.mean(np.where(S[lat, 3] > S[lat, 2], "right", "left") == gold[lat])), 4)
    conf = defaultdict(Counter)
    for g, p in zip(gold, pred): conf[g][p] += 1
    r["confusion"] = {g: dict(c) for g, c in conf.items()}
    print(f"{name}: overall {r['overall']:.3f} | ego L {r['egocentric/left']:.3f} R {r['egocentric/right']:.3f} F {r['egocentric/front']:.3f} B {r['egocentric/behind']:.3f} | o2o {r['object_to_object']:.3f}")
    return r
R = {"model": args.model, "four_bit": not args.bf16, "transformers": transformers.__version__, "args": vars(args),
     "trainable_params": trainable, "train_log": log, "validation": evaluate(VAL, "validation"), "test": evaluate(TEST, "TEST (untouched)")}
R["seconds"] = round(time.time() - t0)
json.dump(R, open(f"{args.out}/finetune_results.json", "w"), indent=1)
model.save_pretrained(f"{args.out}/adapter")
print("saved", os.listdir(args.out), "seconds", R["seconds"])
