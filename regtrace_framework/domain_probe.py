"""Domain probes for adaptive RegTrace construction.

The probe layer is the first executable piece of the agentic framework.  It
turns a raw or semi-constructed corpus into a TraceSpec and makes the framework
state whether the corpus should be accepted, reshaped, or rejected.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .schema import FeedbackPolicy, RoleMapping, TraceSpec, UtilityScore, score_label_balance


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def top_counts(rows: Iterable[dict[str, Any]], field: str, limit: int = 12) -> dict[str, int]:
    counts = Counter()
    for row in rows:
        value = row.get(field)
        if isinstance(value, list):
            for item in value:
                counts[str(item)] += 1
        elif value not in (None, ""):
            counts[str(value)] += 1
    return dict(counts.most_common(limit))


def sec_spec(root: Path) -> TraceSpec:
    path = root / "data/sec_visible_evidence_benchmark_v2/sec_visible_evidence_benchmark_v2.jsonl"
    rows = read_jsonl(path)
    labels = top_counts(rows, "visible_evidence_resolution_label")
    categories = top_counts(rows, "issue_category")
    followup_count = sum(1 for row in rows if row.get("has_real_followup"))

    return TraceSpec(
        domain="SEC comment-letter review",
        task_name="visible-evidence response-resolution review",
        decision="go-primary-benchmark",
        instance_count=len(rows),
        role_mapping=RoleMapping(
            request=["sec_comment"],
            response=["company_response"],
            evidence=["retrieved_snippets", "amended_evidence_best_snippet"],
            label=["visible_evidence_resolution_label"],
            feedback=[
                "scalar_feedback",
                "category_feedback",
                "full_feedback",
                "feedback_sec_request",
                "feedback_company_action",
                "feedback_evidence_summary",
                "feedback_unmet_requirement",
            ],
            external_corroboration=["real_followup_text", "has_real_followup"],
            metadata=[
                "review_thread_id",
                "cik",
                "review_file_no",
                "issue_category",
                "response_year",
            ],
        ),
        label_definition=(
            "resolved iff the visible amended-filing evidence substantially satisfies "
            "the material SEC request; unresolved iff a material requested item, "
            "quantification, exhibit, document, legal/accounting analysis, or other "
            "obligation is still missing from the visible evidence."
        ),
        feedback_policy=FeedbackPolicy(
            scalar="binary correctness against visible_evidence_resolution_label",
            category="issue_category plus coarse gap/category feedback",
            full_text=(
                "natural-language feedback describing the SEC request, company action, "
                "visible evidence coverage, and unmet requirement"
            ),
            external_text="later same-topic SEC follow-up text, used only as noisy corroboration",
            forbidden_test_time_fields=[
                "feedback_*",
                "full_feedback",
                "amended_evidence_* adjudication fields",
                "real_followup_text",
            ],
        ),
        utility=UtilityScore(
            role_observability=5.0,
            evidence_availability=4.5,
            label_viability=score_label_balance(labels),
            feedback_richness=5.0,
            external_corroboration=4.0 if followup_count else 0.0,
            release_viability=4.5,
            optimization_suitability=5.0,
        ),
        label_distribution=labels,
        category_distribution=categories,
        strengths=[
            "Request, response, amended evidence, label, feedback, and follow-up roles are all observable.",
            "Natural-language feedback is aligned with the reasoning failures the reviewer must learn.",
            f"{followup_count} examples have later same-topic SEC follow-up for external corroboration.",
        ],
        risks=[
            "Labels are visible-evidence judgments and do not replace expert legal/accounting review.",
            "Retrieval-conditioned labels can be affected by missing amended-filing evidence.",
        ],
        next_action="Use as the primary benchmark and report retrieval-conditioned limitations.",
    )


def cms_spec(root: Path) -> TraceSpec:
    path = root / "data/cms2567_poc_gepa_splits/grouped_seed17/all.jsonl"
    rows = read_jsonl(path)
    labels = top_counts(rows, "cms_poc_binary_label")
    categories = top_counts(rows, "ftag_group")

    return TraceSpec(
        domain="CMS-2567 plan-of-correction review",
        task_name="deficiency-to-plan adequacy review",
        decision="go-cross-regulatory-adaptation",
        instance_count=len(rows),
        role_mapping=RoleMapping(
            request=["deficiency_text"],
            response=["plan_of_correction_text"],
            evidence=["plan_of_correction_text", "covered_elements", "missing_elements"],
            label=["cms_poc_binary_label", "cms_poc_adequacy_label"],
            feedback=[
                "cms_poc_optimizer_feedback",
                "cms_poc_missing_elements",
                "cms_poc_covered_elements",
                "cms_poc_reason",
            ],
            external_corroboration=["deficiency_corrected", "correction_date", "days_to_correction"],
            metadata=[
                "source_document_id",
                "ccn",
                "ftag",
                "ftag_group",
                "scope_severity",
                "severity_band",
                "state",
                "report_year",
            ],
        ),
        label_definition=(
            "adequate iff the plan of correction materially covers resident-specific "
            "harm, affected population, systemic prevention, monitoring, responsible "
            "party, and credible completion; not_adequate iff material remediation "
            "elements are missing or only generic."
        ),
        feedback_policy=FeedbackPolicy(
            scalar="binary correctness against cms_poc_binary_label",
            category="ftag_group, severity band, and adequacy subtype",
            full_text="covered elements, missing elements, and adjudicated adequacy rationale",
            external_text="CMS correction metadata, treated as weak outcome metadata rather than gold adequacy",
            forbidden_test_time_fields=[
                "cms_poc_* label/rationale/feedback fields",
                "deficiency_corrected",
                "correction_date",
                "days_to_correction",
            ],
        ),
        utility=UtilityScore(
            role_observability=4.5,
            evidence_availability=3.5,
            label_viability=score_label_balance(labels),
            feedback_richness=4.5,
            external_corroboration=2.5,
            release_viability=4.0,
            optimization_suitability=4.0,
        ),
        label_distribution=labels,
        category_distribution=categories,
        strengths=[
            "Regulator deficiency and provider corrective plan are directly observable.",
            "The domain forces the framework to adapt the rubric rather than reuse the SEC checklist verbatim.",
            "Full-feedback optimization already improves over generic and scalar/category CMS controls.",
        ],
        risks=[
            "Correction-date metadata is too skewed to serve as the main adequacy label.",
            "The plan itself is both response and corrective artifact, so evidence is less separable than SEC amended filings.",
        ],
        next_action="Use as the main cross-regulatory adaptation study with CMS-specific rubric induction.",
    )


def fda_spec(root: Path) -> TraceSpec:
    path = root / "data/fda_warning_letters/fda_warning_closeout_trace_candidates.jsonl"
    rows = read_jsonl(path)
    categories = top_counts(rows, "product")
    closeout_labels = {"has_closeout": len(rows)}

    return TraceSpec(
        domain="FDA warning-letter review",
        task_name="warning-to-closeout resolution tracing",
        decision="reshape-before-benchmark",
        instance_count=len(rows),
        role_mapping=RoleMapping(
            request=["warning_excerpt"],
            response=[],
            evidence=["closeout_excerpt"],
            label=["has_closeout", "days_to_closeout"],
            feedback=["closeout_excerpt"],
            external_corroboration=["closeout_issue_date", "closeout_url"],
            metadata=["product", "subject", "issuing_office", "warning_issue_date", "warning_url"],
        ),
        label_definition=(
            "The current public snapshot supports resolution tracing from warning letter "
            "to closeout letter. It does not support SEC-style response-adequacy review "
            "because public company response letters are almost absent."
        ),
        feedback_policy=FeedbackPolicy(
            scalar="closeout existence or delay bucket, after adding negative/non-closeout controls",
            category="product, subject, issuing office, and violation family",
            full_text="closeout language describing FDA's evaluation of corrective actions",
            external_text="closeout letter text",
            forbidden_test_time_fields=["closeout_excerpt for pre-closeout prediction tasks"],
        ),
        utility=UtilityScore(
            role_observability=3.0,
            evidence_availability=2.0,
            label_viability=1.0,
            feedback_richness=3.0,
            external_corroboration=4.0,
            release_viability=4.0,
            optimization_suitability=2.5,
        ),
        label_distribution=closeout_labels,
        category_distribution=categories,
        strengths=[
            "FDA provides public warning and closeout letters with regulatory resolution language.",
            "The domain is a useful stress test because a good construction agent should not force an SEC-style schema.",
            "Linked warning-closeout pairs can support outcome tracing or contrastive resolution verification.",
        ],
        risks=[
            "Public company response letters are almost absent, so request-response-evidence review is not directly observable.",
            "The current linked candidate set is positive-only; classification needs negative or not-yet-closeout controls.",
        ],
        next_action=(
            "Use as an adaptive-construction probe. Build a benchmark only after adding non-closeout controls "
            "or contrastive negatives."
        ),
    )


def build_all_specs(root: Path) -> list[TraceSpec]:
    return [sec_spec(root), cms_spec(root), fda_spec(root)]

