"""
Negative control generation.

A benchmark that measures only recall is worthless: an engine that matches every
input scores 100%. Precision has to be measured against strings that are
structurally similar to listed names but that do not denote a listed party.

Three negative classes are generated, in increasing order of difficulty:

  CROSS_PAIR   Given name from entity A combined with family name from entity B.
               Neither the combination nor the resulting person is listed. Any
               engine scoring on partial token overlap will fire on these.

  TOKEN_SWAP   One token of a listed name replaced with a name token drawn from a
               different entity. Preserves the shape and script of the original
               while denoting someone else.

  EDIT_BEYOND  A string placed deliberately just outside plausible match
               distance: enough edits that a correctly-tuned engine should reject
               it, few enough that a loose threshold will not.

HONEST LIMITATION, stated here and repeated in docs/METHODOLOGY.md: these are
*synthetic* negatives. They measure an engine's discrimination against
structurally adjacent strings. They do NOT estimate a production false-positive
rate, which depends on the customer-name distribution an institution actually
sees and on secondary identifiers (date of birth, nationality, document number)
that this benchmark does not model. Report the two numbers separately and never
present the precision figure as a production alert-volume estimate.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

CROSS_PAIR = "cross_pair"
TOKEN_SWAP = "token_swap"
EDIT_BEYOND = "edit_beyond"


@dataclass(frozen=True)
class Negative:
    text: str
    negative_class: str
    derived_from: tuple


def _seeded(text: str, seed: int) -> int:
    h = hashlib.sha256(f"neg:{seed}:{text}".encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def _tokens(name: str) -> list:
    return [t for t in name.replace(",", " ").split() if len(t) > 1]


def generate(names: list, seed: int = 0, per_class: int = 1, listed_index=None) -> list:
    """Build negative controls from a list of canonical listed names.

    ``listed_index`` should be the casefolded set of every name and alias on the
    list, so generated negatives can be checked not to collide with a real entry.
    """
    listed = listed_index or {n.casefold() for n in names}
    out = []
    if len(names) < 2:
        return out

    for i, name in enumerate(names):
        toks = _tokens(name)
        if len(toks) < 2:
            continue
        r = _seeded(name, seed)

        # --- CROSS_PAIR ---------------------------------------------------
        made = 0
        for step in range(1, len(names)):
            other = names[(i + step * (1 + r % 7)) % len(names)]
            otoks = _tokens(other)
            if len(otoks) < 2 or other == name:
                continue
            candidate = f"{toks[0]} {otoks[-1]}"
            if candidate.casefold() in listed:
                continue
            out.append(Negative(candidate, CROSS_PAIR, (name, other)))
            made += 1
            if made >= per_class:
                break

        # --- TOKEN_SWAP ---------------------------------------------------
        made = 0
        for step in range(1, len(names)):
            other = names[(i + step * (3 + r % 5)) % len(names)]
            otoks = _tokens(other)
            if not otoks or other == name:
                continue
            new = toks.copy()
            new[-1] = otoks[0]
            candidate = " ".join(new)
            if candidate.casefold() in listed or candidate.casefold() == name.casefold():
                continue
            out.append(Negative(candidate, TOKEN_SWAP, (name, other)))
            made += 1
            if made >= per_class:
                break

        # --- EDIT_BEYOND --------------------------------------------------
        # Replace the interior of the longest token, keeping first and last
        # characters. Enough edits that identity is not preserved.
        longest = max(toks, key=len)
        if len(longest) >= 5:
            filler = "aeiou"[r % 5] + "rlnst"[(r // 3) % 5]
            mutated = longest[0] + filler + longest[-1]
            candidate = " ".join(mutated if t == longest else t for t in toks)
            if candidate.casefold() not in listed:
                out.append(Negative(candidate, EDIT_BEYOND, (name,)))

    return out
