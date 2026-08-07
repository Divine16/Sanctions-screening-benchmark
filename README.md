# sanctions-screening-benchmark

A reproducible, open benchmark for measuring how well a name-screening engine
recovers sanctioned parties from *varied* name strings, and how well it
discriminates against structurally similar strings that are not sanctioned.

Screening engines are usually assessed by asking whether they are deployed and
configured. That question is nearly uninformative. This project asks a different
one: **against which specific classes of name variation does this engine fail?**

```
  PERTURBATION          FAMILY             N   HITS   RECALL
  ----------------------------------------------------------
  invisible_char        adversarial       10      4   40.0%  <-- blind spot
  homoglyph             adversarial       20     10   50.0%
  double_collapse       adversarial       17     17  100.0%
  token_drop            benign            12      0    0.0%  <-- blind spot
  translit              benign            16     16  100.0%
  name_order            benign            20     20  100.0%
```

The headline recall figure is not the point. The class-wise profile is: it says
*which* failure you have, which tells you who owns the fix. A miss on an
adversarial class is an evasion exposure. A miss on a benign class is a data
quality problem producing false negatives against ordinary customers.

---

## Why this exists

Public sanctions enforcement records repeatedly describe institutions that had a
screening program, had documented policies, and still failed, because a control
that exists is not a control that works. There is no open, shared way to measure
whether a given screening configuration actually catches the variation it will
encounter. Vendors publish accuracy claims against undisclosed test sets.
Institutions test against their own historical alerts, which are by construction
the cases their current configuration already catches.

This benchmark is an attempt at a common, inspectable, reproducible alternative.

## Design commitments

**No list data is redistributed.** The benchmark fetches the current sanctions
list from the publishing authority at generation time. A generated benchmark
records the retrieval timestamp and endpoint in its manifest, so a result is
always attributable to a specific published list state. See
[docs/LICENSING.md](docs/LICENSING.md).

**Fully deterministic.** Every perturbation is a pure function of
`(input, seed)`. Two people running the same command against the same list state
get byte-identical benchmarks.

**Zero dependencies.** Pure Python 3.9+ standard library, including the
Jaro-Winkler implementation. It runs on a clean interpreter with no install step,
which matters because screening people work on locked-down machines.

**Negative controls are mandatory.** A benchmark that measures only recall is
trivially gamed by an engine that matches everything. Precision is measured
against generated near-miss strings, with an explicit statement of what that
number does and does not mean.

