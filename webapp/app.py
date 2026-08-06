"""
Flask web application for the Sanctions Screening Benchmark.
Provides a beautiful dashboard UI for running benchmarks and viewing results.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, render_template, request

# Make ssb importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ssb import benchmark as bm
from ssb import matching, perturb, sources

app = Flask(__name__)

# ---------------------------------------------------------------------------
# In-memory job store (single-process dev server is fine here)
# ---------------------------------------------------------------------------
_jobs: dict = {}
_jobs_lock = threading.Lock()


def _new_job(job_id: str, kind: str):
    with _jobs_lock:
        _jobs[job_id] = {
            "id": job_id,
            "kind": kind,
            "status": "running",
            "progress": 0,
            "message": "Starting…",
            "result": None,
            "error": None,
            "started_at": time.time(),
        }


def _update_job(job_id: str, **kw):
    with _jobs_lock:
        _jobs[job_id].update(kw)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/classes")
def api_classes():
    fams = perturb.families()
    result = {}
    for family in (perturb.BENIGN, perturb.ADVERSARIAL, perturb.DEGRADED):
        result[family] = [
            {"name": name, "description": perturb.REGISTRY[name].description}
            for name in sorted(fams[family])
        ]
    return jsonify(result)


@app.route("/api/demo", methods=["POST"])
def api_demo():
    """Run demo benchmark (offline fixture) in a background thread."""
    import uuid

    job_id = str(uuid.uuid4())
    threshold = float(request.json.get("threshold", 0.85))
    _new_job(job_id, "demo")

    def run():
        try:
            _update_job(job_id, message="Loading fixture data…", progress=10)
            snapshot = sources.load_fixture()
            _update_job(job_id, message="Building benchmark cases…", progress=25)
            bench = bm.build(snapshot, limit=None, seed=0, max_per_class=2)
            scorecards = []
            matchers = [matching.ExactMatcher(), matching.BaselineMatcher()]
            for i, matcher in enumerate(matchers):
                pct = 40 + i * 30
                _update_job(
                    job_id,
                    message=f"Scoring with {matcher.name}…",
                    progress=pct,
                )
                sc = bm.score(bench, matcher, threshold=threshold)
                scorecards.append(sc.to_dict())
            _update_job(
                job_id,
                status="done",
                progress=100,
                message="Complete",
                result=scorecards,
            )
        except Exception as exc:
            _update_job(job_id, status="error", error=str(exc), progress=0)

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/evaluate", methods=["POST"])
def api_evaluate():
    """Evaluate the bundled benchmark.json."""
    import uuid

    job_id = str(uuid.uuid4())
    threshold = float(request.json.get("threshold", 0.85))
    matcher_name = request.json.get("matcher", "baseline")
    _new_job(job_id, "evaluate")

    bench_path = ROOT / "benchmark.json"
    if not bench_path.exists():
        return jsonify({"error": "benchmark.json not found"}), 400

    def run():
        try:
            _update_job(job_id, message="Loading benchmark.json…", progress=10)
            bench = bm.Benchmark.from_json(bench_path)
            matcher = (
                matching.BaselineMatcher()
                if matcher_name == "baseline"
                else matching.ExactMatcher()
            )
            _update_job(
                job_id,
                message=f"Scoring {bench.manifest.case_count} cases…",
                progress=20,
            )
            sc = bm.score(bench, matcher, threshold=threshold)
            _update_job(
                job_id,
                status="done",
                progress=100,
                message="Complete",
                result=[sc.to_dict()],
            )
        except Exception as exc:
            _update_job(job_id, status="error", error=str(exc), progress=0)

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/match", methods=["POST"])
def api_match():
    """Score a single query vs candidate pair."""
    data = request.json or {}
    query = data.get("query", "")
    candidate = data.get("candidate", "")
    if not query or not candidate:
        return jsonify({"error": "query and candidate required"}), 400

    exact = matching.ExactMatcher()(query, candidate)
    baseline = matching.BaselineMatcher()(query, candidate)
    normalised_q = matching.normalise(query)
    normalised_c = matching.normalise(candidate)

    return jsonify(
        {
            "query": query,
            "candidate": candidate,
            "normalised_query": normalised_q,
            "normalised_candidate": normalised_c,
            "exact_score": round(exact, 4),
            "baseline_score": round(baseline, 4),
        }
    )


@app.route("/api/perturb", methods=["POST"])
def api_perturb():
    """Generate perturbation variants for a name."""
    data = request.json or {}
    name = data.get("name", "")
    if not name:
        return jsonify({"error": "name required"}), 400

    variants = perturb.apply_all(name, entity_id="demo", seed=0, max_per_class=3)
    by_class: dict = {}
    for v in variants:
        by_class.setdefault(v.perturbation, []).append(
            {"text": v.text, "family": v.family}
        )

    return jsonify({"name": name, "variants": by_class})


@app.route("/api/batch-screen", methods=["POST"])
def api_batch_screen():
    """Screen a list of names against the fixture candidate pool.

    New feature: Batch Screener — paste multiple names, get back a row
    per name showing whether it would fire against the offline fixture,
    the best-matching entity, and the similarity score.
    """
    data = request.json or {}
    names_raw = data.get("names", "")
    threshold = float(data.get("threshold", 0.85))
    matcher_name = data.get("matcher", "baseline")

    names = [n.strip() for n in names_raw.splitlines() if n.strip()]
    if not names:
        return jsonify({"error": "no names provided"}), 400
    if len(names) > 100:
        return jsonify({"error": "maximum 100 names per batch"}), 400

    # Load the fixture candidate pool (offline, no network)
    snapshot = sources.load_fixture()
    pool = snapshot.individuals()
    pool = [e for e in pool if len(e.primary_name.split()) >= 2]
    candidates = {e.entity_id: {"names": e.all_names(), "primary": e.primary_name} for e in pool}

    matcher = (
        matching.BaselineMatcher() if matcher_name == "baseline" else matching.ExactMatcher()
    )

    results = []
    for query in names:
        best_id, best_score, best_name = None, 0.0, None
        for eid, info in candidates.items():
            for cand in info["names"]:
                s = matcher(query, cand)
                if s > best_score:
                    best_id, best_score, best_name = eid, s, info["primary"]
        fired = best_score >= threshold
        results.append({
            "query": query,
            "hit": fired,
            "score": round(best_score, 4),
            "matched_entity": best_name if fired else None,
            "entity_id": best_id if fired else None,
        })

    hits = sum(1 for r in results if r["hit"])
    return jsonify({
        "results": results,
        "total": len(results),
        "hits": hits,
        "misses": len(results) - hits,
        "threshold": threshold,
        "matcher": matcher_name,
    })


@app.route("/api/jobs/<job_id>")
def api_job_status(job_id):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    app.run(debug=False, port=5050)
