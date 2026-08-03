#!/usr/bin/env python3
"""Score a custom matcher against a benchmark JSON file.

Usage:
  PYTHONPATH=src python3 examples/evaluate_your_engine.py benchmark.json
  PYTHONPATH=src python3 examples/evaluate_your_engine.py --offline
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ssb.benchmark import Benchmark, build, format_scorecard, score
from ssb.matching import BaselineMatcher
from ssb.sources import load_fixture


def my_engine(query: str, candidate: str) -> float:
    """Replace this with your screening API's similarity score in [0, 1]."""
    return BaselineMatcher()(query, candidate)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("benchmark", nargs="?", help="path to benchmark.json")
    ap.add_argument("--offline", action="store_true", help="build from synthetic fixture")
    ap.add_argument("--threshold", type=float, default=0.85)
    ap.add_argument("--name", default="my-engine")
    args = ap.parse_args(argv)

    if args.offline or args.benchmark is None:
        bench = build(load_fixture(), limit=None, seed=0, max_per_class=2)
    else:
        bench = Benchmark.from_json(args.benchmark)

    sc = score(bench, my_engine, threshold=args.threshold, matcher_name=args.name)
    print(format_scorecard(sc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
