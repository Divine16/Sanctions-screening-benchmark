"""
Sanctions list acquisition and parsing.

No list data is redistributed with this repository. Everything is fetched at run
time from the publishing authority, so a generated benchmark always reflects the
list as published on the date in its manifest. That is deliberate: a benchmark
carrying a stale embedded copy of the SDN list would be both less useful and
legally murkier than one that fetches.

Supported sources
-----------------
ofac_sdn          OFAC Specially Designated Nationals list (primary names)
ofac_sdn_alt      OFAC SDN alternate names / a.k.a. file
ofac_consolidated OFAC Consolidated (non-SDN) sanctions list

Offline use
-----------
Pass ``--offline`` on the CLI, or call ``load_fixture()``, to build against the
small synthetic fixture in tests/fixtures/. The fixture contains no real
designated party — the names are invented — so it is safe to commit and lets the
test suite and CI run with no network.
"""

from __future__ import annotations

import csv
import io
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Primary endpoints, with legacy fallbacks. OFAC has migrated hosts more than
# once; each is tried in order.
ENDPOINTS = {
    "ofac_sdn": (
        "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV",
        "https://www.treasury.gov/ofac/downloads/sdn.csv",
    ),
    "ofac_sdn_alt": (
        "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ALT.CSV",
        "https://www.treasury.gov/ofac/downloads/alt.csv",
    ),
    "ofac_consolidated": (
        "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/CONS_PRIM.CSV",
        "https://www.treasury.gov/ofac/downloads/consolidated/cons_prim.csv",
    ),
}

# OFAC's CSV exports are headerless positional files.
SDN_COLUMNS = [
    "ent_num", "name", "sdn_type", "program", "title",
    "call_sign", "vess_type", "tonnage", "grt", "vess_flag", "vess_owner", "remarks",
]
ALT_COLUMNS = ["ent_num", "alt_num", "alt_type", "alt_name", "alt_remarks"]

_NULL = {"-0-", "-0- ", "", "-0-\n"}


@dataclass
class Entity:
    entity_id: str
    primary_name: str
    entity_type: str = ""
    programs: list = field(default_factory=list)
    aliases: list = field(default_factory=list)

    def all_names(self) -> list:
        return [self.primary_name] + self.aliases


@dataclass
class ListSnapshot:
    source: str
    retrieved_at: str
    entities: list
    endpoint: str = ""

    def individuals(self) -> list:
        return [e for e in self.entities if e.entity_type.lower().startswith("individual")]

    def name_index(self) -> set:
        idx = set()
        for e in self.entities:
            for n in e.all_names():
                idx.add(n.casefold())
        return idx


def _clean(v) -> str:
    if v is None:
        return ""
    v = v.strip()
    return "" if v in _NULL else v


def _download(urls, timeout: int = 60):
    last = None
    for url in urls:
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "sanctions-screening-benchmark/0.1 (+research)"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            return raw.decode("utf-8", errors="replace"), url
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last = exc
            continue
    raise RuntimeError(
        f"could not retrieve any of {urls}. Last error: {last}. "
        "If you are behind a proxy or offline, run with --offline to use the bundled fixture."
    )


def _parse_sdn(text: str) -> dict:
    entities = {}
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if not row or len(row) < 4:
            continue
        padded = list(row) + [""] * (len(SDN_COLUMNS) - len(row))
        rec = dict(zip(SDN_COLUMNS, padded))
        ent_id = _clean(rec["ent_num"])
        name = _clean(rec["name"])
        if not ent_id or not name:
            continue
        programs = [p.strip() for p in _clean(rec["program"]).split(";") if p.strip()]
        entities[ent_id] = Entity(
            entity_id=ent_id,
            primary_name=name,
            entity_type=_clean(rec["sdn_type"]) or "unknown",
            programs=programs,
        )
    return entities


def _parse_alt(text: str, entities: dict) -> None:
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if not row or len(row) < 4:
            continue
        padded = list(row) + [""] * (len(ALT_COLUMNS) - len(row))
        rec = dict(zip(ALT_COLUMNS, padded))
        ent_id = _clean(rec["ent_num"])
        alt = _clean(rec["alt_name"])
        if not ent_id or not alt:
            continue
        ent = entities.get(ent_id)
        if ent is not None and alt not in ent.aliases and alt != ent.primary_name:
            ent.aliases.append(alt)


def fetch(source: str = "ofac_sdn", include_aliases: bool = True) -> ListSnapshot:
    """Retrieve and parse a sanctions list from its publishing authority."""
    if source not in ENDPOINTS:
        raise KeyError(f"unknown source '{source}'. Known: {sorted(ENDPOINTS)}")
    text, endpoint = _download(ENDPOINTS[source])
    entities = _parse_sdn(text)
    if include_aliases and source == "ofac_sdn":
        try:
            alt_text, _ = _download(ENDPOINTS["ofac_sdn_alt"])
            _parse_alt(alt_text, entities)
        except RuntimeError:
            # Aliases are an enhancement, not a requirement.
            pass
    return ListSnapshot(
        source=source,
        retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        entities=list(entities.values()),
        endpoint=endpoint,
    )


def load_fixture(path=None) -> ListSnapshot:
    """Load the synthetic offline fixture. Contains no real designated party."""
    if path is None:
        path = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "synthetic_list.csv"
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    entities = _parse_sdn(text)
    alt_path = path.with_name("synthetic_list_alt.csv")
    if alt_path.exists():
        _parse_alt(alt_path.read_text(encoding="utf-8"), entities)
    return ListSnapshot(
        source="fixture",
        retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        entities=list(entities.values()),
        endpoint=str(path),
    )
