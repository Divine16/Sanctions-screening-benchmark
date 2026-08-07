"""Command line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import benchmark as bm
from . import matching, perturb, sources


def cmd_classes(args) -> int:
    fams = perturb.families()
    for family in (perturb.BENIGN, perturb.ADVERSARIAL, perturb.DEGRADED):
        print(f"\n{family.upper()}")
        print("-" * 72)
        for name in sorted(fams[family]):
            p = perturb.REGISTRY[name]
            print(f"  {name:<20} {p.description}")
    print()
    return 0


def cmd_generate(args) -> int:
    if args.offline:
        snapshot = sources.load_fixture()
        print(f"[offline] using synthetic fixture: {snapshot.endpoint}", file=sys.stderr)
    else:
        print(f"fetching {args.source} ...", file=sys.stderr)
        snapshot = sources.fetch(args.source)
        print(f"retrieved {len(snapshot.entities)} entities from {snapshot.endpoint}", file=sys.stderr)

    only = args.only.split(",") if args.only else None
    bench = bm.build(
        snapshot,
        limit=args.limit,
        seed=args.seed,
        only=only,
        max_per_class=args.max_per_class,
        individuals_only=not args.all_types,
        negatives_per_class=args.negatives_per_class,
    )
    bench.to_json(args.out)
    m = bench.manifest
    print(
        f"wrote {args.out}: {m.case_count} cases "
        f"({m.positive_count} positive, {m.negative_count} negative) "
        f"over {m.entity_count} entities",
        file=sys.stderr,
    )
    return 0


def cmd_evaluate(args) -> int:
    bench = bm.Benchmark.from_json(args.benchmark)
    matcher = {"baseline": matching.BaselineMatcher(), "exact": matching.ExactMatcher()}[args.matcher]
    sc = bm.score(bench, matcher, threshold=args.threshold)
    if args.json:
        print(json.dumps(sc.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(bm.format_scorecard(sc))
    if args.save:
        Path(args.save).write_text(json.dumps(sc.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"scorecard written to {args.save}", file=sys.stderr)
    return 0


def cmd_compare(args) -> int:
    """Compare two matchers on a benchmark, or two saved scorecard files."""
    matchers = {"baseline": matching.BaselineMatcher(), "exact": matching.ExactMatcher()}

    if args.scorecard_a and args.scorecard_b:
        sc_a = bm.Scorecard.from_json(args.scorecard_a)
        sc_b = bm.Scorecard.from_json(args.scorecard_b)
    elif args.benchmark:
        bench = bm.Benchmark.from_json(args.benchmark)
        sc_a = bm.score(bench, matchers[args.a], threshold=args.threshold, matcher_name=args.a)
        sc_b = bm.score(bench, matchers[args.b], threshold=args.threshold, matcher_name=args.b)
    else:
        print("provide a benchmark path or both --scorecard-a and --scorecard-b", file=sys.stderr)
        return 2

    report = bm.format_comparison(sc_a, sc_b)
    if args.json:
        rows = bm.compare(sc_a, sc_b)
        print(
            json.dumps(
                {
                    "a": sc_a.to_dict(),
                    "b": sc_b.to_dict(),
                    "comparison": [
                        {
                            "perturbation": r.perturbation,
                            "family": r.family,
                            "n": r.n,
                            "recall_a": round(r.recall_a, 4),
                            "recall_b": round(r.recall_b, 4),
                            "delta": round(r.delta, 4),
                        }
                        for r in rows
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(report)
    return 0


def cmd_sweep(args) -> int:
    bench = bm.Benchmark.from_json(args.benchmark)
    matcher = {"baseline": matching.BaselineMatcher(), "exact": matching.ExactMatcher()}[args.matcher]
    try:
        thresholds = bm.parse_thresholds(args.thresholds, args.from_threshold, args.to_threshold, args.step)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    result = bm.sweep(bench, matcher, thresholds=thresholds)
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(bm.format_sweep(result))
    if args.save:
        Path(args.save).write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"sweep written to {args.save}", file=sys.stderr)
    return 0


def cmd_demo(args) -> int:
    """Generate from the fixture and evaluate. No network needed."""
    snapshot = sources.load_fixture()
    bench = bm.build(snapshot, limit=None, seed=args.seed, max_per_class=2)
    for matcher in (matching.ExactMatcher(), matching.BaselineMatcher()):
        sc = bm.score(bench, matcher, threshold=args.threshold)
        print(bm.format_scorecard(sc))
        print()
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="ssb",
        description="Reproducible benchmark for sanctions name-screening effectiveness.",
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("classes", help="list the perturbation classes")
    p.set_defaults(func=cmd_classes)

    p = sub.add_parser("generate", help="build a benchmark from a live sanctions list")
    p.add_argument("--source", default="ofac_sdn", choices=sorted(sources.ENDPOINTS))
    p.add_argument("--offline", action="store_true", help="use the bundled synthetic fixture")
    p.add_argument("--limit", type=int, default=250, help="entities to include (default 250)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--only", default=None, help="comma-separated perturbation classes")
    p.add_argument("--max-per-class", type=int, default=2)
    p.add_argument("--negatives-per-class", type=int, default=1)
    p.add_argument("--all-types", action="store_true", help="include vessels/entities, not just individuals")
    p.add_argument("--out", default="benchmark.json")
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("evaluate", help="score a matcher against a benchmark")
    p.add_argument("benchmark")
    p.add_argument("--matcher", default="baseline", choices=["baseline", "exact"])
    p.add_argument("--threshold", type=float, default=0.85)
    p.add_argument("--json", action="store_true")
    p.add_argument("--save", default=None)
    p.set_defaults(func=cmd_evaluate)

    p = sub.add_parser(
        "compare",
        help="compare two matchers on a benchmark, or two saved scorecard files",
    )
    p.add_argument("benchmark", nargs="?", help="benchmark JSON (compare --a vs --b matchers)")
    p.add_argument("--a", default="exact", choices=["baseline", "exact"], help="matcher A (default: exact)")
    p.add_argument("--b", default="baseline", choices=["baseline", "exact"], help="matcher B (default: baseline)")
    p.add_argument("--scorecard-a", default=None, help="first saved scorecard JSON")
    p.add_argument("--scorecard-b", default=None, help="second saved scorecard JSON")
    p.add_argument("--threshold", type=float, default=0.85)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("sweep", help="score a matcher across a range of thresholds")
    p.add_argument("benchmark")
    p.add_argument("--matcher", default="baseline", choices=["baseline", "exact"])
    p.add_argument("--thresholds", default=None, help="comma-separated thresholds, e.g. 0.7,0.8,0.9")
    p.add_argument("--from-threshold", type=float, default=0.50, dest="from_threshold")
    p.add_argument("--to-threshold", type=float, default=0.95, dest="to_threshold")
    p.add_argument("--step", type=float, default=0.05)
    p.add_argument("--json", action="store_true")
    p.add_argument("--save", default=None)
    p.set_defaults(func=cmd_sweep)

    p = sub.add_parser("demo", help="generate and evaluate against the offline fixture")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--threshold", type=float, default=0.85)
    p.set_defaults(func=cmd_demo)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
