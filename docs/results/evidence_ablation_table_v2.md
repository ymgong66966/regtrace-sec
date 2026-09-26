# Benchmark v2 Evidence Ablation

| Input condition | Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 | Unresolved Recall |
|---|---:|---:|---:|---:|---:|
| SEC comment + company response | 0.712 | 0.575 | 0.333 | 0.817 | 0.927 |
| + raw amended-filing snippets | 0.784 | 0.748 | 0.651 | 0.844 | 0.844 |
| + adjudicated evidence summary (oracle upper bound) | 0.964 | 0.956 | 0.938 | 0.975 | 1.000 |

Paper framing:

- Response-only models over-trust company revision claims.
- Raw amended-filing snippets provide a large non-oracle gain, showing that partial observability was a real bottleneck.
- The adjudicated evidence-summary condition is not a deployable baseline; it is an upper bound that validates the label/feedback layer used for prompt optimization and analysis.