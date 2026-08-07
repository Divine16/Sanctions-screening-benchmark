# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions use
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-08-08

### Added

- `compare` command — side-by-side class-wise scorecard diffs for two matchers
  or two saved scorecard JSON files.
- `sweep` command — threshold grid analysis reporting recall, precision, false
  positive rate, and best F1 operating point in one matcher pass.
- `make compare` and `make sweep` Makefile targets for offline smoke checks.
- This changelog.

### Changed

- Scoring refactored to evaluate each case once, then apply thresholds (used by
  `sweep` without re-running the matcher).

## [0.1.0] - 2026-08-07

### Added

- Initial release: eighteen perturbation classes across benign, adversarial, and
  degraded families.
- OFAC SDN list fetch with alias merge; offline synthetic fixture for CI.
- Benchmark generation and evaluation CLI (`generate`, `evaluate`, `demo`,
  `classes`).
- Reference matchers (normalised exact and baseline Jaro-Winkler token-set).
- Synthetic negative controls and class-wise recall scorecards.

[0.2.0]: https://github.com/Divine16/sanctions-screening-benchmark/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Divine16/sanctions-screening-benchmark/releases/tag/v0.1.0
