from __future__ import annotations


def build_dspy_program():
    """Return the DSPy responsiveness program.

    This is isolated so the Week-1 data pipeline does not require DSPy. Install
    DSPy only when running optimizer experiments.
    """
    try:
        import dspy
    except ImportError as exc:
        raise RuntimeError("Install dspy to build the optimizer program.") from exc

    class DetectResponsiveness(dspy.Signature):
        """Decide whether an executive answer substantively addresses the analyst question."""

        analyst_question: str = dspy.InputField()
        executive_answer: str = dspy.InputField()
        label: str = dspy.OutputField(desc="responsive | non_responsive")
        reason: str = dspy.OutputField()

    return dspy.ChainOfThought(DetectResponsiveness)


def build_sec_dspy_program():
    """Return the DSPy program for SEC unresolved-response detection."""
    try:
        import dspy
    except ImportError as exc:
        raise RuntimeError("Install dspy to build the SEC optimizer program.") from exc

    class DetectSecUnresolvedResponse(dspy.Signature):
        """Decide whether a company response leaves an SEC comment unresolved.

        Return exactly one binary label: resolved or unresolved. Do not create
        intermediate labels such as partially resolved.
        """

        sec_comment: str = dspy.InputField(desc="The original SEC staff comment.")
        company_response: str = dspy.InputField(desc="The company's written response to that SEC comment.")
        label: str = dspy.OutputField(
            desc=(
                "Exactly one of: resolved | unresolved. Use unresolved only when a concrete SEC-requested "
                "obligation remains unmet by the company's current response."
            )
        )
        reason: str = dspy.OutputField(desc="Brief explanation grounded in the comment and response.")

    return dspy.ChainOfThought(DetectSecUnresolvedResponse)


def build_sec_expert_response_gap_program():
    """Return a stronger hand-initialized SEC response-gap program."""
    try:
        import dspy
    except ImportError as exc:
        raise RuntimeError("Install dspy to build the SEC optimizer program.") from exc

    class DetectSecResponseGapExpert(dspy.Signature):
        """Evaluate whether a company's written response resolves an SEC staff comment.

        Decision procedure:
        1. Identify the concrete SEC request.
        2. Identify the company's current action in the response.
        3. Compare the request to the action and decide whether a concrete SEC-requested obligation remains unmet.

        Label resolved when the response provides a current, concrete disclosure, amendment,
        deletion, confirmation, quantification, or accounting/legal analysis that satisfies
        the SEC request. Do not require the response letter itself to reproduce every word
        of an amended filing; a present-tense statement such as "we revised the disclosure"
        or "we removed the disclosure" can be sufficient unless the response itself shows
        a specific unmet requirement.

        Label unresolved when the response leaves a concrete gap relative to the SEC request:
        a missing requested detail, missing quantification, missing accounting analysis, a
        topic shift, a refusal, boilerplate, or only a future commitment. "We will revise in
        future filings" is unresolved unless the current response also supplies the requested
        disclosure or analysis now, or the SEC specifically requested future-filed disclosure.

        Return exactly one binary label: resolved or unresolved. Do not create intermediate
        labels such as partially resolved.
        """

        sec_comment: str = dspy.InputField(desc="The original SEC staff comment.")
        company_response: str = dspy.InputField(desc="The company's written response to that SEC comment.")
        label: str = dspy.OutputField(desc="Exactly one of: resolved | unresolved.")
        reason: str = dspy.OutputField(desc="Brief explanation grounded in the SEC request and company response.")

    return dspy.ChainOfThought(DetectSecResponseGapExpert)


