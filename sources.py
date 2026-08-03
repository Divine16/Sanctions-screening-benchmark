"""
Reference matcher.

This exists so the benchmark produces a number out of the box and so anyone can
reproduce a published scorecard without access to a commercial engine. It is a
*baseline*, not a recommendation: normalise, then Jaro-Winkler over token sets,
which is roughly what a competent in-house implementation looks like before
anyone tunes it.

Reporting a commercial engine as "better than baseline" is only meaningful if the
baseline is honest, so the implementation is deliberately reasonable rather than
deliberately weak. It is also deliberately naive about Unicode: normalisation
folds diacritics but does not fold homoglyphs, which is exactly the blind spot
the adversarial perturbation classes are designed to expose.

Zero third-party dependencies. Jaro-Winkler is implemented here so the repository
runs on a clean Python 3.9+ install.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Callable

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_WS = re.compile(r"\s+")

# Tokens that carry no discriminating power in a personal name.
STOPWORDS = {
    "mr", "mrs", "ms", "dr", "prof", "eng", "col", "gen", "sheikh", "shaykh",
    "hajji", "sayyid", "jr", "sr", "ii", "iii", "the", "and",
}


def normalise(text: str, fold_diacritics: bool = True) -> str:
    """Lowercase, strip punctuation, collapse whitespace, optionally fold diacritics."""
    if fold_diacritics:
        nfd = unicodedata.normalize("NFD", text)
        text = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    text = unicodedata.normalize("NFC", text)
    text = _PUNCT.sub(" ", text.casefold())
    return _WS.sub(" ", text).strip()


def tokens(text: str, drop_stopwords: bool = True) -> list:
    toks = normalise(text).split()
    if drop_stopwords:
        toks = [t for t in toks if t not in STOPWORDS]
    return toks


def jaro(s1: str, s2: str) -> float:
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0
    window = max(len1, len2) // 2 - 1
    if window < 0:
        window = 0
    s1_flags = [False] * len1
    s2_flags = [False] * len2
    matches = 0
    for i in range(len1):
        lo = max(0, i - window)
        hi = min(i + window + 1, len2)
        for j in range(lo, hi):
            if not s2_flags[j] and s1[i] == s2[j]:
                s1_flags[i] = s2_flags[j] = True
                matches += 1
                break
    if matches == 0:
        return 0.0
    k = 0
    transpositions = 0
    for i in range(len1):
        if s1_flags[i]:
            while not s2_flags[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1
    transpositions //= 2
    m = float(matches)
    return (m / len1 + m / len2 + (m - transpositions) / m) / 3.0


def jaro_winkler(s1: str, s2: str, prefix_weight: float = 0.1, max_prefix: int = 4) -> float:
    j = jaro(s1, s2)
    if j <= 0.7:
        return j
    prefix = 0
    for a, b in zip(s1[:max_prefix], s2[:max_prefix]):
        if a != b:
            break
        prefix += 1
    return j + prefix * prefix_weight * (1.0 - j)


def token_set_similarity(a: str, b: str, char_sim: Callable = jaro_winkler) -> float:
    """Best-alignment token similarity.

    Each token of the shorter side is greedily matched to its best partner on the
    longer side; the score is the sum of those best similarities divided by the
    length of the longer side, so unmatched tokens dilute the score.
    """
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    if len(ta) > len(tb):
        ta, tb = tb, ta
    remaining = tb.copy()
    total = 0.0
    for t in ta:
        if not remaining:
            break
        best_i, best_s = 0, -1.0
        for i, cand in enumerate(remaining):
            s = char_sim(t, cand)
            if s > best_s:
                best_i, best_s = i, s
        total += best_s
        remaining.pop(best_i)
    return total / max(len(tb), 1)


class BaselineMatcher:
    """Normalise, then token-set Jaro-Winkler. The out-of-the-box reference."""

    name = "baseline-jw-tokenset"

    def __init__(self, fold_diacritics: bool = True, drop_stopwords: bool = True):
        self.fold_diacritics = fold_diacritics
        self.drop_stopwords = drop_stopwords

    def __call__(self, query: str, candidate: str) -> float:
        return token_set_similarity(query, candidate)


class ExactMatcher:
    """Normalised exact equality. Included to make the floor visible."""

    name = "exact-normalised"

    def __call__(self, query: str, candidate: str) -> float:
        return 1.0 if normalise(query) == normalise(candidate) else 0.0