**Honest about its limits.** See [Limitations](#limitations). The precision
figure is not a production alert-volume estimate and is never presented as one.

## Install and run

No installation required.

```bash
git clone https://github.com/Divine16/sanctions-screening-benchmark
cd sanctions-screening-benchmark

# See every perturbation class and what it models
PYTHONPATH=src python3 -m ssb.cli classes

# Run end-to-end against the bundled synthetic fixture, no network needed
PYTHONPATH=src python3 -m ssb.cli demo

# Build a benchmark from the live OFAC SDN list
PYTHONPATH=src python3 -m ssb.cli generate --limit 500 --out benchmark.json

# Score the reference matcher against it
PYTHONPATH=src python3 -m ssb.cli evaluate benchmark.json --threshold 0.85

# Compare two matchers side-by-side on the same benchmark
PYTHONPATH=src python3 -m ssb.cli compare benchmark.json --a exact --b baseline

# Or compare two saved scorecards
PYTHONPATH=src python3 -m ssb.cli evaluate benchmark.json --save scorecard-a.json --matcher exact
PYTHONPATH=src python3 -m ssb.cli evaluate benchmark.json --save scorecard-b.json --matcher baseline
PYTHONPATH=src python3 -m ssb.cli compare --scorecard-a scorecard-a.json --scorecard-b scorecard-b.json

# Sweep thresholds to find a recall/precision trade-off
PYTHONPATH=src python3 -m ssb.cli sweep benchmark.json --matcher baseline
PYTHONPATH=src python3 -m ssb.cli sweep benchmark.json --thresholds 0.7,0.8,0.85,0.9,0.95
```

Run the tests:

```bash
python3 -m unittest discover -s tests -t .
```

See [CHANGELOG.md](CHANGELOG.md) for release history.

## Scoring your own engine

Any callable of the shape `(query: str, candidate: str) -> float` in `[0, 1]`
can be scored. See [examples/evaluate_your_engine.py](examples/evaluate_your_engine.py).

```python
from ssb.benchmark import Benchmark, score, format_scorecard

def my_engine(query: str, candidate: str) -> float:
    return your_screening_api.similarity(query, candidate)

bench = Benchmark.from_json("benchmark.json")
print(format_scorecard(score(bench, my_engine, threshold=0.85, matcher_name="acme-v4")))
```

Nothing leaves your machine. The benchmark is a local JSON file and the harness
makes no network calls during scoring.

## The perturbation classes

Eighteen classes across three families. Full rationale and sourcing in
[docs/METHODOLOGY.md](docs/METHODOLOGY.md).

### Benign, innocent variation

| Class | Models |
|---|---|
| `translit` | Competing romanisations (Muhammad / Mohammed / Mohamad) |
| `diacritics_strip` | Diacritics lost in transit (José to Jose) |
| `diacritics_expand` | German-style expansion (Müller to Mueller) |
| `name_order` | Given/family order reversal; comma-delimited source fields |
| `token_drop` | Missing middle name, patronymic, or nasab element |
| `particle` | Particle handling (al-Zawahiri / al Zawahiri / Zawahiri) |
| `initials` | Given names reduced to initials |
| `title_affix` | Honorifics and generational suffixes |
| `punctuation` | Hyphen, apostrophe and spacing variation |
| `case_fold` | Casing differences |

### Adversarial, deliberate evasion

| Class | Models |
|---|---|
| `homoglyph` | Cyrillic codepoints that render identically to Latin |
| `invisible_char` | Zero-width and non-breaking characters inside tokens |
| `vowel_drop` | Internal vowels removed; still humanly legible |
| `double_collapse` | Repeated letters collapsed or doubled |
| `phonetic` | Phonetically neutral respelling |

### Degraded, upstream system loss

| Class | Models |
|---|---|
| `ocr` | Known OCR confusion pairs from document capture |
| `typo` | Keyboard-adjacency substitution |
| `transpose` | Adjacent character transposition |
| `truncate` | Fixed-width field truncation in legacy systems |

## Limitations

Read these before citing any number this tool produces.

1. **Negative controls are synthetic.** They measure discrimination against
   structurally adjacent strings. They do **not** estimate a production
   false-positive rate, which depends on the customer-name distribution an
   institution actually sees.

2. **Names only.** Real screening decisions use date of birth, nationality,
   document numbers, and address. This benchmark models the name-matching layer
   in isolation. An engine that scores poorly here may perform acceptably in
   production with strong secondary identifiers, and the reverse.

3. **The common-name problem is out of scope.** Where a listed name is also borne
   by millions of unlisted people, the discriminating work is done by secondary
   identifiers, not by string matching. This benchmark does not measure it.

4. **Perturbation realism is argued, not measured.** The classes are grounded in
   documented naming conventions, published OCR confusion sets, and known
   Unicode evasion techniques. What is *not* established is the relative
   frequency of each class in live data. Do not read the class weights as a risk
   ranking. See [docs/METHODOLOGY.md](docs/METHODOLOGY.md#open-questions).

5. **The reference matcher is a baseline, not a recommendation.** It exists so
   the benchmark produces a number without a commercial licence.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Additional perturbation classes are the
most useful contribution, especially ones grounded in a citable naming convention
or a documented evasion technique. Coverage of non-Latin scripts is currently the
weakest area.

## Licence

Code: MIT. See [LICENSE](LICENSE).
Sanctions list data is not redistributed; see [docs/LICENSING.md](docs/LICENSING.md).

## Citation

See [CITATION.cff](CITATION.cff).
