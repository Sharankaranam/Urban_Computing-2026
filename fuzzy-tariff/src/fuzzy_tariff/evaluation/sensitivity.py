"""Sensitivity (membership-function perturbation) and input ablation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from fuzzy_tariff.fuzzy.config import FISSpec, build_fis
from fuzzy_tariff.labeler import FuzzyLabeler


def perturb_spec(spec: FISSpec, rel: float, seed: int) -> FISSpec:
    """Shift every INPUT fuzzy set by a random amount up to +/- rel * universe width.

    Shifting (rather than reshaping) keeps parameters ordered, so the result stays valid.
    """
    rng = np.random.default_rng(seed)
    out = spec.model_copy(deep=True)
    for var in out.inputs.values():
        width = var.universe[1] - var.universe[0]
        for mf in var.sets.values():
            delta = float(rng.uniform(-rel, rel)) * width
            mf.params = [p + delta for p in mf.params]
    return out


def label_agreement(a: pd.Series, b: pd.Series) -> float:
    mask = a.notna() & b.notna()
    return float((a[mask] == b[mask]).mean()) if mask.any() else float("nan")


def membership_sensitivity(
    feats: pd.DataFrame, spec: FISSpec, rel: float = 0.10, n: int = 10, seed: int = 0
) -> pd.DataFrame:
    """Agreement and mean |score difference| between the reference FIS and n perturbed FIS."""
    base = FuzzyLabeler(build_fis(spec)).label(feats)
    rows = []
    for i in range(n):
        pert = FuzzyLabeler(build_fis(perturb_spec(spec, rel, seed + i))).label(feats)
        rows.append(
            {
                "run": i,
                "label_agreement": label_agreement(base["label"], pert["label"]),
                "mean_abs_score_diff": float((base["score"] - pert["score"]).abs().mean()),
            }
        )
    return pd.DataFrame(rows)


def input_ablation(
    feats: pd.DataFrame, spec: FISSpec, neutral: dict[str, float] | None = None
) -> pd.DataFrame:
    """Replace one input at a time by a neutral value and measure how labels change."""
    neutral = neutral or {"G": 0.5, "T": 0.0, "A": 0.5}
    labeler = FuzzyLabeler(build_fis(spec))
    base = labeler.label(feats)
    rows = []
    for var, value in neutral.items():
        if var not in feats:
            continue
        ablated = feats.copy()
        ablated[var] = value
        res = labeler.label(ablated)
        rows.append(
            {
                "ablated_input": var,
                "label_agreement": label_agreement(base["label"], res["label"]),
                "mean_abs_score_diff": float((base["score"] - res["score"]).abs().mean()),
            }
        )
    return pd.DataFrame(rows)
