# RegTrace-SEC

RegTrace-SEC is a benchmark and experiment package for evidence-grounded SEC comment-letter response review. Each example asks whether a company response and retrieved amended-filing snippets visibly resolve a prior SEC staff request.

This repository is organized as a release-ready bundle for the RegTrace-Agent paper. It includes the frozen benchmark, splits, reported result artifacts, reviewer-response analyses, prompts, and scripts used to reproduce the main tables.

## Contents

- `data/sec_visible_evidence_benchmark_v2/`: frozen 472-example benchmark, split files, manifest, and dataset reports.
- `docs/results/`: paper-ready result tables, prompt-evolution artifacts, qualitative cases, evidence ablations, temporal/topic holdouts, and feedback ablations.
- `docs/review_response/`: additional analyses motivated by reviews, including the paired follow-up corroboration test, five-fold OOF summary, supervised baselines, encoder/Jev triage scorers, and independent-feedback ablation.
- `outputs/`: compact raw result JSON/CSV files needed to rebuild reported tables.
- `scripts/`: dataset, retrieval, optimization, evaluation, and analysis scripts.
- `pressback/`: local helper package for SEC/OpenAI/DSPy utilities.
- `paper/`: ACL/FinNLP LaTeX source and figure assets.
- `configs/`: frozen experiment configuration summary.

## Main Benchmark Snapshot

- 472 examples from 109 SEC review threads and 95 companies.
- Labels: 153 resolved and 319 unresolved.
- Issue categories: other, risk factor, SPAC disclosure, revenue recognition, crypto, non-GAAP, and cybersecurity.
- The benchmark is retrieval-conditioned: each example includes raw retrieved amended-filing snippets and labels whether the visible evidence resolves the SEC request.

## Main Result

On the grouped held-out split, all methods receive the same test-time input: SEC comment, company response, and raw retrieved amended-filing snippets.

| Method | Accuracy | Macro-F1 | Unresolved F1 |
|---|---:|---:|---:|
| Baseline prompt | 0.424 | 0.402 | 0.286 |
| MIPROv2 | 0.655 | 0.652 | 0.684 |
| GEPA-scalar | 0.705 | 0.675 | 0.774 |
| GEPA-category | 0.597 | 0.595 | 0.627 |
| GEPA-full | 0.784 | 0.756 | 0.839 |

See `docs/results/final_leaderboard_v2_dev48_gap_m150.md`.

## System Components

RegTrace-Agent is organized as a context-to-feedback review system, not a single prompt. The learned reviewer can be used directly, distilled into a guarded verifier, or paired with cheaper non-generative triage gates.

| Component | Role | Macro-F1 | Note |
|---|---|---:|---|
| Frozen encoder scorer | local non-generative triage head | 0.667 | `all-MiniLM-L6-v2` + logistic head |
| Jev typed decision gate | hosted typed choice gate | 0.722 | high unresolved recall, no rationale generation |
| GEPA-full reviewer | full feedback-trained reviewer | 0.756 | strongest reviewer-training signal |
| RegTrace guarded verifier | policy-distillation prototype | 0.801 | uses distilled obligation-evidence guard |

See `docs/review_response/encoder_scorer_summary.md` and `docs/review_response/jev_decision_gate_summary.md`.

## Reviewer-Response Analyses

The release includes a paired follow-up corroboration analysis. Later same-topic SEC follow-up is treated as a noisy external reference, not as the benchmark label. On the clean 220-example subset, the visible benchmark label reaches 0.756 macro-F1 against this external signal, while GEPA-full OOF reaches 0.590 and the handwritten baseline reaches 0.460. This should be used as label-validity evidence rather than as a method-win claim.

See `docs/review_response/followup_paired_analysis.md`.

The release also includes two reviewer-response additions:

- Non-prompt supervised baselines: TF-IDF logistic regression reaches 0.523 macro-F1 with raw amended-filing snippets, far below GEPA-full, while an oracle-summary variant reaches 0.858 macro-F1. See `docs/review_response/supervised_baselines_summary.md`.
- Non-generative triage scorers: a frozen encoder scorer reaches 0.667 macro-F1 and Jev reaches 0.722 macro-F1 on the grouped held-out test set. These are fast decision gates rather than full reviewer replacements. See `docs/review_response/encoder_scorer_summary.md` and `docs/review_response/jev_decision_gate_summary.md`.
- Independent-feedback ablation: GEPA trained with GPT-5.4-mini feedback that did not see the original adjudication rationales reaches 0.750 macro-F1, close to the original GEPA-full result of 0.756. See `docs/review_response/independent_feedback_ablation.md`.

## Reproduction

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Rebuild the paired follow-up analysis:

```bash
PYTHONPATH=. python scripts/sec_followup_paired_analysis.py
```

Rebuild the final leaderboard table from included outputs:

```bash
PYTHONPATH=. python scripts/sec_build_final_leaderboard_artifact.py
```

Run the non-prompt supervised baselines:

```bash
make supervised-baselines
```

Run local non-generative encoder scorers:

```bash
make encoder-scorers
```

Run the Jev typed decision gate smoke test. This requires a local `.env` file with `JEV_API_KEY` and calls `https://thejevai.com/v1/systemone`:

```bash
make jev-smoke
```

OpenAI-backed optimization and adjudication scripts require `OPENAI_API_KEY`. Existing result artifacts are included so table-level reproduction does not require rerunning every model call. Expensive targets such as `make independent-gepa-ablation` are intentionally explicit and should be run only when regenerating model-call artifacts.

## Release Status

This is a GitHub-ready local bundle. Before public upload, confirm the final code/data license choice and remove any author-identifying metadata if the repository is used for anonymous review.
