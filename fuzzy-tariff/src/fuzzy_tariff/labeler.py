"""Stage-1 labelling service: features -> suitability score -> stable label."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from fuzzy_tariff.fuzzy.config import FuzzyConfig, build_fis, load_config
from fuzzy_tariff.fuzzy.engine import MamdaniFIS
from fuzzy_tariff.stability import enforce_min_block, hysteresis_labels


@dataclass
class FuzzyLabeler:
    fis: MamdaniFIS
    margin: float = 0.1
    min_block: int = 2

    @classmethod
    def from_config(
        cls, cfg: FuzzyConfig | None = None, margin: float = 0.1, min_block: int = 2
    ) -> FuzzyLabeler:
        cfg = cfg or load_config()
        return cls(build_fis(cfg.stage1), margin=margin, min_block=min_block)

    def label(self, feats: pd.DataFrame) -> pd.DataFrame:
        """Return a frame with ``score``, ``raw_label`` (argmax) and stabilised ``label``."""
        cols = {c: feats[c].to_numpy(dtype=float) for c in self.fis.inputs if c in feats}
        batch = self.fis.infer_many(**cols)
        scores = batch.scores
        raw = hysteresis_labels(self.fis, scores, margin=0.0)
        stable = hysteresis_labels(self.fis, scores, margin=self.margin)
        stable = enforce_min_block(stable, self.min_block)
        valid = (
            ~np.isnan(feats["P"].to_numpy(dtype=float))
            if "P" in feats
            else np.ones(len(feats), bool)
        )
        out = pd.DataFrame({"score": scores, "raw_label": raw, "label": stable}, index=feats.index)
        out.loc[~valid, ["score", "raw_label", "label"]] = np.nan
        return out
