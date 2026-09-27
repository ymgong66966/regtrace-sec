# Jev Typed Decision Gate

Split path: `data/sec_visible_evidence_benchmark_v2/splits/grouped_random_dev48_gap/fold_0/test.jsonl`.
Model: `jev-latest`.
Endpoint: `https://thejevai.com/v1/systemone`.
Rows evaluated: 139 predictions, 0 errors.

| Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 | Unresolved Precision | Unresolved Recall |
|---:|---:|---:|---:|---:|---:|
| 0.799 | 0.722 | 0.576 | 0.868 | 0.793 | 0.958 |

Usage: `{"input_tokens": 284402, "output_tokens": 5074, "requests": 139}`.

Jev returns typed decisions rather than generated rationales, making it a candidate high-throughput triage gate.
