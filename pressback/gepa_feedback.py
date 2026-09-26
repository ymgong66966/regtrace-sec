from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


FeedbackMode = Literal["scalar", "category", "full"]


@dataclass(frozen=True)
class GoldExample:
    label: str
    follow_up_text: str | None = None
    bavelas_type: str | None = None
    tier: str = "none"


@dataclass(frozen=True)
class Prediction:
    label: str
    reason: str = ""


@dataclass(frozen=True)
class SecGoldExample:
    label: str
    regulator_feedback: str | None = None
    issue_category: str | None = None
    followup_type: str | None = None
    task: str = "response_gap"


@dataclass(frozen=True)
class SecPrediction:
    label: str
    reason: str = ""


def score_and_feedback(gold: GoldExample, pred: Prediction, mode: FeedbackMode = "full") -> dict[str, float | str]:
    correct = normalize_label(pred.label) == normalize_label(gold.label)
    weight = 1.25 if gold.tier == "cross_analyst" and gold.label == "non_responsive" else 1.0
    score = weight if correct else 0.0
    if mode == "scalar":
        feedback = f"{'Correct' if correct else 'Wrong'} (score {score:.0f})."
    elif mode == "category":
        kind = gold.bavelas_type or "unknown_non_response_type"
        feedback = f"score {score:.0f}. Target discourse category: {kind}."
    elif mode == "full":
        feedback = _full_feedback(gold, pred, score, correct)
    else:
        raise ValueError(f"unknown feedback mode: {mode}")
    return {"score": score, "feedback": feedback}


def normalize_label(label: str) -> str:
    lowered = label.strip().lower().replace("-", "_")
    if lowered in {"nonresponsive", "non_responsive", "evasive", "press_back", "1", "true"}:
        return "non_responsive"
    return "responsive"


def score_sec_and_feedback(gold: SecGoldExample, pred: SecPrediction, mode: FeedbackMode = "full") -> dict[str, float | str]:
    correct = normalize_sec_label(pred.label) == normalize_sec_label(gold.label)
    score = 1.0 if correct else 0.0
    if mode == "scalar":
        feedback = f"{'Correct' if correct else 'Wrong'} (score {score:.0f})."
    elif mode == "category":
        category = gold.issue_category or "unknown_issue"
        followup_type = gold.followup_type or "unknown_followup_type"
        feedback = f"score {score:.0f}. SEC issue category: {category}; follow-up type: {followup_type}."
    elif mode == "full":
        if gold.task in {"real_followup", "real_followup_risk", "real_followup_structured_risk"}:
            feedback = _sec_real_followup_feedback(gold, pred, score, correct)
        elif gold.task == "visible_evidence_resolution":
            feedback = _sec_visible_evidence_feedback(gold, pred, score, correct)
        else:
            feedback = _sec_full_feedback(gold, pred, score, correct)
    else:
        raise ValueError(f"unknown feedback mode: {mode}")
    return {"score": score, "feedback": feedback}


def normalize_sec_label(label: str) -> str:
    lowered = label.strip().lower().replace("-", "_")
    if lowered in {"unresolved", "not_resolved", "followup", "follow_up", "1", "true"}:
        return "unresolved"
    return "resolved"


def _full_feedback(gold: GoldExample, pred: Prediction, score: float, correct: bool) -> str:
    if correct:
        return "score 1. Correct; preserve the cue that distinguished this case."
    if normalize_label(gold.label) == "non_responsive":
        follow_up = gold.follow_up_text or "[missing follow-up text]"
        return (
            f"score {score:.0f}. A real analyst was not satisfied and pressed again: "
            f'"{follow_up}". You judged the answer responsive. Identify the exact '
            "informational demand that remained unanswered."
        )
    return (
        f"score {score:.0f}. No same-topic analyst press-back was observed. You "
        "over-flagged evasion; calibrate to substantive omissions, not cautious wording."
    )


def _sec_full_feedback(gold: SecGoldExample, pred: SecPrediction, score: float, correct: bool) -> str:
    if correct:
        return "score 1. Correct; preserve the cue that distinguished whether the SEC issue was resolved."
    if gold.regulator_feedback:
        if normalize_sec_label(gold.label) == "unresolved":
            return (
                f"score {score:.0f}. The gold label is unresolved. Use this response-gap rationale: "
                f"{gold.regulator_feedback} Identify the concrete disclosure, accounting, or legal issue "
                "left unresolved by the company's current response."
            )
        return (
            f"score {score:.0f}. The gold label is resolved. Use this resolution rationale: "
            f"{gold.regulator_feedback} Do not over-flag responses that currently revise, delete, "
            "or substantively explain the issue in a way that satisfies the SEC request."
        )
    if normalize_sec_label(gold.label) == "unresolved":
        followup = gold.regulator_feedback or "[missing regulator follow-up text]"
        return (
            f"score {score:.0f}. The company response did not resolve the SEC comment. "
            f"A later SEC follow-up said: \"{followup}\". Identify the unresolved disclosure, "
            "accounting, or legal issue that remained after the response."
        )
    return (
        f"score {score:.0f}. No accepted same-topic next-round SEC follow-up was observed. "
        "You over-predicted unresolved status; require a concrete remaining disclosure gap, "
        "not merely a terse or cautious company response."
    )


