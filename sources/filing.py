from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Literal, Optional

Source = Literal["house", "senate", "form4"]
Action = Literal["BUY", "SELL", "EXCHANGE", "OPTION_BUY", "OPTION_SELL"]


@dataclass(frozen=True)
class Filing:
    id: str
    source: Source
    filed_at: str  # ISO 8601 UTC
    person: str
    person_role: str
    ticker: Optional[str]
    company: str
    action: Action
    shares: Optional[float]
    price_per_share: Optional[float]
    value_low: Optional[float]
    value_high: Optional[float]
    value_exact: Optional[float]
    raw_url: str

    def __post_init__(self) -> None:
        has_exact = self.value_exact is not None
        has_range = self.value_low is not None or self.value_high is not None
        if has_exact and has_range:
            raise ValueError("exactly one of value_exact or value_low/high must be set")


def filing_to_dict(f: Filing) -> dict:
    return asdict(f)


def filing_from_dict(d: dict) -> Filing:
    return Filing(**d)
