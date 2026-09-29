"""Shared schema objects for adaptive RegTrace construction.

The schema is intentionally domain-neutral.  SEC comments, CMS deficiencies,
and FDA warning letters all become review traces only after the framework maps
local fields into request, response/correction, evidence, outcome, and feedback
roles.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RoleMapping:
    """Domain-specific fields mapped into the generic review-trace roles."""

    request: list[str]
    response: list[str]
    evidence: list[str]
    label: list[str]
    feedback: list[str]
    external_corroboration: list[str] = field(default_factory=list)
    metadata: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FeedbackPolicy:
    """Optimization feedback channels available for a domain."""

    scalar: str
    category: str | None
    full_text: str | None
    external_text: str | None = None
    forbidden_test_time_fields: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class UtilityScore:
    """A compact decision rubric for whether a corpus can support RegTrace."""

    role_observability: float
    evidence_availability: float
    label_viability: float
    feedback_richness: float
    external_corroboration: float
    release_viability: float
    optimization_suitability: float

    @property
    def mean(self) -> float:
        values = [
            self.role_observability,
            self.evidence_availability,
            self.label_viability,
            self.feedback_richness,
            self.external_corroboration,
            self.release_viability,
            self.optimization_suitability,
        ]
        return sum(values) / len(values)


@dataclass(frozen=True)
class TraceSpec:
    """Paper-facing description of a constructed review-trace task."""

    domain: str
    task_name: str
    decision: str
    instance_count: int
    role_mapping: RoleMapping
    label_definition: str
    feedback_policy: FeedbackPolicy
    utility: UtilityScore
    label_distribution: dict[str, int] = field(default_factory=dict)
    category_distribution: dict[str, int] = field(default_factory=dict)
    strengths: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["utility"]["mean"] = round(self.utility.mean, 3)
        return payload


def score_label_balance(label_distribution: dict[str, int]) -> float:
    """Return a 0-5 score for binary/multiclass balance.

    This is a utility diagnostic, not a statistical test.  Extremely skewed
    labels are still usable for triage, but weak for headline method comparison.
    """

    if not label_distribution:
        return 0.0
    total = sum(label_distribution.values())
    if total == 0:
        return 0.0
    shares = [v / total for v in label_distribution.values()]
    max_share = max(shares)
    if len(shares) == 1:
        return 1.0
    if max_share <= 0.65:
        return 5.0
    if max_share <= 0.75:
        return 4.0
    if max_share <= 0.85:
        return 3.0
    if max_share <= 0.93:
        return 2.0
    return 1.0

