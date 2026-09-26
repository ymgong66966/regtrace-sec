# Benchmark-Level Paper Readiness Memo

## Current Strongest Story

The paper should be framed as a benchmark and method study for evidence-grounded SEC comment-response resolution. The core novelty is not just GEPA, and not just an EDGAR scrape. It is the construction of a context-to-feedback optimization setting where company responses are judged against visible amended-filing evidence, and where adjudicated gap descriptions can serve as rich natural-language feedback for reflective prompt optimization.

## Results That Are Already Strong

1. **Evidence matters.** On Benchmark v2, adding raw amended-filing snippets improves macro-F1 from 0.575 to 0.748 over response-only prompting.
2. **The adjudication layer is meaningful.** The oracle evidence-summary condition reaches macro-F1 0.956, showing that the task becomes tractable when the model is given the exact missing-requirement summary.
3. **Natural-language feedback now has main Benchmark v2 evidence.** On the frozen grouped Benchmark v2 split, GEPA-full reaches macro-F1 0.756 and unresolved F1 0.839, outperforming MIPROv2 (0.652 / 0.684), GEPA-scalar (0.675 / 0.774), and GEPA-category (0.595 / 0.627).
4. **The temporal holdout is strong.** When trained on 2022-2023 and tested on 2024-2025, GEPA-full reaches macro-F1 0.791 and unresolved F1 0.877, compared with 0.519 / 0.489 for MIPROv2 and 0.650 / 0.679 for GEPA-scalar. This is the best current evidence that full feedback learns a transferable evidence-gap policy.
5. **The topic holdout is also strong.** On a held-out topic split that includes crypto and non-GAAP cases absent from the training issue categories, GEPA-full reaches macro-F1 0.734 and unresolved F1 0.849, compared with 0.565 / 0.635 for MIPROv2 and 0.524 / 0.569 for GEPA-scalar. Per-topic breakdown shows GEPA-full improves over MIPROv2 on every nontrivial held-out category, with the largest gains in revenue recognition and non-GAAP.
6. **The dataset is now structurally credible.** Benchmark v2 has 472 examples, 109 SEC review threads, 95 companies, 7 issue categories, 8 gap types, and held-out grouped/time/topic splits.

## What Not To Overclaim

- Do not claim the retrieval pipeline is production-robust. Present it as a reproducible benchmark-construction and upstream evidence-retrieval component.
- Do not present `evidence_summary` as a fair deployment input. It is an oracle upper bound and a feedback/adjudication artifact.
- Do not treat the interrupted Benchmark v2 GEPA sanity run as a negative result. It used an inefficient optimizer-dev design and was stopped.

## Highest-Value Next Experiments

1. **Multi-seed or grouped CV stability:** repeat the final leaderboard for at least two more grouped splits or seeds, focusing on Baseline, MIPROv2, GEPA-scalar, and GEPA-full.
2. **Additional topic generalization:** add at least one more held-out topic configuration or report per-topic breakdown on the current topic split.
3. **Feedback component ablation:** compare full adjudicated feedback vs no evidence summary vs no missing requirement vs synthetic feedback.
4. **Human/LLM audit expansion:** extend the current 60-example audit toward 80-100 examples, focusing on label correctness and retrieval sufficiency.

## Long-Paper Upgrade Path

A short paper can focus on the benchmark, evidence ablation, the final Benchmark v2 leaderboard, temporal/topic holdouts, and qualitative prompt evolution. A long paper now mainly needs multi-seed/grouped-CV stability, additional topic-holdout configurations or per-topic analysis, feedback component ablation, and a stronger audit section.
