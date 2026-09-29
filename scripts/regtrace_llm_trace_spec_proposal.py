#!/usr/bin/env python3
"""Ask an LLM to propose RegTrace schema/rubric specs for a domain.

This is an assistant for the adaptive construction module.  The output is not
treated as truth; it is a proposal that the executable utility gate can compare
against the frozen TraceSpec.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import OpenAI

from pressback.costs import append_usage_record, cost_for_tokens, estimate_text_tokens
from regtrace_framework.domain_probe import build_all_specs, read_jsonl


DOMAIN_PATHS = {
    "sec": "data/sec_visible_evidence_benchmark_v2/sec_visible_evidence_benchmark_v2.jsonl",
    "cms": "data/cms2567_poc_gepa_splits/grouped_seed17/all.jsonl",
    "fda": "data/fda_warning_letters/fda_warning_closeout_trace_candidates.jsonl",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domains", nargs="+", default=["sec", "cms", "fda"], choices=sorted(DOMAIN_PATHS))
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--sample-size", type=int, default=4)
    parser.add_argument("--max-tokens", type=int, default=1800)
    parser.add_argument("--out-dir", default="outputs/adaptive_trace_framework/llm_schema_proposals")
    parser.add_argument("--usage-ledger", default="outputs/openai_usage_ledger.jsonl")
    parser.add_argument("--estimate-only", action="store_true")
    args = parser.parse_args()

    load_env_file(Path(".env"))
    root = Path(".").resolve()
    frozen_specs = {slug(spec.domain): spec.to_dict() for spec in build_all_specs(root)}
    payloads = []
    for domain in args.domains:
        rows = read_jsonl(root / DOMAIN_PATHS[domain])
        payloads.append((domain, build_prompt_payload(domain, rows[: args.sample_size], frozen_specs)))

    estimate = estimate_cost(payloads, args.model, args.max_tokens)
    if args.estimate_only:
        print(json.dumps(estimate, indent=2, ensure_ascii=False))
        return 0
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    client = OpenAI()
    summaries = []
    for domain, payload in payloads:
        proposal = call_model(client, args.model, args.max_tokens, args.usage_ledger, domain, payload)
        proposal["_domain"] = domain
        proposal["_model"] = args.model
        proposal["_sample_size"] = args.sample_size
        proposal_path = out_dir / f"{domain}.llm_trace_spec_proposal.json"
        proposal_path.write_text(json.dumps(proposal, indent=2, ensure_ascii=False), encoding="utf-8")
        summaries.append({"domain": domain, "proposal_path": str(proposal_path), "decision": proposal.get("decision")})

    write_report(out_dir / "summary.md", summaries)
    print(json.dumps({"estimate": estimate, "outputs": summaries}, indent=2, ensure_ascii=False))
    return 0


def build_prompt_payload(domain: str, rows: list[dict[str, Any]], frozen_specs: dict[str, Any]) -> dict[str, Any]:
    compact_rows = [compact_row(row) for row in rows]
    return {
        "domain": domain,
        "available_fields": sorted({key for row in rows for key in row.keys()}),
        "sample_rows": compact_rows,
        "framework_schema": {
            "required_roles": ["request", "response", "evidence", "label", "feedback", "external_corroboration"],
            "utility_dimensions": [
                "role_observability",
                "evidence_availability",
                "label_viability",
                "feedback_richness",
                "external_corroboration",
                "release_viability",
                "optimization_suitability",
            ],
            "valid_decisions": ["go-primary-benchmark", "go-cross-regulatory-adaptation", "reshape-before-benchmark", "reject"],
        },
        "frozen_spec_hint": frozen_specs.get(domain, {}),
    }


def compact_row(row: dict[str, Any]) -> dict[str, Any]:
    keep: dict[str, Any] = {}
    for key, value in row.items():
        if value in (None, "", [], {}):
            continue
        if isinstance(value, (str, int, float, bool)):
            text = str(value)
            keep[key] = text[:900] if len(text) > 900 else value
        elif isinstance(value, list):
            keep[key] = [str(item)[:300] for item in value[:5]]
        else:
            keep[key] = str(value)[:500]
    return keep


def call_model(
    client: OpenAI,
    model: str,
    max_tokens: int,
    usage_ledger: str | None,
    domain: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    started = time.time()
    request: dict[str, Any] = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are designing an adaptive RegTrace construction spec for regulatory review traces. "
                    "Do not force the SEC schema if the available fields do not support it. "
                    "Your job is to propose a role mapping, label policy, feedback policy, utility decision, "
                    "and minimal benchmark plan. Be concrete and conservative."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Given the following domain sample, return strict JSON with keys: "
                    "domain, task_name, decision, role_mapping, label_policy, feedback_policy, "
                    "forbidden_test_time_fields, utility_scores, risks, minimal_experiment, paper_claim.\n\n"
                    f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
                ),
            },
        ],
    }
    if model.startswith("gpt-5"):
        request["max_completion_tokens"] = max_tokens
    else:
        request["max_tokens"] = max_tokens
    response = client.chat.completions.create(**request)
    usage = usage_to_dict(response.usage)
    append_usage_record(
        usage_ledger,
        purpose=f"regtrace_llm_trace_spec_proposal:{domain}",
        model=model,
        usage=usage,
        estimated_cost_usd=cost_for_tokens(model, usage["prompt_tokens"], usage["completion_tokens"]),
    )
    proposal = parse_json(response.choices[0].message.content or "{}")
    proposal["_latency_sec"] = round(time.time() - started, 3)
    proposal["_usage"] = usage
    return proposal


def estimate_cost(payloads: list[tuple[str, dict[str, Any]]], model: str, max_tokens: int) -> dict[str, Any]:
    prompt_tokens = 0
    for _, payload in payloads:
        prompt_tokens += estimate_text_tokens(json.dumps(payload, ensure_ascii=False))
        prompt_tokens += 650
    completion_tokens = len(payloads) * max_tokens
    return {
        "domains": [domain for domain, _ in payloads],
        "model": model,
        "estimated_prompt_tokens": prompt_tokens,
        "estimated_completion_tokens": completion_tokens,
        "estimated_cost_usd": cost_for_tokens(model, prompt_tokens, completion_tokens),
    }


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def usage_to_dict(usage: Any) -> dict[str, int]:
    return {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def parse_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def slug(text: str) -> str:
    lowered = text.lower()
    if "sec" in lowered:
        return "sec"
    if "cms" in lowered:
        return "cms"
    if "fda" in lowered:
        return "fda"
    return lowered.replace(" ", "_")


def write_report(path: Path, summaries: list[dict[str, Any]]) -> None:
    lines = ["# LLM TraceSpec Proposals", ""]
    lines.extend(["| Domain | Decision | Proposal |", "| --- | --- | --- |"])
    for row in summaries:
        lines.append(f"| {row['domain']} | {row.get('decision', '')} | `{row['proposal_path']}` |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

