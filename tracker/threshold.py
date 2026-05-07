from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

from sources.filing import Filing

Bucket = Literal["big", "small"]

CSUITE_ROLES = {"CEO", "CFO", "COO", "President", "Director", "10% owner"}


@dataclass(frozen=True)
class ThresholdConfig:
    min_congress: float
    min_form4: float
    include_lower_insiders: bool


def classify(f: Filing, cfg: ThresholdConfig) -> Bucket:
    if f.source in ("house", "senate"):
        if f.value_low is not None and f.value_low >= cfg.min_congress:
            return "big"
        return "small"
    if f.source == "form4":
        if f.value_exact is None or f.value_exact < cfg.min_form4:
            return "small"
        if not cfg.include_lower_insiders and f.person_role not in CSUITE_ROLES:
            return "small"
        return "big"
    return "small"
