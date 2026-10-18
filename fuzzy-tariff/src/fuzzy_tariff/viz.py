"""Plots for reports and the course write-up (requires the `viz` extra: matplotlib)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

from fuzzy_tariff.fuzzy.config import FISSpec, MFSpec, VarSpec
from fuzzy_tariff.fuzzy.membership import MembershipFunction


def plot_membership_functions(spec: FISSpec, out: str | Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    variables: list[tuple[str, VarSpec]] = [*spec.inputs.items(), (spec.output.name, spec.output)]
    fig, axes = plt.subplots(len(variables), 1, figsize=(8, 2.4 * len(variables)))
    for ax, (name, var) in zip(axes, variables, strict=True):
        lo, hi = var.universe
        x = np.linspace(lo, hi, 500)
        mf_spec: MFSpec
        for label, mf_spec in var.sets.items():
            ax.plot(x, MembershipFunction(mf_spec.shape, tuple(mf_spec.params))(x), label=label)
        ax.set_ylabel(name)
        ax.set_ylim(-0.02, 1.05)
        ax.legend(loc="upper right", fontsize=7, ncol=5)
    fig.tight_layout()
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_tariff_days(
    tariff: pd.DataFrame,
    days: list[str],
    out: str | Path,
    std_energy: float = 12.0,
    std_grid: float = 10.0,
) -> Path:
    """Plot energy, grid and total tariff (Rp./kWh) for example local days."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    local = tariff.copy()
    local.index = local.index.tz_convert("Europe/Zurich")
    fig, axes = plt.subplots(len(days), 1, figsize=(9, 3.6 * len(days)), sharey=True)
    axes = [axes] if len(days) == 1 else list(axes)
    for ax, day in zip(axes, days, strict=True):
        d = local.loc[day]
        ax.step(d.index, d["energy_rp"], where="post", label="energy")
        ax.step(d.index, d["grid_rp"], where="post", label="grid")
        ax.step(d.index, d["total_rp"], where="post", label="total", color="black", lw=1.8)
        ax.axhline(std_energy, color="C0", ls=":", lw=1)
        ax.axhline(std_grid, color="C1", ls=":", lw=1)
        ax.set_title(f"{day} (dotted: standard tariffs)")
        ax.set_ylabel("Rp./kWh")
        ax.legend(loc="upper left", ncol=3, fontsize=8)
    fig.tight_layout()
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path
