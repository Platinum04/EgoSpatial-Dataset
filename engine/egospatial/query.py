"""Structured queries and the deterministic template parser."""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Iterable, Optional

OPS = ("object_to_agent", "object_to_object", "reference_frame", "distance")


@dataclass(frozen=True)
class Query:
    op: str
    target: str
    reference: str = "agent"

    def __post_init__(self):
        if self.op not in OPS:
            raise ValueError(f"unknown op {self.op!r}; expected one of {OPS}")

    def to_dict(self):
        return asdict(self)


_REL = r"(?:relative to|from|with respect to|compared to|in relation to)"
_OBJ = r"[a-z0-9][a-z0-9 _-]*?"
_PATTERNS = [
    # "... the X (is) relative to / from / with respect to (me | the Y)"
    re.compile(rf"\bthe ({_OBJ}) (?:is )?{_REL} (me|myself|the ({_OBJ}))\s*[\.\?!]?\s*$", re.I),
    re.compile(rf"^(?:where|which direction|what direction).*?\bthe ({_OBJ}) (?:is )?{_REL} (me|myself|the ({_OBJ}))\b", re.I),
]
_DIST = re.compile(rf"\bhow far (?:away )?is the ({_OBJ})(?: from (me|myself|the ({_OBJ})))?\s*[\.\?!]?\s*$", re.I)


def _resolve(text: Optional[str], names: Iterable[str]) -> Optional[str]:
    if text is None:
        return None
    t = text.strip().lower()
    for n in sorted(names, key=len, reverse=True):
        nl = n.lower()
        if t == nl or t.endswith(" " + nl):
            return n
    return None


def template_parse(question: str, names: Iterable[str], object_relation: str = "reference_frame") -> Optional[Query]:
    """Parse common English templates into a Query, resolving names against the scene.

    `object_relation` selects the semantics for "X relative to Y":
      - "reference_frame" (V4 dataset convention: face Y, where is X)
      - "object_to_object" (08B-3: displacement Y->X in the agent's frame)
    Returns None if the question is not recognised or names do not resolve.
    """
    names = list(names)
    q = question.strip()
    m = _DIST.search(q)
    if m:
        t = _resolve(m.group(1), names)
        r = "agent" if (m.group(2) is None or m.group(2).lower() in ("me", "myself")) else _resolve(m.group(3), names)
        return Query("distance", t, r) if t and r else None
    for p in _PATTERNS:
        m = p.search(q)
        if not m:
            continue
        t = _resolve(m.group(1), names)
        if m.group(2).lower() in ("me", "myself"):
            return Query("object_to_agent", t) if t else None
        r = _resolve(m.group(3), names)
        if t and r:
            return Query(object_relation, t, r)
        return None
    return None
