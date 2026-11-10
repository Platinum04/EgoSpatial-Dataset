"""CLI:  python -m egospatial --state scene.json --question "Where is the chair relative to me?"
      python -m egospatial --state scene.json --relations
"""
import argparse
import json
import sys

from .orchestrator import SpatialEngine
from .relations import all_relations
from .state import SpatialState, SpatialStateError


def main(argv=None):
    ap = argparse.ArgumentParser(prog="egospatial")
    ap.add_argument("--state", required=True, help="path to canonical state JSON ('-' for stdin)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--question")
    g.add_argument("--relations", action="store_true")
    a = ap.parse_args(argv)
    raw = sys.stdin.read() if a.state == "-" else open(a.state).read()
    if a.relations:
        try:
            st = SpatialState.from_json(raw)
            print(json.dumps({"status": "ok", "relations": all_relations(st)}, indent=2))
        except SpatialStateError as e:
            print(json.dumps({"status": "error", "error": str(e)})); return 2
    else:
        r = SpatialEngine().ask(raw, a.question)
        print(json.dumps(r, indent=2))
        return 0 if r["status"] == "ok" else 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