def build_sec_real_followup_program():
    """Return the DSPy program for real next-round SEC follow-up prediction."""
    try:
        import dspy
    except ImportError as exc:
        raise RuntimeError("Install dspy to build the SEC optimizer program.") from exc

    class DetectSecRealFollowup(dspy.Signature):
        """Predict real SEC continuation risk, not merely textual imperfection.

        Decide whether the company's current response is likely to draw a
        same-obligation next-round SEC follow-up. Label unresolved only when
        the response leaves a concrete disclosure, accounting, legal, or
        compliance obligation open after comparing the SEC request to the
        company's current action. Label resolved when the company substantively
        revises, deletes, confirms, explains, or commits a concrete present
        filing change that plausibly satisfies the same SEC obligation.

        Important calibration: do not require the response letter itself to
        reproduce every word of the amended filing. Many resolved SEC responses
        say "we revised the disclosure" or "we removed the disclosure"; that can
        be sufficient unless the response itself shows a specific unmet
        requirement. Predict the event: whether SEC staff will continue the same
        obligation in the next round.
        """

        sec_comment: str = dspy.InputField(desc="The original SEC staff comment.")
        company_response: str = dspy.InputField(desc="The company's written response to that SEC comment.")
        label: str = dspy.OutputField(
            desc=(
                "resolved | unresolved. Use unresolved when the current response is likely to leave a concrete "
                "same-obligation issue that SEC staff would continue pursuing in a next-round follow-up."
            )
        )
        reason: str = dspy.OutputField(desc="Brief explanation grounded in the SEC request and company response.")

    return dspy.ChainOfThought(DetectSecRealFollowup)


def build_sec_real_followup_risk_program():
    """Return a calibrated risk-scoring program for next-round SEC follow-up."""
    try:
        import dspy
    except ImportError as exc:
        raise RuntimeError("Install dspy to build the SEC optimizer program.") from exc

    class ScoreSecRealFollowupRisk(dspy.Signature):
        """Score real SEC continuation risk before making a binary call.

        Predict the probability-like risk that SEC staff will continue pursuing
        the same obligation in a next-round comment. This is an event-risk task,
        not a pure textual sufficiency task.

        Use high risk only when a concrete requested item remains unmet: missing
        quantification, missing policy, missing accounting analysis, failure to
        amend/delete requested disclosure, or explicit refusal/deferral. Use low
        risk when the company makes a substantive present action such as revising,
        deleting, confirming, quantifying, adding disclosure, or explaining the
        requested issue, unless that action still plainly omits a specific SEC
        request.
        """

        sec_comment: str = dspy.InputField(desc="The original SEC staff comment.")
        company_response: str = dspy.InputField(desc="The company's written response to that SEC comment.")
        risk_score: str = dspy.OutputField(desc="Integer 0-100. Higher means same-obligation SEC follow-up is more likely.")
        label: str = dspy.OutputField(desc="resolved | unresolved, using risk_score >= 50 as unresolved unless reasoning contradicts it.")
        reason: str = dspy.OutputField(desc="Brief explanation naming the concrete unmet obligation or release cue.")

    return dspy.ChainOfThought(ScoreSecRealFollowupRisk)


def build_sec_real_followup_structured_risk_program():
    """Return a structured regulator-followup risk program.

    This gives GEPA more editable surfaces than a direct label-only classifier:
    the optimizer can learn how to identify the SEC obligation, the company's
    release cue, and the surviving unmet requirement before calibrating risk.
    """
    try:
        import dspy
    except ImportError as exc:
        raise RuntimeError("Install dspy to build the SEC optimizer program.") from exc

    class StructuredSecRealFollowupRisk(dspy.Signature):
        """Predict whether SEC staff will pursue the same obligation in the next round.

        This is a regulator reaction task. The target is not whether the response
        is textually perfect; the target is whether the same SEC obligation is
        likely to survive into a later SEC comment.

        Work in this order:
        1. Identify the concrete SEC obligation.
        2. Identify the company's visible current action.
        3. Identify any release cue: present revision, deletion, confirmation,
           quantification, accounting analysis, or specific future-filing
           commitment when the SEC requested future treatment.
        4. Identify any continuation cue: missing quantification, missing policy,
           missing specific disclosure, incomplete accounting/legal analysis,
           explicit refusal, or an amendment claim that still omits the exact
           requested detail.
        5. Score same-obligation follow-up risk.

        Important calibration:
        - A response can be resolved even if it does not quote the full amended
          filing, when it states a substantive present action.
        - A response can still trigger follow-up when the company says it revised
          but the response omits a specific detail SEC later asks for again.
        - Future commitments are low risk when SEC asked for future filings, but
          high risk when SEC asked for current disclosure or current analysis.
        """

        sec_comment: str = dspy.InputField(desc="The original SEC staff comment.")
        company_response: str = dspy.InputField(desc="The company's written response to that SEC comment.")
        sec_obligation: str = dspy.OutputField(desc="The concrete SEC-requested obligation.")
        company_action: str = dspy.OutputField(desc="The visible action or commitment in the company response.")
        release_cue: str = dspy.OutputField(desc="Why SEC might stop pursuing this same obligation.")
        continuation_cue: str = dspy.OutputField(desc="Why SEC might continue pursuing this same obligation.")
        risk_score: str = dspy.OutputField(desc="Integer 0-100. Higher means same-obligation SEC follow-up is more likely.")
        label: str = dspy.OutputField(desc="resolved | unresolved. Use unresolved when risk_score is high.")
        reason: str = dspy.OutputField(desc="Brief final rationale tied to the release or continuation cue.")

    return dspy.ChainOfThought(StructuredSecRealFollowupRisk)


