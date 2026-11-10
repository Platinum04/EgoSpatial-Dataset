"""Hybrid orchestrator: deterministic geometry + optional neural semantic parsing.

Responsibilities (08D-7 decision):
  * Deterministic layer (relations.py) is the ONLY source of geometric answers.
  * A neural semantic parser (e.g. Gemma) may translate free-form questions into a
    structured Query. Its output is validated against the scene before use.
  * If a question cannot be resolved, the engine returns status="unresolved" with a
    clarification message. It never guesses a direction.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Iterable, Optional, Union

from . import relations
from .query import Query, template_parse
from .state import SpatialState, SpatialStateError

# A semantic parser maps (question, object names) -> Query | None
SemanticParser = Callable[[str, Iterable[str]], Optional[Query]]


class SpatialEngine:
    def __init__(self, semantic_parser: Optional[SemanticParser] = None,
                 object_relation: str = "reference_frame"):
        self.semantic_parser = semantic_parser
        self.object_relation = object_relation

    # ---- structured API ---------------------------------------------
    def evaluate(self, state: SpatialState, query: Query) -> Dict[str, Any]:
        if query.target not in state.ids:
            raise SpatialStateError(f"unknown target: {query.target}")
        if query.reference != "agent" and query.reference not in state.ids:
            raise SpatialStateError(f"unknown reference: {query.reference}")
        if query.op == "object_to_agent":
            return relations.object_to_agent(state, query.target)
        if query.op == "object_to_object":
            return relations.object_to_object(state, query.reference, query.target)
        if query.op == "reference_frame":
            return relations.reference_frame(state, query.reference, query.target)
        if query.op == "distance":
            return relations.distance(state, query.target, query.reference)
        raise SpatialStateError(f"unsupported op {query.op}")

    # ---- natural-language API ---------------------------------------
    def ask(self, state: Union[SpatialState, Dict[str, Any], str], question: str) -> Dict[str, Any]:
        t0 = time.perf_counter()
        out: Dict[str, Any] = {"question": question}
        try:
            if isinstance(state, str):
                state = SpatialState.from_json(state)
            elif isinstance(state, dict):
                state = SpatialState.from_dict(state)
            out["source"] = state.source
            names = state.ids
            query, path = template_parse(question, names, self.object_relation), "deterministic(template)"
            if query is None and self.semantic_parser is not None:
                query, path = self.semantic_parser(question, names), "deterministic(neural-parse)"
                if query is not None and (query.target not in names or
                                          (query.reference != "agent" and query.reference not in names) or
                                          query.target == query.reference):
                    query = None  # reject unverifiable parser output
            if query is None:
                out.update(status="unresolved", path="unresolved",
                           message="Could not identify the target/reference among the scene objects. "
                                   "Please rephrase or name the objects explicitly.",
                           objects=names)
            else:
                res = self.evaluate(state, query)
                out.update(status="ok", path=path, query=query.to_dict(), result=res,
                           answer=res.get("direction", res.get("distance_m")))
        except SpatialStateError as e:
            out.update(status="error", path="validation", error=str(e))
        out["latency_ms"] = round((time.perf_counter() - t0) * 1e3, 4)
        return out
