# Sanctions Screening Benchmark Web UI

A Flask-based browser dashboard is included at `webapp/` for the Sanctions Screening Benchmark. It requires [Flask](https://flask.palletsprojects.com/) (standard library otherwise).

## Installation and Running

```bash
# Install Flask if not already present
pip install flask

# Start the server (runs on http://localhost:5050)
PYTHONPATH=src python3 webapp/app.py
```

Open **http://localhost:5050** in your browser. The dashboard has five pages:

| Page | Description |
|---|---|
| **Dashboard** | Run the offline demo or evaluate `benchmark.json`; shows recall/precision scorecard with class-wise breakdown and visual recall bars |
| **Classes** | Browse all 18 perturbation classes grouped by family (Benign / Adversarial / Degraded) with descriptions |
| **Perturb** | Enter any name and instantly see every variant the benchmark engine generates across all perturbation classes |
| **Matcher** | Score a single query name against a candidate name using both the Baseline Jaro-Winkler and Exact matchers |
| **🔎 Batch Screener** *(new)* | Paste up to 100 names (one per line) and screen them all against the offline fixture candidate pool in one click — each name is shown as 🚨 HIT or ✅ CLEAR with its similarity score and the best-matching sanctioned entity |

## Batch Screener

The **Batch Screener** is a feature that makes it easy to test a real customer name list without writing any code:

1. Navigate to the **🔎 Batch Screener** tab.
2. Paste names into the textarea (one name per line, max 100).
3. Adjust the similarity **threshold** (default 0.85) and choose a **matcher**.
4. Click **▶ Screen All Names**.

Results appear immediately with:
- **Summary cards** — total hits, total clears, and hit-rate percentage.
- **Results table** — one row per name, with HIT/CLEAR badge, similarity score bar, and the canonical name of the matched sanctioned entity (when fired).

The screening runs entirely offline against the bundled fixture; no network calls are made and no data leaves your machine.
