"""Test suite. Runs entirely offline against the synthetic fixture."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ssb import benchmark as bm
from ssb import matching, negatives, perturb, sources


class TestPerturbations(unittest.TestCase):
    def test_registry_populated(self):
        self.assertGreaterEqual(len(perturb.REGISTRY), 15)

    def test_every_class_has_a_family(self):
        for name, p in perturb.REGISTRY.items():
            self.assertIn(p.family, (perturb.BENIGN, perturb.ADVERSARIAL, perturb.DEGRADED), name)

    def test_deterministic(self):
        a = perturb.apply_all("Muhammad Yusuf Karimov", "1", seed=7)
        b = perturb.apply_all("Muhammad Yusuf Karimov", "1", seed=7)
        self.assertEqual([v.text for v in a], [v.text for v in b])

    def test_never_returns_the_input_unchanged(self):
        src = "Aleksandr Ivanovich Volkov"
        for v in perturb.apply_all(src, "1", seed=3):
            self.assertNotEqual(v.text.casefold(), src.casefold(), v.perturbation)

    def test_homoglyph_is_visually_identical_but_different_bytes(self):
        out = perturb.p_homoglyph("Osama Jaber", 0)
        self.assertTrue(out)
        for v in out:
            self.assertNotEqual(v, "Osama Jaber")
            self.assertEqual(len(v), len("Osama Jaber"))

    def test_translit_finds_known_cluster(self):
        out = perturb.p_translit("Muhammad Karimov", 0)
        self.assertTrue(any("ohamm" in v.lower() or "ohame" in v.lower() for v in out), out)

    def test_diacritics_strip(self):
        self.assertEqual(perturb.p_diacritics_strip("José Müller", 0), ["Jose Muller"])

    def test_name_order_reverses(self):
        out = perturb.p_name_order("Wei Ming Zhang", 0)
        self.assertIn("Zhang Ming Wei", out)

    def test_conditional_classes_return_empty_gracefully(self):
        for name in perturb.REGISTRY:
            perturb.REGISTRY[name].fn("Li", 0)

    def test_invisible_char_preserves_rendering(self):
        out = perturb.p_invisible_char("Hussein Nasser", 0)
        self.assertTrue(out)
        stripped = "".join(c for c in out[0] if c not in "​‌‍ ⁠")
        self.assertEqual(stripped, "Hussein Nasser")


class TestMatching(unittest.TestCase):
    def test_jaro_winkler_identity(self):
        self.assertAlmostEqual(matching.jaro_winkler("martha", "martha"), 1.0)

    def test_jaro_winkler_known_value(self):
        # Classic reference pair; JW is approximately 0.961
        self.assertAlmostEqual(matching.jaro_winkler("martha", "marhta"), 0.9611, places=3)

    def test_jaro_winkler_disjoint(self):
        self.assertEqual(matching.jaro_winkler("abc", "xyz"), 0.0)

    def test_normalise_folds_diacritics_and_case(self):
        self.assertEqual(matching.normalise("JOSÉ  Müller-Sanchez"), "jose muller sanchez")

    def test_stopwords_dropped(self):
        self.assertNotIn("dr", matching.tokens("Dr. Ahmad Khalid"))

    def test_baseline_scores_exact_at_one(self):
        m = matching.BaselineMatcher()
        self.assertAlmostEqual(m("Ahmad Khalid", "Ahmad Khalid"), 1.0)

    def test_baseline_handles_diacritics(self):
        b, e = matching.BaselineMatcher(), matching.ExactMatcher()
        self.assertGreater(b("Jose Muller", "José Müller"), 0.9)
        self.assertEqual(e("Jose Muller", "José Müller"), 1.0)  # normalisation handles it

    def test_exact_fails_on_homoglyph(self):
        e = matching.ExactMatcher()
        homo = perturb.p_homoglyph("Osama Jaber", 0)[-1]
        self.assertEqual(e(homo, "Osama Jaber"), 0.0)


class TestNegatives(unittest.TestCase):
    def setUp(self):
        self.names = [
            "Muhammad Yusuf Karimov",
            "Ahmad Khalid Farrani",
            "Aleksandr Ivanovich Volkov",
            "Jose Eduardo Sanchez",
        ]

    def test_generates_something(self):
        self.assertTrue(negatives.generate(self.names, seed=1))

    def test_never_collides_with_a_listed_name(self):
        idx = {n.casefold() for n in self.names}
        for n in negatives.generate(self.names, seed=1, listed_index=idx):
            self.assertNotIn(n.text.casefold(), idx)

    def test_classes_present(self):
        classes = {n.negative_class for n in negatives.generate(self.names, seed=1)}
        self.assertIn(negatives.CROSS_PAIR, classes)


class TestSourcesAndBenchmark(unittest.TestCase):
    def setUp(self):
        self.snap = sources.load_fixture()

    def test_fixture_parses(self):
        self.assertEqual(len(self.snap.entities), 12)

    def test_individuals_filter(self):
        self.assertEqual(len(self.snap.individuals()), 10)

    def test_aliases_attached(self):
        by_id = {e.entity_id: e for e in self.snap.entities}
        self.assertIn("KARIMOV, Mohammed Yousef", by_id["9001"].aliases)

    def test_build_produces_positives_and_negatives(self):
        b = bm.build(self.snap, limit=None, seed=0, max_per_class=2)
        self.assertGreater(b.manifest.positive_count, 50)
        self.assertGreater(b.manifest.negative_count, 0)
        self.assertEqual(b.manifest.case_count, len(b.cases))

    def test_roundtrip_json(self):
        import os
        import tempfile

        b = bm.build(self.snap, limit=None, seed=0, max_per_class=1)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "b.json")
            b.to_json(p)
            b2 = bm.Benchmark.from_json(p)
        self.assertEqual(b.manifest.case_count, b2.manifest.case_count)

    def test_scoring_runs_and_is_ordered(self):
        b = bm.build(self.snap, limit=None, seed=0, max_per_class=1)
        exact = bm.score(b, matching.ExactMatcher(), threshold=0.85)
        base = bm.score(b, matching.BaselineMatcher(), threshold=0.85)
        # A fuzzy matcher must recover strictly more than normalised exact match.
        self.assertGreater(base.overall_recall, exact.overall_recall)

    def test_exact_matcher_is_blind_to_adversarial_classes(self):
        b = bm.build(self.snap, limit=None, seed=0, max_per_class=2)
        sc = bm.score(b, matching.ExactMatcher(), threshold=0.85)
        adversarial = [c for c in sc.by_class if c.family == perturb.ADVERSARIAL]
        self.assertTrue(adversarial)
        self.assertLess(sum(c.recall for c in adversarial) / len(adversarial), 0.5)

    def test_scorecard_renders(self):
        b = bm.build(self.snap, limit=None, seed=0, max_per_class=1)
        text = bm.format_scorecard(bm.score(b, matching.BaselineMatcher()))
        self.assertIn("SCORECARD", text)
        self.assertIn("RECALL", text)


class TestCompare(unittest.TestCase):
    def setUp(self):
        self.snap = sources.load_fixture()
        self.bench = bm.build(self.snap, limit=None, seed=0, max_per_class=1)

    def test_compare_shows_delta(self):
        exact = bm.score(self.bench, matching.ExactMatcher(), threshold=0.85)
        base = bm.score(self.bench, matching.BaselineMatcher(), threshold=0.85)
        text = bm.format_comparison(exact, base)
        self.assertIn("COMPARISON", text)
        self.assertIn("DELTA", text)
        self.assertGreater(base.overall_recall, exact.overall_recall)

    def test_scorecard_roundtrip_via_from_json(self):
        import os
        import tempfile

        sc = bm.score(self.bench, matching.BaselineMatcher(), threshold=0.85)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "sc.json")
            Path(p).write_text(json.dumps(sc.to_dict(), ensure_ascii=False), encoding="utf-8")
            loaded = bm.Scorecard.from_json(p)
        self.assertEqual(loaded.matcher, sc.matcher)
        self.assertEqual(len(loaded.by_class), len(sc.by_class))

    def test_compare_rows_align_by_class(self):
        exact = bm.score(self.bench, matching.ExactMatcher(), threshold=0.85)
        base = bm.score(self.bench, matching.BaselineMatcher(), threshold=0.85)
        rows = bm.compare(exact, base)
        self.assertTrue(rows)
        for row in rows:
            self.assertGreater(row.n, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
