# FDA Contrastive RegTrace Benchmark v1

This is a minimal third-domain benchmark for RegTrace. It reshapes FDA warning-letter data into a warning-to-closeout trace-verification task because public company response letters are nearly absent.

## Summary

- Examples: 800
- Warning groups: 400
- Split sizes: `{"train": 480, "dev": 160, "test": 160}`
- Label counts: `{"mismatched": 400, "matched": 400}`

## Task

matched iff the candidate closeout letter is the actual linked FDA closeout for the warning letter; mismatched iff it is a wrong closeout letter sampled as a hard negative.

At test time, a reviewer sees only the warning text, candidate closeout text, and high-level FDA metadata. The true closeout URL and feedback fields are hidden.
