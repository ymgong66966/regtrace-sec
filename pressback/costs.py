from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelPrice:
    input_per_1m: float
    output_per_1m: float = 0.0


# Update this table when changing models. Prices are USD per 1M tokens.
MODEL_PRICES: dict[str, ModelPrice] = {
    "gpt-4o-mini": ModelPrice(input_per_1m=0.15, output_per_1m=0.60),
    "gpt-5.4-mini": ModelPrice(input_per_1m=0.75, output_per_1m=4.50),
    "text-embedding-3-small": ModelPrice(input_per_1m=0.02, output_per_1m=0.0),
}


def estimate_text_tokens(text: str) -> int:
    # Conservative tokenizer-free estimate for English SEC text.
    return max(1, round(len(text) / 4))


def estimate_chat_tokens(sec_comment: str, company_response: str, followup_comment: str) -> tuple[int, int]:
    fixed_prompt_tokens = 320
    input_tokens = fixed_prompt_tokens + estimate_text_tokens(sec_comment[:4000])
    input_tokens += estimate_text_tokens(company_response[:4000])
    input_tokens += estimate_text_tokens(followup_comment[:4000])
    output_tokens = 180
    return input_tokens, output_tokens


def estimate_embedding_tokens(sec_comment: str, followup_comment: str) -> int:
    return estimate_text_tokens(sec_comment[:12000]) + estimate_text_tokens(followup_comment[:12000])


def cost_for_tokens(model: str, input_tokens: int, output_tokens: int = 0, batch_discount: bool = False) -> float:
    price = MODEL_PRICES.get(model)
    if price is None:
        raise KeyError(f"missing price for model: {model}")
    cost = (input_tokens / 1_000_000) * price.input_per_1m
    cost += (output_tokens / 1_000_000) * price.output_per_1m
    if batch_discount:
        cost *= 0.5
    return cost


def append_usage_record(
    ledger_path: str | Path | None,
    *,
    purpose: str,
    model: str,
    usage: dict[str, Any],
    estimated_cost_usd: float,
) -> None:
    if not ledger_path:
        return
    destination = Path(ledger_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "purpose": purpose,
        "model": model,
        "usage": usage,
        "estimated_cost_usd": estimated_cost_usd,
    }
    with destination.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def summarize_ledger(path: str | Path) -> dict[str, Any]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    by_model: dict[str, dict[str, Any]] = {}
    total_cost = 0.0
    for row in rows:
        model = row.get("model", "unknown")
        usage = row.get("usage") or {}
        bucket = by_model.setdefault(
            model,
            {"calls": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "estimated_cost_usd": 0.0},
        )
        bucket["calls"] += 1
        bucket["input_tokens"] += int(usage.get("prompt_tokens") or usage.get("input_tokens") or usage.get("total_tokens") or 0)
        bucket["output_tokens"] += int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        bucket["total_tokens"] += int(usage.get("total_tokens") or 0)
        bucket["estimated_cost_usd"] += float(row.get("estimated_cost_usd") or 0.0)
        total_cost += float(row.get("estimated_cost_usd") or 0.0)
    return {"calls": len(rows), "estimated_cost_usd": total_cost, "by_model": by_model}


def estimate_verification_cost(
    rows: list[dict[str, Any]],
    chat_model: str,
    embedding_model: str,
    unresolved_only: bool = True,
    batch_discount: bool = False,
) -> dict[str, Any]:
    candidates = [row for row in rows if row.get("followup_comment_text")]
    if unresolved_only:
        candidates = [row for row in candidates if row.get("label") == "unresolved"]

    chat_input = chat_output = embedding_input = 0
    for row in candidates:
        ci, co = estimate_chat_tokens(
            str(row.get("sec_comment", "")),
            str(row.get("company_response", "")),
            str(row.get("followup_comment_text", "")),
        )
        chat_input += ci
        chat_output += co
        embedding_input += estimate_embedding_tokens(
            str(row.get("sec_comment", "")),
            str(row.get("followup_comment_text", "")),
        )

    chat_cost = cost_for_tokens(chat_model, chat_input, chat_output, batch_discount=batch_discount)
    embedding_cost = cost_for_tokens(embedding_model, embedding_input, 0, batch_discount=batch_discount)
    return {
        "candidates": len(candidates),
        "chat_model": chat_model,
        "embedding_model": embedding_model,
        "batch_discount": batch_discount,
        "chat_input_tokens_est": chat_input,
        "chat_output_tokens_est": chat_output,
        "embedding_input_tokens_est": embedding_input,
        "chat_cost_usd_est": chat_cost,
        "embedding_cost_usd_est": embedding_cost,
        "total_cost_usd_est": chat_cost + embedding_cost,
    }