def build_sec_visible_evidence_resolution_program():
    """Return the DSPy program for evidence-grounded SEC resolution."""
    try:
        import dspy
    except ImportError as exc:
        raise RuntimeError("Install dspy to build the SEC optimizer program.") from exc

    class DetectVisibleEvidenceResolution(dspy.Signature):
        """Judge whether visible amended-filing evidence satisfies an SEC request.

        This is not a later-follow-up prediction task. The goal is to compare
        the original SEC comment, the company's response, and retrieved amended
        filing evidence. Label resolved only when the visible evidence satisfies
        all material elements of the SEC request. Label unresolved when the
        evidence shows only a partial fix, misses a named item, omits
        quantification, lacks accounting/legal analysis, or provides no visible
        support for the claimed amendment.
        """

        sec_comment: str = dspy.InputField(desc="The original SEC staff comment.")
        company_response: str = dspy.InputField(desc="The company's written response to that SEC comment.")
        amended_evidence: str = dspy.InputField(desc="Retrieved amended filing snippets or quote.")
        label: str = dspy.OutputField(desc="Exactly one of: resolved | unresolved.")
        reason: str = dspy.OutputField(desc="Brief explanation grounded in the SEC request, response, and amended evidence.")

    return dspy.ChainOfThought(DetectVisibleEvidenceResolution)


def build_sec_visible_evidence_resolution_basic_program():
    """Return a deliberately minimal visible-evidence program.

    This is useful for measuring whether GEPA can learn the SEC-style decision
    procedure from feedback, instead of merely polishing an already strong
    hand-written expert prompt.
    """
    try:
        import dspy
    except ImportError as exc:
        raise RuntimeError("Install dspy to build the SEC optimizer program.") from exc

    class DetectVisibleEvidenceResolutionBasic(dspy.Signature):
        """Classify whether a company resolved an SEC comment using the visible evidence."""

        sec_comment: str = dspy.InputField()
        company_response: str = dspy.InputField()
        amended_evidence: str = dspy.InputField()
        label: str = dspy.OutputField(desc="resolved | unresolved")
        reason: str = dspy.OutputField()

    return dspy.ChainOfThought(DetectVisibleEvidenceResolutionBasic)


def build_sec_visible_evidence_resolution_structured_program():
    """Return a structured visible-evidence resolver.

    The hard cases are not simple label decisions. The model must decompose the
    SEC request, map retrieved evidence to each requested element, and then
    decide whether a concrete element is still missing. Exposing those steps as
    fields gives GEPA separate surfaces to improve.
    """
    try:
        import dspy
    except ImportError as exc:
        raise RuntimeError("Install dspy to build the SEC optimizer program.") from exc

    class StructuredVisibleEvidenceResolution(dspy.Signature):
        """Classify SEC comment resolution through explicit evidence-gap analysis."""

        sec_comment: str = dspy.InputField(desc="The original SEC staff comment.")
        company_response: str = dspy.InputField(desc="The company's written response to that SEC comment.")
        amended_evidence: str = dspy.InputField(desc="Retrieved amended filing snippets or quote.")
        sec_request_elements: str = dspy.OutputField(desc="Concrete items the SEC requested, separated by semicolons.")
        evidence_covered_elements: str = dspy.OutputField(desc="Requested items visibly supported by the amended evidence.")
        missing_or_weak_elements: str = dspy.OutputField(
            desc=(
                "Requested items not visibly satisfied, including missing named items, quantification, "
                "exhibit/consent/document, or accounting/legal analysis. Write 'none' only if no material gap remains."
            )
        )
        label: str = dspy.OutputField(desc="resolved | unresolved")
        reason: str = dspy.OutputField(desc="Brief final rationale grounded in the coverage/gap comparison.")

    return dspy.ChainOfThought(StructuredVisibleEvidenceResolution)
