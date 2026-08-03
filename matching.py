"""
Perturbation engine.

Each perturbation class models a *documented* way that a real-world name string
can differ from its canonical form on a sanctions list. The classes fall into
three families, and the distinction matters for how results should be read:

  BENIGN      Variation that arises innocently from data entry, transliteration,
              or naming-convention differences. A screening engine that misses
              these produces false negatives against non-adversarial customers.

  ADVERSARIAL Variation a party is likely to introduce *deliberately* to defeat
              screening. Misses here are evasion, not data quality.

  DEGRADED    Variation introduced by an upstream system — OCR from document
              capture, truncation by a field-length limit, encoding loss.

Every perturbation is deterministic given (input, seed), so a generated
benchmark is exactly reproducible from its manifest.

Rationale and sourcing for the taxonomy is in docs/METHODOLOGY.md.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Callable, Iterable

BENIGN = "benign"
ADVERSARIAL = "adversarial"
DEGRADED = "degraded"


@dataclass(frozen=True)
class Variant:
    """A single generated test case."""

    text: str
    source: str
    perturbation: str
    family: str
    entity_id: str


@dataclass
class Perturbation:
    name: str
    family: str
    description: str
    fn: Callable[[str, int], list]
    conditional: bool = True


REGISTRY: dict = {}


def register(name: str, family: str, description: str, conditional: bool = True):
    def deco(fn):
        REGISTRY[name] = Perturbation(
            name=name, family=family, description=description, fn=fn, conditional=conditional
        )
        return fn

    return deco


def _seeded(text: str, seed: int) -> int:
    """Deterministic pseudo-random integer from (text, seed)."""
    h = hashlib.sha256(f"{seed}:{text}".encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def _dedupe(items: Iterable, original: str) -> list:
    out, seen = [], {original.casefold()}
    for it in items:
        if not it:
            continue
        it = re.sub(r"\s+", " ", it).strip()
        k = it.casefold()
        if k and k not in seen:
            seen.add(k)
            out.append(it)
    return out


# --------------------------------------------------------------------------
# BENIGN — innocent variation
# --------------------------------------------------------------------------

# Romanisation systems disagree. These clusters cover the most common Arabic,
# Persian, Cyrillic and Chinese romanisation divergences seen in sanctions data.
# Each tuple is a set of mutually substitutable renderings.
_TRANSLIT_CLUSTERS = [
    ("muhammad", "mohammed", "mohamed", "muhammed", "mohammad", "muhamad", "mehmet"),
    ("ahmad", "ahmed", "ahmet"),
    ("yusuf", "yousef", "youssef", "yusif", "joseph"),
    ("hussein", "husayn", "husein", "hussain", "hosein"),
    ("abdullah", "abdallah", "abdulla", "abd allah"),
    ("aleksandr", "alexander", "aleksander", "alexandr"),
    ("dmitri", "dmitry", "dmitrii", "dimitri"),
    ("sergei", "sergey", "sergej"),
    ("yevgeny", "evgeny", "evgenii", "eugene"),
    ("ivanov", "ivanoff"),
    ("khalid", "khaled", "haled"),
    ("qasim", "kasim", "kassem", "qassem"),
    ("shaykh", "sheikh", "shaikh", "sheik"),
    ("zhang", "chang"),
    ("li", "lee"),
    ("wang", "wong"),
    ("gaddafi", "qaddafi", "kadafi", "khadafy"),
    ("osama", "usama", "oussama"),
    ("jaber", "jabir", "gaber"),
    ("nasser", "nasir", "naser", "nassir"),
]

_TRANSLIT_INDEX = {}
for _cluster in _TRANSLIT_CLUSTERS:
    for _form in _cluster:
        _TRANSLIT_INDEX[_form] = _cluster


@register(
    "translit",
    BENIGN,
    "Substitute an alternate romanisation of a name token (Muhammad/Mohammed/Mohamad).",
)
def p_translit(text: str, seed: int) -> list:
    tokens = text.split()
    out = []
    for i, tok in enumerate(tokens):
        cluster = _TRANSLIT_INDEX.get(tok.casefold())
        if not cluster:
            continue
        for alt in cluster:
            if alt == tok.casefold():
                continue
            new = tokens.copy()
            new[i] = alt.title() if tok[:1].isupper() else alt
            out.append(" ".join(new))
    return _dedupe(out, text)


@register("diacritics_strip", BENIGN, "Remove diacritical marks (José -> Jose, Müller -> Muller).")
def p_diacritics_strip(text: str, seed: int) -> list:
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return _dedupe([unicodedata.normalize("NFC", stripped)], text)


_UMLAUT_EXPANSION = {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"}


@register("diacritics_expand", BENIGN, "Expand umlauts the German way (Müller -> Mueller).")
def p_diacritics_expand(text: str, seed: int) -> list:
    if not any(ch in _UMLAUT_EXPANSION for ch in text):
        return []
    out = "".join(_UMLAUT_EXPANSION.get(ch, ch) for ch in text)
    return _dedupe([out], text)


@register(
    "name_order",
    BENIGN,
    "Reverse given/family name order — the standard failure for Chinese, Hungarian and "
    "many Arabic naming conventions, and for any comma-delimited source field.",
)
def p_name_order(text: str, seed: int) -> list:
    toks = text.split()
    if len(toks) < 2:
        return []
    out = [" ".join(reversed(toks))]
    if len(toks) > 2:
        out.append(" ".join([toks[-1]] + toks[:-1]))
        out.append(f"{toks[-1]}, {' '.join(toks[:-1])}")
    else:
        out.append(f"{toks[1]}, {toks[0]}")
    return _dedupe(out, text)


@register(
    "token_drop",
    BENIGN,
    "Drop a middle token — patronymic, middle name, or a nasab element.",
)
def p_token_drop(text: str, seed: int) -> list:
    toks = text.split()
    if len(toks) < 3:
        return []
    out = []
    for i in range(1, len(toks) - 1):
        out.append(" ".join(toks[:i] + toks[i + 1 :]))
    return _dedupe(out, text)


_PARTICLES = (
    "al", "el", "bin", "ibn", "abu", "abd", "van", "von", "de", "del",
    "della", "da", "di", "la", "le", "mac", "mc", "o",
)


@register(
    "particle",
    BENIGN,
    "Vary the treatment of name particles (al-Zawahiri / al Zawahiri / alZawahiri / Zawahiri).",
)
def p_particle(text: str, seed: int) -> list:
    out = []
    low = text.casefold()
    if "-" in text:
        out.append(text.replace("-", " "))
        out.append(text.replace("-", ""))
    for part in _PARTICLES:
        pat = re.compile(rf"\b({re.escape(part)})[\s\-]+", re.IGNORECASE)
        if pat.search(low):
            out.append(pat.sub(lambda m: m.group(1) + "-", text))
            out.append(pat.sub(lambda m: m.group(1), text))
            out.append(pat.sub("", text))
    return _dedupe(out, text)


@register("initials", BENIGN, "Reduce given names to initials (John Smith -> J. Smith, J Smith).")
def p_initials(text: str, seed: int) -> list:
    toks = text.split()
    if len(toks) < 2:
        return []
    out = [
        " ".join([f"{toks[0][0]}."] + toks[1:]),
        " ".join([toks[0][0]] + toks[1:]),
    ]
    if len(toks) > 2:
        out.append(" ".join([f"{t[0]}." for t in toks[:-1]] + [toks[-1]]))
    return _dedupe(out, text)


_TITLES = ("Dr.", "Dr", "Mr.", "Sheikh", "Hajji", "Col.", "Gen.", "Eng.", "Prof.", "Sayyid")


@register("title_affix", BENIGN, "Add an honorific or title, or a generational suffix.")
def p_title_affix(text: str, seed: int) -> list:
    r = _seeded(text, seed)
    title = _TITLES[r % len(_TITLES)]
    return _dedupe([f"{title} {text}", f"{text} Jr.", f"{text} II"], text)


@register("punctuation", BENIGN, "Alter hyphens, apostrophes and internal spacing.")
def p_punctuation(text: str, seed: int) -> list:
    out = [
        text.replace("'", ""),
        text.replace("'", " "),
        text.replace("-", " "),
        text.replace("-", ""),
        text.replace(".", ""),
    ]
    return _dedupe(out, text)


@register("case_fold", BENIGN, "Change letter casing (ALL CAPS, lowercase).")
def p_case_fold(text: str, seed: int) -> list:
    return _dedupe([text.upper(), text.lower()], text)


# --------------------------------------------------------------------------
# ADVERSARIAL — deliberate evasion
# --------------------------------------------------------------------------

# Cyrillic characters that render identically or near-identically to Latin ones.
# Substituting these defeats naive exact matching entirely while leaving the
# rendered string visually unchanged.
_HOMOGLYPHS = {
    "a": "а",  # CYRILLIC SMALL LETTER A
    "c": "с",  # CYRILLIC SMALL LETTER ES
    "e": "е",  # CYRILLIC SMALL LETTER IE
    "o": "о",  # CYRILLIC SMALL LETTER O
    "p": "р",  # CYRILLIC SMALL LETTER ER
    "x": "х",  # CYRILLIC SMALL LETTER HA
    "y": "у",  # CYRILLIC SMALL LETTER U
    "i": "і",  # CYRILLIC SMALL LETTER BYELORUSSIAN-UKRAINIAN I
    "s": "ѕ",  # CYRILLIC SMALL LETTER DZE
    "A": "А",
    "B": "В",
    "E": "Е",
    "K": "К",
    "M": "М",
    "H": "Н",
    "O": "О",
    "P": "Р",
    "C": "С",
    "T": "Т",
    "X": "Х",
}


@register(
    "homoglyph",
    ADVERSARIAL,
    "Substitute visually identical Cyrillic codepoints for Latin ones. The rendered "
    "name is unchanged to a human reader; the byte sequence is not.",
)
def p_homoglyph(text: str, seed: int) -> list:
    candidates = [i for i, ch in enumerate(text) if ch in _HOMOGLYPHS]
    if not candidates:
        return []
    out = []
    # Single substitution — the minimum-effort evasion.
    idx = candidates[_seeded(text, seed) % len(candidates)]
    chars = list(text)
    chars[idx] = _HOMOGLYPHS[chars[idx]]
    out.append("".join(chars))
    # Full substitution — every substitutable character.
    out.append("".join(_HOMOGLYPHS.get(ch, ch) for ch in text))
    return _dedupe(out, text)


_INVISIBLES = ["​", "‌", "‍", " ", "⁠"]


@register(
    "invisible_char",
    ADVERSARIAL,
    "Insert zero-width or non-breaking characters inside a token. Invisible when "
    "rendered; breaks tokenisation and exact match.",
)
def p_invisible_char(text: str, seed: int) -> list:
    if len(text) < 3:
        return []
    r = _seeded(text, seed)
    ch = _INVISIBLES[r % len(_INVISIBLES)]
    pos = 1 + (r // 7) % (len(text) - 2)
    return _dedupe([text[:pos] + ch + text[pos:]], text)


@register(
    "vowel_drop",
    ADVERSARIAL,
    "Remove internal vowels — cheap, defeats exact match, remains humanly legible.",
)
def p_vowel_drop(text: str, seed: int) -> list:
    def drop(tok: str) -> str:
        if len(tok) < 4:
            return tok
        return tok[0] + re.sub(r"[aeiouAEIOU]", "", tok[1:-1]) + tok[-1]

    return _dedupe([" ".join(drop(t) for t in text.split())], text)


@register(
    "double_collapse",
    ADVERSARIAL,
    "Collapse or double repeated letters (Hussein/Husein, Nasser/Naser).",
)
def p_double_collapse(text: str, seed: int) -> list:
    collapsed = re.sub(r"(.)\1", r"\1", text)
    doubled = re.sub(r"([bdlmnprst])", r"\1\1", text, count=1)
    return _dedupe([collapsed, doubled], text)


_PHONETIC = [
    ("ph", "f"), ("ck", "k"), ("c", "k"), ("s", "z"),
    ("ei", "ie"), ("y", "i"), ("kh", "h"), ("gh", "g"),
]


@register("phonetic", ADVERSARIAL, "Apply a phonetically neutral spelling substitution.")
def p_phonetic(text: str, seed: int) -> list:
    out = []
    low = text.casefold()
    for a, b in _PHONETIC:
        if a in low:
            out.append(re.sub(re.escape(a), b, text, flags=re.IGNORECASE, count=1))
    return _dedupe(out, text)


# --------------------------------------------------------------------------
# DEGRADED — upstream system loss
# --------------------------------------------------------------------------

_OCR_CONFUSIONS = [
    ("rn", "m"), ("m", "rn"), ("cl", "d"), ("l", "1"), ("I", "l"),
    ("O", "0"), ("0", "O"), ("S", "5"), ("B", "8"), ("Z", "2"),
]


@register(
    "ocr",
    DEGRADED,
    "Apply a known OCR confusion pair. Relevant wherever names enter via document "
    "capture rather than keyed entry.",
)
def p_ocr(text: str, seed: int) -> list:
    out = []
    for a, b in _OCR_CONFUSIONS:
        if a in text:
            out.append(text.replace(a, b, 1))
    return _dedupe(out, text)


_QWERTY_NEIGHBOURS = {
    "q": "wa", "w": "qes", "e": "wrd", "r": "etf", "t": "ryg", "y": "tuh", "u": "yij",
    "i": "uok", "o": "ipl", "p": "o", "a": "qsz", "s": "awdx", "d": "sefc", "f": "drgv",
    "g": "fthb", "h": "gyjn", "j": "hukm", "k": "jil", "l": "ko", "z": "asx", "x": "zsdc",
    "c": "xdfv", "v": "cfgb", "b": "vghn", "n": "bhjm", "m": "njk",
}


@register("typo", DEGRADED, "Single keyboard-adjacency substitution (QWERTY).")
def p_typo(text: str, seed: int) -> list:
    idxs = [i for i, ch in enumerate(text) if ch.casefold() in _QWERTY_NEIGHBOURS]
    if not idxs:
        return []
    r = _seeded(text, seed)
    i = idxs[r % len(idxs)]
    neigh = _QWERTY_NEIGHBOURS[text[i].casefold()]
    sub = neigh[(r // 11) % len(neigh)]
    chars = list(text)
    chars[i] = sub.upper() if text[i].isupper() else sub
    return _dedupe(["".join(chars)], text)


@register("transpose", DEGRADED, "Transpose two adjacent characters.")
def p_transpose(text: str, seed: int) -> list:
    if len(text) < 4:
        return []
    positions = [i for i in range(len(text) - 1) if text[i] != " " and text[i + 1] != " "]
    if not positions:
        return []
    i = positions[_seeded(text, seed) % len(positions)]
    chars = list(text)
    chars[i], chars[i + 1] = chars[i + 1], chars[i]
    return _dedupe(["".join(chars)], text)


@register(
    "truncate",
    DEGRADED,
    "Truncate to a fixed field width — models a legacy system with a 20- or "
    "35-character name field.",
)
def p_truncate(text: str, seed: int) -> list:
    out = []
    for width in (20, 35):
        if len(text) > width:
            out.append(text[:width].rstrip())
    return _dedupe(out, text)


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


def families() -> dict:
    out = {BENIGN: [], ADVERSARIAL: [], DEGRADED: []}
    for name, p in REGISTRY.items():
        out[p.family].append(name)
    return out


def apply_all(
    text: str,
    entity_id: str,
    seed: int = 0,
    only=None,
    max_per_class: int = 3,
) -> list:
    """Generate every variant of ``text`` across the selected perturbation classes."""
    variants = []
    names = only if only is not None else list(REGISTRY)
    for name in names:
        pert = REGISTRY.get(name)
        if pert is None:
            raise KeyError(f"unknown perturbation: {name}")
        produced = pert.fn(text, seed)[:max_per_class]
        for v in produced:
            variants.append(
                Variant(
                    text=v,
                    source=text,
                    perturbation=name,
                    family=pert.family,
                    entity_id=entity_id,
                )
            )
    return variants
