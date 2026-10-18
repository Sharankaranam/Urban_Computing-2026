"""Label stability: hysteresis on output memberships and a minimum block length."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from fuzzy_tariff.fuzzy.engine import MamdaniFIS


def best_set(memberships: dict[str, float], order: Sequence[str]) -> str:
    """Set with the highest membership; ties resolve to the earlier set in ``order``."""
    return max(order, key=lambda s: (memberships[s], -order.index(s)))


def hysteresis_labels(
    fis: MamdaniFIS, scores: NDArray[np.float64] | Sequence[float], margin: float = 0.1
) -> list[str | float]:
    """Label each score by its strongest output set, but only switch label when the new set
    beats the current one by at least ``margin`` membership. NaN scores give NaN labels."""
    order = list(fis.output.sets)
    current: str | None = None
    labels: list[str | float] = []
    for s in scores:
        if np.isnan(s):
            labels.append(np.nan)
            continue
        mem = fis.output_memberships_at(float(s))
        cand = best_set(mem, order)
        if current is None or cand == current or mem[cand] - mem[current] >= margin:
            current = cand
        labels.append(current)
    return labels


def enforce_min_block(labels: Sequence[str | float], min_len: int = 2) -> list[str | float]:
    """Replace runs shorter than ``min_len`` by the previous label (or next, at the start).

    Suitable for day-ahead labelling where the whole sequence is known. NaN runs are kept.
    """
    out = list(labels)
    if min_len <= 1 or not out:
        return out
    n = len(out)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and _same(out[j + 1], out[i]):
            j += 1
        run_len = j - i + 1
        is_nan = isinstance(out[i], float) and np.isnan(out[i])
        if run_len < min_len and not is_nan:
            if i > 0 and not _is_nan(out[i - 1]):
                repl = out[i - 1]
            elif j + 1 < n and not _is_nan(out[j + 1]):
                repl = out[j + 1]
            else:
                repl = out[i]
            for k in range(i, j + 1):
                out[k] = repl
        i = j + 1
    return out


def _is_nan(x: str | float) -> bool:
    return isinstance(x, float) and bool(np.isnan(x))


def _same(a: str | float, b: str | float) -> bool:
    return (_is_nan(a) and _is_nan(b)) or a == b
