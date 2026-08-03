# Contributing

The most useful contribution is a new perturbation class, especially one grounded
in a citable naming convention or a documented evasion technique.

## Adding a perturbation class

A class needs four things. All four, or it doesn't go in.

1. **A function** in `src/ssb/perturb.py`, registered with `@register(name,
   family, description)`. It takes `(text: str, seed: int)` and returns a list of
   variant strings. It must be a pure function of its inputs: no clocks, no
   randomness that isn't derived from `seed` via `_seeded()`. Reproducibility is
   the point of the project.

2. **A family assignment.** `BENIGN` for variation that arises innocently,
   `ADVERSARIAL` for variation introduced deliberately to defeat matching,
   `DEGRADED` for variation introduced by an upstream system. This is the most
   important decision you'll make, because it determines how a low score on your
   class should be read.

3. **A test** in `tests/test_ssb.py`. At minimum: that it never returns the input
   unchanged, and that it produces what you claim for a representative input.

4. **A paragraph** in `docs/METHODOLOGY.md` explaining what real-world phenomenon
   it models. Not what it does, what it *models*. A class nobody can justify is
   noise in every scorecard that includes it.

Return an empty list rather than raising when a class doesn't apply to an input.
Most classes are conditional.

## Where help is most needed

**Non-Latin script coverage.** Currently the benchmark generates Latin-script
variants of names that are themselves already romanised. Screening against native
script is a separate and harder problem and is not represented at all.

**Entity and vessel names.** The perturbation classes were designed for personal
names. Corporate names have their own variation grammar: legal-form suffixes,
abbreviation, translation, transliteration of the trading name but not the legal
name. None of it is modelled.

**Alias structure.** OFAC alias records carry type information (a.k.a., f.k.a.,
strong versus weak) that could sharpen both positive generation and scoring. It is
currently ignored.

**Additional list sources.** EU consolidated, UN, UK OFSI. The parsing layer in
`src/ssb/sources.py` is structured to take them; nobody has written them.

**Better negative controls.** The three synthetic classes are a floor, not a
ceiling. A more realistic negative distribution would materially improve what the
precision figure means.

## Things that will get a change rejected

- Adding a third-party dependency. The zero-dependency property is deliberate: it
  means anyone can run this on a locked-down corporate machine, which is exactly
  where screening people work.
- Committing sanctions list data. Nothing is redistributed; see
  `docs/LICENSING.md`.
- Weakening the reference matcher to make a comparison look better. It's a
  baseline, and an honest one is the only kind worth having.
- Perturbations tuned to defeat a specific vendor's product.

## Reporting a result

If you run the benchmark against a commercial engine, you're welcome to open an
issue with the class-wise profile. Please **do not name the vendor** unless your
agreement with them clearly permits it. An anonymised profile, for example
"Engine A, commercial, deployed at a mid-size US bank", is more useful than
nothing and avoids putting you in a difficult position.

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

Everything runs offline against the synthetic fixture. No network, no accounts, no
API keys.