def _sec_visible_evidence_feedback(gold: SecGoldExample, pred: SecPrediction, score: float, correct: bool) -> str:
    """Natural-language feedback for the amended-filing evidence task.

    GEPA only has an advantage over scalar optimizers when it can repeatedly see
    the domain rationale behind both successes and failures. Returning a generic
    "correct" message on correct cases starves the optimizer, especially when
    minibatches are small and often perfect. Keep the full adjudication text in
    the loop for both correct and incorrect predictions.
    """
    gold_label = normalize_sec_label(gold.label)
    pred_label = normalize_sec_label(pred.label)
    rationale = gold.regulator_feedback or "[missing evidence rationale]"

    if correct and gold_label == "resolved":
        return (
            f"score {score:.0f}. Correct resolved call. Gold rationale: {rationale} "
            "Preserve this rule: resolved requires visible amended-filing evidence that covers the material SEC "
            "request, but it does not require every hypothetical detail beyond the SEC's actual request."
        )
    if correct and gold_label == "unresolved":
        return (
            f"score {score:.0f}. Correct unresolved call. Gold rationale: {rationale} "
            "Preserve this rule: unresolved means the visible amended evidence still misses a named request, "
            "quantification, exhibit/consent/document, or accounting/legal analysis that the SEC asked for."
        )
    if gold_label == "resolved" and pred_label == "unresolved":
        return (
            f"score {score:.0f}. False positive. Gold is resolved. Gold rationale: {rationale} "
            "Calibrate down: do not demand extra analysis, quantification, or legal framing unless the SEC "
            "actually requested it. If the amended evidence directly answers the requested item, label resolved."
        )
    return (
        f"score {score:.0f}. False negative. Gold is unresolved. Gold rationale: {rationale} "
        "Calibrate up: a company claim that it amended the filing is not enough when the visible amended "
        "evidence still omits a specific requested item, required number, consent/exhibit, or analysis."
    )


def _sec_real_followup_feedback(gold: SecGoldExample, pred: SecPrediction, score: float, correct: bool) -> str:
    """Feedback tuned for the event-level real-followup task.

    The event label is noisier than a text-level sufficiency label: SEC staff may
    stop following a topic even when the response is terse, and may continue a
    topic after a partially responsive answer. The useful GEPA signal is
    therefore calibration: distinguish concrete same-obligation continuation
    risk from generic regulatory caution.
    """
    gold_label = normalize_sec_label(gold.label)
    pred_label = normalize_sec_label(pred.label)

    if correct and gold_label == "resolved":
        return (
            "score 1. Correct resolved event call. Preserve the release cue: for this task, a response can be "
            "resolved when the company makes a substantive present filing action such as revising, deleting, "
            "confirming, quantifying, or explaining the requested disclosure. Do not require the response letter "
            "to reproduce the complete amended filing text."
        )
    if correct and gold_label == "unresolved":
        return (
            "score 1. Correct unresolved event call. Preserve the continuation cue: the response left a concrete "
            "same-obligation gap that SEC staff later pursued, not just a stylistic imperfection."
        )

    if gold_label == "resolved" and pred_label == "unresolved":
        rationale = gold.regulator_feedback or "No verified same-topic next-round SEC follow-up was observed."
        return (
            f"score {score:.0f}. False positive for the real-followup event task. Gold is resolved. "
            f"{rationale} Calibrate down: do not predict unresolved merely because the response is terse, "
            "does not quote the full amendment, or could hypothetically provide more detail. Predict unresolved "
            "only when a specific item requested by the SEC remains unmet after the company's current action. "
            "Present-tense actions like 'we revised,' 'we deleted,' 'we added disclosure,' 'we confirmed,' or "
            "'we provided the requested statement' are release cues unless contradicted by a concrete missing item."
        )

    followup = gold.regulator_feedback or "[missing real SEC follow-up text]"
    return (
        f"score {score:.0f}. False negative for the real-followup event task. Gold is unresolved. "
        f"Real later SEC follow-up evidence: {followup} Learn the continuation cue: identify the exact same "
        "SEC obligation that survived the company's response, such as missing quantification, missing policy, "
        "missing accounting analysis, or an explicit reissue of the prior request."
    )
