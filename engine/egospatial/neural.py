"""Optional neural semantic parser backed by Gemma-2-2b-it (requires torch + transformers).

The parser only translates a free-form question into a structured Query. The geometric
answer is always computed by the deterministic engine. Measured in 08E (paraphrase stress).
"""
from __future__ import annotations

import json
import re
from typing import Iterable, Optional

from .query import Query

# v2 prompt (milestone 11): 87.5% vs 73.8% for v1 on 240 fresh, previously unseen phrasings.
PROMPT = ("Objects in the scene: {objects}\n"
          "Question: {question}\n"
          "Identify the TARGET object being located, and the REFERENCE frame:\n"
          "- REFERENCE is \"me\" when the question asks where the target is relative to the speaker's own current facing.\n"
          "- REFERENCE is an object X when the question uses X as the direction to face or compare against "
          "(e.g. 'relative to X', 'if I face X', 'looking toward X', 'with X straight ahead').\n"
          'Reply with only JSON like {{"target": "lamp", "reference": "desk"}}')

_ME = {"me", "myself", "agent", "i", "speaker"}


def parse_json_reply(raw: str, names: Iterable[str], object_relation: str = "reference_frame") -> Optional[Query]:
    names = {n.lower(): n for n in names}
    m = re.search(r"\{[^{}]*\}", raw)
    if not m:
        return None
    try:
        j = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    t = names.get(str(j.get("target", "")).strip().lower())
    r_raw = str(j.get("reference", "")).strip().lower()
    if t is None:
        return None
    if r_raw in _ME:
        return Query("object_to_agent", t)
    r = names.get(r_raw)
    if r is None or r == t:
        return None
    return Query(object_relation, t, r)


class GemmaSemanticParser:
    """Callable (question, names) -> Query | None. Loads google/gemma-2-2b-it lazily."""

    def __init__(self, model_id: str = "google/gemma-2-2b-it", model=None, tokenizer=None,
                 device: Optional[str] = None, object_relation: str = "reference_frame", max_new_tokens: int = 32):
        self.model_id, self.model, self.tokenizer = model_id, model, tokenizer
        self.device, self.object_relation, self.max_new_tokens = device, object_relation, max_new_tokens

    def _load(self):
        if self.model is None:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id, dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None)
            self.model.eval()

    def __call__(self, question: str, names: Iterable[str]) -> Optional[Query]:
        import torch
        self._load()
        names = list(names)
        text = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": PROMPT.format(objects=", ".join(sorted(names)), question=question)}],
            tokenize=False, add_generation_prompt=True)
        enc = self.tokenizer(text, return_tensors="pt", add_special_tokens=False).to(self.model.device)
        with torch.no_grad():
            out = self.model.generate(**enc, max_new_tokens=self.max_new_tokens, do_sample=False,
                                      pad_token_id=self.tokenizer.eos_token_id)
        raw = self.tokenizer.decode(out[0, enc["input_ids"].shape[1]:], skip_special_tokens=True)
        return parse_json_reply(raw, names, self.object_relation)
