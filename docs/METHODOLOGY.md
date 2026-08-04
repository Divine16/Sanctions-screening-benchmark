# Methodology

This document states what each perturbation class models, why families matter, and
what the precision figure does and does not mean. Implementation lives in
`src/ssb/perturb.py` and `src/ssb/negatives.py`.

## Families

| Family | Meaning of a miss |
|---|---|
| **Benign** | False negative against ordinary customers / data-quality loss |
| **Adversarial** | Evasion exposure — a party can defeat the control deliberately |
| **Degraded** | Upstream system loss (OCR, truncation, encoding) |

The class-wise recall profile is the primary deliverable. Aggregate F1 is not.

## Benign classes

| Class | Models |
|---|---|
| `translit` | Competing romanisations (Muhammad / Mohammed / Mohamad) |
| `diacritics_strip` | Diacritics lost in transit (José → Jose) |
| `diacritics_expand` | German-style umlaut expansion (Müller → Mueller) |
| `name_order` | Given/family order reversal; comma-delimited source fields |
| `token_drop` | Missing middle name, patronymic, or nasab element |
| `particle` | Particle handling (al-Zawahiri / al Zawahiri / Zawahiri) |
| `initials` | Given names reduced to initials |
| `title_affix` | Honorifics and generational suffixes |
| `punctuation` | Hyphen, apostrophe and spacing variation |
| `case_fold` | Casing differences |

## Adversarial classes

| Class | Models |
|---|---|
| `homoglyph` | Cyrillic codepoints that render identically to Latin |
| `invisible_char` | Zero-width and non-breaking characters inside tokens |
| `vowel_drop` | Internal vowels removed; still humanly legible |
| `double_collapse` | Repeated letters collapsed or doubled |
| `phonetic` | Phonetically neutral respelling |

## Degraded classes

| Class | Models |
|---|---|
| `ocr` | Known OCR confusion pairs from document capture |
| `typo` | Keyboard-adjacency substitution |
| `transpose` | Adjacent character transposition |
| `truncate` | Fixed-width field truncation in legacy systems |

## Negative controls

Three synthetic negative classes measure discrimination against structurally
adjacent strings that do not denote a listed party:

- `cross_pair` — given name from entity A with family name from entity B
- `token_swap` — one token replaced from a different entity
- `edit_beyond` — interior mutation that should fall outside a tuned match distance

They do **not** estimate a production false-positive rate. That depends on the
customer-name distribution an institution actually sees and on secondary
identifiers this benchmark does not model.

## Determinism

Every perturbation is a pure function of `(input, seed)`. Two runs against the
same list state and seed produce byte-identical benchmarks.

## Open questions

1. Relative frequency of each class in live screening traffic is not established.
   Do not treat class weights as a risk ranking.
2. Non-Latin script coverage is absent; the fixture and generators operate on
   already-romanised strings.
3. Corporate and vessel name grammars are largely unmodelled.
4. OFAC alias type (a.k.a. / f.k.a., strong vs weak) is ignored during generation.
