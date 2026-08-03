# Licensing of sanctions list data

This repository redistributes **no** sanctions list data.

The benchmark fetches list content from the publishing authority at generation
time (see `src/ssb/sources.py`). Generated benchmarks record the retrieval
timestamp and endpoint in the manifest so a result is attributable to a specific
published list state.

The offline fixture under `tests/fixtures/` is entirely synthetic. It contains
no real designated party and exists only so tests and `ssb.cli demo` can run
without network access.

Do not commit live SDN, consolidated, or other official list extracts to this
repository.
